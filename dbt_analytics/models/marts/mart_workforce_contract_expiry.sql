{{ config(materialized='view') }}

WITH anchor AS (
        SELECT last_day(CAST(MAX(payroll_period) || '-01' AS DATE)) AS anchor_date
        FROM {{ ref('stg_payroll') }}
    )
    SELECT 
        COUNT(DISTINCT CASE WHEN contract_end_date < (SELECT anchor_date FROM anchor) THEN employee_id END) AS expired,
        COUNT(DISTINCT CASE WHEN contract_end_date BETWEEN (SELECT anchor_date FROM anchor) AND (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN employee_id END) AS "0_30",
        COUNT(DISTINCT CASE WHEN contract_end_date BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 31 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 60 DAY THEN employee_id END) AS "31_60",
        COUNT(DISTINCT CASE WHEN contract_end_date BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 61 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN employee_id END) AS "61_90",
        COUNT(DISTINCT CASE WHEN contract_end_date > (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN employee_id END) AS "90_plus",
        COUNT(DISTINCT CASE WHEN contract_end_date IS NULL THEN employee_id END) AS missing_date
    FROM {{ ref('base_active_workforce') }}
