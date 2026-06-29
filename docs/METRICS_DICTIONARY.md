# Metrics Dictionary Documentation

This file describes the business formulas and rules used in the HR Analytics Command Center.

## Executive Summary Metrics

### 1. Active Headcount
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active'`
- **Source**: `dim_employees` (from `employees_sample.csv`)
- **Filters**: `month`, `company`, `project`, `department`, `nationality`
- **Limitations**: Reflects the status value at the end of the snapshot month.

### 2. Joiners This Month
- **Formula**: `COUNT(DISTINCT employee_id) WHERE joining_date BETWEEN month_start AND month_end`
- **Source**: `dim_employees` (from `employees_sample.csv`)
- **Filters**: `month`, `company`, `project`
- **Limitations**: Relies on accurate `joining_date` entries.

### 3. Leavers This Month
- **Formula**: `COUNT(DISTINCT employee_id) WHERE termination_date BETWEEN month_start AND month_end`
- **Source**: `dim_employees` (from `employees_sample.csv`)
- **Filters**: `month`, `company`, `project`
- **Limitations**: Dependent on timely termination updates.

### 4. Turnover Rate
- **Formula**: `leavers_this_month / active_headcount` (temporary Milestone 1 metric, to be replaced by average active headcount in Milestone 2)
- **Source**: `dim_employees`
- **Filters**: `month`, `company`
- **Limitations**: High values may occur in small teams/departments.

### 5. Payroll Cost
- **Formula**: `SUM(gross_pay) WHERE payroll_period = selected_month`
- **Source**: `fact_payroll` (from `payroll_sample.csv`)
- **Filters**: `month`, `company`, `project`
- **Limitations**: Requires completed monthly payroll run inputs.

### 6. Overtime Cost
- **Formula**: `SUM(overtime_amount) WHERE payroll_period = selected_month`
- **Source**: `fact_payroll` (from `payroll_sample.csv`)
- **Filters**: `month`, `project`
- **Limitations**: Limited to paid overtime recorded on the payslip.

### 7. Absence Days
- **Formula**: `SUM(absence_days)`
- **Source**: `fact_attendance` (from `attendance_sample.csv`)
- **Filters**: `month`, `project`
- **Limitations**: Only captures unapproved or unpaid absences recorded by attendance system.

### 8. Data Quality Score
- **Formula**: `1.0 - (total_errors / total_checks)` where total checks is `8 * total_employees`
- **Source**: `fact_data_quality_issues`
- **Filters**: None (global pipeline evaluation)
- **Limitations**: Scoring weights all validations equally.

## Workforce Metrics

### 9. Saudi Headcount
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND is_saudi = TRUE`
- **Source**: `dim_employees` (from `employees_sample.csv`)
- **Filters**: `month`, `department`, `project`

### 10. Non-Saudi Headcount
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND is_saudi = FALSE`
- **Source**: `dim_employees` (from `employees_sample.csv`)
- **Filters**: `month`, `department`, `project`

### 11. Saudization Rate
- **Formula**: `saudi_headcount / active_headcount`
- **Source**: `dim_employees`
- **Filters**: `month`, `department`, `project`
- **Limitations**: Reflects raw head counts, not GOSI-weighted rules.

### 12. Employees on Probation
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND joining_date BETWEEN (anchor_date - 90 days) AND anchor_date` (does not count future joining dates)
- **Source**: `dim_employees`
- **Filters**: `month`, `department`
- **Limitations**: Relies on accurate `joining_date` input.

### 13. Contracts Expiring in 30 Days
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND contract_end_date BETWEEN anchor_date AND (anchor_date + 30 days)`
- **Source**: `dim_employees`
- **Filters**: `month`, `department`, `project`
- **Limitations**: Does not count expired contracts or null end dates (which are classified separately).

### 14. Iqamas Expiring in 30 Days
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND is_saudi = FALSE AND iqama_expiry BETWEEN anchor_date AND (anchor_date + 30 days)`
- **Source**: Joined from `compliance` (preferred source joined by `employee_id`)
- **Filters**: `month`, `department`, `project`
- **Limitations**: Excludes Saudis. Relies on compliance log updates.

### 15. Missing Manager
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND (manager_id IS NULL OR manager_id = '')`
- **Source**: `dim_employees`
- **Filters**: `department`, `project`

### 16. Missing Project
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND (project IS NULL OR project = '')`
- **Source**: `dim_employees`
- **Filters**: `department`

### 17. Missing Cost Center
- **Formula**: `COUNT(DISTINCT employee_id) WHERE status = 'Active' AND (cost_center IS NULL OR cost_center = '')`
- **Source**: `dim_employees`
- **Filters**: `department`, `project`

## Payroll & Cost Metrics

### 18. Total Payroll Cost
- **Formula**: `SUM(gross_pay)`
- **Source**: `base_payroll_current` (calculated from `payroll_sample.csv`)
- **Validation Rule**: Equal to `SUM(basic_salary + allowances_cost + overtime_cost)` minus mismatch variance (or `SUM(gross_pay)` across all records).

### 19. Net Payroll
- **Formula**: `SUM(net_pay)`
- **Source**: `base_payroll_current`
- **Validation Rule**: Reconciles to `gross_pay - deductions`.

### 20. Employees Paid
- **Formula**: `COUNT(DISTINCT employee_id)`
- **Source**: `base_payroll_current`

### 21. Average Cost per Employee
- **Formula**: `total_payroll_cost / employees_paid`
- **Source**: `mart_payroll_kpis`

### 22. Payroll Variance MoM
- **Formula**: `(total_payroll_cost_current - total_payroll_cost_previous) / total_payroll_cost_previous`
- **Source**: `mart_payroll_kpis` (compares current vs previous month)

### 23. Basic Salary Cost
- **Formula**: `SUM(basic_salary)`
- **Source**: `base_payroll_current`

### 24. Allowances Cost
- **Formula**: `SUM(housing_allowance + transport_allowance + other_allowances)`
- **Source**: `base_payroll_current`

### 25. Overtime Cost
- **Formula**: `SUM(overtime_amount)`
- **Source**: `base_payroll_current`

### 26. Deductions
- **Formula**: `SUM(deductions)`
- **Source**: `base_payroll_current`

### 27. Payroll Exceptions Count
- **Formula**: `COUNT(*)`
- **Source**: `mart_payroll_exceptions`

## Attendance & Overtime Metrics

### 28. Attendance Compliance %
- **Formula**: `1.0 - (COUNT(CASE WHEN calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0 THEN 1 END) / CAST(COUNT(*) AS DOUBLE))`
- **Source**: `base_expected_attendance` (uses expected workdays as denominator)

### 29. Absence Days
- **Formula**: `SUM(absence_days)` (defined as 1.0 when attendance logs are missing or explicitly marked absent)
- **Source**: `base_expected_attendance`

### 30. Late Minutes
- **Formula**: `SUM(calculated_late_minutes)` where `calculated_late_minutes = GREATEST(date_diff('minute', scheduled_start, actual_check_in) - grace_period_minutes, 0)`
- **Source**: `base_attendance_current`

### 31. Excused Late Minutes
- **Formula**: `SUM(excused_late_minutes)`
- **Source**: `base_attendance_current`

### 32. Net Late Minutes
- **Formula**: `SUM(calculated_net_late_minutes)` where `calculated_net_late_minutes = GREATEST(calculated_late_minutes - excused_late_minutes, 0)`
- **Source**: `base_attendance_current`

### 33. Early Leave Minutes
- **Formula**: `SUM(date_diff('minute', actual_check_out, scheduled_end))` when `actual_check_out < scheduled_end`
- **Source**: `base_attendance_current`

### 34. Missing Punch Count
- **Formula**: `SUM(missing_punch_count)` (identifies check-in missing, check-out missing, one punch only, and both punches missing)
- **Source**: `base_attendance_current`

### 35. Overtime Hours
- **Formula**: `SUM(overtime_hours)` where `overtime_approved = TRUE`
- **Source**: `base_attendance_current`

### 36. Overtime Cost
- **Formula**: `SUM(payroll_ot_cost)`
- **Source**: `base_attendance_payroll_overtime` (reconciled against payroll overtime ledger)

### 37. Attendance Exception Count
- **Formula**: `COUNT(*)` (sum of 14 audit reconciliation rules)
- **Source**: `mart_attendance_exceptions`

## Recruitment & Workforce Planning Metrics

### 38. Open Requisitions
- **Formula**: `COUNT(requisition_id) WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold')`
- **Source**: `base_recruitment_requisitions_current`

### 39. Approved Vacancies
- **Formula**: `SUM(quantity) WHERE status = 'Approved'`
- **Source**: `base_vacancy_population`

### 40. Candidates in Pipeline
- **Formula**: `COUNT(candidate_id)`
- **Source**: `base_candidate_pipeline_current`

### 41. Interviews Scheduled
- **Formula**: `COUNT(interview_id) WHERE interview_date BETWEEN report_month_start AND report_month_end`
- **Source**: `base_interview_activity_current`

### 42. Offers Extended
- **Formula**: `COUNT(offer_id) WHERE offer_date BETWEEN report_month_start AND report_month_end`
- **Source**: `base_offer_activity_current`

### 43. Offer Acceptance %
- **Formula**: `accepted offers / decided offers` where decided offers includes status values `Accepted`, `Rejected`, `Declined` (excluding `Pending`)
- **Source**: `base_offer_activity_current`

### 44. Hires This Month
- **Formula**: `COUNT(candidate_id) WHERE hire_date BETWEEN report_month_start AND report_month_end` where `hire_date` is mapped to `onboarding.start_date` when status is hired/started/completed
- **Source**: `base_onboarding_current`

### 45. Average Time to Fill
- **Formula**: `AVG(hire_date - approval_date)` for linked requisition-candidate-onboarding chains
- **Source**: `mart_recruitment_time_to_fill`

### 46. Overdue Requisitions
- **Formula**: `COUNT(requisition_id) WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND effective_target_hire_date < report_anchor_date`
- **Source**: `base_recruitment_requisitions_current`

### 47. Workforce Plan Fulfillment %
- **Formula**: `actual_active_headcount / planned_headcount` where actual headcount comes from `base_active_workforce` and planned headcount comes from `base_workforce_plan_current`. If planned headcount is 0: returns 100% if actual is 0, else 0%
- **Source**: `mart_workforce_plan_vs_actual`

### 48. Recruitment Exception Count
- **Formula**: `COUNT(*)` (sum of 20 recruitment audit exceptions)
- **Source**: `mart_recruitment_exceptions`

*Note on Historical Trends Simulation:* The historical trends visually plotted for months `2026-04` and `2026-05` in `mart_recruitment_trends` are simulated static values for MVP layout demonstration. Live data begins in `2026-06`.


