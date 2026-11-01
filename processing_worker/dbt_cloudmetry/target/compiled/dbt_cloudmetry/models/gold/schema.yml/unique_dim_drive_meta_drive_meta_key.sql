
    
    

select
    drive_meta_key as unique_field,
    count(*) as n_records

from "memory"."main"."dim_drive_meta"
where drive_meta_key is not null
group by drive_meta_key
having count(*) > 1


