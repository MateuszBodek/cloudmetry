
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select error_code_key
from "memory"."main"."dim_rusefi_error_code"
where error_code_key is null



  
  
      
    ) dbt_internal_test