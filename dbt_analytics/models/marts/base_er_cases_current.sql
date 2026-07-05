{{ config(materialized='view') }}

SELECT 
        row_number() OVER (ORDER BY c.case_id, c.employee_id, c.created_date, c.case_type, c.priority) AS er_case_record_id,
        c.case_id,
        c.employee_id,
        c.case_type,
        c.case_status,
        c.priority,
        c.created_date,
        c.target_due_date,
        c.closed_date,
        c.owner_id,
        c.escalated,
        c.escalation_reason,
        c.legal_reference,
        c.case_number,
        c.description,
        e.employee_name,
        COALESCE(e.project, 'Unassigned') AS project,
        COALESCE(e.department, 'Unassigned') AS department,
        e.manager_id,
        e.company,
        e.nationality,
        e.job_title,
        e.cost_center,
        CASE 
            WHEN e.employee_id IS NULL THEN 'Unknown Employee'
            WHEN e.status = 'Active' THEN 'Active Employee'
            WHEN e.status = 'Inactive' THEN 'Inactive Employee'
            WHEN e.status = 'Terminated' THEN 'Terminated Employee'
            ELSE 'Unknown Status Employee'
        END AS subject_classification
    FROM {{ ref('stg_employee_relations') }} c
    LEFT JOIN {{ ref('base_employees_deduplicated') }} e ON c.employee_id = e.employee_id
    WHERE c.created_date <= '{{ var('report_month_end') }}'
      AND (
          c.closed_date IS NULL 
          OR c.closed_date > '{{ var('report_month_end') }}'
          OR (c.closed_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}')
          OR (c.created_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}')
      )
