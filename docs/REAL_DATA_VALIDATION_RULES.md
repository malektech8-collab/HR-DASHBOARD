# HR Command Center — Real Data Validation Rules

This document details the checks and rules that must be executed by the intake validation script before data is staged.

---

## 1. Employee Master validation
- **Employee ID**: Must be present (`NOT_NULL`), unique, and match standard format (regex: `^EMP-[0-9]{4}$`).
- **Employee Number**: Must be unique across all active profiles.
- **Dates**: `joining_date` must be a valid date format (YYYY-MM-DD); `termination_date` must not be before `joining_date`.
- **Status**: Must be in: `["Active", "Terminated", "Suspended", "On Leave"]`.
- **Organizational Alignment**: `department`, `project`, and `cost_center` must map to registered values in `business_rules.yml`.

---

## 2. Payroll Validation
- **Employee ID**: Must exist in Employee Master.
- **Calculations**: `gross_salary - total_deductions = net_salary`. Any variance must be flagged as a warning.
- **Deduction and Allowances**: Negative values are strictly prohibited.
- **Duplicate Records**: An employee cannot have more than one payroll record per period.
- **Control Totals**: Total payroll cost must match the sum of gross pay reported in NetSuite ledgers.

---

## 3. Attendance Validation
- **Punches**: `check_out` must not be before `check_in`.
- **Date Context**: Date must be in the current report month.
- **Duplicate Punches**: Identical timestamp rows must be de-duplicated at import.
- **Overtime Hours**: Positive numbers only; overtime cost must match standard formula (`overtime_hours * base_hourly_rate * 1.5`).

---

## 4. Compliance Validation
- **Government IDs**: Iqama or National ID must be a 10-digit number.
- **Expiry Dates**: Expiry dates must be valid future dates.
- **Portals**: GOSI and WPS status fields must map to approved compliance lists.

---

## 5. Employee Relations Validation
- **Case IDs**: Unique constraints strictly enforced.
- **Timeline**: `closed_date` must not be before `created_date`.
- **Narratives**: Text columns are parsed to scrub names and financial numbers.

---

## 6. Recruitment & Workforce Planning Validation
- **Approved Vacancies**: Target headcount must be a positive integer.
- **Salary details**: Salary figures in offer letters must be within the salary band of the job profile.

---

## 7. Talent & Performance Validation
- **Performance Rating**: Must be an integer in range `[1, 5]`.
- **Succession Planning**: Successor employee IDs must match active employees.
- **Training Hours**: Course duration must be a positive number.
