

-- depends_on: "memory"."main"."gold_drive_telemetry"
-- depends_on: "memory"."main"."dim_drive_meta"
-- depends_on: "memory"."main"."dim_weather_conditions"
-- depends_on: "memory"."main"."dim_fuel_profile"
-- depends_on: "memory"."main"."dim_thermal_profile"
-- depends_on: "memory"."main"."dim_rusefi_error_code"

WITH telemetry AS (
    SELECT *
    FROM delta_scan('s3://gold/drive_telemetry')
),
warmup_cutoffs AS (
    SELECT
        vehicle_id,
        drive_id,
        COALESCE(
            MIN(sampled_at) FILTER (WHERE clt >= 85 AND oil_temp >= 82),
            MAX(sampled_at)
        ) AS warmup_complete_timestamp,
        COALESCE(
            ARG_MIN(clt, sampled_at) FILTER (
                WHERE clt BETWEEN -35.0 AND 150.0 AND rpm >= 500
            ),
            ARG_MIN(clt, sampled_at) FILTER (WHERE clt BETWEEN -35.0 AND 150.0)
        ) AS start_clt_c,
        COALESCE(
            ARG_MIN(oil_temp, sampled_at) FILTER (
                WHERE oil_temp BETWEEN -35.0 AND 150.0 AND rpm >= 500
            ),
            ARG_MIN(oil_temp, sampled_at)
                FILTER (WHERE oil_temp BETWEEN -35.0 AND 150.0)
        ) AS start_oil_temp_c
    FROM telemetry
    GROUP BY vehicle_id, drive_id
),
telemetry_with_warmup AS (
    SELECT
        telemetry.*,
        telemetry.sampled_at <= warmup_cutoffs.warmup_complete_timestamp
            AND NOT (
                COALESCE(warmup_cutoffs.start_clt_c >= 85, FALSE)
                AND COALESCE(warmup_cutoffs.start_oil_temp_c >= 82, FALSE)
            )
            AS is_before_warmup_complete
    FROM telemetry
    INNER JOIN warmup_cutoffs USING (vehicle_id, drive_id)
),
gear_steps AS (
    SELECT
        vehicle_id,
        drive_id,
        detected_gear,
        LAG(detected_gear) OVER (
            PARTITION BY vehicle_id, drive_id ORDER BY sampled_at
        ) AS previous_gear
    FROM telemetry
    WHERE detected_gear BETWEEN 1 AND 6
      AND effective_speed_kmh > 5.0
),
gear_stats AS (
    SELECT
        vehicle_id,
        drive_id,
        COUNT(*) FILTER (
            WHERE detected_gear IS NOT NULL
              AND previous_gear IS NOT NULL
              AND detected_gear <> previous_gear
        ) AS gear_shifts_count
    FROM gear_steps
    GROUP BY vehicle_id, drive_id
),
rev_limit_steps AS (
    SELECT
        vehicle_id,
        drive_id,
        rev_limit_active,
        LAG(rev_limit_active) OVER (
            PARTITION BY vehicle_id, drive_id ORDER BY sampled_at
        ) AS previous_rev_limit_active
    FROM telemetry
),
rev_limit_stats AS (
    SELECT
        vehicle_id,
        drive_id,
        COUNT(*) FILTER (
            WHERE rev_limit_active = 1
              AND COALESCE(previous_rev_limit_active, 0) <> 1
        ) AS rev_limit_events_count
    FROM rev_limit_steps
    GROUP BY vehicle_id, drive_id
),
weather_metrics AS (
    SELECT
        vehicle_id,
        drive_id,
        SUM(weather_precipitation_mm) AS total_precipitation_mm,
        AVG(weather_temp_c) AS avg_ambient_temp_c,
        AVG(weather_wind_speed_ms) AS avg_wind_speed_ms
    FROM (
        SELECT
            vehicle_id,
            drive_id,
            weather_hour_bucket,
            AVG(weather_precipitation_mm) AS weather_precipitation_mm,
            AVG(weather_temp_c) AS weather_temp_c,
            AVG(weather_wind_speed_ms) AS weather_wind_speed_ms
        FROM telemetry
        WHERE weather_hour_bucket IS NOT NULL
        GROUP BY vehicle_id, drive_id, weather_hour_bucket
    )
    GROUP BY vehicle_id, drive_id
),
drive_metrics AS (
    SELECT
        vehicle_id,
        drive_id,
        MIN(sampled_at) AS start_timestamp,
        MAX(sampled_at) AS end_timestamp,
        MAX(elapsed_drive_time_s) AS duration_seconds,
        MAX(cumulative_drive_distance_km) AS total_distance_km,
        MAX(fuel_total_consumed) - MIN(fuel_total_consumed)
            AS total_fuel_consumed_g,
        (MAX(fuel_total_consumed) - MIN(fuel_total_consumed)) / 750.0
            AS measured_fuel_l,
        SUM(fuel_flow_rate * dt_s) / 750.0 AS integrated_fuel_l,
        ARG_MIN(warning_last, sampled_at)
            FILTER (WHERE warning_last > 0) AS first_warning_code,
        ARG_MAX(warning_last, sampled_at)
            FILTER (WHERE warning_last > 0) AS last_warning_code,
        ARG_MAX(stop_engine_code, sampled_at)
            FILTER (WHERE stop_engine_code > 0) AS stop_engine_code_key_raw,
        MODE(ign_cut_code) FILTER (WHERE ign_cut_code > 0)
            AS dominant_ign_cut_code_raw,
        MODE(fuel_cut_code) FILTER (WHERE fuel_cut_code > 0)
            AS dominant_fuel_cut_code_raw,
        list_sort(list_distinct(list_concat(
            list(CAST(warning_last AS INTEGER))
                FILTER (WHERE warning_last > 0),
            list(CAST(stop_engine_code AS INTEGER))
                FILTER (WHERE stop_engine_code > 0),
            list(CAST(ign_cut_code AS INTEGER))
                FILTER (WHERE ign_cut_code > 0),
            list(CAST(fuel_cut_code AS INTEGER))
                FILTER (WHERE fuel_cut_code > 0)
        ))) AS error_codes,
        MIN(sampled_at) FILTER (WHERE warning_last > 0) AS first_warning_timestamp,
        MAX(warning_counter) - MIN(warning_counter) AS total_warnings_delta,
        MAX(trigger_error_counter) - MIN(trigger_error_counter)
            AS trigger_errors_delta,
        COALESCE(SUM(dt_s) FILTER (WHERE rev_limit_active = 1), 0.0)
            AS rev_limit_active_duration_s,
        MAX(check_engine) AS check_engine_triggered_flag,
        MAX(total_spark_cut) - MIN(total_spark_cut) AS total_spark_cuts_delta,
        MAX(total_fuel_cut) - MIN(total_fuel_cut) AS total_fuel_cuts_delta,
        MAX(cpu_usage_percent) AS max_cpu_usage_pct,
        AVG(cpu_usage_percent) AS avg_cpu_usage_pct,
        MAX(analog_sensors_supply_failure) AS analog_supply_failure_flag,

        COALESCE(
            ARG_MIN(clt, sampled_at) FILTER (
                WHERE clt BETWEEN -35.0 AND 150.0 AND rpm >= 500
            ),
            ARG_MIN(clt, sampled_at) FILTER (WHERE clt BETWEEN -35.0 AND 150.0)
        ) AS start_clt_c,
        COALESCE(
            ARG_MIN(oil_temp, sampled_at) FILTER (
                WHERE oil_temp BETWEEN -35.0 AND 150.0 AND rpm >= 500
            ),
            ARG_MIN(oil_temp, sampled_at)
                FILTER (WHERE oil_temp BETWEEN -35.0 AND 150.0)
        ) AS start_oil_temp_c,
        MAX(clt) AS max_clt_c,
        MIN(clt) FILTER (WHERE clt > -35.0) AS min_clt_c,
        AVG(clt) AS avg_clt_c,
        AVG(clt) FILTER (WHERE clt > 87.0) AS avg_hot_clt_c,
        COALESCE(
            ARG_MAX(clt, sampled_at) FILTER (
                WHERE clt BETWEEN -35.0 AND 150.0 AND rpm >= 500
            ),
            ARG_MAX(clt, sampled_at) FILTER (WHERE clt BETWEEN -35.0 AND 150.0)
        ) AS end_clt_c,
        MAX(oil_temp) AS max_oil_temp_c,
        MIN(oil_temp) FILTER (WHERE oil_temp > -35.0) AS min_oil_temp_c,
        AVG(oil_temp) AS avg_oil_temp_c,
        AVG(oil_temp) FILTER (WHERE oil_temp > 90.0) AS avg_hot_oil_temp_c,
        COALESCE(
            ARG_MAX(oil_temp, sampled_at) FILTER (
                WHERE oil_temp BETWEEN -35.0 AND 150.0 AND rpm >= 500
            ),
            ARG_MAX(oil_temp, sampled_at)
                FILTER (WHERE oil_temp BETWEEN -35.0 AND 150.0)
        ) AS end_oil_temp_c,
        MAX(mat) AS max_mat_c,
        AVG(mat) AS avg_mat_c,
        AVG(mat) FILTER (WHERE is_clean_wot_pull) AS wot_avg_mat_c,
        MAX(air_charge_temperature_estimate) AS max_charge_temp_est_c,
        AVG(air_charge_temperature_estimate) AS avg_charge_temp_est_c,
        AVG(intercooler_heat_soak_delta_c) AS intercooler_heat_soak_avg_c,
        MAX(intercooler_heat_soak_delta_c) AS intercooler_heat_soak_max_c,
        MAX(mat) FILTER (WHERE rpm >= 500) - MIN(mat) FILTER (WHERE rpm >= 500)
            AS mat_thermal_rise_c,
        MIN(oil_pressure / 100.0) FILTER (
            WHERE oil_temp >= 82.0
              AND is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
        )
            AS min_hot_oil_pressure_bar,
        MIN(oil_pressure / 100.0) FILTER (
            WHERE oil_temp >= 82.0
              AND is_active_engine_window
              AND rpm >= 3000
              AND oil_pressure / 100.0 > 0.1
        ) AS min_hot_load_oil_pressure_bar,
        MIN(oil_pressure / 100.0) FILTER (
            WHERE is_active_engine_window
              AND oil_temp >= 80.0
              AND rpm BETWEEN 650 AND 1250
              AND oil_pressure / 100.0 > 0.1
        ) AS min_hot_idle_oil_pressure_bar,
        MIN(oil_pressure_per_1k_rpm_bar) FILTER (
            WHERE is_active_engine_window AND rpm BETWEEN 1500 AND 4000
        ) AS min_oil_pressure_per_1k_rpm_bar,
        AVG(oil_pressure_per_1k_rpm_bar) FILTER (
            WHERE is_active_engine_window AND rpm BETWEEN 1500 AND 4000
        ) AS avg_oil_pressure_per_1k_rpm_bar,
        MIN(oil_pressure_safety_margin_bar) FILTER (
            WHERE is_active_engine_window AND rpm >= 650
        )
            AS min_oil_pressure_safety_margin_bar,
        COUNT(*) FILTER (WHERE is_low_oil_pressure_for_rpm)
            AS low_oil_pressure_samples_count,
        COALESCE(SUM(dt_s) FILTER (WHERE is_low_oil_pressure_for_rpm), 0.0)
            AS low_oil_pressure_duration_s,
        COUNT(*) FILTER (
            WHERE is_low_oil_pressure_for_rpm
              AND ABS(imu_lateral_accel_g) >= 0.35
        ) AS oil_starvation_in_cornering_samples_count,
        CASE
            WHEN COALESCE(
                SUM(dt_s) FILTER (WHERE is_low_oil_pressure_for_rpm),
                0.0
            ) >= 0.15
              OR COUNT(*) FILTER (WHERE is_low_oil_pressure_for_rpm) >= 3
                THEN TRUE
            ELSE FALSE
        END AS low_oil_pressure_damage_risk_flag,
        AVG(oil_pressure / 100.0) FILTER (
            WHERE is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
        ) AS avg_oil_pressure_bar,
        MAX(oil_pressure / 100.0) FILTER (
            WHERE is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
        ) AS max_oil_pressure_bar,
        MIN(batt_v) FILTER (WHERE rpm >= 500 AND batt_v > 5.0) AS min_batt_v,
        AVG(batt_v) FILTER (WHERE rpm >= 500 AND batt_v > 5.0) AS avg_batt_v,
        MAX(batt_v) AS max_batt_v,
        MAX(ecu_cpu_temperature) AS max_ecu_cpu_temp_c,
        AVG(ecu_cpu_temperature) AS avg_ecu_cpu_temp_c,
        MIN(elapsed_drive_time_s) FILTER (WHERE clt >= 85)
            AS first_clt_85_time_s,
        MIN(cumulative_drive_distance_km) FILTER (WHERE clt >= 85)
            AS first_clt_85_distance_km,
        MIN(elapsed_drive_time_s) FILTER (WHERE oil_temp >= 82)
            AS first_oil_82_time_s,
        MIN(cumulative_drive_distance_km) FILTER (WHERE oil_temp >= 82)
            AS first_oil_82_distance_km,
        AVG(rpm) FILTER (WHERE is_before_warmup_complete) AS warmup_avg_rpm,
        MAX(rpm) FILTER (WHERE is_before_warmup_complete) AS warmup_max_rpm,
        AVG(map) FILTER (WHERE is_before_warmup_complete)
            AS warmup_avg_map_kpa,
        AVG(tps) FILTER (WHERE is_before_warmup_complete)
            AS warmup_avg_tps_pct,
        AVG(effective_speed_kmh) FILTER (WHERE is_before_warmup_complete)
            AS warmup_avg_speed_kmh,
        COUNT(*) FILTER (
            WHERE is_before_warmup_complete AND effective_speed_kmh < 5
        ) * 100.0 / NULLIF(
            COUNT(*) FILTER (WHERE is_before_warmup_complete), 0
        )
            AS warmup_traffic_or_idle_time_pct,
        COUNT(*) FILTER (
            WHERE is_before_warmup_complete
              AND effective_speed_kmh >= 40 AND tps < 50
        ) * 100.0 / NULLIF(
            COUNT(*) FILTER (WHERE is_before_warmup_complete), 0
        )
            AS warmup_cruise_time_pct,
        COUNT(*) FILTER (
            WHERE is_before_warmup_complete
              AND (tps >= 60 OR map >= 110 OR rpm >= 4000)
        ) * 100.0 / NULLIF(
            COUNT(*) FILTER (WHERE is_before_warmup_complete), 0
        )
            AS warmup_high_load_time_pct,
        COUNT(*) FILTER (
            WHERE is_before_warmup_complete
              AND (oil_temp < 75 OR clt < 75)
              AND (rpm >= 4500 OR map >= 130 OR tps >= 80)
        ) AS cold_engine_abuse_samples_count,

        AVG(ambient_air_density_kg_m3) AS ambient_air_density_kg_m3,
        AVG(manifold_charge_density_kg_m3) FILTER (WHERE is_clean_wot_pull)
            AS wot_manifold_charge_density_kg_m3,
        AVG(effective_charge_density_kg_m3) FILTER (WHERE is_clean_wot_pull)
            AS wot_effective_charge_density_kg_m3,
        AVG(sae_correction_factor) AS sae_correction_factor,
        AVG(effective_longitudinal_accel_g) FILTER (WHERE is_clean_wot_pull)
            AS wot_raw_accel_avg_g,
        MAX(effective_longitudinal_accel_g) FILTER (WHERE is_clean_wot_pull)
            AS wot_raw_accel_max_g,
        AVG(instant_wot_accel_index_g_per_bar) FILTER (WHERE is_clean_wot_pull)
            AS wot_accel_index_g_per_bar,
        AVG(imu_longitudinal_accel_g / NULLIF(map / 100.0, 0))
            FILTER (WHERE is_clean_wot_pull) AS wot_imu_accel_index_g_per_bar,
        AVG(instant_wot_accel_index_g_per_bar
            / NULLIF(manifold_charge_density_kg_m3, 0))
            FILTER (WHERE is_clean_wot_pull) AS wot_boost_weather_efficiency_score,
        COUNT(*) FILTER (WHERE is_clean_wot_pull) AS wot_samples_count,
        COALESCE(SUM(dt_s) FILTER (WHERE is_clean_wot_pull), 0.0)
            AS wot_duration_seconds,

        AVG(timing_ignition) AS avg_ignition_timing_deg,
        MAX(timing_ignition) AS max_ignition_timing_deg,
        AVG(timing_ignition) FILTER (WHERE is_clean_wot_pull)
            AS wot_avg_ignition_timing_deg,
        MIN(timing_ignition) FILTER (WHERE is_clean_wot_pull)
            AS wot_min_ignition_timing_deg,
        AVG(timing_base_ignition) AS avg_base_ignition_timing_deg,
        AVG(dynamic_timing_trim_deg) AS avg_dynamic_timing_trim_deg,
        AVG(dynamic_timing_trim_deg) FILTER (WHERE is_clean_wot_pull)
            AS wot_avg_dynamic_timing_trim_deg,
        MAX(ignition_load) AS max_ignition_load,
        AVG(ignition_load) FILTER (WHERE is_clean_wot_pull) AS wot_avg_ignition_load,
        AVG(ignition_coil_charge_time) AS avg_coil_charge_time_ms,
        MAX(ignition_coil_charge_time) AS max_coil_charge_time_ms,
        AVG(ignition_coil_duty_cycle) AS avg_coil_duty_cycle_pct,
        MAX(ignition_coil_duty_cycle) AS max_coil_duty_cycle_pct,
        AVG(ignition_dwell_deviation) AS avg_dwell_deviation_ms,
        MAX(ABS(ignition_dwell_deviation)) AS max_abs_dwell_deviation_ms,
        MAX(ignition_overcharge_canceled) - MIN(ignition_overcharge_canceled)
            AS overcharge_canceled_delta,
        MAX(ignition_over_dwell_not_scheduled)
            - MIN(ignition_over_dwell_not_scheduled) AS overdwell_not_scheduled_delta,
        MAX(ignition_undecharge_warnings) - MIN(ignition_undecharge_warnings)
            AS ignition_undercharge_warnings_delta,
        MAX(ignition_overcharge_warnings) - MIN(ignition_overcharge_warnings)
            AS ignition_overcharge_warnings_delta,
        MAX(knock_count) - MIN(knock_count) AS knock_events_delta_count,
        MAX(knock_retard) AS max_knock_retard_deg,
        AVG(knock_retard) FILTER (WHERE knock_retard > 0)
            AS avg_active_knock_retard_deg,
        MAX(knock_current_level) AS max_knock_level_dbv,
        AVG(knock_current_level) AS avg_knock_level_dbv,

        AVG(fuel_flow_rate) AS avg_fuel_flow_gps,
        AVG(fuel_flow_rate) * 3.6 / 0.750 AS avg_fuel_flow_lph,
        MAX(fuel_flow_rate) AS max_fuel_flow_gps,
        MAX(fuel_flow_rate) * 3.6 / 0.750 AS max_fuel_flow_lph,
        AVG(fuel_ve) AS avg_ve_pct,
        MAX(fuel_ve) AS max_ve_pct,
        AVG(fuel_ve) FILTER (WHERE is_clean_wot_pull) AS wot_avg_ve_pct,
        MAX(fuel_last_inj_pulse_width) AS max_injector_pulse_width_ms,
        AVG(fuel_last_inj_pulse_width) AS avg_injector_pulse_width_ms,
        MAX(fuel_injector_duty_cycle) AS max_injector_duty_cycle_pct,
        AVG(fuel_injector_duty_cycle) AS avg_injector_duty_cycle_pct,
        AVG(afr) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) AS avg_afr,
        AVG(afr) FILTER (WHERE is_clean_wot_pull) AS wot_avg_afr,
        AVG("lambda") FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) AS avg_lambda,
        AVG("lambda") FILTER (WHERE is_clean_wot_pull) AS wot_avg_lambda,
        MIN("lambda") FILTER (WHERE is_clean_wot_pull) AS wot_min_lambda,
        MAX("lambda") FILTER (WHERE is_clean_wot_pull) AS wot_max_lambda,
        AVG(afr_error) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) AS avg_afr_error,
        AVG(afr_error) FILTER (WHERE is_clean_wot_pull) AS wot_avg_afr_error,
        MAX(afr_error) FILTER (WHERE is_clean_wot_pull)
            AS wot_max_lean_spike_afr_error,
        AVG(ego_cor1) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) AS avg_ego_cor1_pct,
        MIN(ego_cor1) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) AS min_ego_cor1_pct,
        MAX(ego_cor1) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) AS max_ego_cor1_pct,
        AVG(stft_bank_1) AS avg_stft_bank1_pct,
        MAX(ABS(stft_bank_1)) AS max_abs_stft_bank1_pct,
        AVG(ltft_bank_1) AS avg_ltft_bank1_pct,
        AVG(fuel_total_correction) AS avg_fuel_total_correction,
        MAX(fuel_total_correction) AS max_fuel_total_correction,
        MAX(fuel_tps_ae_change) AS max_tps_ae_change,
        MAX(fuel_load) AS max_fuel_load,
        AVG(fuel_load) AS avg_fuel_load,
        COALESCE(SUM(dt_s) FILTER (WHERE dfco_active = 1), 0.0)
            AS dfco_duration_seconds,
        COALESCE(SUM(dt_s) FILTER (WHERE dfco_active = 1), 0.0)
            * 100.0 / NULLIF(SUM(dt_s), 0) AS dfco_time_pct,

        MAX(map) AS max_map_kpa,
        AVG(map) AS avg_map_kpa,
        MAX(effective_map) AS max_effective_map_kpa,
        MAX(boost_gauge_kpa) AS max_boost_gauge_kpa,
        AVG(boost_error_kpa) FILTER (WHERE is_clean_wot_pull)
            AS wot_avg_boost_error_kpa,
        COALESCE(
            MAX(map - boost_target) FILTER (
                WHERE boost_target > COALESCE(NULLIF(baro_pressure, 0), 100.0) + 5.0
                AND tps >= 70.0
                AND map > boost_target
            ),
            0.0
        ) AS max_boost_overshoot_kpa,
        AVG(boost_output) AS avg_boost_output_pct,
        MAX(boost_output) AS max_boost_output_pct,
        AVG(wastegate_position_sensor) AS avg_wastegate_pos_pct,
        MAX(wastegate_position_sensor) AS max_wastegate_pos_pct,

        AVG(NULLIF(baro_pressure, 0)) AS avg_baro_pressure_kpa,

        MAX(effective_speed_kmh) AS max_effective_speed_kmh,
        AVG(effective_speed_kmh) AS avg_effective_speed_kmh,
        MAX(vehicle_speed) AS max_ecu_vehicle_speed_kmh,
        MAX(gps_speed_kmh) AS max_gps_speed_kmh,
        CASE
            WHEN MAX(COALESCE(vehicle_speed, 0)) <= 1.0 THEN 0.0
            ELSE COALESCE(
                COUNT(*) FILTER (
                    WHERE effective_speed_kmh > 2.0 AND vehicle_speed > 1.0
                ) * 100.0
                    / NULLIF(COUNT(*) FILTER (WHERE effective_speed_kmh > 2.0), 0),
                0.0
            )
        END AS ecu_speed_coverage_pct,
        COUNT(*) FILTER (
            WHERE is_gps_fresh = TRUE AND gps_speed_kmh IS NOT NULL
        ) * 100.0 / COUNT(*) AS gps_speed_coverage_pct,
        MAX(ABS(wheel_slip_delta_kmh))
            FILTER (WHERE speed_source_mode = 'DUAL_ACTIVE')
            AS max_wheel_slip_delta_kmh,
        COUNT(*) FILTER (
            WHERE speed_source_mode = 'DUAL_ACTIVE'
              AND ABS(wheel_slip_delta_kmh) >= 5
        ) AS wheel_slip_events_count,
        MAX(rpm) AS max_rpm,
        AVG(rpm) AS avg_rpm,
        MAX(d_rpm) AS max_drpm_per_s,
        MAX(tps) AS max_tps_pct,
        AVG(tps) AS avg_tps_pct,
        NULLIF(MAX(throttle_pedal_position), 0) AS max_throttle_pedal_pct,
        SUM(CASE WHEN is_clean_wot_pull THEN COALESCE(dt_s, 0) ELSE 0 END)
            * 100.0 / NULLIF(SUM(COALESCE(dt_s, 0)), 0) AS wot_time_pct,
        MAX(imu_longitudinal_accel_g) AS max_longitudinal_accel_g,
        MAX(-imu_longitudinal_accel_g)
            FILTER (WHERE imu_longitudinal_accel_g < 0)
            AS max_longitudinal_braking_g,
        MAX(ABS(imu_lateral_accel_g)) AS max_lateral_g,
        MAX(combined_g_force) AS max_combined_g_force,
        AVG(combined_g_force) AS avg_combined_g_force,
        MAX(detected_gear) AS highest_detected_gear
    FROM telemetry_with_warmup
    GROUP BY vehicle_id, drive_id
),
drive_with_dimensions AS (
    SELECT
        metrics.*,
        dim_drive_meta.drive_meta_key,
        dim_weather_conditions.weather_key,
        dim_fuel_profile.fuel_profile_key,
        dim_thermal_profile.thermal_profile_key,
        weather_metrics.total_precipitation_mm,
        weather_metrics.avg_ambient_temp_c,
        weather_metrics.avg_wind_speed_ms,
        CAST(CASE
            WHEN EXISTS (
                SELECT 1 FROM "memory"."main"."rusefi_error_codes" e
                WHERE e.raw_code_id = COALESCE(metrics.first_warning_code, 0)
            ) THEN COALESCE(metrics.first_warning_code, 0)
            ELSE 999
        END AS INTEGER) AS first_warning_code_key,
        CAST(CASE
            WHEN EXISTS (
                SELECT 1 FROM "memory"."main"."rusefi_error_codes" e
                WHERE e.raw_code_id = COALESCE(metrics.last_warning_code, 0)
            ) THEN COALESCE(metrics.last_warning_code, 0)
            ELSE 999
        END AS INTEGER) AS last_warning_code_key,
        CAST(CASE
            WHEN EXISTS (
                SELECT 1 FROM "memory"."main"."rusefi_error_codes" e
                WHERE e.raw_code_id = COALESCE(metrics.stop_engine_code_key_raw, 0)
            ) THEN COALESCE(metrics.stop_engine_code_key_raw, 0)
            ELSE 999
        END AS INTEGER) AS stop_engine_code_key,
        CAST(CASE
            WHEN EXISTS (
                SELECT 1 FROM "memory"."main"."rusefi_error_codes" e
                WHERE e.raw_code_id = COALESCE(metrics.dominant_ign_cut_code_raw, 0)
            ) THEN COALESCE(metrics.dominant_ign_cut_code_raw, 0)
            ELSE 999
        END AS INTEGER) AS dominant_ign_cut_key,
        CAST(CASE
            WHEN EXISTS (
                SELECT 1 FROM "memory"."main"."rusefi_error_codes" e
                WHERE e.raw_code_id = COALESCE(metrics.dominant_fuel_cut_code_raw, 0)
            ) THEN COALESCE(metrics.dominant_fuel_cut_code_raw, 0)
            ELSE 999
        END AS INTEGER) AS dominant_fuel_cut_key
    FROM drive_metrics AS metrics
    LEFT JOIN delta_scan('s3://gold/dim_drive_meta') AS dim_drive_meta
      USING (vehicle_id, drive_id)
    LEFT JOIN delta_scan('s3://gold/dim_weather_conditions')
        AS dim_weather_conditions USING (vehicle_id, drive_id)
    LEFT JOIN delta_scan('s3://gold/dim_fuel_profile') AS dim_fuel_profile
      USING (vehicle_id, drive_id)
    LEFT JOIN delta_scan('s3://gold/dim_thermal_profile')
        AS dim_thermal_profile USING (vehicle_id, drive_id)
    LEFT JOIN weather_metrics USING (vehicle_id, drive_id)
)
SELECT
    drive_id,
    vehicle_id,
    drive_meta_key,
    weather_key,
    fuel_profile_key,
    thermal_profile_key,
    first_warning_code_key,
    last_warning_code_key,
    stop_engine_code_key,
    dominant_ign_cut_key,
    dominant_fuel_cut_key,
    error_codes,
    duration_seconds,
    duration_seconds < 300 AS is_repark_or_micro_trip_flag,
    duration_seconds >= 300 AND total_distance_km >= 0.5
        AS is_valid_analytical_drive_flag,
    total_distance_km,
    COALESCE(start_clt_c >= 85, FALSE) AS started_warm_clt_85c_flag,
    COALESCE(start_oil_temp_c >= 82, FALSE) AS started_warm_oil_82c_flag,
    COALESCE(max_clt_c >= 85, FALSE) AS reached_clt_85c_flag,
    COALESCE(max_oil_temp_c >= 82, FALSE) AS reached_oil_82c_flag,
    CASE
        WHEN start_clt_c >= 85 THEN 0.0
        WHEN max_clt_c >= 85 THEN first_clt_85_time_s
    END AS time_to_clt_85c_s,
    CASE
        WHEN start_clt_c >= 85 THEN 0.0
        WHEN max_clt_c >= 85 THEN first_clt_85_distance_km
    END AS distance_to_clt_85c_km,
    CASE
        WHEN start_oil_temp_c >= 82 THEN 0.0
        WHEN max_oil_temp_c >= 82 THEN first_oil_82_time_s
    END AS time_to_oil_82c_s,
    CASE
        WHEN start_oil_temp_c >= 82 THEN 0.0
        WHEN max_oil_temp_c >= 82 THEN first_oil_82_distance_km
    END AS distance_to_oil_82c_km,
    warmup_avg_rpm,
    warmup_max_rpm,
    warmup_avg_map_kpa,
    warmup_avg_tps_pct,
    warmup_avg_speed_kmh,
    warmup_traffic_or_idle_time_pct,
    warmup_cruise_time_pct,
    warmup_high_load_time_pct,
    cold_engine_abuse_samples_count,
    ambient_air_density_kg_m3,
    wot_manifold_charge_density_kg_m3,
    wot_effective_charge_density_kg_m3,
    sae_correction_factor,
    wot_raw_accel_avg_g,
    wot_raw_accel_max_g,
    wot_accel_index_g_per_bar,
    wot_imu_accel_index_g_per_bar,
    wot_boost_weather_efficiency_score,
    wot_accel_index_g_per_bar * sae_correction_factor
        AS wot_sae_corrected_accel_index,
    wot_samples_count,
    wot_duration_seconds,
    avg_ignition_timing_deg,
    max_ignition_timing_deg,
    wot_avg_ignition_timing_deg,
    wot_min_ignition_timing_deg,
    avg_base_ignition_timing_deg,
    avg_dynamic_timing_trim_deg,
    wot_avg_dynamic_timing_trim_deg,
    max_ignition_load,
    wot_avg_ignition_load,
    avg_coil_charge_time_ms,
    max_coil_charge_time_ms,
    avg_coil_duty_cycle_pct,
    max_coil_duty_cycle_pct,
    avg_dwell_deviation_ms,
    max_abs_dwell_deviation_ms,
    overcharge_canceled_delta,
    overdwell_not_scheduled_delta,
    ignition_undercharge_warnings_delta,
    ignition_overcharge_warnings_delta,
    knock_events_delta_count,
    max_knock_retard_deg,
    avg_active_knock_retard_deg,
    max_knock_level_dbv,
    avg_knock_level_dbv,
    total_fuel_consumed_g,
    COALESCE(NULLIF(measured_fuel_l, 0), integrated_fuel_l) AS total_fuel_consumed_l,
    CASE
        WHEN total_distance_km >= 0.2
            THEN COALESCE(NULLIF(measured_fuel_l, 0), integrated_fuel_l)
                / NULLIF(total_distance_km, 0) * 100.0
    END AS avg_fuel_consumption_l_100km,
    avg_fuel_flow_gps,
    avg_fuel_flow_lph,
    max_fuel_flow_gps,
    max_fuel_flow_lph,
    avg_ve_pct,
    max_ve_pct,
    wot_avg_ve_pct,
    max_injector_pulse_width_ms,
    avg_injector_pulse_width_ms,
    max_injector_duty_cycle_pct,
    avg_injector_duty_cycle_pct,
    avg_afr,
    wot_avg_afr,
    avg_lambda,
    wot_avg_lambda,
    wot_min_lambda,
    wot_max_lambda,
    avg_afr_error,
    wot_avg_afr_error,
    wot_max_lean_spike_afr_error,
    avg_ego_cor1_pct,
    min_ego_cor1_pct,
    max_ego_cor1_pct,
    avg_stft_bank1_pct,
    max_abs_stft_bank1_pct,
    avg_ltft_bank1_pct,
    avg_fuel_total_correction,
    max_fuel_total_correction,
    max_tps_ae_change,
    max_fuel_load,
    avg_fuel_load,
    dfco_time_pct,
    dfco_duration_seconds,
    max_map_kpa,
    avg_map_kpa,
    max_effective_map_kpa,
    max_boost_gauge_kpa,
    wot_avg_boost_error_kpa,
    max_boost_overshoot_kpa,
    avg_boost_output_pct,
    max_boost_output_pct,
    avg_wastegate_pos_pct,
    max_wastegate_pos_pct,
    max_clt_c,
    min_clt_c,
    avg_clt_c,
    avg_hot_clt_c,
    end_clt_c,
    max_mat_c,
    avg_mat_c,
    wot_avg_mat_c,
    max_charge_temp_est_c,
    avg_charge_temp_est_c,
    intercooler_heat_soak_avg_c,
    intercooler_heat_soak_max_c,
    mat_thermal_rise_c,
    max_oil_temp_c,
    min_oil_temp_c,
    avg_oil_temp_c,
    avg_hot_oil_temp_c,
    end_oil_temp_c,
    avg_oil_pressure_bar,
    max_oil_pressure_bar,
    min_hot_oil_pressure_bar,
    min_hot_load_oil_pressure_bar,
    min_hot_idle_oil_pressure_bar,
    min_oil_pressure_per_1k_rpm_bar,
    avg_oil_pressure_per_1k_rpm_bar,
    min_oil_pressure_safety_margin_bar,
    low_oil_pressure_samples_count,
    low_oil_pressure_duration_s,
    oil_starvation_in_cornering_samples_count,
    low_oil_pressure_damage_risk_flag,
    min_batt_v,
    avg_batt_v,
    max_batt_v,
    max_ecu_cpu_temp_c,
    avg_ecu_cpu_temp_c,
    max_effective_speed_kmh,
    avg_effective_speed_kmh,
    max_ecu_vehicle_speed_kmh,
    max_gps_speed_kmh,
    ecu_speed_coverage_pct,
    gps_speed_coverage_pct,
    max_wheel_slip_delta_kmh,
    wheel_slip_events_count,
    max_rpm,
    avg_rpm,
    max_drpm_per_s,
    max_tps_pct,
    avg_tps_pct,
    max_throttle_pedal_pct,
    wot_time_pct,
    max_longitudinal_accel_g,
    max_longitudinal_braking_g,
    max_lateral_g,
    max_combined_g_force,
    avg_combined_g_force,
    highest_detected_gear,
    COALESCE(gear_stats.gear_shifts_count, 0) AS gear_shifts_count,
    COALESCE(rev_limit_stats.rev_limit_events_count, 0)
        AS rev_limit_events_count,
    avg_ambient_temp_c,
    avg_baro_pressure_kpa,
    total_precipitation_mm,
    avg_wind_speed_ms,
    total_warnings_delta,
    first_warning_timestamp,
    trigger_errors_delta,
    rev_limit_active_duration_s,
    check_engine_triggered_flag,
    total_spark_cuts_delta,
    total_fuel_cuts_delta,
    max_cpu_usage_pct,
    avg_cpu_usage_pct,
    analog_supply_failure_flag
FROM drive_with_dimensions
LEFT JOIN gear_stats USING (vehicle_id, drive_id)
LEFT JOIN rev_limit_stats USING (vehicle_id, drive_id)