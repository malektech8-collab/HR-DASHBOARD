{{ config(materialized='view') }}

WITH ranked AS (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY talent_review_record_id DESC) AS rn
        FROM {{ ref('base_talent_review_source_records') }}
        WHERE employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
    )
    SELECT * FROM ranked WHERE rn = 1
