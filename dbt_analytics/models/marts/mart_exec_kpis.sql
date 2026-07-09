{{ config(materialized='view') }}

WITH hc AS (
        SELECT COUNT(DISTINCT employee_id) AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE status = 'Active'
    ),
    jn AS (
        SELECT COUNT(DISTINCT employee_id) AS joiners_count
        FROM {{ ref('stg_employees') }}
        WHERE joining_date >= '{{ var('report_month_start') }}' AND joining_date <= '{{ var('report_month_end') }}'
    ),
    lv AS (
        SELECT COUNT(DISTINCT employee_id) AS leavers_count
        FROM {{ ref('stg_employees') }}
        WHERE termination_date >= '{{ var('report_month_start') }}' AND termination_date <= '{{ var('report_month_end') }}'
    ),
    pay AS (
        SELECT
            COALESCE(SUM(gross_pay), 0.0) AS payroll_cost,
            COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost
        FROM {{ ref('stg_payroll') }}
        WHERE payroll_period = '{{ var('report_month') }}'
    ),
    att AS (
        SELECT COALESCE(SUM(absence_days), 0.0) AS absence_days
        FROM {{ ref('stg_attendance') }}
        WHERE attendance_date >= '{{ var('report_month_start') }}' AND attendance_date <= '{{ var('report_month_end') }}'
    ),
    dq AS (
        SELECT 
            1.0 - (CAST(COUNT(*) AS FLOAT) / (SELECT COALESCE(NULLIF(COUNT(DISTINCT employee_id), 0), 1) * 8.0 FROM {{ ref('stg_employees') }})) AS data_quality_score
        FROM {{ ref('stg_data_quality') }}
    )
    SELECT
        '{{ var('report_month') }}' AS report_month,
        hc.active_headcount,
        jn.joiners_count,
        lv.leavers_count,
        CASE 
            WHEN hc.active_headcount = 0 THEN 0.0 
            ELSE CAST(lv.leavers_count AS FLOAT) / hc.active_headcount 
        END AS turnover_rate,
        pay.payroll_cost,
        pay.overtime_cost,
        att.absence_days,
        dq.data_quality_score
    FROM hc, jn, lv, pay, att, dq
