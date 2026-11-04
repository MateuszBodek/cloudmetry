from __future__ import annotations

from urllib.parse import urlparse

import duckdb
import pandas as pd
import streamlit as st

from processing_worker.src.config import Settings, create_duckdb_connection


@st.cache_resource(show_spinner="Łączenie z lakehouse…")
def get_connection() -> duckdb.DuckDBPyConnection:
    settings = Settings()
    connection = create_duckdb_connection(settings)
    connection.execute("INSTALL delta")
    connection.execute("LOAD delta")
    endpoint = urlparse(settings.endpoint)
    connection.execute(
        "CREATE OR REPLACE SECRET cloudmetry_dashboard_s3 "
        "(TYPE S3, KEY_ID ?, SECRET ?, REGION ?, ENDPOINT ?, "
        "URL_STYLE 'path', USE_SSL ?)",
        [
            settings.access_key,
            settings.secret_key,
            settings.region,
            endpoint.netloc,
            endpoint.scheme == "https",
        ],
    )
    return connection


@st.cache_data(show_spinner="Pobieranie podsumowań przejazdów…", ttl=300)
def load_drive_summaries() -> pd.DataFrame:
    settings = Settings()
    query = """
        SELECT
            f.*,
            dm.drive_date,
            dm.start_timestamp,
            dm.time_of_day_bucket,
            dm.trip_duration_category,
            dm.speed_telemetry_mode,
            df.consumption_band,
            df.driving_style_category,
            df.afr_tuning_health_band,
            dw.boost_weather_class,
            dw.ambient_temp_band,
            dw.baro_pressure_band,
            dw.precipitation_status,
            dw.wind_intensity_band,
            dt.warmup_driving_style_category,
            dt.thermal_completion_status,
            dt.intake_heat_soak_regime,
            dt.oil_pressure_health_status
        FROM delta_scan(?) AS f
        LEFT JOIN delta_scan(?) AS dm USING (vehicle_id, drive_id)
        LEFT JOIN delta_scan(?) AS df USING (vehicle_id, drive_id)
        LEFT JOIN delta_scan(?) AS dt USING (vehicle_id, drive_id)
        LEFT JOIN delta_scan(?) AS dw USING (vehicle_id, drive_id)
    """
    return (
        get_connection()
        .execute(
            query,
            [
                settings.gold_drive_summary_table,
                settings.gold_dim_drive_meta_table,
                settings.gold_dim_fuel_profile_table,
                settings.gold_dim_thermal_profile_table,
                settings.gold_dim_weather_conditions_table,
            ],
        )
        .fetchdf()
    )


@st.cache_data(show_spinner="Pobieranie danych telemetrycznych…", ttl=300)
def load_vehicle_telemetry(vehicle_id: str) -> pd.DataFrame:
    uri = Settings().gold_table
    query = """
        SELECT drive_id, elapsed_drive_time_s, effective_speed_kmh
        FROM delta_scan(?)
        WHERE vehicle_id = ?
        ORDER BY drive_id, elapsed_drive_time_s
    """
    return get_connection().execute(query, [uri, vehicle_id]).fetchdf()


@st.cache_data(show_spinner="Pobieranie szczegółów przejazdu…", ttl=300)
def load_drive_telemetry(vehicle_id: str, drive_id: str) -> pd.DataFrame:
    uri = Settings().gold_table
    query = """
        SELECT *
        FROM delta_scan(?)
        WHERE vehicle_id = ? AND drive_id = ?
        ORDER BY elapsed_drive_time_s, source_time_s
    """
    return get_connection().execute(query, [uri, vehicle_id, drive_id]).fetchdf()


@st.cache_data(show_spinner="Pobieranie trasy przejazdu…", ttl=300)
def load_drive_route(vehicle_id: str, drive_id: str) -> pd.DataFrame:
    uri = Settings().gold_table
    query = """
        SELECT
            elapsed_drive_time_s,
            latitude,
            longitude,
            effective_speed_kmh,
            combined_g_force
        FROM delta_scan(?)
        WHERE vehicle_id = ? AND drive_id = ?
          AND latitude BETWEEN -90 AND 90
          AND longitude BETWEEN -180 AND 180
        ORDER BY elapsed_drive_time_s, source_time_s
    """
    return get_connection().execute(query, [uri, vehicle_id, drive_id]).fetchdf()


@st.cache_data(show_spinner="Wczytywanie słownika kodów…", ttl=300)
def load_error_codes() -> pd.DataFrame:
    uri = Settings().gold_dim_rusefi_error_code_table
    return get_connection().execute("SELECT * FROM delta_scan(?)", [uri]).fetchdf()
