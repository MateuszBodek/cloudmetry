

SELECT
    vehicle_id,
    drive_id,
    source_time_s,
    sampled_at,
    CAST(sampled_at AS DATE) AS event_date,
    TRY_CAST(json_extract_string(data_json, '$.x_g') AS DOUBLE) AS x_g,
    TRY_CAST(json_extract_string(data_json, '$.y_g') AS DOUBLE) AS y_g,
    TRY_CAST(json_extract_string(data_json, '$.z_g') AS DOUBLE) AS z_g,
    source_file
FROM "memory"."main"."stg_bronze_deduped"
WHERE stream = 'accelerometer'