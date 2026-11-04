{{
    config(
        materialized='external',
        plugin='delta_merge',
        format='parquet',
        location=var('dbt_staging_uri') ~ '/' ~ var('batch_id') ~ '_gold_drive_telemetry.parquet',
        options={},
        delta_merge_options={
            'location': var('gold_telemetry_uri'),
            'key_columns': ['vehicle_id', 'drive_id', 'source_time_s'],
            'partition_by': ['event_date']
        }
    )
}}

-- depends_on: {{ ref('silver_accelerometer') }}
-- depends_on: {{ ref('silver_telemetry') }}
-- depends_on: {{ ref('silver_gps') }}

{% set telemetry_fields = var('telemetry_columns') %}

WITH affected_drives AS (
    SELECT DISTINCT vehicle_id, drive_id
    FROM {{ ref('stg_bronze_deduped') }}
    WHERE stream IN ('gps', 'telemetry', 'accelerometer')
),
accelerometer AS (
    SELECT source.*
    FROM delta_scan('{{ var("silver_accelerometer_uri") }}') AS source
    WHERE (vehicle_id, drive_id) IN (
        SELECT vehicle_id, drive_id FROM affected_drives
    )
),
telemetry AS (
    SELECT source.*
    FROM delta_scan('{{ var("silver_telemetry_uri") }}') AS source
    WHERE (vehicle_id, drive_id) IN (
        SELECT vehicle_id, drive_id FROM affected_drives
    )
),
gps AS (
    SELECT source.*
    FROM delta_scan('{{ var("silver_gps_uri") }}') AS source
    WHERE (vehicle_id, drive_id) IN (
        SELECT vehicle_id, drive_id FROM affected_drives
    )
),
weather AS (
    SELECT source.*
    FROM delta_scan('{{ var("silver_weather_uri") }}') AS source
),
joined AS (
    SELECT
        accelerometer.vehicle_id,
        accelerometer.drive_id,
        accelerometer.source_time_s,
        accelerometer.sampled_at,
        TRY_CAST(accelerometer.sampled_at AS TIMESTAMPTZ) AS sampled_at_ts,
        accelerometer.event_date,
        accelerometer.x_g AS accel_x_g,
        accelerometer.y_g AS accel_y_g,
        accelerometer.z_g AS accel_z_g,
        accelerometer.source_file AS accelerometer_source_file,
        telemetry.source_time_s AS telemetry_source_time_s,
        telemetry.sampled_at AS telemetry_sampled_at,
        telemetry.source_file AS telemetry_source_file,
        {% for col in telemetry_fields %}
        telemetry."{{ col }}" AS "{{ col }}"{% if not loop.last %},{% endif %}
        {% endfor %},
        gps.source_time_s AS gps_source_time_s,
        gps.sampled_at AS gps_sampled_at,
        gps.latitude AS gps_latitude,
        gps.longitude AS gps_longitude,
        gps.recorded_at AS gps_recorded_at,
        gps.heading_deg AS gps_heading_deg,
        gps.speed_kph AS gps_speed_kmh,
        gps.lat_grid AS gps_lat_grid,
        gps.lon_grid AS gps_lon_grid,
        gps.hour_bucket AS gps_hour_bucket,
        gps.weather_hour_bucket,
        COALESCE(gps.temperature_2m, weather.temperature_2m) AS weather_temp_c,
        COALESCE(gps.precipitation, weather.precipitation)
            AS weather_precipitation_mm,
        COALESCE(gps.surface_pressure_hpa, weather.surface_pressure_hpa)
            AS weather_pressure_hpa,
        COALESCE(gps.relative_humidity_2m, weather.relative_humidity_2m)
            AS weather_relative_humidity_pct,
        weather.wind_speed_10m AS weather_wind_speed_ms,
        gps.source_file AS gps_source_file
    FROM accelerometer
    ASOF LEFT JOIN telemetry
      ON accelerometer.vehicle_id = telemetry.vehicle_id
     AND accelerometer.drive_id = telemetry.drive_id
     AND accelerometer.source_time_s >= telemetry.source_time_s
    ASOF LEFT JOIN gps
      ON accelerometer.vehicle_id = gps.vehicle_id
     AND accelerometer.drive_id = gps.drive_id
     AND accelerometer.source_time_s >= gps.source_time_s
    LEFT JOIN weather
      ON gps.lat_grid = weather.lat_grid
     AND gps.lon_grid = weather.lon_grid
     AND gps.hour_bucket = weather.hour_bucket
),
aged AS (
    SELECT
        *,
        (source_time_s - telemetry_source_time_s) * 1000.0
            AS telemetry_sample_age_ms,
        (source_time_s - gps_source_time_s) * 1000.0 AS gps_sample_age_ms,
        date_diff(
            'millisecond',
            weather_hour_bucket,
            timezone('Europe/Warsaw', sampled_at_ts)
        ) / 1000.0 AS weather_sample_age_seconds
    FROM joined
),
freshness AS (
    SELECT
        *,
        COALESCE(telemetry_sample_age_ms BETWEEN 0 AND 500, FALSE)
            AS is_telemetry_fresh,
        COALESCE(gps_sample_age_ms BETWEEN 0 AND 2000, FALSE)
            AS is_gps_fresh,
        COALESCE(
            ABS(weather_sample_age_seconds) <= 7200
                OR weather_temp_c IS NOT NULL,
            FALSE
        ) AS is_weather_fresh
    FROM aged
),
cleaned AS (
    SELECT
        * EXCLUDE (
            {% for col in telemetry_fields %}
            "{{ col }}"{% if not loop.last %}, {% endif %}
            {% endfor %},
            gps_latitude,
            gps_longitude,
            gps_heading_deg,
            gps_speed_kmh,
            gps_lat_grid,
            gps_lon_grid,
            weather_temp_c,
            weather_precipitation_mm,
            weather_pressure_hpa,
            weather_relative_humidity_pct,
            weather_wind_speed_ms
        ),
        {% for col in telemetry_fields %}
        CASE WHEN is_telemetry_fresh THEN "{{ col }}" END AS "{{ col }}",
        {% endfor %}
        CASE WHEN is_gps_fresh THEN gps_latitude END AS gps_latitude,
        CASE WHEN is_gps_fresh THEN gps_longitude END AS gps_longitude,
        CASE WHEN is_gps_fresh THEN gps_heading_deg END AS gps_heading_deg,
        CASE WHEN is_gps_fresh THEN gps_speed_kmh END AS gps_speed_kmh,
        CASE WHEN is_gps_fresh THEN gps_lat_grid END AS gps_lat_grid,
        CASE WHEN is_gps_fresh THEN gps_lon_grid END AS gps_lon_grid,
        CASE WHEN is_weather_fresh THEN weather_temp_c END AS weather_temp_c,
        CASE WHEN is_weather_fresh THEN weather_precipitation_mm END
            AS weather_precipitation_mm,
        CASE WHEN is_weather_fresh THEN weather_pressure_hpa END
            AS weather_pressure_hpa,
        CASE WHEN is_weather_fresh THEN weather_relative_humidity_pct END
            AS weather_relative_humidity_pct,
        CASE WHEN is_weather_fresh THEN weather_wind_speed_ms END
            AS weather_wind_speed_ms
    FROM freshness
),
speed_presence AS (
    SELECT
        *,
        MAX(COALESCE(vehicle_speed, 0)) OVER (
            PARTITION BY vehicle_id, drive_id
        ) > 5.0 AS has_ecu_speed,
        MAX(COALESCE(gps_speed_kmh, 0)) OVER (
            PARTITION BY vehicle_id, drive_id
        ) > 5.0 AS has_gps_speed
    FROM cleaned
),
speed_choice AS (
    SELECT
        *,
        CASE
            WHEN has_ecu_speed AND has_gps_speed THEN 'DUAL_ACTIVE'
            WHEN NOT has_ecu_speed AND has_gps_speed THEN 'GPS_ONLY'
            WHEN has_ecu_speed AND NOT has_gps_speed THEN 'ECU_VSS_ONLY'
            ELSE 'NO_VALID_SPEED'
        END AS speed_source_mode,
        CASE
            WHEN has_gps_speed AND is_gps_fresh AND gps_speed_kmh > 0
                THEN gps_speed_kmh
            WHEN has_ecu_speed THEN COALESCE(vehicle_speed, 0.0)
            ELSE COALESCE(gps_speed_kmh, vehicle_speed, 0.0)
        END AS effective_speed_kmh,
        CASE
            WHEN has_gps_speed AND is_gps_fresh AND gps_speed_kmh > 0
                THEN gps_source_time_s
            WHEN has_ecu_speed THEN telemetry_source_time_s
            WHEN gps_speed_kmh IS NOT NULL THEN gps_source_time_s
            ELSE telemetry_source_time_s
        END AS effective_speed_source_time_s,
        CASE
            WHEN has_ecu_speed AND has_gps_speed AND is_gps_fresh
                THEN vehicle_speed - gps_speed_kmh
        END AS wheel_slip_delta_kmh
    FROM speed_presence
),
distance_steps AS (
    SELECT
        *,
        CASE
            WHEN source_time_s - LAG(source_time_s) OVER (
                PARTITION BY vehicle_id, drive_id
                ORDER BY sampled_at_ts, source_time_s
            ) BETWEEN 0.001 AND 1.0
                THEN source_time_s - LAG(source_time_s) OVER (
                    PARTITION BY vehicle_id, drive_id
                    ORDER BY sampled_at_ts, source_time_s
                )
            ELSE 0.02
        END AS dt_s
    FROM speed_choice
),
distances AS (
    SELECT
        *,
        effective_speed_kmh / 3600.0 * dt_s AS step_distance_km,
        SUM(effective_speed_kmh / 3600.0 * dt_s) OVER (
            PARTITION BY vehicle_id, drive_id
            ORDER BY sampled_at_ts, source_time_s
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_drive_distance_km,
        date_diff(
            'millisecond',
            MIN(sampled_at_ts) OVER (PARTITION BY vehicle_id, drive_id),
            sampled_at_ts
        ) / 1000.0 AS elapsed_drive_time_s,
        (effective_speed_kmh - LAG(effective_speed_kmh) OVER (
            PARTITION BY vehicle_id, drive_id
            ORDER BY sampled_at_ts, source_time_s
        )) / 3.6 / NULLIF(dt_s, 0) / 9.80665 AS row_speed_deriv_accel_g
    FROM distance_steps
),
speed_update_rows AS (
    SELECT
        vehicle_id,
        drive_id,
        effective_speed_source_time_s AS speed_update_time_s,
        effective_speed_kmh,
        ROW_NUMBER() OVER (
            PARTITION BY vehicle_id, drive_id, effective_speed_source_time_s
            ORDER BY sampled_at_ts, source_time_s
        ) AS update_row_number
    FROM distances
    WHERE effective_speed_source_time_s IS NOT NULL
),
speed_updates AS (
    SELECT
        vehicle_id,
        drive_id,
        speed_update_time_s,
        effective_speed_kmh,
        LAG(effective_speed_kmh) OVER (
            PARTITION BY vehicle_id, drive_id ORDER BY speed_update_time_s
        ) AS lagged_speed_kmh,
        LAG(speed_update_time_s) OVER (
            PARTITION BY vehicle_id, drive_id ORDER BY speed_update_time_s
        ) AS lagged_speed_time_s
    FROM speed_update_rows
    WHERE update_row_number = 1
),
derived AS (
    SELECT
        distances.*,
        (speed_updates.effective_speed_kmh - speed_updates.lagged_speed_kmh)
            / 3.6
            / NULLIF(
                speed_updates.speed_update_time_s - speed_updates.lagged_speed_time_s,
                0
            )
            / 9.80665 AS speed_deriv_accel_g
    FROM distances
    LEFT JOIN speed_updates
      ON distances.vehicle_id = speed_updates.vehicle_id
     AND distances.drive_id = speed_updates.drive_id
     AND distances.effective_speed_source_time_s = speed_updates.speed_update_time_s
),
imu_offsets AS (
    SELECT
        *,
        MEDIAN(accel_y_g) FILTER (
            WHERE effective_speed_kmh < 1.0 AND ABS(accel_y_g) <= 1.8
        ) OVER (PARTITION BY vehicle_id, drive_id) AS stationary_longitudinal_offset_g,
        MEDIAN(accel_x_g) FILTER (
            WHERE effective_speed_kmh < 1.0 AND ABS(accel_x_g) <= 1.8
        ) OVER (PARTITION BY vehicle_id, drive_id) AS stationary_lateral_offset_g
    FROM derived
),
imu_filtered AS (
    SELECT
        *,
        CASE
            WHEN ABS(accel_y_g) <= 1.8
                THEN accel_y_g - COALESCE(stationary_longitudinal_offset_g, 0.0)
        END AS calibrated_longitudinal_accel_g,
        CASE
            WHEN ABS(accel_x_g) <= 1.8
                THEN accel_x_g - COALESCE(stationary_lateral_offset_g, 0.0)
        END AS calibrated_lateral_accel_g
    FROM imu_offsets
),
imu_smoothed AS (
    SELECT
        *,
        AVG(calibrated_longitudinal_accel_g) OVER (
            PARTITION BY vehicle_id, drive_id
            ORDER BY sampled_at_ts, source_time_s
            ROWS BETWEEN 10 PRECEDING AND 10 FOLLOWING
        ) AS smoothed_longitudinal_accel_g,
        AVG(calibrated_lateral_accel_g) OVER (
            PARTITION BY vehicle_id, drive_id
            ORDER BY sampled_at_ts, source_time_s
            ROWS BETWEEN 10 PRECEDING AND 10 FOLLOWING
        ) AS smoothed_lateral_accel_g
    FROM imu_filtered
),
wot_state AS (
    SELECT
        *,
        COALESCE((
            effective_speed_kmh >= 30.0
            AND tps >= 85.0
            AND ABS(COALESCE(d_tps, 0)) < 15.0
            AND COALESCE(d_rpm, 0) > 200.0
            AND COALESCE(total_spark_cut, 0) = 0
            AND COALESCE(total_fuel_cut, 0) = 0
            AND COALESCE(rev_limit_active, 0) = 0
        ), FALSE) AS is_clean_wot_pull
    FROM imu_smoothed
),
imu_alignment AS (
    SELECT
        *,
        AVG(smoothed_longitudinal_accel_g * speed_deriv_accel_g) FILTER (
            WHERE is_clean_wot_pull
              AND COALESCE(d_rpm, 0) > 300
              AND COALESCE(tps, 0) > 50
              AND speed_deriv_accel_g IS NOT NULL
        ) OVER (PARTITION BY vehicle_id, drive_id) AS imu_longitudinal_alignment_score
    FROM wot_state
),
aligned_imu AS (
    SELECT
        *,
        CASE
            WHEN imu_longitudinal_alignment_score < 0
                THEN -smoothed_longitudinal_accel_g
            ELSE smoothed_longitudinal_accel_g
        END AS imu_longitudinal_accel_g,
        smoothed_lateral_accel_g AS imu_lateral_accel_g
    FROM imu_alignment
),
gforce AS (
    SELECT
        *,
        SQRT(
            POWER(imu_longitudinal_accel_g, 2)
            + POWER(imu_lateral_accel_g, 2)
        ) AS combined_g_force,
        COALESCE(speed_deriv_accel_g, imu_longitudinal_accel_g)
            AS effective_longitudinal_accel_g
    FROM aligned_imu
),
ambient_inputs AS (
    SELECT
        *,
        COALESCE(
            NULLIF(baro_pressure, 0),
            NULLIF(weather_pressure_hpa / 10.0, 0),
            101.325
        ) AS effective_baro_kpa,
        COALESCE(
            weather_temp_c,
            MIN(NULLIF(mat, 0)) OVER (PARTITION BY vehicle_id, drive_id),
            20.0
        ) AS effective_ambient_temp_c
    FROM gforce
),
drive_windows AS (
    SELECT
        *,
        MAX(elapsed_drive_time_s) OVER (
            PARTITION BY vehicle_id, drive_id
        ) AS max_drive_time_s,
        MIN(elapsed_drive_time_s) FILTER (WHERE rpm >= 650) OVER (
            PARTITION BY vehicle_id, drive_id
        ) AS first_engine_running_time_s,
        MAX(elapsed_drive_time_s) FILTER (WHERE rpm >= 650) OVER (
            PARTITION BY vehicle_id, drive_id
        ) AS last_engine_running_time_s
    FROM ambient_inputs
),
active_engine_windows AS (
    SELECT
        *,
        COALESCE(
            rpm >= 650
                AND elapsed_drive_time_s > first_engine_running_time_s + 2.0
                AND elapsed_drive_time_s < last_engine_running_time_s - 1.0,
            FALSE
        ) AS is_active_engine_window
    FROM drive_windows
),
oil_pressure_targets AS (
    SELECT
        *,
        CASE
            WHEN NOT is_active_engine_window OR rpm < 650 THEN NULL
            WHEN rpm < 900 THEN 1.00
            WHEN rpm < 4000 THEN 1.00 + 0.71 * ((rpm - 900.0) / 1000.0)
            ELSE 3.20
        END AS min_safe_oil_pressure_target_bar,
        CASE
            WHEN is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
                THEN (oil_pressure / 100.0) / (rpm / 1000.0)
        END AS oil_pressure_per_1k_rpm_bar
    FROM active_engine_windows
),
metrics AS (
    SELECT
        *,
        afr - fuel_target_afr AS afr_error,
        "lambda" - fuel_target_lambda AS lambda_error,
        map - effective_baro_kpa AS boost_gauge_kpa,
        map - boost_target AS boost_error_kpa,
        timing_ignition - timing_base_ignition AS dynamic_timing_trim_deg,
        (effective_baro_kpa * 1000.0)
            / (287.05 * (effective_ambient_temp_c + 273.15))
            AS ambient_air_density_kg_m3,
        (map * 1000.0) / (287.05 * (NULLIF(mat, 0) + 273.15))
            AS manifold_charge_density_kg_m3,
        (effective_map * 1000.0)
            / (
                287.05
                * (NULLIF(air_charge_temperature_estimate, 0) + 273.15)
            )
            AS effective_charge_density_kg_m3,
        1.180 * (
            (99.0 / effective_baro_kpa)
            * SQRT((effective_ambient_temp_c + 273.15) / 298.15)
        ) - 0.180 AS sae_correction_factor,
        mat - weather_temp_c AS intercooler_heat_soak_delta_c
    FROM oil_pressure_targets
),
oil_pressure_metrics AS (
    SELECT
        *,
        CASE
            WHEN is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
                THEN oil_pressure / 100.0 - min_safe_oil_pressure_target_bar
        END AS oil_pressure_safety_margin_bar,
        CASE
            WHEN is_active_engine_window
              AND rpm >= 650
              AND oil_pressure / 100.0 > 0.1
              AND oil_pressure / 100.0 < min_safe_oil_pressure_target_bar
                THEN TRUE
            ELSE FALSE
        END AS is_low_oil_pressure_for_rpm
    FROM metrics
),
final_metrics AS (
    SELECT
        *,
        CASE
            WHEN is_clean_wot_pull AND map > 0
                THEN imu_longitudinal_accel_g / (map / 100.0)
        END AS instant_wot_accel_index_g_per_bar
    FROM oil_pressure_metrics
)
SELECT
    vehicle_id,
    drive_id,
    source_time_s,
    sampled_at,
    sampled_at_ts,
    event_date,
    imu_longitudinal_accel_g AS x_g,
    imu_lateral_accel_g AS y_g,
    accel_z_g AS z_g,
    accelerometer_source_file,
    telemetry_source_time_s,
    telemetry_sampled_at,
    telemetry_sample_age_ms,
    is_telemetry_fresh,
    telemetry_source_file,
    {% for col in telemetry_fields %}
    "{{ col }}",
    {% endfor %}
    map AS map_kpa,
    clt AS coolant_temp,
    mat AS intake_air_temp_c,
    vehicle_speed AS vehicle_speed_kph,
    oil_pressure AS oil_pressure_kpa,
    batt_v AS battery_voltage_v,
    gps_source_time_s,
    gps_sampled_at,
    gps_sample_age_ms,
    is_gps_fresh,
    gps_latitude AS latitude,
    gps_longitude AS longitude,
    gps_recorded_at,
    gps_heading_deg AS heading_deg,
    gps_speed_kmh,
    gps_lat_grid AS lat_grid,
    gps_lon_grid AS lon_grid,
    gps_hour_bucket,
    weather_hour_bucket,
    weather_sample_age_seconds,
    is_weather_fresh,
    weather_temp_c,
    weather_precipitation_mm,
    weather_pressure_hpa,
    weather_relative_humidity_pct,
    weather_wind_speed_ms,
    gps_source_file,
    has_ecu_speed,
    has_gps_speed,
    speed_source_mode,
    effective_speed_kmh,
    wheel_slip_delta_kmh,
    dt_s,
    step_distance_km,
    cumulative_drive_distance_km,
    elapsed_drive_time_s,
    max_drive_time_s,
    is_active_engine_window,
    oil_pressure_per_1k_rpm_bar,
    min_safe_oil_pressure_target_bar,
    oil_pressure_safety_margin_bar,
    is_low_oil_pressure_for_rpm,
    speed_deriv_accel_g,
    imu_longitudinal_accel_g,
    imu_lateral_accel_g,
    combined_g_force,
    effective_longitudinal_accel_g,
    afr_error,
    lambda_error,
    boost_gauge_kpa,
    boost_error_kpa,
    dynamic_timing_trim_deg,
    ambient_air_density_kg_m3,
    manifold_charge_density_kg_m3,
    effective_charge_density_kg_m3,
    sae_correction_factor,
    intercooler_heat_soak_delta_c,
    is_clean_wot_pull,
    instant_wot_accel_index_g_per_bar
FROM final_metrics
