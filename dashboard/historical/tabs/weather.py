import pandas as pd

from dashboard.ui import chart_info, field_table, line_chart


def render_weather_tab(row: pd.Series, telemetry: pd.DataFrame) -> None:
    field_table(
        row,
        [
            "boost_weather_class",
            "ambient_temp_band",
            "baro_pressure_band",
            "precipitation_status",
            "wind_intensity_band",
            "ambient_air_density_kg_m3",
            "wot_manifold_charge_density_kg_m3",
            "wot_effective_charge_density_kg_m3",
            "sae_correction_factor",
            "wot_imu_accel_index_g_per_bar",
            "wot_sae_corrected_accel_index",
            "wot_boost_weather_efficiency_score",
            "intercooler_heat_soak_avg_c",
            "intercooler_heat_soak_max_c",
            "mat_thermal_rise_c",
            "max_charge_temp_est_c",
            "max_map_kpa",
            "max_boost_gauge_kpa",
            "wot_avg_boost_error_kpa",
            "max_boost_overshoot_kpa",
            "max_boost_output_pct",
            "max_wastegate_pos_pct",
        ],
        "Warunki atmosferyczne i doładowanie",
    )
    if "map_kpa" in telemetry:
        line_chart(
            telemetry,
            ["map_kpa", "boost_target", "boost_output"],
            "MAP, cel doładowania i wyjście sterownika",
        )
    else:
        chart_info()
    density_fields = [
        field
        for field in (
            "ambient_air_density_kg_m3",
            "manifold_charge_density_kg_m3",
            "effective_charge_density_kg_m3",
        )
        if field in telemetry
    ]
    line_chart(telemetry, density_fields, "Gęstość powietrza i ładunku (kg/m³)")
