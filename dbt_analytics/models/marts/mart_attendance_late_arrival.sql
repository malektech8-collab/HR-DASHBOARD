{{ config(materialized='view') }}

SELECT 
        employee_id,
        employee_name,
        department,
        project,
        COALESCE(SUM(calculated_late_minutes), 0) AS total_late_minutes,
        COALESCE(SUM(excused_late_minutes), 0) AS total_excused_minutes,
        COALESCE(SUM(calculated_net_late_minutes), 0) AS total_net_late_minutes,
        COUNT(CASE WHEN calculated_late_minutes > 0 THEN 1 END) AS late_arrival_incidents_count
    FROM {{ ref('base_expected_attendance') }}
    GROUP BY employee_id, employee_name, department, project
    HAVING total_late_minutes > 0
