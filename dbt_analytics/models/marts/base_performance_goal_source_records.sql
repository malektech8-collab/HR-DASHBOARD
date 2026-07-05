{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY goal_id, employee_id, due_date) AS performance_goal_record_id,
        goal_id, employee_id, title, status, due_date, completed_date
    FROM {{ ref('stg_performance_goals') }}
