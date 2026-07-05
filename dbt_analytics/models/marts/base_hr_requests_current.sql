{{ config(materialized='view') }}

SELECT 
        r.request_id,
        r.employee_id,
        r.request_type,
        r.request_status,
        r.created_at,
        r.closed_at,
        r.owner AS owner_id,
        r.sla_hours,
        r.actual_hours,
        r.sla_breached,
        COALESCE(r.project, e.project, 'Unassigned') AS project,
        COALESCE(e.department, 'Unassigned') AS department
    FROM {{ ref('stg_hr_requests') }} r
    LEFT JOIN {{ ref('base_employees_deduplicated') }} e ON r.employee_id = e.employee_id
    WHERE r.created_at <= '{{ var('report_month_end') }} 23:59:59'
      AND (r.closed_at IS NULL OR r.closed_at >= '{{ var('report_month_start') }} 00:00:00')
