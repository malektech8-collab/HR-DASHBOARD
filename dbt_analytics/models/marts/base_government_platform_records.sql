{{ config(materialized='view') }}

SELECT 
        c.employee_id,
        c.period,
        c.qiwa_status,
        c.gosi_status,
        c.mudad_status,
        c.contract_authenticated,
        c.gosi_salary,
        c.payroll_basic_salary,
        c.occupation_code,
        c.occupation_match_status,
        c.work_permit_expiry,
        c.iqama_expiry,
        c.health_insurance_status,
        e.employee_name,
        e.status AS employee_status,
        e.is_saudi,
        e.nationality,
        e.project,
        e.department,
        e.cost_center,
        CASE 
            WHEN e.employee_id IS NULL THEN 'Unknown Employee'
            WHEN e.status = 'Active' THEN 'Active Employee'
            WHEN e.status = 'Inactive' THEN 'Inactive Employee'
            WHEN e.status = 'Terminated' THEN 'Terminated Employee'
            ELSE 'Unknown Status Employee'
        END AS record_classification
    FROM {{ ref('stg_compliance') }} c
    LEFT JOIN {{ ref('base_employees_deduplicated') }} e ON c.employee_id = e.employee_id
    WHERE c.period = '{{ var('report_month') }}'
