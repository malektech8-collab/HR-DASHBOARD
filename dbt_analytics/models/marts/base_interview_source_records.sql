{{ config(materialized='view') }}

SELECT 
        row_number() OVER (ORDER BY interview_id, candidate_id, interview_date) AS interview_record_id,
        interview_id,
        candidate_id,
        interview_date,
        recruiter_id AS interviewer_id,
        rating,
        outcome
    FROM {{ ref('stg_interviews') }}
