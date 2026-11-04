import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.analytics import acceleration_record
from dashboard.ui import (
    chart_info,
    format_drive_duration,
    format_value,
    metric_group,
    render_route_map,
    row_value,
)


def render_main_tab(
    row: pd.Series, telemetry: pd.DataFrame, route: pd.DataFrame
) -> None:
    metric_group(
        [
            ("Dystans", row_value(row, "total_distance_km"), "km", ""),
            (
                "Czas",
                format_drive_duration(row_value(row, "duration_seconds")),
                "",
                "",
            ),
            (
                "Spalanie",
                row_value(row, "avg_fuel_consumption_l_100km"),
                "L/100km",
                "",
            ),
            ("Maks. prędkość", row_value(row, "max_effective_speed_kmh"), "km/h", ""),
            ("Maks. RPM", row_value(row, "max_rpm"), "RPM", ""),
        ]
    )
    metric_group(
        [
            ("Maks. boost", row_value(row, "max_boost_gauge_kpa"), "kPa", ""),
            ("Przyspieszenie IMU", row_value(row, "max_longitudinal_accel_g"), "G", ""),
            ("Hamowanie IMU", row_value(row, "max_longitudinal_braking_g"), "G", ""),
            ("Boczne IMU", row_value(row, "max_lateral_g"), "G", ""),
            ("Łączne G z IMU", row_value(row, "max_combined_g_force"), "G", ""),
        ]
    )
    samples = (
        telemetry[["elapsed_drive_time_s", "effective_speed_kmh"]].dropna()
        if {"elapsed_drive_time_s", "effective_speed_kmh"}.issubset(telemetry.columns)
        else pd.DataFrame()
    )
    record = acceleration_record(
        [
            (float(time_s), float(speed))
            for time_s, speed in samples.itertuples(index=False, name=None)
        ]
    )
    metric_group(
        [
            (
                "Rekord przyspieszenia",
                f"{record[0]}   w   {record[1]:.2f} s" if record else None,
                "",
                "",
            ),
            (
                "Spalone paliwo",
                format_value(row_value(row, "total_fuel_consumed_l"), "L", digits=2),
                "",
                "",
            ),
        ]
    )

    color_options = {"Prędkość (km/h)": "effective_speed_kmh"}
    if "combined_g_force" in route and route["combined_g_force"].notna().any():
        color_options["Łączne przeciążenie (G)"] = "combined_g_force"
    color_label = st.selectbox(
        "Kolor punktów GPS",
        options=list(color_options),
        key=f"drive_route_color_by_{row_value(row, 'drive_id')}",
    )
    color_by = color_options[color_label]
    render_route_map(
        route,
        title=f"Trasa przejazdu GPS · kolor punktów: {color_label.lower()}",
        height=430,
        color_by=color_by,
    )

    signals = (
        ("effective_speed_kmh", "Prędkość efektywna (km/h)"),
        ("rpm", "RPM"),
        ("tps", "TPS (%)"),
        ("map_kpa", "MAP (kPa)"),
        ("imu_longitudinal_accel_g", "Przyspieszenie wzdłużne (G)"),
    )
    present = [(field, label) for field, label in signals if field in telemetry]
    if "elapsed_drive_time_s" not in telemetry or not present:
        chart_info()
        return
    figure = make_subplots(
        rows=len(present),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        subplot_titles=[label for _, label in present],
    )
    for row_index, (field, label) in enumerate(present, start=1):
        figure.add_trace(
            go.Scatter(
                x=telemetry["elapsed_drive_time_s"],
                y=telemetry[field],
                name=label,
                mode="lines",
                connectgaps=False,
            ),
            row=row_index,
            col=1,
        )
    figure.update_xaxes(title_text="Czas przejazdu (s)", row=len(present), col=1)
    figure.update_layout(
        title="Przebieg telemetryczny",
        height=210 * len(present),
        showlegend=False,
        hovermode="x",
    )
    st.plotly_chart(figure, width="stretch")
