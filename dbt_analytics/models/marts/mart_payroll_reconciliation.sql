{{ config(materialized='view') }}

WITH totals AS (
        SELECT 
            COALESCE(SUM(gross_pay), 0.0) AS total_gross_payroll,
            COALESCE(SUM(basic_salary), 0.0) AS basic_salary_sum,
            COALESCE(SUM(housing_allowance), 0.0) AS housing_allowance_sum,
            COALESCE(SUM(transport_allowance), 0.0) AS transport_allowance_sum,
            COALESCE(SUM(other_allowances), 0.0) AS other_allowances_sum,
            COALESCE(SUM(overtime_amount), 0.0) AS overtime_sum,
            COALESCE(SUM(deductions), 0.0) AS deductions_sum,
            COALESCE(SUM(net_pay), 0.0) AS net_payroll,
            COUNT(DISTINCT employee_id) AS employees_paid_count
        FROM {{ ref('base_payroll_current') }}
    ),
    components_sum AS (
        SELECT 
            basic_salary_sum + housing_allowance_sum + transport_allowance_sum + other_allowances_sum + overtime_sum AS sum_displayed_components
        FROM totals
    ),
    project_total AS (
        SELECT COALESCE(SUM(total_payroll_cost), 0.0) AS project_payroll_total FROM {{ ref('mart_payroll_by_project') }}
    ),
    dept_total AS (
        SELECT COALESCE(SUM(total_payroll_cost), 0.0) AS department_payroll_total FROM {{ ref('mart_payroll_by_department') }}
    ),
    exceptions AS (
        SELECT COUNT(*) AS payroll_exception_count FROM {{ ref('mart_payroll_exceptions') }}
    )
    SELECT 
        t.*,
        c.sum_displayed_components,
        t.total_gross_payroll - c.sum_displayed_components AS unreconciled_component_difference,
        t.total_gross_payroll - t.deductions_sum AS gross_minus_deductions,
        (t.total_gross_payroll - t.deductions_sum) - t.net_payroll AS net_unreconciled_difference,
        p.project_payroll_total,
        d.department_payroll_total,
        e.payroll_exception_count
    FROM totals t, components_sum c, project_total p, dept_total d, exceptions e
