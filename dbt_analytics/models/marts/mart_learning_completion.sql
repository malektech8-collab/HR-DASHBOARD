{{ config(materialized='view') }}

SELECT
        COALESCE(t.category, 'Uncategorized') AS category,
        COUNT(CASE WHEN l.status = 'Completed' THEN 1 END) AS completed_enrollments,
        COUNT(CASE WHEN l.status != 'Cancelled' THEN 1 END) AS eligible_enrollments,
        COALESCE(SUM(CASE WHEN l.status = 'Completed' THEN t.duration_hours ELSE 0 END), 0) AS total_hours
    FROM {{ ref('base_learning_enrollments_current') }} l
    LEFT JOIN {{ ref('base_training_catalog_current') }} t ON l.course_id = t.course_id
    GROUP BY t.category
