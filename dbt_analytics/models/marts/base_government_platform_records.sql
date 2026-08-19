{{ config(materialized='view') }}

SELECT 
        c.employee_id,
        c.period,
        qiwa.qiwa_status,
        gosi.gosi_status,
        wps.mudad_status,
        qiwa.contract_authenticated,
        gosi.gosi_salary,
        -- From the PAYROLL domain now, via base_compliance_current. The
        -- name is unchanged because the meaning is.
        pay.basic_salary AS payroll_basic_salary,
        gosi.occupation_code,
        gosi.occupation_match_status,
        qiwa.work_permit_expiry,
        e.iqama_expiry,   -- employees now, see base_compliance_current
        health.health_insurance_status,
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
    -- COMPLIANCE-FIRST, still: a platform row for an unknown employee keeps
    -- its row and its 'Unknown Employee' classification. With four sources the
    -- spine is the UNION of their keys - a row present in any one platform is
    -- a record this model must surface, and an inner join to any single
    -- platform would drop the others.
    FROM (
        SELECT employee_id, period FROM {{ ref('stg_compliance_gosi') }}
        UNION
        SELECT employee_id, period FROM {{ ref('stg_compliance_qiwa') }}
        UNION
        SELECT employee_id, period FROM {{ ref('stg_compliance_wps') }}
        UNION
        SELECT employee_id, period FROM {{ ref('stg_compliance_health') }}
    ) c
    LEFT JOIN {{ ref('stg_compliance_gosi') }}   gosi   ON c.employee_id = gosi.employee_id   AND c.period = gosi.period
    LEFT JOIN {{ ref('stg_compliance_qiwa') }}   qiwa   ON c.employee_id = qiwa.employee_id   AND c.period = qiwa.period
    LEFT JOIN {{ ref('stg_compliance_wps') }}    wps    ON c.employee_id = wps.employee_id    AND c.period = wps.period
    LEFT JOIN {{ ref('stg_compliance_health') }} health ON c.employee_id = health.employee_id AND health.period = c.period
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
