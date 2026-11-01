{{ config(materialized='view') }}

SELECT DISTINCT ON (vehicle_id, drive_id, stream, source_time_s)
    vehicle_id,
    drive_id,
    stream,
    source_time_s,
    sampled_at,
    generated_at,
    data_json,
    filename AS source_file
FROM read_parquet(
    {{ var('bronze_files') }},
    filename = true,
    union_by_name = true
)
ORDER BY
    vehicle_id,
    drive_id,
    stream,
    source_time_s,
    TRY_CAST(generated_at AS TIMESTAMP) DESC NULLS LAST,
    filename DESC
