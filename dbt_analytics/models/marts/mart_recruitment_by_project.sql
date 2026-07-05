{{ config(materialized='view') }}

SELECT 
        project,
        COUNT(*) AS total_requisitions,
        COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS open_requisitions,
        COUNT(CASE WHEN status IN ('Closed', 'Filled') THEN 1 END) AS closed_requisitions,
        COUNT(CASE WHEN effective_target_hire_date < CURRENT_DATE AND status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS overdue_requisitions
    FROM {{ ref('base_recruitment_requisitions_current') }}
    GROUP BY project
