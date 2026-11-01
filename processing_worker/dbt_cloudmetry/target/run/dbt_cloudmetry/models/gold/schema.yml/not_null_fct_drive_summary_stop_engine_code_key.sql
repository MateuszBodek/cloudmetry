
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select stop_engine_code_key
from "memory"."main"."fct_drive_summary"
where stop_engine_code_key is null



  
  
      
    ) dbt_internal_test