
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select drive_id
from "memory"."main"."gold_drive_telemetry"
where drive_id is null



  
  
      
    ) dbt_internal_test