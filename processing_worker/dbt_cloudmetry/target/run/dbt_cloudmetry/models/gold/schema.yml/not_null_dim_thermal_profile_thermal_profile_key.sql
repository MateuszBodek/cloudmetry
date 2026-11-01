
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select thermal_profile_key
from "memory"."main"."dim_thermal_profile"
where thermal_profile_key is null



  
  
      
    ) dbt_internal_test