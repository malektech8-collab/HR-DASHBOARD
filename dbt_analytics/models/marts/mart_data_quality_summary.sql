{{ config(materialized='view') }}

SELECT 
        (SELECT data_quality_score FROM {{ ref('mart_exec_kpis') }}) AS data_quality_score,
        COUNT(CASE WHEN issue_type = 'Missing Manager' THEN 1 END) AS missing_manager_count,
        COUNT(CASE WHEN issue_type = 'Missing Project' THEN 1 END) AS missing_project_count,
        COUNT(CASE WHEN issue_type = 'Missing Cost Center' THEN 1 END) AS missing_cost_center_count,
        COUNT(CASE WHEN issue_type = 'Missing Nationality' THEN 1 END) AS missing_nationality_count,
        COUNT(CASE WHEN issue_type = 'Duplicate Employee ID' THEN 1 END) AS duplicate_employee_count,
        COUNT(CASE WHEN issue_type IN ('Inactive Employee with Payroll Record', 'Negative or Abnormal Payroll Value', 'Active Employee with Missing Salary') THEN 1 END) AS invalid_payroll_count
    FROM {{ ref('stg_data_quality') }}
