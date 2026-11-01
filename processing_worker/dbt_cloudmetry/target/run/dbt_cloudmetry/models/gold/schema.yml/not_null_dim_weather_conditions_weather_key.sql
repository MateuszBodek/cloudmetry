
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select weather_key
from "memory"."main"."dim_weather_conditions"
where weather_key is null



  
  
      
    ) dbt_internal_test