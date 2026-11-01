

SELECT
    raw_code_id AS error_code_key,
    raw_code_id,
    code_category,
    code_name,
    code_description_pl,
    severity_level
FROM "memory"."main"."rusefi_error_codes"