
    
    

with child as (
    select weather_key as from_field
    from "memory"."main"."fct_drive_summary"
    where weather_key is not null
),

parent as (
    select weather_key as to_field
    from "memory"."main"."dim_weather_conditions"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


