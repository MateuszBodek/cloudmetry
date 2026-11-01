
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select fuel_profile_key
from "memory"."main"."fct_drive_summary"
where fuel_profile_key is null



  
  
      
    ) dbt_internal_test