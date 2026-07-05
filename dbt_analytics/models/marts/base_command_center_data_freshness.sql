{{ config(materialized='view') }}

SELECT '{{ ref('stg_payroll') }}' AS module_key, '{{ ref('stg_payroll') }}' AS source_table, CAST(MAX(payroll_period) AS VARCHAR) AS max_source_date FROM {{ ref('stg_payroll') }} UNION ALL
    SELECT '{{ ref('stg_attendance') }}' AS module_key, '{{ ref('stg_attendance') }}' AS source_table, CAST(MAX(attendance_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_attendance') }} UNION ALL
    SELECT 'recruitment' AS module_key, '{{ ref('stg_recruitment_requisitions') }}' AS source_table, CAST(MAX(approval_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_recruitment_requisitions') }} UNION ALL
    SELECT 'talent' AS module_key, '{{ ref('stg_performance_reviews') }}' AS source_table, CAST(MAX(completed_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_performance_reviews') }} UNION ALL
    SELECT '{{ ref('stg_compliance') }}' AS module_key, '{{ ref('stg_compliance') }}' AS source_table, CAST(MAX(period) AS VARCHAR) AS max_source_date FROM {{ ref('stg_compliance') }} UNION ALL
    SELECT 'er' AS module_key, '{{ ref('stg_employee_relations') }}' AS source_table, CAST(MAX(COALESCE(closed_date, created_date)) AS VARCHAR) AS max_source_date FROM {{ ref('stg_employee_relations') }} UNION ALL
    SELECT 'workforce' AS module_key, '{{ ref('stg_employees') }}' AS source_table, CAST(MAX(joining_date) AS VARCHAR) AS max_source_date FROM {{ ref('stg_employees') }}
