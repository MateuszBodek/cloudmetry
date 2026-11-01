

-- depends_on: "memory"."main"."gold_drive_telemetry"

WITH drive_stats AS (
    SELECT
        vehicle_id,
        drive_id,
        MIN(event_date) AS drive_date,
        MIN(sampled_at_ts) AS start_timestamp,
        MAX(sampled_at_ts) AS end_timestamp,
        MAX(elapsed_drive_time_s) AS duration_seconds,
        ARG_MAX(speed_source_mode, sampled_at_ts) AS speed_telemetry_mode
    FROM (
        SELECT
            vehicle_id,
            drive_id,
            event_date,
            TRY_CAST(sampled_at AS TIMESTAMPTZ) AS sampled_at_ts,
            elapsed_drive_time_s,
            speed_source_mode
        FROM delta_scan('s3://gold/drive_telemetry')
    )
    GROUP BY vehicle_id, drive_id
)
SELECT
    md5(vehicle_id || '|' || drive_id) AS drive_meta_key,
    vehicle_id,
    drive_id,
    drive_date,
    dayofweek(drive_date) AS day_of_week,
    CASE
        WHEN hour(start_timestamp AT TIME ZONE 'Europe/Warsaw') BETWEEN 5 AND 11
            THEN 'Morning'
        WHEN hour(start_timestamp AT TIME ZONE 'Europe/Warsaw') BETWEEN 12 AND 16
            THEN 'Afternoon'
        WHEN hour(start_timestamp AT TIME ZONE 'Europe/Warsaw') BETWEEN 17 AND 21
            THEN 'Evening'
        ELSE 'Night'
    END AS time_of_day_bucket,
    start_timestamp,
    end_timestamp,
    duration_seconds,
    CASE
        WHEN duration_seconds < 300 THEN 'Repark / Micro-Trip (<5 min)'
        WHEN duration_seconds <= 900 THEN 'Short Trip (5-15 min)'
        WHEN duration_seconds <= 2700 THEN 'Standard Trip (15-45 min)'
        ELSE 'Long Session (>45 min)'
    END AS trip_duration_category,
    duration_seconds < 300 AS is_repark_or_micro_trip_flag,
    CASE speed_telemetry_mode
        WHEN 'DUAL_ACTIVE' THEN 'Dual Sensor (ECU VSS + GPS)'
        WHEN 'GPS_ONLY' THEN 'GPS Speed Only (ECU VSS=0)'
        WHEN 'ECU_VSS_ONLY' THEN 'ECU VSS Only (No GPS)'
        ELSE 'No Valid Speed Sensor'
    END AS speed_telemetry_mode
FROM drive_stats