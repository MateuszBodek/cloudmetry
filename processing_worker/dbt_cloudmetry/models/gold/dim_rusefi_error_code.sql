{{
    config(
        materialized='external',
        plugin='delta_merge',
        format='parquet',
        location=var('dbt_staging_uri') ~ '/' ~ var('batch_id') ~ '_dim_rusefi_error_code.parquet',
        options={},
        delta_merge_options={
            'location': var('gold_dim_rusefi_error_code_uri'),
            'key_columns': ['error_code_key']
        }
    )
}}

SELECT
    raw_code_id AS error_code_key,
    raw_code_id,
    code_category,
    code_name,
    code_description_pl,
    severity_level
FROM {{ ref('rusefi_error_codes') }}
