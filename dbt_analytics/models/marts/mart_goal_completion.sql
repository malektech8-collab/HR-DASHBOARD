{{ config(materialized='view') }}

SELECT
        COALESCE(e.department, 'Unknown') AS department,
        COUNT(CASE WHEN g.status = 'Completed' THEN 1 END) AS completed_goals,
        COUNT(CASE WHEN g.status = 'In Progress' THEN 1 END) AS in_progress_goals,
        COUNT(CASE WHEN g.status = 'Overdue' THEN 1 END) AS overdue_goals,
        COUNT(CASE WHEN g.status = 'Not Started' THEN 1 END) AS not_started_goals,
        COUNT(CASE WHEN g.status = 'Cancelled' THEN 1 END) AS cancelled_goals,
        COUNT(CASE WHEN g.status != 'Cancelled' THEN 1 END) AS eligible_goals
    FROM {{ ref('base_performance_goals_current') }} g
    LEFT JOIN {{ ref('base_talent_employee_population') }} e ON g.employee_id = e.employee_id
    GROUP BY e.department
