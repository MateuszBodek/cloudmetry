

-- depends_on: "memory"."main"."gold_drive_telemetry"

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
            ) AS is_before_warmup_complete
    FROM telemetry
    INNER JOIN warmup_cutoffs USING (vehicle_id, drive_id)
),
drive_thermal AS (
    SELECT
        vehicle_id,
        drive_id,
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
        MAX(oil_temp) AS max_oil_temp_c,
        MAX(mat) AS max_mat_c,
        MIN(oil_pressure / 100.0) FILTER (
            WHERE oil_temp >= 82.0
              AND is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
        )
            AS min_hot_oil_pressure_bar,
        MIN(oil_pressure_per_1k_rpm_bar) FILTER (
            WHERE is_active_engine_window AND rpm BETWEEN 1500 AND 4000
        ) AS min_oil_pressure_per_1k_rpm_bar,
        MIN(oil_pressure_safety_margin_bar) FILTER (
            WHERE is_active_engine_window AND rpm >= 650
        )
            AS min_oil_pressure_safety_margin_bar,
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
              AND (clt < 75 OR oil_temp < 75)
              AND (rpm >= 4500 OR map >= 130 OR tps >= 80)
        ) AS cold_engine_abuse_samples_count
    FROM telemetry_with_warmup
    GROUP BY vehicle_id, drive_id
)
SELECT
    md5(vehicle_id || '|' || drive_id) AS thermal_profile_key,
    vehicle_id,
    drive_id,
    CASE
        WHEN start_clt_c >= 85 AND start_oil_temp_c >= 82
            THEN 'Started Pre-Warmed (CLT>=85C & Oil>=82C)'
        WHEN warmup_high_load_time_pct > 15 OR cold_engine_abuse_samples_count > 10
            THEN 'Aggressive / High-Load Cold Warmup'
        WHEN warmup_traffic_or_idle_time_pct >= 50 OR warmup_avg_speed_kmh < 15
            THEN 'Traffic Jam / Stationary Idle Warmup'
        WHEN warmup_cruise_time_pct >= 40 OR warmup_avg_speed_kmh >= 45
            THEN 'Gentle Steady Cruising Warmup'
        ELSE 'Mixed Urban Warmup'
    END AS warmup_driving_style_category,
    CASE
        WHEN max_clt_c IS NULL AND max_oil_temp_c IS NULL THEN 'Unknown'
        WHEN max_clt_c >= 85 AND max_oil_temp_c >= 82
            THEN 'Fully Warmed (CLT>=85C & Oil>=82C)'
        WHEN max_clt_c >= 85 AND COALESCE(max_oil_temp_c, 0) < 82
            THEN 'Coolant Only Warmed (CLT>=85C, Oil<82C)'
        ELSE 'Under-Warmed Short Trip (CLT<85C & Oil<82C)'
    END AS thermal_completion_status,
    CASE
        WHEN max_mat_c IS NULL THEN 'Unknown'
        WHEN max_mat_c < 25 THEN 'Cool Intake (MAT < 25C)'
        WHEN max_mat_c <= 45 THEN 'Moderate Intake (25-45C)'
        ELSE 'Severe Heat Soak (MAT > 45C)'
    END AS intake_heat_soak_regime,
    CASE
        WHEN oil_starvation_in_cornering_samples_count >= 3
            THEN 'CRITICAL: Cornering Oil Starvation (Lateral G Slosh)'
        WHEN low_oil_pressure_damage_risk_flag
            THEN 'CRITICAL: Below Safe Pressure-vs-RPM Curve (<1.0 bar idle / <3.2 bar load)'
        WHEN min_oil_pressure_safety_margin_bar < 0.25
          OR min_oil_pressure_per_1k_rpm_bar < 0.80
            THEN 'WARNING: Thin Safety Margin (<0.25 bar above RPM floor or ratio <0.80)'
        ELSE 'Healthy Oil Pressure Curve'
    END AS oil_pressure_health_status
FROM drive_thermal