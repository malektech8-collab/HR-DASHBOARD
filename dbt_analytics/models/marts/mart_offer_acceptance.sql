{{ config(materialized='view') }}

SELECT 
        offer_status,
        COUNT(*) AS offer_count
    FROM {{ ref('base_offer_activity_current') }}
    GROUP BY offer_status
