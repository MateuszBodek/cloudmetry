
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select drive_meta_key
from "memory"."main"."fct_drive_summary"
where drive_meta_key is null



  
  
      
    ) dbt_internal_test