
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select dominant_fuel_cut_key
from "memory"."main"."fct_drive_summary"
where dominant_fuel_cut_key is null



  
  
      
    ) dbt_internal_test