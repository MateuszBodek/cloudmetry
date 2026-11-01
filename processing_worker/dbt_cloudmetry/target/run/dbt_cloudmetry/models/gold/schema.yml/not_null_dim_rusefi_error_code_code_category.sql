
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select code_category
from "memory"."main"."dim_rusefi_error_code"
where code_category is null



  
  
      
    ) dbt_internal_test