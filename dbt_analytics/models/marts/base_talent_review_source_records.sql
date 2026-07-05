{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY review_id, employee_id, performance_rating) AS talent_review_record_id,
        review_id, employee_id, performance_rating, potential_rating, flight_risk, retention_risk
    FROM {{ ref('stg_talent_reviews') }}
