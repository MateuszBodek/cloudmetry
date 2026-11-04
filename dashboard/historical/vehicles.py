import pandas as pd
import streamlit as st

from dashboard.ui import format_value, metric_group


def _render_vehicle_card(vehicle_id: str, drives: pd.DataFrame, index: int) -> None:
    vehicle_drives = drives[drives["vehicle_id"].astype(str) == vehicle_id]
    last_active = (
        vehicle_drives["start_timestamp"].max()
        if "start_timestamp" in vehicle_drives
        else None
    )
    total_distance = (
        pd.to_numeric(vehicle_drives["total_distance_km"], errors="coerce").sum()
        if "total_distance_km" in vehicle_drives
        else None
    )
    with st.container(border=True):
        st.subheader(f"🚘 {vehicle_id}")
        metric_group(
            [
                ("Przejazdy", len(vehicle_drives), "", ""),
                ("Dystans łączny", total_distance, "km", ""),
                ("Ostatnia aktywność", last_active, "", ""),
            ]
        )
        if "oil_pressure_health_status" in vehicle_drives:
            latest = vehicle_drives.sort_values(
                "start_timestamp", na_position="first"
            ).iloc[-1]
            st.caption(
                "Stan pojazdu · "
                + format_value(latest["oil_pressure_health_status"], digits=0)
            )
        if st.button(
            "Wybierz pojazd",
            key=f"select_vehicle_{index}",
            type="primary",
            width="stretch",
        ):
            st.session_state["selected_vehicle_id"] = vehicle_id
            st.session_state["section_nav"] = "Podsumowanie pojazdu"
            st.session_state["workspace_mode"] = "Analiza Historyczna"
            st.rerun()


def render_vehicle_landing(drives: pd.DataFrame) -> None:
    st.title("Moje Pojazdy")
    st.caption("Flota i szybki podgląd aktywności z warstwy Gold.")
    if drives.empty or "vehicle_id" not in drives:
        st.warning("Nie znaleziono pojazdów w tabeli fct_drive_summary.")
        return
    vehicle_ids = sorted(drives["vehicle_id"].dropna().astype(str).unique())
    for index, vehicle_id in enumerate(vehicle_ids):
        _render_vehicle_card(vehicle_id, drives, index)
