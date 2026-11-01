
    
    

select
    raw_code_id as unique_field,
    count(*) as n_records

from "memory"."main"."rusefi_error_codes"
where raw_code_id is not null
group by raw_code_id
having count(*) > 1


