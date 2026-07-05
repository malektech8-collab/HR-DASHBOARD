{{ config(materialized='view') }}

SELECT 
        '{{ var('report_month') }}' AS report_month,
        '{{ var('report_month_start') }}' AS report_month_start,
        '{{ var('report_month_end') }}' AS report_month_end,
        CAST(now() AS TIMESTAMP) AS last_refresh_timestamp
