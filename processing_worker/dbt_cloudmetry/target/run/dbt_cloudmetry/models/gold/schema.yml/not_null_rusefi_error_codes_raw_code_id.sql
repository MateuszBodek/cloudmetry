
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select raw_code_id
from "memory"."main"."rusefi_error_codes"
where raw_code_id is null



  
  
      
    ) dbt_internal_test