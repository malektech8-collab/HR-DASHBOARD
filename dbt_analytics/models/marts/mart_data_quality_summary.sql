{{ config(materialized='view') }}

SELECT 
        (SELECT data_quality_score FROM {{ ref('mart_exec_kpis') }}) AS data_quality_score,
        -- THE SAME FACT, ANSWERED THE SAME WAY AS mart_workforce_kpis.
        --
        -- These counted ROWS ON THE DATA QUALITY PAGE, and with the column
        -- absent no such rows are produced - so the count came out 0 while
        -- the workforce mart said NULL. Two surfaces, one fact, two different
        -- answers, and 0 is the wrong one: it reads as "nobody is missing a
        -- cost centre" for a client who does not record cost centres at all.
        --
        -- The gate is the same dbt var, resolved from the same onboarding
        -- registry, so the two marts cannot drift apart again.
        CASE WHEN {{ var('has_manager_id_source_sql') }}
             THEN COUNT(CASE WHEN issue_type = 'Missing Manager' THEN 1 END)
        END AS missing_manager_count,
        COUNT(CASE WHEN issue_type = 'Missing Project' THEN 1 END) AS missing_project_count,
        CASE WHEN {{ var('has_cost_center_source_sql') }}
             THEN COUNT(CASE WHEN issue_type = 'Missing Cost Center' THEN 1 END)
        END AS missing_cost_center_count,
        COUNT(CASE WHEN issue_type = 'Missing Nationality' THEN 1 END) AS missing_nationality_count,
        COUNT(CASE WHEN issue_type = 'Duplicate Employee ID' THEN 1 END) AS duplicate_employee_count,
        COUNT(CASE WHEN issue_type IN ('Inactive Employee with Payroll Record', 'Negative or Abnormal Payroll Value', 'Active Employee with Missing Salary') THEN 1 END) AS invalid_payroll_count
    FROM {{ ref('stg_data_quality') }}
