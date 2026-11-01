
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select raw_code_id
from "memory"."main"."dim_rusefi_error_code"
where raw_code_id is null



  
  
      
    ) dbt_internal_test