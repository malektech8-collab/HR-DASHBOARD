{{ config(materialized='view') }}

SELECT *
    FROM {{ ref('stg_workforce_plan') }}
    WHERE period = '{rec_report_month}'
