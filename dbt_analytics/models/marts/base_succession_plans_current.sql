{{ config(materialized='view') }}

SELECT s.*
    FROM {{ ref('base_succession_source_records') }} s
    WHERE s.is_critical = TRUE
    {% if var('critical_titles_sql') | trim != '' %}
       OR s.role_title IN ({{ var('critical_titles_sql') }})
    {% endif %}

