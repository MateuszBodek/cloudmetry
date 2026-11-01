
    
    

with child as (
    select thermal_profile_key as from_field
    from "memory"."main"."fct_drive_summary"
    where thermal_profile_key is not null
),

parent as (
    select thermal_profile_key as to_field
    from "memory"."main"."dim_thermal_profile"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


