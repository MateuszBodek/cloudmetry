
      create or replace view "memory"."main"."dim_rusefi_error_code__dbt_int" as (
        select * from read_parquet('s3://silver/_dbt_staging/c5a46b420cbd4133a7aae602aa05f963_dim_rusefi_error_code.parquet', union_by_name=False)
        -- if relation is empty, filter by all columns having null values
        
      );
    