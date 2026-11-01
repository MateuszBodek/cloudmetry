
    
    

select
    error_code_key as unique_field,
    count(*) as n_records

from "memory"."main"."dim_rusefi_error_code"
where error_code_key is not null
group by error_code_key
having count(*) > 1


