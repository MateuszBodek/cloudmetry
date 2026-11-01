{{
    config(
        materialized='external',
        plugin='delta_merge',
        format='parquet',
        location=var('dbt_staging_uri') ~ '/' ~ var('batch_id') ~ '_dim_weather_conditions.parquet',
        options={},
        delta_merge_options={
            'location': var('gold_dim_weather_conditions_uri'),
            'key_columns': ['weather_key']
        }
    )
}}

-- depends_on: {{ ref('gold_drive_telemetry') }}

WITH drives AS (
    SELECT
        vehicle_id,
        drive_id,
        AVG(ambient_air_density_kg_m3) AS fallback_air_density_kg_m3,
        AVG(NULLIF(baro_pressure, 0)) AS fallback_baro_kpa
    FROM delta_scan('{{ var("gold_telemetry_uri") }}')
    GROUP BY vehicle_id, drive_id
),
weather_by_hour AS (
    SELECT
        vehicle_id,
        drive_id,
        weather_hour_bucket,
        AVG(weather_temp_c) AS weather_temp_c,
        AVG(NULLIF(weather_pressure_hpa, 0)) AS weather_pressure_hpa,
        AVG(weather_precipitation_mm) AS weather_precipitation_mm,
        AVG(weather_relative_humidity_pct) AS weather_relative_humidity_pct,
        AVG(weather_wind_speed_ms) AS weather_wind_speed_ms,
        AVG(ambient_air_density_kg_m3) AS ambient_air_density_kg_m3
    FROM delta_scan('{{ var("gold_telemetry_uri") }}')
    WHERE weather_hour_bucket IS NOT NULL
    GROUP BY vehicle_id, drive_id, weather_hour_bucket
),
weather_by_drive AS (
    SELECT
        vehicle_id,
        drive_id,
        AVG(weather_temp_c) AS ambient_temp_c,
        AVG(weather_pressure_hpa / 10.0) AS baro_pressure_kpa,
        SUM(weather_precipitation_mm) AS total_precipitation_mm,
        AVG(weather_relative_humidity_pct) AS relative_humidity_pct,
        AVG(weather_wind_speed_ms) AS avg_wind_speed_ms,
        AVG(ambient_air_density_kg_m3) AS ambient_air_density_kg_m3
    FROM weather_by_hour
    GROUP BY vehicle_id, drive_id
)
SELECT
    md5(drives.vehicle_id || '|' || drives.drive_id) AS weather_key,
    drives.vehicle_id,
    drives.drive_id,
    CASE
        WHEN ambient_temp_c IS NULL THEN 'Unknown'
        WHEN ambient_temp_c < 10 THEN 'Cold (<10 C)'
        WHEN ambient_temp_c < 25 THEN 'Mild (10-25 C)'
        WHEN ambient_temp_c < 35 THEN 'Warm (25-35 C)'
        ELSE 'Hot (>=35 C)'
    END AS ambient_temp_band,
    CASE
        WHEN COALESCE(
            weather_by_drive.baro_pressure_kpa,
            drives.fallback_baro_kpa
        ) IS NULL THEN 'Unknown'
        WHEN COALESCE(
            weather_by_drive.baro_pressure_kpa,
            drives.fallback_baro_kpa
        ) < 95 THEN 'Low (<95 kPa)'
        WHEN COALESCE(
            weather_by_drive.baro_pressure_kpa,
            drives.fallback_baro_kpa
        ) < 103 THEN 'Normal (95-103 kPa)'
        ELSE 'High (>=103 kPa)'
    END AS baro_pressure_band,
    CASE
        WHEN total_precipitation_mm IS NULL THEN 'Unknown'
        WHEN total_precipitation_mm = 0 THEN 'Dry'
        ELSE 'Precipitation'
    END AS precipitation_status,
    CASE
        WHEN avg_wind_speed_ms IS NULL THEN 'Unknown'
        WHEN avg_wind_speed_ms < 2 THEN 'Low Wind (<2 m/s)'
        WHEN avg_wind_speed_ms < 6 THEN 'Moderate Wind (2-6 m/s)'
        ELSE 'High Wind (>=6 m/s)'
    END AS wind_intensity_band,
    CASE
        WHEN COALESCE(
            weather_by_drive.ambient_air_density_kg_m3,
            drives.fallback_air_density_kg_m3
        ) IS NULL THEN 'Unknown'
        WHEN COALESCE(
            weather_by_drive.ambient_air_density_kg_m3,
            drives.fallback_air_density_kg_m3
        ) > 1.23
            THEN 'Prime Boost Weather (High Density > 1.23 kg/m3)'
        WHEN COALESCE(
            weather_by_drive.ambient_air_density_kg_m3,
            drives.fallback_air_density_kg_m3
        ) >= 1.18
            THEN 'Standard Atmosphere (1.18 - 1.23 kg/m3)'
        ELSE 'Hot / Low Air Density (< 1.18 kg/m3)'
    END AS boost_weather_class
FROM drives
LEFT JOIN weather_by_drive USING (vehicle_id, drive_id)
