{{ config(materialized='view') }}

WITH raw_fresh AS (
        SELECT 
            f.module_key,
            f.source_table,
            f.max_source_date,
            CASE 
                WHEN f.max_source_date IS NULL THEN TRUE
                WHEN f.module_key = '{{ ref('stg_payroll') }}' AND f.max_source_date < c.report_month THEN TRUE
                WHEN f.module_key = '{{ ref('stg_attendance') }}' AND CAST(f.max_source_date AS DATE) < CAST(c.report_month_end AS DATE) THEN TRUE
                WHEN f.module_key = 'recruitment' AND f.max_source_date IS NULL THEN TRUE
                WHEN f.module_key = 'talent' AND f.max_source_date IS NULL THEN TRUE
                WHEN f.module_key = '{{ ref('stg_compliance') }}' AND f.max_source_date < c.report_month THEN TRUE
                WHEN f.module_key = 'er' AND f.max_source_date < c.report_month THEN TRUE
                ELSE FALSE
            END AS stale_flag,
            CASE 
                WHEN f.max_source_date IS NULL THEN 'No transaction data found in source table'
                WHEN f.module_key = '{{ ref('stg_payroll') }}' AND f.max_source_date < c.report_month THEN 'Payroll period ' || f.max_source_date || ' is older than expected report month ' || c.report_month
                WHEN f.module_key = '{{ ref('stg_attendance') }}' AND CAST(f.max_source_date AS DATE) < CAST(c.report_month_end AS DATE) THEN 'Attendance date ' || f.max_source_date || ' is older than expected report month end ' || c.report_month_end
                WHEN f.module_key = 'recruitment' AND f.max_source_date IS NULL THEN 'Recruitment requisitions data is missing'
                WHEN f.module_key = 'talent' AND f.max_source_date IS NULL THEN 'Talent reviews data is missing'
                WHEN f.module_key = '{{ ref('stg_compliance') }}' AND f.max_source_date < c.report_month THEN 'Compliance period ' || f.max_source_date || ' is older than expected report month ' || c.report_month
                WHEN f.module_key = 'er' AND f.max_source_date < c.report_month THEN 'ER period ' || f.max_source_date || ' is older than expected report month ' || c.report_month
                ELSE 'Data is current'
            END AS stale_reason
        FROM {{ ref('base_command_center_data_freshness') }} f
        CROSS JOIN {{ ref('base_command_center_report_context') }} c
    )
    SELECT 
        reg.module_key,
        reg.module_label,
        COALESCE(rf.source_table, CASE reg.module_key WHEN 'executive' THEN '{{ ref('mart_exec_kpis') }}' WHEN 'data-quality' THEN '{{ ref('stg_data_quality') }}' ELSE 'derived' END) AS source_table,
        COALESCE(rf.max_source_date, CAST(c.report_month_end AS VARCHAR)) AS max_source_date,
        c.last_refresh_timestamp,
        CASE reg.module_key
            WHEN 'executive' THEN COALESCE((SELECT bool_or(stale_flag) FROM raw_fresh), FALSE)
            WHEN 'data-quality' THEN FALSE
            ELSE COALESCE(rf.stale_flag, FALSE)
        END AS stale_flag,
        CASE reg.module_key
            WHEN 'executive' THEN 'Derived from overall system state'
            WHEN 'data-quality' THEN 'Refreshed during DQ pipeline run'
            ELSE COALESCE(rf.stale_reason, 'Data is current')
        END AS stale_reason
    FROM {{ ref('base_command_center_module_registry') }} reg
    CROSS JOIN {{ ref('base_command_center_report_context') }} c
    LEFT JOIN raw_fresh rf ON reg.module_key = rf.module_key
