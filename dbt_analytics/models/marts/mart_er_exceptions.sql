{{ config(materialized='view') }}

-- 1. Open case missing owner
    SELECT case_id, employee_name, 'Missing Case Owner' AS issue_type, 'Open case has no owner assigned' AS description, 'Critical' AS severity, 'Assign an owner to investigate' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (owner_id IS NULL OR TRIM(owner_id) = '')
    UNION ALL
    -- 2. Open case missing project
    SELECT case_id, employee_name, 'Missing Project' AS issue_type, 'Open case has no project link' AS description, 'Warning' AS severity, 'Update subject employee project assignment' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (project = 'Unassigned' OR project IS NULL)
    UNION ALL
    -- 3. Open case missing department
    SELECT case_id, employee_name, 'Missing Department' AS issue_type, 'Open case has no department link' AS description, 'Warning' AS severity, 'Update subject employee department assignment' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (department = 'Unassigned' OR department IS NULL)
    UNION ALL
    -- 4. Open case missing case type
    SELECT case_id, employee_name, 'Missing Case Type' AS issue_type, 'Case type is blank' AS description, 'Critical' AS severity, 'Specify Grievance, Disciplinary, or Labor Case' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (case_type IS NULL OR TRIM(case_type) = '')
    UNION ALL
    -- 5. Open case missing priority
    SELECT case_id, employee_name, 'Missing Priority' AS issue_type, 'Case priority is blank' AS description, 'Warning' AS severity, 'Set priority level to High, Medium, or Low' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (priority IS NULL OR TRIM(priority) = '')
    UNION ALL
    -- 6. Open case missing target due date
    SELECT case_id, employee_name, 'Missing Target Due Date' AS issue_type, 'Target due date is blank in source records' AS description, 'Critical' AS severity, 'Set target due date based on SLA rules' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND target_due_date IS NULL
    UNION ALL
    -- 7. Open case overdue
    SELECT case_id, employee_name, 'Overdue Open Case' AS issue_type, 'Open case has breached its effective target due date: ' || CAST(effective_target_due_date AS VARCHAR), 'Critical' AS severity, 'Expedite investigation and case resolution' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status IN ('Open', 'In Progress', 'Pending') AND '{{ var('report_anchor_date') }}' > effective_target_due_date
    UNION ALL
    -- 8. Closed case missing closure date
    SELECT case_id, employee_name, 'Missing Closure Date' AS issue_type, 'Case is status Closed but has no closed_date', 'Critical' AS severity, 'Fill closed_date in log' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_status = 'Closed' AND closed_date IS NULL
    UNION ALL
    -- 9. Closed case with closure date before creation date
    SELECT case_id, employee_name, 'Invalid Date Range' AS issue_type, 'Case closed_date (' || COALESCE(CAST(closed_date AS VARCHAR), 'N/A') || ') is before created_date (' || CAST(created_date AS VARCHAR) || ')', 'Critical' AS severity, 'Correct date entries' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE closed_date IS NOT NULL AND closed_date < created_date
    UNION ALL
    -- 10. Case assigned to inactive owner
    SELECT cp.case_id, cp.owner_employee_name, 'Inactive Case Owner' AS issue_type, 'Case investigator owner is classified as: ' || cp.owner_classification, 'Warning' AS severity, 'Reassign case owner to active employee' AS recommended_action, cp.er_case_record_id
    FROM {{ ref('base_er_case_parties') }} cp WHERE cp.owner_classification IN ('Inactive Employee', 'Terminated Employee', 'Unknown Employee')
    UNION ALL
    -- 11. Case linked to inactive employee
    SELECT cp.case_id, cp.subject_employee_name, 'Inactive Case Subject' AS issue_type, 'Case subject employee is classified as: ' || cp.subject_classification, 'Warning' AS severity, 'Check if case is archive or needs resolution closure' AS recommended_action, cp.er_case_record_id
    FROM {{ ref('base_er_case_parties') }} cp WHERE cp.subject_classification IN ('Inactive Employee', 'Terminated Employee')
    UNION ALL
    -- 12. Duplicate case ID
    SELECT case_id, employee_name, 'Duplicate Case ID' AS issue_type, 'Case ID is logged more than once', 'Critical' AS severity, 'Deduplicate ER logs' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_id IN (SELECT case_id FROM {{ ref('base_er_case_population') }} GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 13. SLA status missing
    SELECT case_id, employee_name, 'Missing SLA Status' AS issue_type, 'SLA {{ ref('stg_compliance') }} clock cannot evaluate status', 'Warning' AS severity, 'Provide created_date and target_due_date' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE sla_status = 'Not Eligible'
    UNION ALL
    -- 14. Escalated case missing escalation reason
    SELECT case_id, employee_name, 'Missing Escalation Reason' AS issue_type, 'Case is flagged escalated but reason is blank', 'Warning' AS severity, 'Document reason for case escalation' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE escalated = TRUE AND (escalation_reason IS NULL OR TRIM(escalation_reason) = '')
    UNION ALL
    -- 15. Labor case missing legal reference or case number
    SELECT case_id, employee_name, 'Missing Legal Reference' AS issue_type, 'Labor case is missing court case number or reference log', 'Warning' AS severity, 'Enter legal case details' AS recommended_action, er_case_record_id
    FROM {{ ref('base_er_case_population') }} WHERE case_type = 'Labor Case' AND (legal_reference IS NULL OR TRIM(legal_reference) = '' OR case_number IS NULL OR TRIM(case_number) = '')
