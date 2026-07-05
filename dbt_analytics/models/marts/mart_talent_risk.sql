{{ config(materialized='view') }}

SELECT
        pr.employee_id,
        COALESCE(e.department, 'Unknown') AS department,
        COALESCE(e.project, 'Unassigned') AS project,
        pr.performance_category,
        COALESCE(tr.potential_rating, 'Unknown') AS potential_rating,
        COALESCE(tr.flight_risk, 'Unknown') AS flight_risk,
        CASE
            WHEN tr.flight_risk = 'High' AND (tr.potential_rating = 'High' OR pr.performance_category IN ('Outstanding', 'Exceeds Expectations'))
                THEN 'High Risk'
            WHEN (tr.flight_risk = 'High' AND tr.potential_rating NOT IN ('High') AND pr.performance_category NOT IN ('Outstanding', 'Exceeds Expectations'))
              OR (tr.flight_risk = 'Medium' AND (tr.potential_rating IN ('High', 'Medium') OR pr.performance_category IN ('Outstanding', 'Exceeds Expectations', 'Meets Expectations')))
                THEN 'Medium Risk'
            ELSE 'Low Risk'
        END AS risk_category
    FROM {{ ref('base_performance_reviews_current') }} pr
    LEFT JOIN {{ ref('base_talent_reviews_current') }} tr ON pr.employee_id = tr.employee_id
    LEFT JOIN {{ ref('base_talent_employee_population') }} e ON pr.employee_id = e.employee_id
