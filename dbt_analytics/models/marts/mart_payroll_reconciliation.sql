{{ config(materialized='view') }}

WITH totals AS (
        SELECT 
            COALESCE(SUM(gross_pay), 0.0) AS total_gross_payroll,
            COALESCE(SUM(basic_salary), 0.0) AS basic_salary_sum,
            COALESCE(SUM(housing_allowance), 0.0) AS housing_allowance_sum,
            COALESCE(SUM(transport_allowance), 0.0) AS transport_allowance_sum,
            CASE WHEN {{ var('has_payroll_other_allowances_sql') }}
             THEN COALESCE(SUM(other_allowances), 0.0) END AS other_allowances_sum,
            CASE WHEN {{ var('has_payroll_overtime_sql') }}
             THEN COALESCE(SUM(overtime_amount), 0.0) END AS overtime_sum,
            CASE WHEN {{ var('has_payroll_deductions_sql') }}
             THEN COALESCE(SUM(deductions), 0.0) END AS deductions_sum,
            COALESCE(SUM(net_pay), 0.0) AS net_payroll,
            COUNT(DISTINCT employee_id) AS employees_paid_count
        FROM {{ ref('base_payroll_current') }}
    ),
    components_sum AS (
        -- NULL PROPAGATION HERE IS DELIBERATE. With a component withheld this
        -- total, and the two differences derived from it below, become NULL -
        -- which is the honest answer, because gross cannot be reconciled
        -- against components the client did not send. A number here would be
        -- the difference between gross and an incomplete sum, presented as
        -- unexplained payroll.
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
