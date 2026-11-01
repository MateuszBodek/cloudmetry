
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select severity_level
from "memory"."main"."rusefi_error_codes"
where severity_level is null



  
  
      
    ) dbt_internal_test