{{ config(materialized='view') }}

SELECT 
        row_number() OVER (ORDER BY offer_id, candidate_id, offer_date) AS offer_record_id,
        offer_id,
        candidate_id,
        offer_date,
        salary,
        outcome_status AS offer_status,
        outcome_date
    FROM {{ ref('stg_offers') }}
