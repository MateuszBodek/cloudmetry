
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select first_warning_code_key
from "memory"."main"."fct_drive_summary"
where first_warning_code_key is null



  
  
      
    ) dbt_internal_test