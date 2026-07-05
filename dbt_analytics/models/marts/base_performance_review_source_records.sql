{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY review_id, employee_id, completed_date, rating) AS performance_review_record_id,
        review_id, employee_id, reviewer_id, review_period, rating, status, completed_date
    FROM {{ ref('stg_performance_reviews') }}
