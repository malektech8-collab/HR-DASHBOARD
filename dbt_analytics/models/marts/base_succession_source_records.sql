{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY plan_id, critical_role_id, successor_employee_id) AS succession_plan_record_id,
        plan_id, critical_role_id, role_title, current_employee_id, successor_employee_id, readiness, flight_risk, is_critical
    FROM {{ ref('stg_succession_plans') }}
