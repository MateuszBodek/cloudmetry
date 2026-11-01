{{
    config(
        materialized='external',
        plugin='delta_merge',
        format='parquet',
        location=var('dbt_staging_uri') ~ '/' ~ var('batch_id') ~ '_dim_fuel_profile.parquet',
        options={},
        delta_merge_options={
            'location': var('gold_dim_fuel_profile_uri'),
            'key_columns': ['fuel_profile_key']
        }
    )
}}

-- depends_on: {{ ref('gold_drive_telemetry') }}

WITH fuel_trim_inputs AS (
    SELECT
        *,
        AVG(stft_bank_1) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) OVER (PARTITION BY vehicle_id, drive_id) AS avg_stft_bank_1,
        AVG(ltft_bank_1) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) OVER (PARTITION BY vehicle_id, drive_id) AS avg_ltft_bank_1,
        AVG(ego_cor1) FILTER (
            WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
        ) OVER (PARTITION BY vehicle_id, drive_id) AS avg_ego_cor1,
        COUNT(*) FILTER (
            WHERE rpm >= 500
              AND COALESCE(dfco_active, 0) = 0
              AND stft_bank_1 IS NOT NULL
              AND stft_bank_1 NOT IN (0.0, 100.0)
        ) OVER (PARTITION BY vehicle_id, drive_id) AS non_sentinel_stft_sample_count
    FROM delta_scan('{{ var("gold_telemetry_uri") }}')
),
fuel_trim_normalized AS (
    SELECT
        *,
        CASE
            WHEN stft_bank_1 IS NULL THEN 0.0
            WHEN avg_stft_bank_1 BETWEEN 50.0 AND 150.0
                THEN stft_bank_1 - 100.0
            WHEN avg_stft_bank_1 BETWEEN 0.5 AND 1.5
                THEN (stft_bank_1 - 1.0) * 100.0
            ELSE stft_bank_1
        END AS stft_deviation_pct,
        CASE
            WHEN ltft_bank_1 IS NULL THEN 0.0
            WHEN avg_ltft_bank_1 BETWEEN 50.0 AND 150.0
                THEN ltft_bank_1 - 100.0
            WHEN avg_ltft_bank_1 BETWEEN 0.5 AND 1.5
                THEN (ltft_bank_1 - 1.0) * 100.0
            ELSE ltft_bank_1
        END AS ltft_deviation_pct,
        CASE
            WHEN ego_cor1 IS NULL THEN 0.0
            WHEN avg_ego_cor1 BETWEEN 50.0 AND 150.0
                THEN ego_cor1 - 100.0
            WHEN avg_ego_cor1 BETWEEN 0.5 AND 1.5
                THEN (ego_cor1 - 1.0) * 100.0
            ELSE ego_cor1
        END AS ego_deviation_pct
    FROM fuel_trim_inputs
),
drive_fuel AS (
    SELECT
        vehicle_id,
        drive_id,
        MAX(cumulative_drive_distance_km) AS total_distance_km,
        MAX(fuel_total_consumed) - MIN(fuel_total_consumed) AS measured_fuel_g,
        SUM(fuel_flow_rate * dt_s) / 750.0 AS integrated_fuel_l,
        CASE
            WHEN MAX(non_sentinel_stft_sample_count) = 0
                THEN AVG(ABS(ego_deviation_pct)) FILTER (
                    WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
                )
            ELSE AVG(ABS(stft_deviation_pct + ltft_deviation_pct)) FILTER (
                WHERE rpm >= 500 AND COALESCE(dfco_active, 0) = 0
            )
        END AS avg_abs_fuel_trim_pct,
        AVG(effective_speed_kmh) AS avg_speed_kmh,
        AVG(tps) AS avg_tps_pct,
        SUM(CASE WHEN is_clean_wot_pull THEN COALESCE(dt_s, 0) ELSE 0 END)
            * 100.0 / NULLIF(SUM(COALESCE(dt_s, 0)), 0) AS wot_time_pct
    FROM fuel_trim_normalized
    GROUP BY vehicle_id, drive_id
),
profile AS (
    SELECT
        *,
        COALESCE(NULLIF(measured_fuel_g, 0) / 750.0, integrated_fuel_l)
            AS total_fuel_consumed_l,
        COALESCE(NULLIF(measured_fuel_g, 0) / 750.0, integrated_fuel_l)
            / NULLIF(total_distance_km, 0) * 100.0 AS fuel_consumption_l_100km
    FROM drive_fuel
)
SELECT
    md5(vehicle_id || '|' || drive_id) AS fuel_profile_key,
    vehicle_id,
    drive_id,
    CASE
        WHEN total_distance_km < 0.2 OR fuel_consumption_l_100km IS NULL
            THEN 'Stationary / N/A'
        WHEN fuel_consumption_l_100km < 8 THEN '<8 L/100km'
        WHEN fuel_consumption_l_100km < 12 THEN '8-12 L/100km'
        WHEN fuel_consumption_l_100km < 18 THEN '12-18 L/100km'
        ELSE '>18 L/100km'
    END AS consumption_band,
    CASE
        WHEN wot_time_pct >= 20 OR avg_tps_pct >= 55 THEN 'Track / WOT Heavy'
        WHEN avg_tps_pct >= 35 OR avg_speed_kmh >= 60 THEN 'Spirited / Boost'
        WHEN avg_tps_pct < 20 AND avg_speed_kmh >= 25 THEN 'Eco / Cruise'
        ELSE 'Mixed Street'
    END AS driving_style_category,
    CASE
        WHEN avg_abs_fuel_trim_pct < 3 THEN 'Well Tuned (<3% trim)'
        WHEN avg_abs_fuel_trim_pct <= 8 THEN 'Moderate Correction (3-8% trim)'
        ELSE 'Needs Retune (>8% trim)'
    END AS afr_tuning_health_band
FROM profile
