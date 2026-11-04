import pandas as pd
import streamlit as st

from dashboard.analytics import format_drive_duration
from dashboard.data import load_drive_route, load_drive_telemetry
from dashboard.historical.tabs.diagnostics import render_diagnostics_tab
from dashboard.historical.tabs.drive_meta import render_drive_meta_tab
from dashboard.historical.tabs.fuel import render_fuel_tab
from dashboard.historical.tabs.main import render_main_tab
from dashboard.historical.tabs.thermal import render_thermal_tab
from dashboard.historical.tabs.weather import render_weather_tab
from dashboard.ui import drive_label, row_value


def render_drive_explorer(
    vehicle_drives: pd.DataFrame, code_table: pd.DataFrame
) -> None:
    st.header("Moje Przejazdy")
    if vehicle_drives.empty:
        st.info("Ten pojazd nie ma zarejestrowanych przejazdów.")
        return
    if "drive_id" not in vehicle_drives:
        st.error("Tabela fct_drive_summary nie zawiera kolumny drive_id.")
        return
    drive_table = vehicle_drives[
        [
            column
            for column in (
                "start_timestamp",
                "duration_seconds",
                "total_distance_km",
                "driving_style_category",
                "boost_weather_class",
                "total_warnings_delta",
                "trigger_errors_delta",
                "drive_id",
            )
            if column in vehicle_drives.columns
        ]
    ].sort_values("start_timestamp", ascending=False, na_position="last")
    if "duration_seconds" in drive_table:
        drive_table["duration_seconds"] = drive_table["duration_seconds"].map(
            format_drive_duration
        )
        drive_table = drive_table.rename(columns={"duration_seconds": "Czas przejazdu"})
    st.dataframe(drive_table, hide_index=True, width="stretch")

    drives_by_id = {str(row["drive_id"]): row for _, row in vehicle_drives.iterrows()}
    drive_ids = list(drives_by_id)
    selected_id = str(st.session_state.get("selected_drive_id", ""))
    if selected_id not in drives_by_id:
        selected_id = drive_ids[0]
    selected_id = st.selectbox(
        "Wybierz przejazd",
        drive_ids,
        index=drive_ids.index(selected_id),
        format_func=lambda value: drive_label(value, drives_by_id),
        key="drive_selector",
    )
    st.session_state["selected_drive_id"] = selected_id
    drive = drives_by_id[selected_id]
    vehicle_id = str(row_value(drive, "vehicle_id"))
    telemetry = load_drive_telemetry(vehicle_id, selected_id)
    route = load_drive_route(vehicle_id, selected_id)
    tabs = st.tabs(
        [
            "Przegląd Przejazdu",
            "Kontekst i Dynamika",
            "Paliwo i Strojenie",
            "Termika i Smarowanie",
            "Pogoda i Boost Weather",
            "Diagnostyka, Zapłon i Błędy",
        ]
    )
    with tabs[0]:
        render_main_tab(drive, telemetry, route)
    with tabs[1]:
        render_drive_meta_tab(drive, telemetry)
    with tabs[2]:
        render_fuel_tab(drive, telemetry)
    with tabs[3]:
        render_thermal_tab(drive, telemetry)
    with tabs[4]:
        render_weather_tab(drive, telemetry)
    with tabs[5]:
        render_diagnostics_tab(drive, telemetry, code_table)
