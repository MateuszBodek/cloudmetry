
      create or replace view "memory"."main"."dim_thermal_profile__dbt_int" as (
        select * from read_parquet('s3://silver/_dbt_staging/c5a46b420cbd4133a7aae602aa05f963_dim_thermal_profile.parquet', union_by_name=False)
        -- if relation is empty, filter by all columns having null values
        
      );
    