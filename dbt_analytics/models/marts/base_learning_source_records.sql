{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY enrollment_id, employee_id, course_id, enrollment_date) AS learning_enrollment_record_id,
        enrollment_id, employee_id, course_id, status, enrollment_date, completion_date
    FROM {{ ref('stg_learning_enrollments') }}
