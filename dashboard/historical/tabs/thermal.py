import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.ui import chart_info, field_table, is_missing, row_value


def render_thermal_tab(row: pd.Series, telemetry: pd.DataFrame) -> None:
    field_table(
        row,
        [
            "warmup_driving_style_category",
            "thermal_completion_status",
            "intake_heat_soak_regime",
            "oil_pressure_health_status",
            "start_clt_c",
            "max_clt_c",
            "avg_hot_clt_c",
            "time_to_clt_85c_s",
            "distance_to_clt_85c_km",
            "start_oil_temp_c",
            "max_oil_temp_c",
            "avg_hot_oil_temp_c",
            "time_to_oil_82c_s",
            "distance_to_oil_82c_km",
            "warmup_traffic_or_idle_time_pct",
            "warmup_cruise_time_pct",
            "warmup_high_load_time_pct",
            "warmup_avg_rpm",
            "warmup_max_rpm",
            "cold_engine_abuse_samples_count",
            "min_hot_idle_oil_pressure_bar",
            "min_hot_oil_pressure_bar",
            "min_hot_load_oil_pressure_bar",
            "min_oil_pressure_per_1k_rpm_bar",
            "min_oil_pressure_safety_margin_bar",
            "low_oil_pressure_duration_s",
            "oil_starvation_in_cornering_samples_count",
        ],
        "Rozgrzewanie silnika i smarowanie",
    )
    abuse = row_value(row, "cold_engine_abuse_samples_count", 0)
    if not is_missing(abuse) and abuse > 0:
        st.warning(
            f"Wykryto {int(abuse)} próbek wysokiego obciążenia na zimnym silniku."
        )
    if "elapsed_drive_time_s" in telemetry:
        figure = go.Figure()
        for field, label in (
            ("coolant_temp", "CLT"),
            ("oil_temp", "Olej"),
            ("intake_air_temp_c", "MAT"),
        ):
            if field in telemetry:
                figure.add_trace(
                    go.Scatter(
                        x=telemetry["elapsed_drive_time_s"],
                        y=telemetry[field],
                        mode="lines",
                        name=label,
                    )
                )
        if figure.data:
            figure.add_hline(y=85, line_dash="dash", annotation_text="CLT 85°C")
            figure.add_hline(y=82, line_dash="dot", annotation_text="Olej 82°C")
            figure.update_layout(
                title="Temperatury i progi robocze",
                xaxis_title="Czas przejazdu (s)",
                yaxis_title="Temperatura (°C)",
            )
            st.plotly_chart(figure, width="stretch")
        else:
            chart_info()
    required = {
        "rpm",
        "oil_pressure_kpa",
        "min_safe_oil_pressure_target_bar",
    }
    if required.issubset(telemetry.columns):
        pressure = telemetry.dropna(
            subset=["rpm", "oil_pressure_kpa", "min_safe_oil_pressure_target_bar"]
        ).copy()
        if not pressure.empty:
            pressure["oil_pressure_bar"] = pressure["oil_pressure_kpa"] / 100
            figure = go.Figure()
            figure.add_trace(
                go.Scatter(
                    x=pressure["rpm"],
                    y=pressure["oil_pressure_bar"],
                    mode="markers",
                    name="Ciśnienie zmierzone",
                    marker={"color": "#2d9cdb", "size": 6, "opacity": 0.65},
                )
            )
            target = pressure.sort_values("rpm")
            figure.add_trace(
                go.Scatter(
                    x=target["rpm"],
                    y=target["min_safe_oil_pressure_target_bar"],
                    mode="lines",
                    name="Minimalna krzywa bezpieczeństwa",
                    line={"color": "red", "width": 3},
                )
            )
            figure.update_layout(
                title="Ciśnienie oleju względem RPM",
                xaxis_title="RPM",
                yaxis_title="Ciśnienie oleju (bar)",
            )
            st.plotly_chart(figure, width="stretch")
        else:
            chart_info()
    else:
        chart_info("Brak pomiaru ciśnienia oleju lub krzywej bezpieczeństwa RPM.")
