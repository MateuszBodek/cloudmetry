
    
    

select
    drive_id as unique_field,
    count(*) as n_records

from "memory"."main"."fct_drive_summary"
where drive_id is not null
group by drive_id
having count(*) > 1


