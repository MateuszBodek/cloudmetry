

SELECT
    vehicle_id,
    drive_id,
    source_time_s,
    sampled_at,
    CAST(sampled_at AS DATE) AS event_date,
    
  
    TRY_CAST(json_extract_string(data_json, '$.time') AS DOUBLE) AS "time",
  
    TRY_CAST(json_extract_string(data_json, '$.uptime') AS DOUBLE) AS "uptime",
  
    TRY_CAST(json_extract_string(data_json, '$.rpm') AS DOUBLE) AS "rpm",
  
    TRY_CAST(json_extract_string(data_json, '$.d_rpm') AS DOUBLE) AS "d_rpm",
  
    TRY_CAST(json_extract_string(data_json, '$.map') AS DOUBLE) AS "map",
  
    TRY_CAST(json_extract_string(data_json, '$.effective_map') AS DOUBLE) AS "effective_map",
  
    TRY_CAST(json_extract_string(data_json, '$.baro_pressure') AS DOUBLE) AS "baro_pressure",
  
    TRY_CAST(json_extract_string(data_json, '$.tps') AS DOUBLE) AS "tps",
  
    TRY_CAST(json_extract_string(data_json, '$.d_tps') AS DOUBLE) AS "d_tps",
  
    TRY_CAST(json_extract_string(data_json, '$.throttle_pedal_position') AS DOUBLE) AS "throttle_pedal_position",
  
    TRY_CAST(json_extract_string(data_json, '$.clt') AS DOUBLE) AS "clt",
  
    TRY_CAST(json_extract_string(data_json, '$.mat') AS DOUBLE) AS "mat",
  
    TRY_CAST(json_extract_string(data_json, '$.oil_temp') AS DOUBLE) AS "oil_temp",
  
    TRY_CAST(json_extract_string(data_json, '$.oil_pressure') AS DOUBLE) AS "oil_pressure",
  
    TRY_CAST(json_extract_string(data_json, '$.air_charge_temperature_estimate') AS DOUBLE) AS "air_charge_temperature_estimate",
  
    TRY_CAST(json_extract_string(data_json, '$.ecu_cpu_temperature') AS DOUBLE) AS "ecu_cpu_temperature",
  
    TRY_CAST(json_extract_string(data_json, '$.batt_v') AS DOUBLE) AS "batt_v",
  
    TRY_CAST(json_extract_string(data_json, '$.afr') AS DOUBLE) AS "afr",
  
    TRY_CAST(json_extract_string(data_json, '$.lambda') AS DOUBLE) AS "lambda",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_target_afr') AS DOUBLE) AS "fuel_target_afr",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_target_lambda') AS DOUBLE) AS "fuel_target_lambda",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_ve') AS DOUBLE) AS "fuel_ve",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_last_inj_pulse_width') AS DOUBLE) AS "fuel_last_inj_pulse_width",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_injector_duty_cycle') AS DOUBLE) AS "fuel_injector_duty_cycle",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_total_correction') AS DOUBLE) AS "fuel_total_correction",
  
    TRY_CAST(json_extract_string(data_json, '$.ego_cor1') AS DOUBLE) AS "ego_cor1",
  
    TRY_CAST(json_extract_string(data_json, '$.stft_bank_1') AS DOUBLE) AS "stft_bank_1",
  
    TRY_CAST(json_extract_string(data_json, '$.ltft_bank_1') AS DOUBLE) AS "ltft_bank_1",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_flow_rate') AS DOUBLE) AS "fuel_flow_rate",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_total_consumed') AS DOUBLE) AS "fuel_total_consumed",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_tps_ae_change') AS DOUBLE) AS "fuel_tps_ae_change",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_load') AS DOUBLE) AS "fuel_load",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_load') AS DOUBLE) AS "ignition_load",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_coil_charge_time') AS DOUBLE) AS "ignition_coil_charge_time",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_coil_duty_cycle') AS DOUBLE) AS "ignition_coil_duty_cycle",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_overcharge_canceled') AS DOUBLE) AS "ignition_overcharge_canceled",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_over_dwell_not_scheduled') AS DOUBLE) AS "ignition_over_dwell_not_scheduled",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_dwell_deviation') AS DOUBLE) AS "ignition_dwell_deviation",
  
    TRY_CAST(json_extract_string(data_json, '$.timing_ignition') AS DOUBLE) AS "timing_ignition",
  
    TRY_CAST(json_extract_string(data_json, '$.timing_base_ignition') AS DOUBLE) AS "timing_base_ignition",
  
    TRY_CAST(json_extract_string(data_json, '$.knock_current_level') AS DOUBLE) AS "knock_current_level",
  
    TRY_CAST(json_extract_string(data_json, '$.knock_retard') AS DOUBLE) AS "knock_retard",
  
    TRY_CAST(json_extract_string(data_json, '$.knock_count') AS DOUBLE) AS "knock_count",
  
    TRY_CAST(json_extract_string(data_json, '$.boost_target') AS DOUBLE) AS "boost_target",
  
    TRY_CAST(json_extract_string(data_json, '$.boost_output') AS DOUBLE) AS "boost_output",
  
    TRY_CAST(json_extract_string(data_json, '$.wastegate_position_sensor') AS DOUBLE) AS "wastegate_position_sensor",
  
    TRY_CAST(json_extract_string(data_json, '$.vehicle_speed') AS DOUBLE) AS "vehicle_speed",
  
    TRY_CAST(json_extract_string(data_json, '$.detected_gear') AS DOUBLE) AS "detected_gear",
  
    TRY_CAST(json_extract_string(data_json, '$.trigger_error_counter') AS DOUBLE) AS "trigger_error_counter",
  
    TRY_CAST(json_extract_string(data_json, '$.rev_limit_active') AS DOUBLE) AS "rev_limit_active",
  
    TRY_CAST(json_extract_string(data_json, '$.check_engine') AS DOUBLE) AS "check_engine",
  
    TRY_CAST(json_extract_string(data_json, '$.stop_engine_code') AS DOUBLE) AS "stop_engine_code",
  
    TRY_CAST(json_extract_string(data_json, '$.warning_last') AS DOUBLE) AS "warning_last",
  
    TRY_CAST(json_extract_string(data_json, '$.warning_counter') AS DOUBLE) AS "warning_counter",
  
    TRY_CAST(json_extract_string(data_json, '$.ign_cut_code') AS DOUBLE) AS "ign_cut_code",
  
    TRY_CAST(json_extract_string(data_json, '$.total_spark_cut') AS DOUBLE) AS "total_spark_cut",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_undecharge_warnings') AS DOUBLE) AS "ignition_undecharge_warnings",
  
    TRY_CAST(json_extract_string(data_json, '$.ignition_overcharge_warnings') AS DOUBLE) AS "ignition_overcharge_warnings",
  
    TRY_CAST(json_extract_string(data_json, '$.fuel_cut_code') AS DOUBLE) AS "fuel_cut_code",
  
    TRY_CAST(json_extract_string(data_json, '$.total_fuel_cut') AS DOUBLE) AS "total_fuel_cut",
  
    TRY_CAST(json_extract_string(data_json, '$.dfco_active') AS DOUBLE) AS "dfco_active",
  
    TRY_CAST(json_extract_string(data_json, '$.cpu_usage_percent') AS DOUBLE) AS "cpu_usage_percent",
  
    TRY_CAST(json_extract_string(data_json, '$.analog_sensors_supply_failure') AS DOUBLE) AS "analog_sensors_supply_failure"
  
,
    source_file
FROM "memory"."main"."stg_bronze_deduped"
WHERE stream = 'telemetry'