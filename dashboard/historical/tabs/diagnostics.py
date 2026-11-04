import pandas as pd
import streamlit as st

from dashboard.ui import codes_for_drive, field_table, line_chart


def render_diagnostics_tab(
    row: pd.Series, telemetry: pd.DataFrame, code_table: pd.DataFrame
) -> None:
    decoded = codes_for_drive(row, code_table)
    st.markdown("**Dekoder błędów i odcięć rusEFI**")
    if decoded.empty:
        st.info("Nie zarejestrowano kodów błędów ani odcięć.")
    else:
        preferred = [
            "raw_code_id",
            "code_category",
            "code_name",
            "code_description_pl",
            "severity_level",
            "first_warning_timestamp",
        ]
        st.dataframe(
            decoded[[field for field in preferred if field in decoded]],
            hide_index=True,
            width="stretch",
        )
    field_table(
        row,
        [
            "total_warnings_delta",
            "trigger_errors_delta",
            "total_spark_cuts_delta",
            "total_fuel_cuts_delta",
            "rev_limit_events_count",
            "rev_limit_active_duration_s",
            "check_engine_triggered_flag",
            "analog_supply_failure_flag",
            "min_batt_v",
            "avg_batt_v",
            "max_batt_v",
            "max_ecu_cpu_temp_c",
            "max_cpu_usage_pct",
            "avg_ignition_timing_deg",
            "wot_avg_ignition_timing_deg",
            "wot_min_ignition_timing_deg",
            "avg_dynamic_timing_trim_deg",
            "wot_avg_dynamic_timing_trim_deg",
            "avg_coil_charge_time_ms",
            "max_coil_charge_time_ms",
            "max_coil_duty_cycle_pct",
            "avg_dwell_deviation_ms",
            "max_abs_dwell_deviation_ms",
            "overcharge_canceled_delta",
            "overdwell_not_scheduled_delta",
            "ignition_undercharge_warnings_delta",
            "ignition_overcharge_warnings_delta",
            "knock_events_delta_count",
            "max_knock_retard_deg",
            "avg_active_knock_retard_deg",
            "max_knock_level_dbv",
        ],
        "Diagnostyka krytyczna, zasilanie i zapłon",
    )
    ignition = [
        field
        for field in (
            "timing_ignition",
            "timing_base_ignition",
            "knock_current_level",
            "knock_retard",
        )
        if field in telemetry
    ]
    line_chart(telemetry, ignition, "Zapłon i spalanie stukowe")
    line_chart(
        telemetry,
        ["battery_voltage_v", "ignition_coil_charge_time"],
        "Napięcie akumulatora i czas ładowania cewki",
    )
