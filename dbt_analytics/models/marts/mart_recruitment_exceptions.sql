{{ config(materialized='view') }}

-- 1. Open requisition missing recruiter
    SELECT requisition_id AS record_id_str, 'Missing Recruiter' AS issue_type, 'Open requisition has no owner recruiter assigned' AS description, 'Critical' AS severity, 'Assign a recruiter' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (recruiter_id IS NULL OR TRIM(recruiter_id) = '')
    UNION ALL
    -- 2. Open requisition missing project
    SELECT requisition_id AS record_id_str, 'Missing Project' AS issue_type, 'Open requisition has no project assignment' AS description, 'Warning' AS severity, 'Assign a project code' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (project = 'Unassigned' OR project IS NULL)
    UNION ALL
    -- 3. Open requisition missing department
    SELECT requisition_id AS record_id_str, 'Missing Department' AS issue_type, 'Open requisition has no department' AS description, 'Warning' AS severity, 'Assign a department' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (department = 'Unassigned' OR department IS NULL)
    UNION ALL
    -- 4. Open requisition missing cost center
    SELECT requisition_id AS record_id_str, 'Missing Cost Center' AS issue_type, 'Open requisition has no cost center' AS description, 'Warning' AS severity, 'Assign a cost center' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (cost_center IS NULL OR TRIM(cost_center) = '')
    UNION ALL
    -- 5. Open requisition missing job title
    SELECT requisition_id AS record_id_str, 'Missing Job Title' AS issue_type, 'Open requisition job title is blank' AS description, 'Critical' AS severity, 'Enter job title' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (job_title IS NULL OR TRIM(job_title) = '')
    UNION ALL
    -- 6. Open requisition missing target hire date
    SELECT requisition_id AS record_id_str, 'Missing Target Hire Date' AS issue_type, 'Open requisition target hire date is blank' AS description, 'Warning' AS severity, 'Provide target hire date' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND target_hire_date IS NULL
    UNION ALL
    -- 7. Requisition overdue
    SELECT requisition_id AS record_id_str, 'Overdue Requisition' AS issue_type, 'Open requisition has breached its effective target date: ' || CAST(effective_target_hire_date AS VARCHAR), 'Critical' AS severity, 'Expedite sourcing and pipeline conversions' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND '{{ var('report_anchor_date') }}' > effective_target_hire_date
    UNION ALL
    -- 8. Requisition approved but no candidates
    SELECT requisition_id AS record_id_str, 'Empty Candidate Pipeline' AS issue_type, 'Requisition is open but has 0 candidates linked', 'Warning' AS severity, 'Source and link candidates to requisition' AS recommended_action
    FROM {{ ref('base_recruitment_requisitions_current') }} WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND requisition_id NOT IN (SELECT DISTINCT requisition_id FROM {{ ref('base_candidate_pipeline_current') }})
    UNION ALL
    -- 9. Candidate missing pipeline stage
    SELECT candidate_id AS record_id_str, 'Missing Pipeline Stage' AS issue_type, 'Candidate application has no pipeline stage logged', 'Warning' AS severity, 'Assign current pipeline stage' AS recommended_action
    FROM {{ ref('base_candidate_canonical') }} WHERE pipeline_stage IS NULL OR TRIM(pipeline_stage) = ''
    UNION ALL
    -- 10. Candidate linked to unknown requisition
    SELECT candidate_id AS record_id_str, 'Unknown Requisition Link' AS issue_type, 'Candidate is linked to requisition ID ' || COALESCE(requisition_id, 'N/A') || ' which does not exist in master requisitions table', 'Critical' AS severity, 'Link candidate to active requisition' AS recommended_action
    FROM {{ ref('base_candidate_source_records') }} WHERE requisition_id NOT IN (SELECT DISTINCT requisition_id FROM {{ ref('base_requisition_source_records') }})
    UNION ALL
    -- 11. Interview scheduled without interviewer
    SELECT interview_id AS record_id_str, 'Missing Interviewer' AS issue_type, 'Interview has no interviewer assigned', 'Warning' AS severity, 'Assign interviewer employee ID' AS recommended_action
    FROM {{ ref('base_interview_source_records') }} WHERE (interviewer_id IS NULL OR TRIM(interviewer_id) = '')
    UNION ALL
    -- 12. Interview scheduled without date/time
    SELECT interview_id AS record_id_str, 'Missing Interview Date' AS issue_type, 'Interview record has no scheduled date and time', 'Warning' AS severity, 'Set scheduled interview timestamp' AS recommended_action
    FROM {{ ref('base_interview_source_records') }} WHERE interview_date IS NULL
    UNION ALL
    -- 13. Offer extended without salary
    SELECT offer_id AS record_id_str, 'Offer Missing Salary' AS issue_type, 'Offer extended has no base salary details', 'Critical' AS severity, 'Enter base salary details' AS recommended_action
    FROM {{ ref('base_offer_source_records') }} WHERE salary IS NULL OR salary <= 0
    UNION ALL
    -- 14. Offer accepted but onboarding not started
    SELECT o.offer_id AS record_id_str, 'Onboarding Not Triggered' AS issue_type, 'Offer status is Accepted but onboarding is not logged', 'Critical' AS severity, 'Create onboarding record' AS recommended_action
    FROM {{ ref('base_offer_source_records') }} o WHERE o.offer_status = 'Accepted' AND o.candidate_id NOT IN (SELECT DISTINCT candidate_id FROM {{ ref('base_onboarding_source_records') }})
    UNION ALL
    -- 15. Onboarding linked to unknown employee
    SELECT onboarding_id AS record_id_str, 'Unknown Employee ID' AS issue_type, 'Onboarding record links to employee ID ' || COALESCE(employee_id, 'N/A') || ' which is missing from employee directory', 'Warning' AS severity, 'Verify active employee ID and link' AS recommended_action
    FROM {{ ref('base_onboarding_source_records') }} WHERE employee_id IS NOT NULL AND employee_id NOT IN (SELECT DISTINCT employee_id FROM {{ ref('base_employees_deduplicated') }})
    UNION ALL
    -- 16. Duplicate requisition ID
    SELECT requisition_id AS record_id_str, 'Duplicate Requisition ID' AS issue_type, 'Requisition ID is logged multiple times in source records', 'Critical' AS severity, 'Deduplicate requisition records' AS recommended_action
    FROM {{ ref('base_requisition_source_records') }} WHERE requisition_id IN (SELECT requisition_id FROM {{ ref('base_requisition_source_records') }} GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 17. Duplicate candidate ID
    SELECT candidate_id AS record_id_str, 'Duplicate Candidate ID' AS issue_type, 'Candidate ID is logged multiple times in source records', 'Critical' AS severity, 'Deduplicate candidate records' AS recommended_action
    FROM {{ ref('base_candidate_source_records') }} WHERE candidate_id IN (SELECT candidate_id FROM {{ ref('base_candidate_source_records') }} GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 18. Workforce plan missing project or department
    SELECT 'Plan_Row' AS record_id_str, 'Missing Plan Dimension' AS issue_type, 'Workforce plan record has null project or department', 'Warning' AS severity, 'Specify project and department details' AS recommended_action
    FROM {{ ref('base_workforce_plan_current') }} WHERE project IS NULL OR TRIM(project) = '' OR department IS NULL OR TRIM(department) = ''
    UNION ALL
    -- 19. Actual headcount greater than planned headcount
    SELECT COALESCE(wp.project, 'Unassigned') || '-' || COALESCE(wp.department, 'Unassigned') AS record_id_str, 'Plan Exceeded' AS issue_type, 'Actual headcount (' || CAST(COALESCE(ahc.actual_count, 0) AS VARCHAR) || ') exceeds planned headcount (' || CAST(wp.planned_headcount AS VARCHAR) || ')', 'Warning' AS severity, 'Review project hiring plan' AS recommended_action
    FROM {{ ref('base_workforce_plan_current') }} wp
    LEFT JOIN (
        SELECT project, department, COUNT(*) AS actual_count
        FROM {{ ref('base_active_workforce') }}
        GROUP BY 1, 2
    ) ahc ON wp.project = ahc.project AND wp.department = ahc.department
    WHERE COALESCE(ahc.actual_count, 0) > wp.planned_headcount
    UNION ALL
    -- 20. Planned headcount not fulfilled by target date
    SELECT COALESCE(wp.project, 'Unassigned') || '-' || COALESCE(wp.department, 'Unassigned') AS record_id_str, 'Plan Unfulfilled' AS issue_type, 'Planned headcount (' || CAST(wp.planned_headcount AS VARCHAR) || ') has not been fulfilled (Actual: ' || CAST(COALESCE(ahc.actual_count, 0) AS VARCHAR) || ') by target date ' || '{{ var('report_month_end') }}', 'Warning' AS severity, 'Expedite hiring pipeline' AS recommended_action
    FROM {{ ref('base_workforce_plan_current') }} wp
    LEFT JOIN (
        SELECT project, department, COUNT(*) AS actual_count
        FROM {{ ref('base_active_workforce') }}
        GROUP BY 1, 2
    ) ahc ON wp.project = ahc.project AND wp.department = ahc.department
    WHERE COALESCE(ahc.actual_count, 0) < wp.planned_headcount
    UNION ALL
    -- 21. Null or negative vacancy quantity
    SELECT request_id AS record_id_str, 'Invalid Vacancy Quantity' AS issue_type, 'Vacancy request Approved has invalid quantity: ' || COALESCE(CAST(quantity AS VARCHAR), 'NULL'), 'Critical' AS severity, 'Enter positive quantity' AS recommended_action
    FROM {{ ref('base_vacancy_population') }} WHERE quantity IS NULL OR quantity <= 0
    UNION ALL
    -- 22. Unknown candidate source channel
    SELECT candidate_id AS record_id_str, 'Unknown Source Channel' AS issue_type, 'Candidate has un-normalized source channel: ' || COALESCE(raw_source, 'NULL'), 'Warning' AS severity, 'Update to standard channel' AS recommended_action
    FROM {{ ref('base_candidate_source_records') }} WHERE raw_source NOT IN ('LinkedIn', 'Indeed', 'Referral', 'Direct', 'Agency')
