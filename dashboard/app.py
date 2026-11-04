from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

repository_root = str(Path(__file__).resolve().parents[1])
if repository_root not in sys.path:
    sys.path.insert(0, repository_root)

from dashboard.data import (  # noqa: E402
    load_drive_summaries,
    load_error_codes,
)
from dashboard.historical.drive_explorer import render_drive_explorer  # noqa: E402
from dashboard.historical.overview import render_vehicle_overview  # noqa: E402
from dashboard.historical.vehicles import render_vehicle_landing  # noqa: E402
from dashboard.live_view.page import render_live_view  # noqa: E402
from dashboard.ui import format_value as _format  # noqa: E402, F401
from dashboard.ui import route_figure as _route_figure  # noqa: E402, F401

st.set_page_config(
    page_title="CloudMetry · Gold Layer",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles = Path(__file__).with_name("style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)


def main() -> None:
    st.title("CloudMetry")
    st.caption("Gold Layer Lakehouse · analiza telemetrii i przejazdów")

    drives = load_drive_summaries()
    code_table = load_error_codes()
    if drives.empty:
        st.warning("Tabela fct_drive_summary nie zawiera jeszcze przejazdów.")
        st.stop()
    if "vehicle_id" not in drives.columns:
        st.error("Brak wymaganej kolumny vehicle_id w fct_drive_summary.")
        st.stop()

    vehicles = sorted(drives["vehicle_id"].dropna().astype(str).unique())
    if not vehicles:
        st.warning("Nie znaleziono identyfikatorów pojazdów.")
        st.stop()

    st.session_state.setdefault("selected_vehicle_id", None)
    st.session_state.setdefault("section_nav", "Podsumowanie pojazdu")
    st.session_state.setdefault("workspace_mode", "Analiza Historyczna")
    st.session_state.setdefault("selected_drive_id", None)
    selected = st.session_state.get("selected_vehicle_id")
    if selected is not None and str(selected) not in vehicles:
        st.session_state["selected_vehicle_id"] = None
        selected = None

    with st.sidebar:
        st.title("CloudMetry")
        st.caption("Nawigacja")
        if st.button("← Moje Pojazdy", width="stretch"):
            st.session_state["selected_vehicle_id"] = None
            st.rerun()
        selected_vehicle = st.selectbox(
            "Pojazd",
            ["— wybierz —", *vehicles],
            index=(vehicles.index(str(selected)) + 1 if selected is not None else 0),
        )
        if selected_vehicle != "— wybierz —":
            st.session_state["selected_vehicle_id"] = selected_vehicle
        elif selected is None:
            st.session_state["selected_vehicle_id"] = None
        st.checkbox(
            "Ukryj krótkie przeparkowania (< 5 min)",
            value=True,
            key="hide_micro_trips",
            help="Krótkie przejazdy są pomijane w agregatach i trendach pojazdu.",
        )
        if st.session_state.get("selected_vehicle_id"):
            st.radio(
                "Sekcja",
                ["Podsumowanie pojazdu", "Moje Przejazdy"],
                key="section_nav",
            )

    selected_vehicle_id = st.session_state.get("selected_vehicle_id")
    if not selected_vehicle_id:
        render_vehicle_landing(drives)
        return

    vehicle_drives = drives[
        drives["vehicle_id"].astype(str) == str(selected_vehicle_id)
    ].copy()
    st.subheader(f"Pojazd · {selected_vehicle_id}")
    st.radio(
        "Tryb pracy",
        ["Analiza Historyczna", "Podgląd na żywo"],
        horizontal=True,
        key="workspace_mode",
    )
    if st.session_state["workspace_mode"] == "Podgląd na żywo":
        render_live_view()
        return

    if st.session_state["section_nav"] == "Moje Przejazdy":
        render_drive_explorer(vehicle_drives, code_table)
    else:
        render_vehicle_overview(
            vehicle_drives,
            show_micro_trips=not st.session_state["hide_micro_trips"],
            vehicle_id=str(selected_vehicle_id),
        )


if __name__ == "__main__":
    main()
