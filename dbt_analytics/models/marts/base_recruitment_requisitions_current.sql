{{ config(materialized='view') }}

SELECT 
        *,
        COALESCE(target_hire_date, approval_date + {{ var('default_sla_days') }}) AS effective_target_hire_date
    FROM {{ ref('base_requisition_source_records') }}
    WHERE approval_date <= '{{ var('report_month_end') }}'
      AND (
          status IN ('Open', 'Approved', 'In Progress', 'On Hold')
          OR closed_date > '{{ var('report_month_end') }}'
          OR (closed_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}')
          OR (approval_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}')
      )
      AND status NOT IN ('Cancelled', 'Rejected', 'Draft')
