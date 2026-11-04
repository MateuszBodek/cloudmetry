import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.data import load_drive_route, load_vehicle_telemetry
from dashboard.ui import (
    chart_info,
    format_drive_duration,
    format_value,
    is_missing,
    metric_group,
    navigate_to_drive,
    navigate_to_drive_list,
    records_across_drives,
    render_route_map,
    row_value,
)


def render_vehicle_overview(
    vehicle_drives: pd.DataFrame,
    show_micro_trips: bool,
    vehicle_id: str,
) -> None:
    st.header("Podsumowanie Pojazdu")
    drives = vehicle_drives.copy()
    if not show_micro_trips and "is_repark_or_micro_trip_flag" in drives:
        drives = drives[~drives["is_repark_or_micro_trip_flag"].fillna(True)]
    if drives.empty:
        st.info("Brak przejazdów spełniających wybrane filtry.")
        return

    distance = (
        pd.to_numeric(drives.get("total_distance_km"), errors="coerce")
        if "total_distance_km" in drives
        else pd.Series(dtype=float)
    )
    fuel = (
        pd.to_numeric(drives.get("total_fuel_consumed_l"), errors="coerce")
        if "total_fuel_consumed_l" in drives
        else pd.Series(dtype=float)
    )
    weighted_consumption = (
        fuel.sum(min_count=1) / distance.sum(min_count=1) * 100
        if fuel.notna().any() and distance.sum(min_count=1) not in (None, 0)
        else None
    )
    total_fuel = fuel.sum(min_count=1) if fuel.notna().any() else None

    st.subheader("Dystans, czas i przejazdy")
    metric_group(
        [
            ("Liczba przejazdów", f"{len(drives):.0f}", "", ""),
            ("Całkowity dystans", distance.sum(min_count=1), "km", ""),
            ("Średni dystans przejazdu", distance.mean(), "km", ""),
            (
                "Średni czas przejazdu",
                format_drive_duration(
                    pd.to_numeric(
                        drives.get("duration_seconds"), errors="coerce"
                    ).mean()
                )
                if "duration_seconds" in drives
                else None,
                "",
                "",
            ),
        ]
    )
    max_boost_bar = (
        pd.to_numeric(drives["max_boost_gauge_kpa"], errors="coerce").max() / 100
        if "max_boost_gauge_kpa" in drives
        else None
    )
    limiter_duration = (
        pd.to_numeric(drives["rev_limit_active_duration_s"], errors="coerce").sum(
            min_count=1
        )
        if "rev_limit_active_duration_s" in drives
        else None
    )
    limiter_duration_display = (
        format_drive_duration(limiter_duration)
        if not is_missing(limiter_duration)
        else "Brak danych"
    )
    wot_imu_index = (
        pd.to_numeric(drives["wot_imu_accel_index_g_per_bar"], errors="coerce").max()
        if "wot_imu_accel_index_g_per_bar" in drives
        else None
    )
    wot_imu_index_display = (
        format_value(wot_imu_index, "G/bar", digits=4)
        if not is_missing(wot_imu_index)
        else "Brak danych"
    )

    st.subheader("Silnik")
    metric_group(
        [
            (
                "Najlepszy indeks WOT (IMU)",
                wot_imu_index_display,
                "",
                "",
            ),
            (
                "Czas limiter łącznie",
                limiter_duration_display,
                "",
                "",
            ),
            (
                "Maks. doładowanie",
                max_boost_bar,
                "bar",
                "",
            ),
            (
                "Czas WOT łącznie",
                drives["wot_duration_seconds"].sum()
                if "wot_duration_seconds" in drives
                else None,
                "s",
                "",
            ),
        ]
    )

    st.subheader("Spalanie")
    metric_group(
        [
            (
                "Średnie spalanie ważone",
                weighted_consumption,
                "L/100km",
                "Suma paliwa / suma dystansu × 100.",
            ),
            ("Zużyte paliwo", total_fuel, "L", ""),
        ]
    )

    st.subheader("Rekordy przeciążeń i czasy przyspieszenia")
    acceleration_g = (
        pd.to_numeric(drives["wot_raw_accel_max_g"], errors="coerce").max()
        if "wot_raw_accel_max_g" in drives
        else None
    )
    braking_g = (
        pd.to_numeric(drives["max_longitudinal_braking_g"], errors="coerce").max()
        if "max_longitudinal_braking_g" in drives
        else None
    )
    lateral_g = (
        pd.to_numeric(drives["max_lateral_g"], errors="coerce").max()
        if "max_lateral_g" in drives
        else None
    )
    combined_g = (
        pd.to_numeric(drives["max_combined_g_force"], errors="coerce").max()
        if "max_combined_g_force" in drives
        else None
    )

    allowed_drive_ids = set(drives["drive_id"].dropna().astype(str))
    acceleration_times = records_across_drives(
        load_vehicle_telemetry(vehicle_id), allowed_drive_ids
    )
    times_col, chart_col = st.columns(2)
    with times_col:
        st.markdown("**Najlepsze czasy przyspieszenia**")
        with st.container(key="acceleration_times"):
            for label in (
                "0–60 km/h",
                "0–100 km/h",
                "30–80 km/h",
                "100–200 km/h",
            ):
                seconds = acceleration_times.get(label)
                st.metric(
                    label,
                    f"{seconds:.2f} s" if seconds is not None else "Brak danych",
                )

    with chart_col:
        st.markdown("**Maksymalne przeciążenia**")
        if not any(
            is_missing(value) for value in (acceleration_g, braking_g, lateral_g)
        ):
            lateral_value = abs(float(lateral_g))
            brake_value = abs(float(braking_g))
            acceleration_value = abs(float(acceleration_g))
            diamond_x = [0, lateral_value, 0, -lateral_value, 0]
            diamond_y = [
                brake_value,
                0,
                -acceleration_value,
                0,
                brake_value,
            ]
            axis_extent = (
                max(
                    1.0,
                    lateral_value,
                    brake_value,
                    acceleration_value,
                )
                * 1.2
            )
            figure = go.Figure()
            figure.add_trace(
                go.Scatter(
                    x=diamond_x,
                    y=diamond_y,
                    mode="lines",
                    fill="toself",
                    fillcolor="rgba(0, 212, 255, 0.22)",
                    line={"color": "#00d4ff", "width": 2},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=diamond_x[:-1],
                    y=diamond_y[:-1],
                    mode="markers+text",
                    text=[
                        f"Hamowanie<br>{brake_value:.2f} G",
                        f"Boczne<br>{lateral_value:.2f} G",
                        f"Przyspieszenie WOT (IMU)<br>{acceleration_value:.2f} G",
                        f"Boczne<br>{lateral_value:.2f} G",
                    ],
                    textposition=[
                        "top center",
                        "middle right",
                        "bottom center",
                        "middle left",
                    ],
                    marker={"size": 9, "color": "#00d4ff"},
                    hovertemplate="X: %{x:.2f} G<br>Y: %{y:.2f} G<extra></extra>",
                    showlegend=False,
                )
            )
            combined_text = (
                f"Maks. całkowite przeciążenie: {combined_g:.2f} G"
                if not is_missing(combined_g)
                else "Maks. całkowite przeciążenie: Brak danych"
            )
            figure.add_annotation(
                text=combined_text,
                xref="paper",
                yref="paper",
                x=0.98,
                y=0.02,
                xanchor="right",
                yanchor="bottom",
                showarrow=False,
                bgcolor="rgba(24, 31, 42, .85)",
                borderpad=6,
            )
            figure.update_layout(
                xaxis={
                    "title": "Przeciążenie boczne (G)",
                    "range": [-axis_extent, axis_extent],
                    "zeroline": True,
                    "zerolinewidth": 2,
                    "zerolinecolor": "#aab4c0",
                    "scaleanchor": "y",
                    "scaleratio": 1,
                },
                yaxis={
                    "title": "Przeciążenie wzdłużne (G)",
                    "range": [-axis_extent, axis_extent],
                    "zeroline": True,
                    "zerolinewidth": 2,
                    "zerolinecolor": "#aab4c0",
                },
                height=430,
                margin={"l": 40, "r": 30, "t": 20, "b": 50},
                showlegend=False,
            )
            st.plotly_chart(figure, width="stretch")
        else:
            chart_info("Brak danych do wyznaczenia przeciążeń na wykresie.")

    latest = vehicle_drives.sort_values(
        "start_timestamp", ascending=False, na_position="last"
    ).iloc[0]
    st.subheader("Ostatni Przejazd - Szybkie Podsumowanie")
    with st.container(border=True, key="latest_drive_summary"):
        st.markdown(
            f"**{format_value(row_value(latest, 'start_timestamp'), digits=0)}** · "
            f"`{format_value(row_value(latest, 'drive_id'), digits=0)}`"
        )
        summary_col, map_col = st.columns([1.6, 1])
        with summary_col:
            metric_group(
                [
                    ("Dystans", row_value(latest, "total_distance_km"), "km", ""),
                    (
                        "Czas",
                        format_drive_duration(row_value(latest, "duration_seconds")),
                        "",
                        "",
                    ),
                    (
                        "Spalanie",
                        row_value(latest, "avg_fuel_consumption_l_100km"),
                        "L/100km",
                        "",
                    ),
                ]
            )
            metric_group(
                [
                    (
                        "Spalone paliwo",
                        format_value(
                            row_value(latest, "total_fuel_consumed_l"),
                            "L",
                            digits=2,
                        ),
                        "",
                        "",
                    ),
                    ("Maks. CLT", row_value(latest, "max_clt_c"), "°C", ""),
                    (
                        "Maks. temp. oleju",
                        row_value(latest, "max_oil_temp_c"),
                        "°C",
                        "",
                    ),
                ]
            )
            oil_status = row_value(latest, "oil_pressure_health_status")
            if not is_missing(oil_status):
                st.caption(
                    f"Stan ciśnienia oleju · {format_value(oil_status, digits=0)}"
                )
            low_oil_pressure = bool(
                row_value(latest, "low_oil_pressure_damage_risk_flag", False)
            ) or str(row_value(latest, "oil_pressure_health_status", "")).startswith(
                "CRITICAL:"
            )
            has_diagnostics = any(
                not is_missing(row_value(latest, field))
                and row_value(latest, field) > 0
                for field in (
                    "total_warnings_delta",
                    "trigger_errors_delta",
                    "total_spark_cuts_delta",
                    "total_fuel_cuts_delta",
                    "knock_events_delta_count",
                )
            )
            error_codes = row_value(latest, "error_codes", [])
            if pd.api.types.is_list_like(error_codes):
                has_diagnostics = has_diagnostics or len(error_codes) > 0
            if low_oil_pressure:
                st.error("Ryzyko niskiego ciśnienia oleju podczas przejazdu.")
            elif has_diagnostics:
                st.warning("W tym przejeździe wystąpiły błędy lub odcięcia.")

            action_col, list_col = st.columns([1.5, 1])
            action_col.button(
                "Przejdź do pełnej analizy tego przejazdu",
                key="latest_drive_detail",
                type="primary",
                on_click=navigate_to_drive,
                args=(str(latest["drive_id"]),),
            )
            list_col.button(
                "Lista wszystkich przejazdów",
                key="latest_drive_list",
                on_click=navigate_to_drive_list,
            )
        with map_col:
            latest_route = load_drive_route(vehicle_id, str(latest["drive_id"]))
            render_route_map(
                latest_route,
                title="Podgląd trasy GPS",
                height=255,
            )

    st.subheader("Wykresy Trendów Pojazdu")
    chart_col, weather_col = st.columns(2)
    with chart_col:
        if {"avg_fuel_consumption_l_100km", "start_timestamp"}.issubset(drives.columns):
            chart_data = drives.dropna(subset=["avg_fuel_consumption_l_100km"])
            if not chart_data.empty:
                figure = px.bar(
                    chart_data,
                    x="start_timestamp",
                    y="avg_fuel_consumption_l_100km",
                    color="driving_style_category"
                    if "driving_style_category" in chart_data
                    else None,
                    hover_data=["drive_id"],
                    title="Spalanie na przejazd · styl jazdy",
                    labels={
                        "start_timestamp": "Data",
                        "avg_fuel_consumption_l_100km": "L/100km",
                        "driving_style_category": "Styl jazdy",
                    },
                )
                st.plotly_chart(figure, width="stretch")
            else:
                chart_info()
        else:
            chart_info()
    with weather_col:
        required = {
            "ambient_air_density_kg_m3",
            "wot_imu_accel_index_g_per_bar",
        }
        if required.issubset(drives.columns):
            figure = px.scatter(
                drives,
                x="ambient_air_density_kg_m3",
                y="wot_imu_accel_index_g_per_bar",
                color="boost_weather_class"
                if "boost_weather_class" in drives
                else None,
                hover_data=["drive_id"],
                title="Indeks przyspieszenia WOT a gęstość powietrza",
                labels={
                    "ambient_air_density_kg_m3": "Gęstość otoczenia (kg/m³)",
                    "wot_imu_accel_index_g_per_bar": "Indeks IMU (G/bar)",
                    "boost_weather_class": "Boost weather",
                },
            )
            st.plotly_chart(figure, width="stretch")
        else:
            chart_info()
