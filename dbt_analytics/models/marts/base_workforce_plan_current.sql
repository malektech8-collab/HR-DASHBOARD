{{ config(materialized='view') }}

SELECT *
    FROM {{ ref('stg_workforce_plan') }}
    WHERE period = '{{ var('report_month') }}'
