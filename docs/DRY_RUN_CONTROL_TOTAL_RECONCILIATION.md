# Dry-Run Control Total Reconciliation

This document details the checksum equations verified during dry-run ingestion tests.

---

## 1. Checksum Verification Formulas

### 1.1 HRIS / Employee Master
*   ** Roster Balance Check**:
    $$\text{Saudi Count (9)} + \text{Non-Saudi Count (9)} + \text{Missing (1)} = \text{Active Headcount (19)}$$

### 1.2 Payroll Ledger
*   **Total Gross Sum**: sum of `gross_salary` matches expected contract total `446175.00`.
*   **Balance Equation Check**:
    $$\text{Total Gross (446175.00)} - \text{Total Deductions (28000.00)} = \text{Total Net Pay (418175.00)}$$

### 1.3 Attendance logs
*   **Workday Punch Count**:
    $$\text{Unique Employees (19)} \times \text{Scheduled Workdays (26)} = \text{Expected Rows (494)}$$

### 1.4 Government / Compliance
*   **Saudization Ratio Check**:
    $$\frac{\text{Saudi Count (9)}}{\text{Saudi (9) + Non-Saudi (9)}} \times 100 = 50.00\%$$

### 1.5 Employee Relations
*   **Case Status Balance Check**:
    $$\text{Open Cases (8)} + \text{Closed Cases (2)} + \text{New Cases (9)} = \text{Total ER Population (11)}$$

### 1.6 Recruitment
*   **Fulfillment Ratio Check**:
    $$\frac{\text{Hired Candidates (1)}}{\text{Approved Vacancies (2)}} \times 100 = 50.00\%$$
*   **Offer Acceptance**:
    $$\frac{\text{Accepted Offers (3)}}{\text{Extended Offers (3)}} \times 100 = 100.00\%$$

### 1.7 Talent & Learning
*   **Goal Completion**:
    $$\frac{\text{Completed Goals (1)}}{\text{Total Goals (3)}} \times 100 = 33.33\%$$
*   **LMS Completion**:
    $$\frac{\text{Completed LMS Enrollments (2)}}{\text{Total LMS Enrollments (3)}} \times 100 = 66.67\%$$
