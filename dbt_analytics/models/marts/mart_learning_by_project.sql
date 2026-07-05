{{ config(materialized='view') }}

SELECT
        COALESCE(e.project, 'Unassigned') AS project,
        COALESCE(e.department, 'Unknown') AS department,
        COUNT(CASE WHEN l.status = 'Completed' THEN 1 END) AS completed_enrollments,
        COALESCE(SUM(CASE WHEN l.status = 'Completed' THEN t.duration_hours ELSE 0 END), 0) AS total_hours
    FROM {{ ref('base_learning_enrollments_current') }} l
    LEFT JOIN {{ ref('base_talent_employee_population') }} e ON l.employee_id = e.employee_id
    LEFT JOIN {{ ref('base_training_catalog_current') }} t ON l.course_id = t.course_id
    GROUP BY e.project, e.department
