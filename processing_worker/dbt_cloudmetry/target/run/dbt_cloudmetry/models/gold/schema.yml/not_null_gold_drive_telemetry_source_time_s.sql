
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select source_time_s
from "memory"."main"."gold_drive_telemetry"
where source_time_s is null



  
  
      
    ) dbt_internal_test