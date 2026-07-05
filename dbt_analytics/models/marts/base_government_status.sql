{{ config(materialized='view') }}

SELECT 
        employee_id,
        employee_name,
        is_saudi,
        gosi_status,
        mudad_status AS wps_status,
        gosi_salary,
        payroll_basic_salary,
        CASE WHEN gosi_status IS NOT NULL THEN 1 ELSE 0 END AS has_gosi_source,
        CASE WHEN mudad_status IS NOT NULL THEN 1 ELSE 0 END AS has_wps_source
    FROM {{ ref('base_compliance_current') }}
