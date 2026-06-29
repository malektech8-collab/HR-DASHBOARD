# Source Control Totals Specification

This document details the mathematical verification calculations and checks enforced during ingestion to ensure data completeness and consistency.

---

## 1. Validation Calculations

### 1.1 Employee Master
*   **Total Employee Count**: `COUNT(employee_id)`. Must match expected HR roster count.
*   **National Demographics Check**: `Saudi Count + Non-Saudi Count = Total Employee Count`.

### 1.2 Payroll Ledger
*   **Gross Pay Equation**:
    $$\text{Gross Pay} = \text{Basic Salary} + \text{Housing Allowance} + \text{Transport Allowance} + \text{Other Allowance} + \text{Overtime Amount}$$
*   **Net Pay Equation**:
    $$\text{Net Pay} = \text{Gross Pay} - \text{Deductions}$$
*   **Total Payroll Outflow**: Sum of net pay across all payroll records.

### 1.3 Attendance Logs
*   **Punch Match Validation**:
    $$\text{Total Attendance Rows} = \text{Expected Workdays} \times \text{Active Employees}$$
*   **Check-out Presence Check**: Excused or missing check-out checks.

### 1.4 Government / Compliance
*   **Saudization Percentage**:
    $$\text{Saudization \%} = \frac{\text{Saudi Headcount}}{\text{Total Headcount}} \times 100$$
*   **Iqama Validity Ratio**: Valid Iqamas vs Total non-Saudi employees.

### 1.5 Employee Relations
*   **Case Status Balance Check**:
    $$\text{Total Cases} = \text{Open Cases} + \text{Closed Cases}$$

### 1.6 Recruitment
*   **Fulfillment Ratio Check**:
    $$\frac{\text{Hired Candidates}}{\text{Approved Vacancies}} \times 100$$

### 1.7 Talent & Succession
*   **Review Completion Ratio**:
    $$\text{Review Completion \%} = \frac{\text{Completed Reviews}}{\text{Total Employees}} \times 100$$

### 1.8 Command Center Metadata
*   **Audited Module Balance**: Verified active modules registry vs base check counts.

---

## 2. Dry-Run Verification Targets
All calculations and balance checking formulas are verified using targets in [synthetic_dry_run_control_totals.yml](file:///c:/tmp/HR-DASHBOARD/config/synthetic_dry_run_control_totals.yml) during Gate 4 checks.
