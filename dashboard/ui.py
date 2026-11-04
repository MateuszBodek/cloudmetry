from __future__ import annotations

from collections.abc import Iterable
from numbers import Real
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.analytics import (
    acceleration_records,
    format_drive_duration,
)

FIELD_LABELS = {
    "drive_date": "Data przejazdu",
    "time_of_day_bucket": "Pora dnia",
    "trip_duration_category": "Kategoria czasu",
    "is_repark_or_micro_trip_flag": "Krótkie przeparkowanie",
    "speed_telemetry_mode": "Źródło prędkości",
    "ecu_speed_coverage_pct": "Pokrycie prędkością ECU (%)",
    "gps_speed_coverage_pct": "Pokrycie prędkością GPS (%)",
    "gear_shifts_count": "Zmiany biegów",
    "highest_detected_gear": "Najwyższy bieg",
    "max_drpm_per_s": "Maks. tempo wzrostu RPM (RPM/s)",
    "wot_time_pct": "Czas WOT (%)",
    "wot_duration_seconds": "Czas WOT (s)",
    "max_wheel_slip_delta_kmh": "Maks. poślizg kół (km/h)",
    "wheel_slip_events_count": "Zdarzenia poślizgu kół",
    "consumption_band": "Przedział spalania",
    "driving_style_category": "Styl jazdy",
    "afr_tuning_health_band": "Kondycja strojenia AFR",
    "total_fuel_consumed_l": "Zużyte paliwo (L)",
    "total_fuel_consumed_g": "Zużyte paliwo (g)",
    "avg_fuel_consumption_l_100km": "Średnie spalanie (L/100km)",
    "avg_fuel_flow_lph": "Średni przepływ paliwa (L/h)",
    "max_fuel_flow_lph": "Maks. przepływ paliwa (L/h)",
    "max_fuel_flow_gps": "Maks. przepływ paliwa (g/s)",
    "dfco_duration_seconds": "Czas DFCO (s)",
    "dfco_time_pct": "Udział DFCO (%)",
    "max_injector_duty_cycle_pct": "Maks. wypełnienie wtrysku (%)",
    "max_injector_pulse_width_ms": "Maks. czas wtrysku (ms)",
    "avg_ve_pct": "Średnia VE (%)",
    "wot_avg_ve_pct": "Średnia VE przy WOT (%)",
    "avg_afr": "Średnie AFR",
    "wot_avg_afr": "Średnie AFR przy WOT",
    "avg_lambda": "Średnia lambda",
    "wot_min_lambda": "Min. lambda przy WOT",
    "avg_afr_error": "Średni błąd AFR",
    "wot_avg_afr_error": "Średni błąd AFR przy WOT",
    "wot_max_lean_spike_afr_error": "Maks. ubogi skok AFR przy WOT",
    "avg_ego_cor1_pct": "Średnia korekta EGO (%)",
    "avg_stft_bank1_pct": "Średnia STFT bank 1 (%)",
    "avg_ltft_bank1_pct": "Średnia LTFT bank 1 (%)",
    "max_tps_ae_change": "Maks. zmiana TPS AE",
    "warmup_driving_style_category": "Styl rozgrzewania",
    "thermal_completion_status": "Stan rozgrzania",
    "intake_heat_soak_regime": "Nagrzanie dolotu",
    "oil_pressure_health_status": "Stan ciśnienia oleju",
    "start_clt_c": "CLT na starcie (°C)",
    "max_clt_c": "Maks. CLT (°C)",
    "avg_hot_clt_c": "Średnia CLT na ciepło (°C)",
    "time_to_clt_85c_s": "Czas do CLT 85°C (s)",
    "distance_to_clt_85c_km": "Dystans do CLT 85°C (km)",
    "start_oil_temp_c": "Temp. oleju na starcie (°C)",
    "max_oil_temp_c": "Maks. temp. oleju (°C)",
    "avg_hot_oil_temp_c": "Średnia temp. oleju na ciepło (°C)",
    "time_to_oil_82c_s": "Czas do oleju 82°C (s)",
    "distance_to_oil_82c_km": "Dystans do oleju 82°C (km)",
    "warmup_traffic_or_idle_time_pct": "Postój / ruch podczas rozgrzewania (%)",
    "warmup_cruise_time_pct": "Spokojna jazda podczas rozgrzewania (%)",
    "warmup_high_load_time_pct": "Wysokie obciążenie na zimno (%)",
    "warmup_avg_rpm": "Średnie RPM podczas rozgrzewania",
    "warmup_max_rpm": "Maks. RPM podczas rozgrzewania",
    "cold_engine_abuse_samples_count": "Próbki wysokiego obciążenia na zimno",
    "min_hot_idle_oil_pressure_bar": (
        "Min. ciśnienie oleju na ciepłym biegu jałowym (bar)"
    ),
    "min_hot_oil_pressure_bar": "Min. ciśnienie oleju na ciepło (bar)",
    "min_hot_load_oil_pressure_bar": "Min. ciśnienie oleju pod obciążeniem (bar)",
    "min_oil_pressure_per_1k_rpm_bar": "Min. ciśnienie na 1000 RPM (bar)",
    "min_oil_pressure_safety_margin_bar": "Min. margines bezpieczeństwa oleju (bar)",
    "low_oil_pressure_duration_s": "Czas niskiego ciśnienia oleju (s)",
    "oil_starvation_in_cornering_samples_count": "Próbki niedoboru oleju w zakręcie",
    "boost_weather_class": "Klasa warunków doładowania",
    "ambient_temp_band": "Przedział temp. otoczenia",
    "baro_pressure_band": "Przedział ciśnienia atmosferycznego",
    "precipitation_status": "Opady",
    "wind_intensity_band": "Intensywność wiatru",
    "ambient_air_density_kg_m3": "Gęstość powietrza otoczenia (kg/m³)",
    "wot_manifold_charge_density_kg_m3": (
        "Gęstość ładunku w kolektorze przy WOT (kg/m³)"
    ),
    "wot_effective_charge_density_kg_m3": (
        "Efektywna gęstość ładunku przy WOT (kg/m³)"
    ),
    "sae_correction_factor": "Współczynnik korekcji SAE",
    "wot_accel_index_g_per_bar": "Indeks przyspieszenia WOT z IMU (G/bar)",
    "wot_imu_accel_index_g_per_bar": "Indeks IMU WOT (G/bar)",
    "wot_sae_corrected_accel_index": "Indeks WOT skorygowany SAE",
    "wot_boost_weather_efficiency_score": "Efektywność doładowania / pogody",
    "intercooler_heat_soak_avg_c": "Śr. nagrzanie intercoolera (°C)",
    "intercooler_heat_soak_max_c": "Maks. nagrzanie intercoolera (°C)",
    "mat_thermal_rise_c": "Wzrost temp. MAT (°C)",
    "max_charge_temp_est_c": "Maks. estymowana temp. ładunku (°C)",
    "max_map_kpa": "Maks. MAP (kPa)",
    "max_boost_gauge_kpa": "Maks. doładowanie względne (kPa)",
    "wot_avg_boost_error_kpa": "Śr. błąd doładowania WOT (kPa)",
    "max_boost_overshoot_kpa": "Maks. przestrzał doładowania (kPa)",
    "max_boost_output_pct": "Maks. wyjście sterowania boostem (%)",
    "max_wastegate_pos_pct": "Maks. pozycja wastegate (%)",
    "total_warnings_delta": "Nowe ostrzeżenia",
    "trigger_errors_delta": "Błędy triggera",
    "total_spark_cuts_delta": "Odcięcia iskry",
    "total_fuel_cuts_delta": "Odcięcia paliwa",
    "rev_limit_events_count": "Zdarzenia ogranicznika RPM",
    "rev_limit_active_duration_s": "Czas aktywnego ogranicznika (s)",
    "check_engine_triggered_flag": "Check Engine",
    "analog_supply_failure_flag": "Błąd zasilania analogowego",
    "min_batt_v": "Min. napięcie akumulatora (V)",
    "avg_batt_v": "Śr. napięcie akumulatora (V)",
    "max_batt_v": "Maks. napięcie akumulatora (V)",
    "max_ecu_cpu_temp_c": "Maks. temp. CPU ECU (°C)",
    "max_cpu_usage_pct": "Maks. użycie CPU (%)",
    "avg_ignition_timing_deg": "Średni kąt zapłonu (deg)",
    "wot_avg_ignition_timing_deg": "Średni kąt zapłonu WOT (deg)",
    "wot_min_ignition_timing_deg": "Min. kąt zapłonu WOT (deg)",
    "avg_dynamic_timing_trim_deg": "Śr. dynamiczna korekta zapłonu (deg)",
    "wot_avg_dynamic_timing_trim_deg": "Śr. korekta zapłonu WOT (deg)",
    "avg_coil_charge_time_ms": "Śr. czas ładowania cewki (ms)",
    "max_coil_charge_time_ms": "Maks. czas ładowania cewki (ms)",
    "max_coil_duty_cycle_pct": "Maks. wypełnienie cewki (%)",
    "avg_dwell_deviation_ms": "Śr. odchylenie dwell (ms)",
    "max_abs_dwell_deviation_ms": "Maks. bezwzględne odchylenie dwell (ms)",
    "overcharge_canceled_delta": "Anulowane przeładowania cewki",
    "overdwell_not_scheduled_delta": "Niezaplanowane overdwell",
    "ignition_undercharge_warnings_delta": "Ostrzeżenia o niedoładowaniu",
    "ignition_overcharge_warnings_delta": "Ostrzeżenia o przeładowaniu",
    "knock_events_delta_count": "Zdarzenia spalania stukowego",
    "max_knock_retard_deg": "Maks. korekta knock (deg)",
    "avg_active_knock_retard_deg": "Śr. aktywna korekta knock (deg)",
    "max_knock_level_dbv": "Maks. poziom knock (dBV)",
}


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def format_value(value: Any, unit: str = "", digits: int | None = 2) -> str:
    if is_missing(value):
        return "Brak danych"
    if isinstance(value, bool):
        return "Tak" if value else "Nie"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "Brak danych"
    if isinstance(value, Real):
        formatted = f"{value:,}" if digits is None else f"{value:,.{digits}f}"
        return f"{formatted}{f' {unit}' if unit else ''}"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def row_value(row: pd.Series, column: str, default: Any = None) -> Any:
    return row[column] if column in row.index else default


def metric_group(metrics: Iterable[tuple[str, Any, str, str]]) -> None:
    metrics = list(metrics)
    if not metrics:
        return
    columns = st.columns(min(len(metrics), 5))
    for index, (label, value, unit, help_text) in enumerate(metrics):
        columns[index % len(columns)].metric(
            label, format_value(value, unit), help=help_text or None
        )


def field_table(row: pd.Series, fields: Iterable[str], title: str) -> None:
    available = [field for field in fields if field in row.index]
    if not available:
        return
    st.markdown(f"**{title}**")
    table = pd.DataFrame(
        {
            "Metryka": [
                FIELD_LABELS.get(field, field.replace("_", " ")) for field in available
            ],
            "Wartość": [
                format_value(
                    row[field],
                    digits=(
                        4
                        if field == "wot_imu_accel_index_g_per_bar"
                        else None
                        if field == "total_fuel_consumed_l"
                        else 2
                    ),
                )
                for field in available
            ],
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")


def chart_info(message: str = "Brak danych telemetrycznych dla tego wykresu.") -> None:
    st.info(message)


def route_figure(
    route: pd.DataFrame,
    *,
    title: str,
    height: int,
    color_by: str = "effective_speed_kmh",
) -> go.Figure | None:
    if not {"latitude", "longitude"}.issubset(route.columns):
        return None
    route = route.dropna(subset=["latitude", "longitude"]).copy()
    route = route[
        route["latitude"].between(-90, 90) & route["longitude"].between(-180, 180)
    ]
    if "elapsed_drive_time_s" in route:
        route = route.sort_values("elapsed_drive_time_s", kind="stable")
    if route.empty:
        return None
    if len(route) > 2500:
        step = max(1, len(route) // 2500)
        route = route.iloc[::step].copy()

    marker_route = route
    figure = go.Figure()
    figure.add_trace(
        go.Scattermap(
            lon=route["longitude"],
            lat=route["latitude"],
            mode="lines",
            name="Trasa",
            line={"color": "#00d4ff", "width": 4},
            hoverinfo="skip",
        )
    )
    marker = {"size": 7, "color": "#00d4ff"}
    colorbar_title = {
        "effective_speed_kmh": "km/h",
        "combined_g_force": "G",
    }.get(color_by, "")
    if color_by in marker_route:
        marker = {
            "size": 7,
            "color": marker_route[color_by],
            "colorscale": "Turbo",
            "showscale": height > 300,
            "colorbar": {"title": colorbar_title},
        }
    custom_data = [
        column
        for column in dict.fromkeys(
            ("elapsed_drive_time_s", "effective_speed_kmh", color_by)
        )
        if column in marker_route
    ]
    hover_details = []
    if "elapsed_drive_time_s" in custom_data:
        hover_details.append("Czas: %{customdata[0]:.1f} s")
    if "effective_speed_kmh" in custom_data:
        speed_index = custom_data.index("effective_speed_kmh")
        hover_details.append(f"Prędkość: %{{customdata[{speed_index}]:.1f}} km/h")
    if color_by == "combined_g_force" and color_by in custom_data:
        g_force_index = custom_data.index(color_by)
        hover_details.append(f"Łączne G: %{{customdata[{g_force_index}]:.3f}} G")
    figure.add_trace(
        go.Scattermap(
            lon=marker_route["longitude"],
            lat=marker_route["latitude"],
            mode="markers",
            name="Punkty GPS",
            marker=marker,
            customdata=(marker_route[custom_data].to_numpy() if custom_data else None),
            hovertemplate=(
                "Lon: %{lon:.5f}<br>Lat: %{lat:.5f}"
                + ("<br>" + "<br>".join(hover_details) if hover_details else "")
                + "<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title=title,
        height=height,
        margin={"l": 8, "r": 8, "t": 42, "b": 8},
        showlegend=False,
        map={"style": "carto-darkmatter", "fitbounds": "locations"},
    )
    return figure


def render_route_map(
    route: pd.DataFrame,
    *,
    title: str,
    height: int,
    color_by: str = "effective_speed_kmh",
) -> None:
    figure = route_figure(route, title=title, height=height, color_by=color_by)
    if figure is None:
        chart_info("Brak współrzędnych GPS dla tego przejazdu.")
        return
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def line_chart(
    data: pd.DataFrame,
    columns: Iterable[str],
    title: str,
    *,
    x: str = "elapsed_drive_time_s",
    x_title: str = "Czas przejazdu (s)",
) -> None:
    series = [column for column in columns if column in data.columns]
    if x not in data.columns or not series:
        chart_info()
        return
    chart_data = data[[x, *series]].dropna(how="all", subset=series)
    if chart_data.empty:
        chart_info()
        return
    figure = px.line(
        chart_data,
        x=x,
        y=series,
        title=title,
        labels={x: x_title},
    )
    figure.update_layout(legend_title_text="Sygnał", hovermode="x unified")
    st.plotly_chart(figure, width="stretch")


def drive_label(drive_id: str, drives_by_id: dict[str, pd.Series]) -> str:
    row = drives_by_id[drive_id]
    date = format_value(row_value(row, "start_timestamp"), digits=0)
    duration = format_drive_duration(row_value(row, "duration_seconds"))
    distance = format_value(row_value(row, "total_distance_km"), "km", 1)
    style = format_value(row_value(row, "driving_style_category"), digits=0)
    weather = format_value(row_value(row, "boost_weather_class"), digits=0)
    warnings = format_value(row_value(row, "total_warnings_delta"), digits=0)
    return (
        f"{date} · {duration} · {distance} · {style} · {weather} · "
        f"ostrzeżenia: {warnings} · {drive_id}"
    )


def codes_for_drive(row: pd.Series, code_table: pd.DataFrame) -> pd.DataFrame:
    codes: set[int] = set()
    listed = row_value(row, "error_codes", [])
    if isinstance(listed, (list, tuple, set)):
        for code in listed:
            if not is_missing(code):
                codes.add(int(code))
    key_fields = (
        "first_warning_code_key",
        "last_warning_code_key",
        "stop_engine_code_key",
        "dominant_ign_cut_key",
        "dominant_fuel_cut_key",
    )
    for field in key_fields:
        value = row_value(row, field)
        if not is_missing(value) and int(value) not in (0, 999):
            codes.add(int(value))
    if not codes:
        return pd.DataFrame(
            columns=[
                "raw_code_id",
                "code_category",
                "code_name",
                "code_description_pl",
                "severity_level",
                "first_warning_timestamp",
            ]
        )
    if "raw_code_id" not in code_table.columns:
        return pd.DataFrame({"raw_code_id": sorted(codes)})
    decoded = code_table[code_table["raw_code_id"].isin(codes)].copy()
    missing_codes = codes.difference(
        int(code) for code in decoded["raw_code_id"].dropna().tolist()
    )
    if missing_codes:
        decoded = pd.concat(
            [
                decoded,
                pd.DataFrame({"raw_code_id": sorted(missing_codes)}),
            ],
            ignore_index=True,
        )
    decoded = decoded.drop_duplicates(subset=["raw_code_id"])
    decoded["first_warning_timestamp"] = None
    warning_code = row_value(row, "first_warning_code_key")
    if not is_missing(warning_code) and "first_warning_timestamp" in row.index:
        decoded.loc[
            decoded["raw_code_id"] == int(warning_code), "first_warning_timestamp"
        ] = row["first_warning_timestamp"]
    return decoded


def record_across_drives(
    telemetry: pd.DataFrame, allowed_drive_ids: set[str]
) -> tuple[str, float] | None:
    records = records_across_drives(telemetry, allowed_drive_ids)
    for label in ("0–100 km/h", "0–60 km/h", "30–80 km/h"):
        if label in records:
            return label, records[label]
    return None


def records_across_drives(
    telemetry: pd.DataFrame, allowed_drive_ids: set[str]
) -> dict[str, float]:
    if telemetry.empty or not {
        "drive_id",
        "elapsed_drive_time_s",
        "effective_speed_kmh",
    }.issubset(telemetry.columns):
        return {}
    records: dict[str, list[float]] = {}
    for drive_id, samples in telemetry.groupby("drive_id", sort=False):
        if str(drive_id) not in allowed_drive_ids:
            continue
        samples = samples[["elapsed_drive_time_s", "effective_speed_kmh"]].dropna()
        drive_records = acceleration_records(
            [
                (float(time_s), float(speed))
                for time_s, speed in samples.itertuples(index=False, name=None)
            ]
        )
        for label, seconds in drive_records.items():
            records.setdefault(label, []).append(seconds)
    return {label: min(values) for label, values in records.items()}


def navigate_to_drive(drive_id: str) -> None:
    st.session_state["selected_drive_id"] = drive_id
    st.session_state["section_nav"] = "Moje Przejazdy"


def navigate_to_drive_list() -> None:
    st.session_state["section_nav"] = "Moje Przejazdy"
