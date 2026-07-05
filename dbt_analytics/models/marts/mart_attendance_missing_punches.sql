{{ config(materialized='view') }}

SELECT 
        employee_id,
        employee_name,
        department,
        project,
        COUNT(CASE WHEN actual_check_in IS NULL AND actual_check_out IS NOT NULL THEN 1 END) AS missing_check_in_count,
        COUNT(CASE WHEN actual_check_in IS NOT NULL AND actual_check_out IS NULL THEN 1 END) AS missing_check_out_count,
        COALESCE(SUM(missing_punch_count), 0) AS total_missing_punches
    FROM {{ ref('base_expected_attendance') }}
    GROUP BY employee_id, employee_name, department, project
    HAVING total_missing_punches > 0
