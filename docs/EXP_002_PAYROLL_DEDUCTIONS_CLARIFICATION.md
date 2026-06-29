# Mapping Clarification — EXP-002 Payroll Deductions

This document clarifies the mapping strategy and access controls applied to payroll deductions.

---

## 1. Deductions Ingestion Strategy

*   **Single Aggregate Field**: The system maps the raw total deductions to a single canonical field `deductions`.
*   **Detailed Deductions Out of Scope**: Employee-level deduction categories (loan repayments, advances, GOSI contributions, absences) are out-of-scope and excluded from ingestion.
*   **Data Aggregation**: Standard dashboard widgets use aggregate deduction sums for department and project cost metrics.
*   **Access Restrictions**: Row-level visibility of the total deductions amount is restricted to payroll-authorized roles only.
*   **Verification**: Calculated net pay is verified against the basic salary, allowances, and aggregate deductions:
    $$\text{Net Pay} = \text{Gross Pay} - \text{Deductions}$$
