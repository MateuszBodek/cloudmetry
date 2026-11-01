
    
    

select
    weather_key as unique_field,
    count(*) as n_records

from "memory"."main"."dim_weather_conditions"
where weather_key is not null
group by weather_key
having count(*) > 1


