
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select severity_level
from "memory"."main"."dim_rusefi_error_code"
where severity_level is null



  
  
      
    ) dbt_internal_test