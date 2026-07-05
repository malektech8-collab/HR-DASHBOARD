{{ config(materialized='view') }}

SELECT 
        '2026-04' AS month,
        COUNT(DISTINCT employee_id) AS active_headcount
    FROM {{ ref('stg_employees') }}
    WHERE joining_date <= '2026-04-30' 
      AND (termination_date IS NULL OR termination_date > '2026-04-30')
    UNION ALL
    SELECT 
        '2026-05' AS month,
        COUNT(DISTINCT employee_id) AS active_headcount
    FROM {{ ref('stg_employees') }}
    WHERE joining_date <= '2026-05-31' 
      AND (termination_date IS NULL OR termination_date > '2026-05-31')
    UNION ALL
    SELECT 
        '2026-06' AS month,
        COUNT(DISTINCT employee_id) AS active_headcount
    FROM {{ ref('base_active_workforce') }}
