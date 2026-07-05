{{ config(materialized='view') }}

SELECT 
        c.er_case_record_id,
        c.case_id,
        c.employee_id AS subject_employee_id,
        c.employee_name AS subject_employee_name,
        c.subject_classification,
        c.owner_id AS owner_employee_id,
        eo.employee_name AS owner_employee_name,
        eo.status AS owner_raw_status,
        CASE 
            WHEN c.owner_id IS NULL OR TRIM(c.owner_id) = '' THEN 'Unknown Employee'
            WHEN eo.employee_id IS NULL THEN 'Unknown Employee'
            WHEN eo.status = 'Active' THEN 'Active Employee'
            WHEN eo.status = 'Inactive' THEN 'Inactive Employee'
            WHEN eo.status = 'Terminated' THEN 'Terminated Employee'
            ELSE 'Unknown Status Employee'
        END AS owner_classification
    FROM {{ ref('base_er_cases_current') }} c
    LEFT JOIN {{ ref('base_employees_deduplicated') }} eo ON c.owner_id = eo.employee_id
