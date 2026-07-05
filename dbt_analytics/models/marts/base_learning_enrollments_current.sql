{{ config(materialized='view') }}

SELECT l.*
    FROM {{ ref('base_learning_source_records') }} l
    WHERE l.employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
      AND l.enrollment_date <= DATE '{{ var('talent_month_end') }}'
