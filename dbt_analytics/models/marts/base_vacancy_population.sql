{{ config(materialized='view') }}

SELECT *
    FROM {{ ref('stg_vacancy_requests') }}
    WHERE status = 'Approved'
      AND approved_date <= '{{ var('report_month_end') }}'
