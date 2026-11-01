
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select drive_meta_key as from_field
    from "memory"."main"."fct_drive_summary"
    where drive_meta_key is not null
),

parent as (
    select drive_meta_key as to_field
    from "memory"."main"."dim_drive_meta"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test