{{ config(materialized='view') }}

SELECT 'payroll' AS module_key, 'payroll' AS source_table, CAST(MAX(payroll_period) AS VARCHAR) AS max_source_date FROM {{ ref('stg_payroll') }} UNION ALL
    SELECT 'attendance' AS module_key, 'attendance' AS source_table, CAST(MAX(attendance_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_attendance') }} UNION ALL
    SELECT 'recruitment' AS module_key, 'recruitment_requisitions' AS source_table, CAST(MAX(approval_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_recruitment_requisitions') }} UNION ALL
    SELECT 'talent' AS module_key, 'performance_reviews' AS source_table, CAST(MAX(completed_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_performance_reviews') }} UNION ALL
    -- Freshness across the four platform files: the module is as fresh as
    -- the most recent period any of them carries.
    SELECT 'compliance' AS module_key, 'compliance' AS source_table, CAST(MAX(period) AS VARCHAR) AS max_source_date FROM (
        SELECT period FROM {{ ref('stg_compliance_gosi') }}
        UNION ALL SELECT period FROM {{ ref('stg_compliance_qiwa') }}
        UNION ALL SELECT period FROM {{ ref('stg_compliance_wps') }}
        UNION ALL SELECT period FROM {{ ref('stg_compliance_health') }}
    ) UNION ALL
    SELECT 'er' AS module_key, 'employee_relations' AS source_table, CAST(MAX(COALESCE(closed_date, created_date)) AS VARCHAR) AS max_source_date FROM {{ ref('stg_employee_relations') }} UNION ALL
    SELECT 'workforce' AS module_key, 'employees' AS source_table, CAST(MAX(joining_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_employees') }}
