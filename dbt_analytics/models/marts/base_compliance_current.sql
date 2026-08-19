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
        qiwa.qiwa_status,
        gosi.gosi_status,
        wps.mudad_status,
        qiwa.contract_authenticated,
        gosi.gosi_salary,
        -- FROM THE PAYROLL DOMAIN, not copied into the compliance file.
        --
        -- This column existed so gosi_salary could be compared against what
        -- payroll actually paid - a real and valuable finding. But it asked the
        -- CLIENT to copy payroll figures into a compliance export so that we
        -- could compare two numbers we already hold, and rejected their file
        -- when they could not. Same species as the derived columns.
        --
        -- The NAME is kept deliberately: it still means "basic salary per
        -- payroll", so base_government_status, base_government_platform_records
        -- and both comparison arms read it unchanged. Only its source moved.
        pay.basic_salary AS payroll_basic_salary,
        gosi.occupation_code,
        gosi.occupation_match_status,
        qiwa.work_permit_expiry,
        -- FROM THE EMPLOYEES SIDE. iqama_expiry moved to the employees
        -- contract (the period test: it changes when the iqama is
        -- reissued, not when the month turns). Taking it here means the
        -- seven models reading it through this view need no edit - the
        -- same reason stg_employees resolves `project` in one place.
        e.iqama_expiry,
        e.iqama_occupation,
        health.health_insurance_status
    FROM {{ ref('base_active_workforce') }} e
    -- ONE JOIN PER PLATFORM. Four LEFT JOINs on (employee_id, period)
    -- produce the same row set as one, PROVIDED each file has at most one row
    -- per key - the fan-out hazard the payroll join below also guards.
    LEFT JOIN {{ ref('stg_compliance_gosi') }}   gosi   ON e.employee_id = gosi.employee_id   AND gosi.period   = '{{ var('report_month') }}'
    LEFT JOIN {{ ref('stg_compliance_qiwa') }}   qiwa   ON e.employee_id = qiwa.employee_id   AND qiwa.period   = '{{ var('report_month') }}'
    LEFT JOIN {{ ref('stg_compliance_wps') }}    wps    ON e.employee_id = wps.employee_id    AND wps.period    = '{{ var('report_month') }}'
    LEFT JOIN {{ ref('stg_compliance_health') }} health ON e.employee_id = health.employee_id AND health.period = '{{ var('report_month') }}'
    -- Aggregated to ONE row per employee. base_payroll_current is one row per
    -- payroll line, and a duplicate line would otherwise multiply every
    -- compliance row for that employee - changing counts on a page that has
    -- nothing to do with payroll. Duplicate payroll rows are reported by
    -- mart_payroll_exceptions, which is where that finding belongs.
    LEFT JOIN (
        SELECT employee_id, MAX(basic_salary) AS basic_salary
        FROM {{ ref('base_payroll_current') }}
        GROUP BY employee_id
    ) pay ON e.employee_id = pay.employee_id
