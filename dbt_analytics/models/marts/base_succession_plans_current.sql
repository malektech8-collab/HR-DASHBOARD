{{ config(materialized='view') }}

SELECT s.*
    FROM {{ ref('base_succession_source_records') }} s
    WHERE (s.is_critical = TRUE OR s.role_title IN ({{ var('critical_titles_sql') }}))
