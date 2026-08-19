{{ config(materialized='view') }}

SELECT 
        c.employee_id,
        c.period,
        c.qiwa_status,
        c.gosi_status,
        c.mudad_status,
        c.contract_authenticated,
        c.gosi_salary,
        -- From the PAYROLL domain now, via base_compliance_current. The
        -- name is unchanged because the meaning is.
        pay.basic_salary AS payroll_basic_salary,
        c.occupation_code,
        c.occupation_match_status,
        c.work_permit_expiry,
        e.iqama_expiry,   -- employees now, see base_compliance_current
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
    -- Payroll joined directly rather than through base_compliance_current:
    -- this model is COMPLIANCE-FIRST on purpose, so a compliance row for an
    -- unknown employee keeps its row and its 'Unknown Employee' classification.
    -- Reading through the employees-first view would silently drop exactly the
    -- rows this model exists to surface.
    LEFT JOIN (
        SELECT employee_id, MAX(basic_salary) AS basic_salary
        FROM {{ ref('base_payroll_current') }}
        GROUP BY employee_id
    ) pay ON c.employee_id = pay.employee_id
    WHERE c.period = '{{ var('report_month') }}'
