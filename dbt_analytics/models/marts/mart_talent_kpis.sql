{{ config(materialized='view') }}

WITH talent_pop AS (SELECT COUNT(*) AS total FROM {{ ref('base_talent_employee_population') }}),
    reviewed AS (SELECT COUNT(DISTINCT employee_id) AS cnt FROM {{ ref('base_performance_reviews_current') }}),
    avg_rating AS (SELECT ROUND(AVG(rating), 2) AS avg_r FROM {{ ref('base_performance_reviews_current') }}),
    high_perf AS (SELECT COUNT(DISTINCT employee_id) AS cnt FROM {{ ref('base_performance_reviews_current') }} WHERE performance_category IN ('Outstanding', 'Exceeds Expectations')),
    low_perf  AS (SELECT COUNT(DISTINCT employee_id) AS cnt FROM {{ ref('base_performance_reviews_current') }} WHERE performance_category IN ('Needs Improvement', 'Unsatisfactory')),
    goals AS (
        SELECT
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) AS completed_goals,
            COUNT(CASE WHEN status != 'Cancelled' THEN 1 END) AS eligible_goals
        FROM {{ ref('base_performance_goals_current') }}
    ),
    learning AS (
        SELECT
            COUNT(CASE WHEN l.status = 'Completed' THEN 1 END) AS completed_enr,
            COUNT(CASE WHEN l.status != 'Cancelled' THEN 1 END) AS eligible_enr,
            COALESCE(SUM(CASE WHEN l.status = 'Completed' THEN t.duration_hours ELSE 0 END), 0) AS total_hours,
            COUNT(DISTINCT CASE WHEN l.status = 'Completed' THEN l.employee_id END) AS unique_trainees
        FROM {{ ref('base_learning_enrollments_current') }} l
        LEFT JOIN {{ ref('base_training_catalog_current') }} t ON l.course_id = t.course_id
    ),
    succession AS (
        WITH valid_successors AS (
            SELECT DISTINCT critical_role_id
            FROM {{ ref('base_succession_plans_current') }} s
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        )
        SELECT
            COUNT(DISTINCT critical_role_id) AS total_roles
        FROM {{ ref('base_succession_plans_current') }}
    ),
    covered_roles AS (
        SELECT COUNT(DISTINCT critical_role_id) AS covered
        FROM {{ ref('base_succession_plans_current') }} s
        WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
          AND s.successor_employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
          AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
    ),
    ready_now AS (
        SELECT COUNT(DISTINCT successor_employee_id) AS cnt
        FROM {{ ref('base_succession_plans_current') }}
        WHERE readiness = 'Ready Now'
          AND successor_employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    ),
    exc_count AS (SELECT COUNT(*) AS cnt FROM {{ ref('mart_talent_exceptions') }})
    SELECT
        CAST(reviewed.cnt AS DOUBLE) AS employees_reviewed,
        CASE WHEN talent_pop.total = 0 THEN 0.0
             ELSE ROUND(100.0 * reviewed.cnt / talent_pop.total, 2) END AS review_completion_pct,
        avg_rating.avg_r AS average_performance_rating,
        CAST(high_perf.cnt AS DOUBLE) AS high_performers,
        CAST(low_perf.cnt AS DOUBLE) AS low_performers,
        CASE WHEN goals.eligible_goals = 0 THEN 0.0
             ELSE ROUND(100.0 * goals.completed_goals / goals.eligible_goals, 2) END AS goal_completion_pct,
        CASE WHEN learning.eligible_enr = 0 THEN 0.0
             ELSE ROUND(100.0 * learning.completed_enr / learning.eligible_enr, 2) END AS training_completion_pct,
        CASE WHEN learning.unique_trainees = 0 THEN 0.0
             ELSE ROUND(learning.total_hours / learning.unique_trainees, 2) END AS average_training_hours,
        CASE WHEN succession.total_roles = 0 THEN 100.0
             ELSE ROUND(100.0 * covered_roles.covered / succession.total_roles, 2) END AS critical_roles_covered_pct,
        CAST(ready_now.cnt AS DOUBLE) AS ready_successors,
        CAST(exc_count.cnt AS DOUBLE) AS talent_exception_count
    FROM talent_pop, reviewed, avg_rating, high_perf, low_perf, goals, learning, succession, covered_roles, ready_now, exc_count
