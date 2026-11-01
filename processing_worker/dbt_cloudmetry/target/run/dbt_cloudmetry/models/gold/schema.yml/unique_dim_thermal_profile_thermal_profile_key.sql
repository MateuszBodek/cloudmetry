
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    thermal_profile_key as unique_field,
    count(*) as n_records

from "memory"."main"."dim_thermal_profile"
where thermal_profile_key is not null
group by thermal_profile_key
having count(*) > 1



  
  
      
    ) dbt_internal_test