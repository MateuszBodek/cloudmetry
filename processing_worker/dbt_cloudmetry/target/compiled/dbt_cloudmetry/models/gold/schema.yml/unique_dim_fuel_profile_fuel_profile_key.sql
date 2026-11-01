
    
    

select
    fuel_profile_key as unique_field,
    count(*) as n_records

from "memory"."main"."dim_fuel_profile"
where fuel_profile_key is not null
group by fuel_profile_key
having count(*) > 1


