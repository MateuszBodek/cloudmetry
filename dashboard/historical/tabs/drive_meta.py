import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.ui import chart_info, field_table, line_chart


def render_drive_meta_tab(row: pd.Series, telemetry: pd.DataFrame) -> None:
    field_table(
        row,
        [
            "drive_date",
            "time_of_day_bucket",
            "trip_duration_category",
            "is_repark_or_micro_trip_flag",
            "speed_telemetry_mode",
            "ecu_speed_coverage_pct",
            "gps_speed_coverage_pct",
            "gear_shifts_count",
            "highest_detected_gear",
            "max_drpm_per_s",
            "wot_time_pct",
            "wot_duration_seconds",
            "max_wheel_slip_delta_kmh",
            "wheel_slip_events_count",
        ],
        "Kontekst przejazdu i dynamika",
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if {"imu_lateral_accel_g", "imu_longitudinal_accel_g"}.issubset(telemetry):
            figure = px.scatter(
                telemetry,
                x="imu_lateral_accel_g",
                y="imu_longitudinal_accel_g",
                color="effective_speed_kmh"
                if "effective_speed_kmh" in telemetry
                else None,
                title="Diagram G-G · tarcie i dynamika",
                labels={
                    "imu_lateral_accel_g": "Przyspieszenie boczne (G)",
                    "imu_longitudinal_accel_g": "Przyspieszenie wzdłużne (G)",
                    "effective_speed_kmh": "Prędkość (km/h)",
                },
            )
            st.plotly_chart(figure, width="stretch")
        else:
            chart_info()
    with col_b:
        speed_fields = ["gps_speed_kmh", "vehicle_speed_kph"]
        if any(field in telemetry for field in speed_fields):
            line_chart(telemetry, speed_fields, "Prędkość ECU a GPS")
        else:
            chart_info()
        if "detected_gear" in telemetry:
            gear = telemetry.dropna(subset=["detected_gear"])
            if not gear.empty:
                figure = px.histogram(
                    gear,
                    x="detected_gear",
                    title="Rozkład wykrytych biegów",
                    labels={"detected_gear": "Bieg"},
                    nbins=8,
                )
                st.plotly_chart(figure, width="stretch")
