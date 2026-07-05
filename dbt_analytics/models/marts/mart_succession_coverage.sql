{{ config(materialized='view') }}

SELECT
        s.critical_role_id,
        s.role_title,
        COUNT(DISTINCT s.successor_employee_id) FILTER (
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        ) AS valid_successor_count,
        CASE WHEN COUNT(DISTINCT s.successor_employee_id) FILTER (
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        ) > 0 THEN 'Covered' ELSE 'Not Covered' END AS coverage_status
    FROM {{ ref('base_succession_plans_current') }} s
    GROUP BY s.critical_role_id, s.role_title
