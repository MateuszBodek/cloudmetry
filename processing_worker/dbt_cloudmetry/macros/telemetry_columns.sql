{% macro telemetry_columns() %}
  {% for col in var('telemetry_columns') %}
    TRY_CAST(json_extract_string(data_json, '$.{{ col }}') AS DOUBLE) AS "{{ col }}"{% if not loop.last %},{% endif %}
  {% endfor %}
{% endmacro %}
