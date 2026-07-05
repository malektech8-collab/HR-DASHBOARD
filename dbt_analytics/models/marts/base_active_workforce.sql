{{ config(materialized='view') }}

WITH ranked_employees AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY joining_date DESC, contract_end_date DESC) as row_num
        FROM {{ ref('stg_employees') }}
        WHERE status = 'Active'
    )
    SELECT * EXCLUDE (row_num)
    FROM ranked_employees
    WHERE row_num = 1
