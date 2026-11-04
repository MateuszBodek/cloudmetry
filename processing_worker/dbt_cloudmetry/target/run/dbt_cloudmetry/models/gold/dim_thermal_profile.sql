
      create or replace view "memory"."main"."dim_thermal_profile__dbt_int" as (
        select * from read_parquet('s3://silver/_dbt_staging/a696ccbb2baa4eafa102c01f890ad05a_dim_thermal_profile.parquet', union_by_name=False)
        -- if relation is empty, filter by all columns having null values
        
      );
    