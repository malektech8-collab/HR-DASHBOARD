{{ config(materialized='view') }}

SELECT 
        e.employee_id,
        e.employee_name,
        e.nationality,
        e.is_saudi,
        e.company,
        e.department,
        e.project,
        e.cost_center,
        e.job_title,
        e.employment_type,
        c.qiwa_status,
        c.gosi_status,
        c.mudad_status,
        c.contract_authenticated,
        c.gosi_salary,
        c.payroll_basic_salary,
        c.occupation_code,
        c.occupation_match_status,
        c.work_permit_expiry,
        -- FROM THE EMPLOYEES SIDE. iqama_expiry moved to the employees
        -- contract (the period test: it changes when the iqama is
        -- reissued, not when the month turns). Taking it here means the
        -- seven models reading it through this view need no edit - the
        -- same reason stg_employees resolves `project` in one place.
        e.iqama_expiry,
        e.iqama_occupation,
        c.health_insurance_status
    FROM {{ ref('base_active_workforce') }} e
    LEFT JOIN {{ ref('stg_compliance') }} c ON e.employee_id = c.employee_id AND c.period = '{{ var('report_month') }}'
