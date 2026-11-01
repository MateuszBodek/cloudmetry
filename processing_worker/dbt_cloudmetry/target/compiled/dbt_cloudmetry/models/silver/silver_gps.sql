

WITH gps AS (
    SELECT
        vehicle_id,
        drive_id,
        source_time_s,
        sampled_at,
        CAST(sampled_at AS DATE) AS event_date,
        TRY_CAST(json_extract_string(data_json, '$.latitude') AS DOUBLE) AS latitude,
        TRY_CAST(json_extract_string(data_json, '$.longitude') AS DOUBLE) AS longitude,
        TRY_CAST(
            to_timestamp(
                TRY_CAST(
                    json_extract_string(data_json, '$.recorded_at_epoch_s') AS DOUBLE
                )
            ) AS TIMESTAMPTZ
        ) AS recorded_at,
        TRY_CAST(json_extract_string(data_json, '$.heading_deg') AS DOUBLE)
            AS heading_deg,
        COALESCE(
            TRY_CAST(json_extract_string(data_json, '$.speed_kph') AS DOUBLE),
            TRY_CAST(json_extract_string(data_json, '$.speed') AS DOUBLE) * 3.6
        ) AS speed_kph,
        ROUND(
            TRY_CAST(json_extract_string(data_json, '$.latitude') AS DOUBLE), 2
        ) AS lat_grid,
        ROUND(
            TRY_CAST(json_extract_string(data_json, '$.longitude') AS DOUBLE), 2
        ) AS lon_grid,
        source_file
    FROM "memory"."main"."stg_bronze_deduped"
    WHERE stream = 'gps'
),
gps_with_hour AS (
    SELECT
        *,
        date_trunc(
            'hour',
            timezone('Europe/Warsaw', recorded_at)
        ) AS hour_bucket
    FROM gps
)
SELECT
    gps.vehicle_id,
    gps.drive_id,
    gps.source_time_s,
    gps.sampled_at,
    gps.event_date,
    gps.latitude,
    gps.longitude,
    gps.recorded_at,
    gps.heading_deg,
    gps.speed_kph,
    gps.lat_grid,
    gps.lon_grid,
    gps.hour_bucket,
    weather.hour_bucket AS weather_hour_bucket,
    weather.temperature_2m,
    weather.precipitation,
    weather.surface_pressure_hpa,
    weather.relative_humidity_2m,
    gps.source_file
FROM gps_with_hour AS gps
LEFT JOIN delta_scan('s3://silver/weather') AS weather
  ON gps.lat_grid = weather.lat_grid
 AND gps.lon_grid = weather.lon_grid
 AND gps.hour_bucket = weather.hour_bucket