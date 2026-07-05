{{ config(materialized='view') }}

SELECT * EXCLUDE (rn)
    FROM (
        SELECT *,
               row_number() OVER (PARTITION BY candidate_id ORDER BY applied_date DESC, candidate_record_id DESC) AS rn
        FROM {{ ref('base_candidate_source_records') }}
    )
    WHERE rn = 1
