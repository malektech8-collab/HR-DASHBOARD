{{ config(materialized='view') }}

WITH anchor AS (
        SELECT last_day(CAST('{{ var('report_month') }}-01' AS DATE)) AS anchor_date
    ),
    emp_stats AS (
        SELECT 
            e.employee_id,
            e.is_saudi,
            e.joining_date,
            e.contract_end_date,
            e.manager_id,
            e.project,
            e.cost_center,
            c.iqama_expiry
        FROM {{ ref('base_active_workforce') }} e
        LEFT JOIN {{ ref('stg_compliance') }} c ON e.employee_id = c.employee_id
    ),
    kpi_calc AS (
        SELECT
            COUNT(DISTINCT employee_id) AS active_headcount,
            COUNT(DISTINCT CASE WHEN is_saudi = TRUE THEN employee_id END) AS saudi_headcount,
            COUNT(DISTINCT CASE WHEN is_saudi = FALSE THEN employee_id END) AS non_saudi_headcount,
            COUNT(DISTINCT CASE WHEN joining_date >= (SELECT anchor_date FROM anchor) - INTERVAL 90 DAY AND joining_date <= (SELECT anchor_date FROM anchor) THEN employee_id END) AS probation_count,
            COUNT(DISTINCT CASE WHEN contract_end_date >= (SELECT anchor_date FROM anchor) AND contract_end_date <= (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN employee_id END) AS contract_expiring_30,
            COUNT(DISTINCT CASE WHEN iqama_expiry >= (SELECT anchor_date FROM anchor) AND iqama_expiry <= (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN employee_id END) AS iqama_expiring_30,
            COUNT(DISTINCT CASE WHEN manager_id IS NULL OR manager_id = '' THEN employee_id END) AS missing_manager_count,
            COUNT(DISTINCT CASE WHEN project IS NULL OR project = '' THEN employee_id END) AS missing_project_count,
            COUNT(DISTINCT CASE WHEN cost_center IS NULL OR cost_center = '' THEN employee_id END) AS missing_cost_center_count
        FROM emp_stats
    )
    SELECT 
        active_headcount,
        saudi_headcount,
        non_saudi_headcount,
        CASE WHEN active_headcount = 0 THEN 0.0 ELSE CAST(saudi_headcount AS FLOAT) / active_headcount END AS saudization_rate,
        probation_count,
        contract_expiring_30,
        iqama_expiring_30,
        missing_manager_count,
        missing_project_count,
        missing_cost_center_count
    FROM kpi_calc
