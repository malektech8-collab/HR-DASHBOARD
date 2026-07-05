{{ config(materialized='view') }}

SELECT e.department,
        COUNT(DISTINCT pr.employee_id) AS reviewed_count,
        ROUND(AVG(pr.rating), 2) AS average_rating,
        COUNT(CASE WHEN pr.performance_category IN ('Outstanding', 'Exceeds Expectations') THEN 1 END) AS high_performers,
        COUNT(CASE WHEN pr.performance_category IN ('Needs Improvement', 'Unsatisfactory') THEN 1 END) AS low_performers
    FROM {{ ref('base_performance_reviews_current') }} pr
    JOIN {{ ref('base_talent_employee_population') }} e ON pr.employee_id = e.employee_id
    GROUP BY e.department
