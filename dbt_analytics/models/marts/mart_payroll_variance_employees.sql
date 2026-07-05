{{ config(materialized='view') }}

SELECT 
        c.employee_id,
        c.employee_name,
        COALESCE(p.gross_pay, 0.0) AS prev_amount,
        c.gross_pay AS curr_amount,
        c.gross_pay - COALESCE(p.gross_pay, 0.0) AS change_amount,
        CASE 
            WHEN COALESCE(p.gross_pay, 0.0) = 0.0 THEN 0.0 
            ELSE (c.gross_pay - p.gross_pay) / p.gross_pay 
        END AS change_pct
    FROM {{ ref('base_payroll_current') }} c
    LEFT JOIN {{ ref('base_payroll_previous') }} p ON c.employee_id = p.employee_id
