{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY assessment_id, employee_id, competency_name, assessed_date) AS competency_assessment_record_id,
        assessment_id, employee_id, competency_name, required_score, actual_score, assessed_date
    FROM {{ ref('stg_competency_assessments') }}
