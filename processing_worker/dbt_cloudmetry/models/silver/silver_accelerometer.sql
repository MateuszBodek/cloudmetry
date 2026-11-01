{{
    config(
        materialized='external',
        plugin='delta_merge',
        format='parquet',
        location=var('dbt_staging_uri') ~ '/' ~ var('batch_id') ~ '_silver_accelerometer.parquet',
        options={},
        delta_merge_options={
            'location': var('silver_accelerometer_uri'),
            'key_columns': ['vehicle_id', 'drive_id', 'source_time_s'],
            'partition_by': ['event_date']
        }
    )
}}

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
FROM {{ ref('stg_bronze_deduped') }}
WHERE stream = 'accelerometer'
