import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.ui import chart_info, field_table, line_chart


def render_fuel_tab(row: pd.Series, telemetry: pd.DataFrame) -> None:
    field_table(
        row,
        [
            "consumption_band",
            "driving_style_category",
            "afr_tuning_health_band",
            "total_fuel_consumed_l",
            "total_fuel_consumed_g",
            "avg_fuel_consumption_l_100km",
            "avg_fuel_flow_lph",
            "max_fuel_flow_lph",
            "max_fuel_flow_gps",
            "dfco_duration_seconds",
            "dfco_time_pct",
            "max_injector_duty_cycle_pct",
            "max_injector_pulse_width_ms",
            "avg_ve_pct",
            "wot_avg_ve_pct",
            "avg_afr",
            "wot_avg_afr",
            "avg_lambda",
            "wot_min_lambda",
            "avg_afr_error",
            "wot_avg_afr_error",
            "wot_max_lean_spike_afr_error",
            "avg_ego_cor1_pct",
            "avg_stft_bank1_pct",
            "avg_ltft_bank1_pct",
            "max_tps_ae_change",
        ],
        "Paliwo, strojenie, wtryskiwacze i sonda lambda",
    )
    if {"afr", "fuel_target_afr"}.issubset(telemetry):
        line_chart(telemetry, ["afr", "fuel_target_afr"], "AFR rzeczywiste i docelowe")
    elif {"lambda", "fuel_target_lambda"}.issubset(telemetry):
        line_chart(
            telemetry, ["lambda", "fuel_target_lambda"], "Lambda rzeczywista i docelowa"
        )
    else:
        chart_info("Brak sygnału AFR/lambda lub wartości docelowej.")
    line_chart(
        telemetry,
        ["ego_cor1", "stft_bank_1"],
        "Korekta EGO i STFT bank 1 (%)",
    )
    color_field = next(
        (field for field in ("afr_error", "fuel_ve") if field in telemetry), None
    )
    if {"rpm", "map_kpa"}.issubset(telemetry.columns) and color_field:
        figure = px.scatter(
            telemetry,
            x="rpm",
            y="map_kpa",
            color=color_field,
            title="Mapa strojenia · RPM / MAP",
            labels={
                "rpm": "RPM",
                "map_kpa": "MAP (kPa)",
                color_field: "Błąd AFR" if color_field == "afr_error" else "VE (%)",
            },
        )
        st.plotly_chart(figure, width="stretch")
    else:
        chart_info("Brak RPM, MAP lub AFR error / VE do mapy strojenia.")
