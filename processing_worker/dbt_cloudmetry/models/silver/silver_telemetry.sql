{{
    config(
        materialized='external',
        plugin='delta_merge',
        format='parquet',
        location=var('dbt_staging_uri') ~ '/' ~ var('batch_id') ~ '_silver_telemetry.parquet',
        options={},
        delta_merge_options={
            'location': var('silver_telemetry_uri'),
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
    {{ telemetry_columns() }},
    source_file
FROM {{ ref('stg_bronze_deduped') }}
WHERE stream = 'telemetry'
