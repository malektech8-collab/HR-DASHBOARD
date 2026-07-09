{{ config(materialized='view') }}

-- 1. Active employee missing performance review
    SELECT e.employee_id AS record_id_str, 'Missing Performance Review' AS issue_type,
        'Active employee ' || e.employee_id || ' has no completed review for ' || '{{ var('report_month') }}' AS description,
        'Warning' AS severity, 'Assign and complete a performance review' AS recommended_action
    FROM {{ ref('base_talent_employee_population') }} e
    WHERE e.employee_id NOT IN (SELECT DISTINCT employee_id FROM {{ ref('base_performance_reviews_current') }})
    UNION ALL
    -- 2. Performance review linked to unknown employee
    SELECT s.employee_id AS record_id_str, 'Review Linked to Unknown Employee' AS issue_type,
        'Review ID ' || s.review_id || ' links to employee_id ' || s.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on review record' AS recommended_action
    FROM {{ ref('base_performance_review_source_records') }} s
    WHERE s.employee_id NOT IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    UNION ALL
    -- 3. Duplicate performance review ID
    SELECT s.review_id AS record_id_str, 'Duplicate Performance Review ID' AS issue_type,
        'Review ID ' || s.review_id || ' appears more than once in source records' AS description,
        'Critical' AS severity, 'Deduplicate performance review records' AS recommended_action
    FROM {{ ref('base_performance_review_source_records') }} s
    WHERE s.review_id IN (SELECT review_id FROM {{ ref('base_performance_review_source_records') }} GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 4. Review completed without rating
    SELECT s.review_id AS record_id_str, 'Review Completed Without Rating' AS issue_type,
        'Review ' || s.review_id || ' for employee ' || s.employee_id || ' is Completed but has no rating' AS description,
        'Critical' AS severity, 'Enter rating before marking review Completed' AS recommended_action
    FROM {{ ref('base_performance_review_source_records') }} s
    WHERE s.status = 'Completed' AND (s.rating IS NULL)
    UNION ALL
    -- 5. Rating outside allowed range
    SELECT s.review_id AS record_id_str, 'Rating Outside Allowed Range' AS issue_type,
        'Review ' || s.review_id || ' has rating ' || CAST(s.rating AS VARCHAR) || ' which is outside allowed range {{ var('min_rating') }}–{{ var('max_rating') }}' AS description,
        'Critical' AS severity, 'Correct rating to within 1.0–5.0 scale' AS recommended_action
    FROM {{ ref('base_performance_review_source_records') }} s
    WHERE s.rating IS NOT NULL AND (s.rating < {{ var('min_rating') }} OR s.rating > {{ var('max_rating') }})
    UNION ALL
    -- 6. Review missing reviewer/manager
    SELECT s.review_id AS record_id_str, 'Review Missing Reviewer' AS issue_type,
        'Review ' || s.review_id || ' has no reviewer_id assigned' AS description,
        'Critical' AS severity, 'Assign a reviewer before finalizing review' AS recommended_action
    FROM {{ ref('base_performance_review_source_records') }} s
    WHERE s.reviewer_id IS NULL OR TRIM(s.reviewer_id) = ''
    UNION ALL
    -- 7. Goal linked to unknown employee
    SELECT g.goal_id AS record_id_str, 'Goal Linked to Unknown Employee' AS issue_type,
        'Goal ' || g.goal_id || ' links to employee ' || g.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on goal record' AS recommended_action
    FROM {{ ref('base_performance_goal_source_records') }} g
    WHERE g.employee_id NOT IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    UNION ALL
    -- 8. Goal missing status
    SELECT g.goal_id AS record_id_str, 'Goal Missing Status' AS issue_type,
        'Goal ' || g.goal_id || ' for employee ' || g.employee_id || ' has no status' AS description,
        'Warning' AS severity, 'Set goal status (Completed/In Progress/Overdue etc.)' AS recommended_action
    FROM {{ ref('base_performance_goal_source_records') }} g
    WHERE g.status IS NULL OR TRIM(g.status) = ''
    UNION ALL
    -- 9. Goal overdue
    SELECT g.goal_id AS record_id_str, 'Goal Overdue' AS issue_type,
        'Goal ' || g.goal_id || ' for employee ' || g.employee_id || ' is past due date ' || CAST(g.due_date AS VARCHAR) AS description,
        'Warning' AS severity, 'Resolve or update overdue goal' AS recommended_action
    FROM {{ ref('base_performance_goal_source_records') }} g
    WHERE g.status NOT IN ('Completed', 'Cancelled') AND g.due_date < DATE '{{ var('talent_month_end') }}'
    UNION ALL
    -- 10. Competency assessment linked to unknown employee
    SELECT c.assessment_id AS record_id_str, 'Competency Linked to Unknown Employee' AS issue_type,
        'Assessment ' || c.assessment_id || ' links to employee ' || c.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on competency assessment' AS recommended_action
    FROM {{ ref('base_competency_source_records') }} c
    WHERE c.employee_id NOT IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    UNION ALL
    -- 11. Competency score outside allowed range
    SELECT c.assessment_id AS record_id_str, 'Competency Score Outside Range' AS issue_type,
        'Assessment ' || c.assessment_id || ' has score outside 1–5 (required=' || CAST(c.required_score AS VARCHAR) || ', actual=' || CAST(c.actual_score AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Correct competency scores to 1.0–5.0 range' AS recommended_action
    FROM {{ ref('base_competency_source_records') }} c
    WHERE (c.required_score IS NOT NULL AND (c.required_score < {{ var('min_rating') }} OR c.required_score > {{ var('max_rating') }}))
       OR (c.actual_score IS NOT NULL AND (c.actual_score < {{ var('min_rating') }} OR c.actual_score > {{ var('max_rating') }}))
    UNION ALL
    -- 12. Critical role missing successor
    SELECT s.critical_role_id AS record_id_str, 'Critical Role Missing Successor' AS issue_type,
        'Critical role ' || s.role_title || ' (' || s.critical_role_id || ') has no nominated successor' AS description,
        'Warning' AS severity, 'Nominate a successor for this critical role' AS recommended_action
    FROM {{ ref('base_succession_plans_current') }} s
    WHERE s.successor_employee_id IS NULL OR TRIM(s.successor_employee_id) = ''
    UNION ALL
    -- 13. Successor linked to unknown employee
    SELECT s.successor_employee_id AS record_id_str, 'Successor Linked to Unknown Employee' AS issue_type,
        'Succession plan ' || s.plan_id || ' successor ' || s.successor_employee_id || ' is not in employee master directory' AS description,
        'Critical' AS severity, 'Correct successor_employee_id in succession plan' AS recommended_action
    FROM {{ ref('base_succession_plans_current') }} s
    WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
      AND s.successor_employee_id NOT IN (SELECT employee_id FROM {{ ref('base_active_workforce') }})
      AND s.successor_employee_id NOT IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    UNION ALL
    -- 14. Successor assigned to inactive employee
    SELECT s.successor_employee_id AS record_id_str, 'Successor Assigned to Inactive Employee' AS issue_type,
        'Succession plan ' || s.plan_id || ' successor ' || s.successor_employee_id || ' is inactive or terminated' AS description,
        'Warning' AS severity, 'Reassign succession to an active employee' AS recommended_action
    FROM {{ ref('base_succession_plans_current') }} s
    INNER JOIN (
        SELECT employee_id FROM {{ ref('stg_employees') }} WHERE status NOT IN ('Active')
    ) inactive ON s.successor_employee_id = inactive.employee_id
    UNION ALL
    -- 15. Successor readiness missing
    SELECT s.plan_id AS record_id_str, 'Successor Readiness Missing' AS issue_type,
        'Succession plan ' || s.plan_id || ' for role ' || s.role_title || ' has no readiness value' AS description,
        'Critical' AS severity, 'Set readiness status for this successor nomination' AS recommended_action
    FROM {{ ref('base_succession_plans_current') }} s
    WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
      AND (s.readiness IS NULL OR TRIM(s.readiness) = '')
    UNION ALL
    -- 16. Training enrollment linked to unknown employee
    SELECT l.enrollment_id AS record_id_str, 'Enrollment Linked to Unknown Employee' AS issue_type,
        'Enrollment ' || l.enrollment_id || ' links to employee ' || l.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on enrollment record' AS recommended_action
    FROM {{ ref('base_learning_source_records') }} l
    WHERE l.employee_id NOT IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    UNION ALL
    -- 17. Training completed without completion date
    SELECT l.enrollment_id AS record_id_str, 'Training Completed Without Date' AS issue_type,
        'Enrollment ' || l.enrollment_id || ' has status Completed but no completion_date' AS description,
        'Critical' AS severity, 'Set completion_date on completed enrollment' AS recommended_action
    FROM {{ ref('base_learning_source_records') }} l
    WHERE l.status = 'Completed' AND l.completion_date IS NULL
    UNION ALL
    -- 18. Training hours missing or invalid
    SELECT t.course_id AS record_id_str, 'Training Hours Missing or Invalid' AS issue_type,
        'Course ' || t.course_name || ' has invalid/zero duration hours: ' || COALESCE(CAST(t.duration_hours AS VARCHAR), 'NULL') AS description,
        'Critical' AS severity, 'Enter valid positive training hours for this course' AS recommended_action
    FROM {{ ref('base_training_catalog_current') }} t
    WHERE t.duration_hours IS NULL OR t.duration_hours <= 0
    UNION ALL
    -- 19. Learning course missing category
    SELECT t.course_id AS record_id_str, 'Learning Course Missing Category' AS issue_type,
        'Course ' || t.course_name || ' has no category assigned' AS description,
        'Warning' AS severity, 'Assign a category to this training course' AS recommended_action
    FROM {{ ref('base_training_catalog_current') }} t
    WHERE t.category IS NULL OR TRIM(t.category) = ''
    UNION ALL
    -- 20. Talent review missing potential rating
    SELECT tr.employee_id AS record_id_str, 'Talent Review Missing Potential Rating' AS issue_type,
        'Talent review for employee ' || tr.employee_id || ' is missing the potential_rating field' AS description,
        'Critical' AS severity, 'Enter potential rating on talent review record' AS recommended_action
    FROM {{ ref('base_talent_review_source_records') }} tr
    WHERE tr.potential_rating IS NULL OR TRIM(tr.potential_rating) = ''
    UNION ALL
    -- 21. High performer with high flight risk
    SELECT pr.employee_id AS record_id_str, 'High Performer With High Flight Risk' AS issue_type,
        'Employee ' || pr.employee_id || ' is rated ' || pr.performance_category || ' but has high flight risk' AS description,
        'Warning' AS severity, 'Engage retention measures for this high-performer' AS recommended_action
    FROM {{ ref('base_performance_reviews_current') }} pr
    INNER JOIN {{ ref('base_talent_reviews_current') }} tr ON pr.employee_id = tr.employee_id
    WHERE pr.performance_category IN ('Outstanding', 'Exceeds Expectations') AND tr.flight_risk = 'High'
    UNION ALL
    -- 22. Critical employee without successor
    SELECT e.employee_id AS record_id_str, 'Critical Employee Without Successor' AS issue_type,
        'Employee ' || e.employee_id || ' (' || e.job_title || ') is in a critical role but has no succession plan' AS description,
        'Warning' AS severity, 'Create a succession plan for this critical employee' AS recommended_action
    FROM {{ ref('base_talent_employee_population') }} e
    WHERE e.job_title IN ({{ var('critical_titles_sql') }})
      AND e.employee_id NOT IN (
          SELECT DISTINCT current_employee_id FROM {{ ref('base_succession_plans_current') }}
          WHERE successor_employee_id IS NOT NULL AND TRIM(successor_employee_id) != ''
      )
    UNION ALL
    -- 23. Duplicate skill record
    SELECT s.employee_id AS record_id_str, 'Duplicate Skill Record' AS issue_type,
        'Employee ' || s.employee_id || ' has duplicate entry for skill: ' || s.skill_name AS description,
        'Warning' AS severity, 'Deduplicate employee skill records' AS recommended_action
    FROM {{ ref('base_employee_skill_source_records') }} s
    WHERE EXISTS (
        SELECT 1 FROM {{ ref('base_employee_skill_source_records') }} s2
        WHERE s2.employee_id = s.employee_id AND s2.skill_name = s.skill_name
        GROUP BY s2.employee_id, s2.skill_name HAVING COUNT(*) > 1
    )
    UNION ALL
    -- 24. Career path missing next role
    SELECT cp.employee_id AS record_id_str, 'Career Path Missing Next Role' AS issue_type,
        'Career path for employee ' || cp.employee_id || ' has no next_role defined' AS description,
        'Warning' AS severity, 'Define the next_role for this career path entry' AS recommended_action
    FROM {{ ref('stg_career_paths') }} cp
    WHERE cp.next_role IS NULL OR TRIM(cp.next_role) = ''
