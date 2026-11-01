
    
    

with child as (
    select first_warning_code_key as from_field
    from "memory"."main"."fct_drive_summary"
    where first_warning_code_key is not null
),

parent as (
    select error_code_key as to_field
    from "memory"."main"."dim_rusefi_error_code"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


