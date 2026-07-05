{{ config(materialized='view') }}

SELECT 
        row_number() OVER (ORDER BY requisition_id, job_title, department, project, cost_center, owner_id, approval_date) AS requisition_record_id,
        requisition_id,
        job_title,
        department,
        project,
        cost_center,
        owner_id AS recruiter_id,
        approval_date,
        target_hire_date,
        closed_date,
        status
    FROM {{ ref('stg_recruitment_requisitions') }}
