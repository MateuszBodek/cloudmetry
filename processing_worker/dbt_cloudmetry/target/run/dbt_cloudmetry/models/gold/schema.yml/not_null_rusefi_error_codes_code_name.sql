
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select code_name
from "memory"."main"."rusefi_error_codes"
where code_name is null



  
  
      
    ) dbt_internal_test