{{ config(materialized='view') }}

SELECT 
        COALESCE(project, 'Missing Project') AS project,
        COUNT(DISTINCT employee_id) AS headcount,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        CASE WHEN {{ var('has_payroll_overtime_sql') }}
                 THEN COALESCE(SUM(overtime_amount), 0.0) END AS overtime_cost
    FROM {{ ref('base_payroll_current') }}
    GROUP BY project
