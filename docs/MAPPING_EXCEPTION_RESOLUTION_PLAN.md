# Mapping Exception Resolution Plan

This plan outlines the design and governance decisions taken to resolve the outstanding field mapping exceptions for Gate 2.

---

## 1. Exception 1: Successor Employee Reference (EXP-001)

### 1.1 Resolution Plan
To secure successor employee identities, the system implements **Opaque Successor Key Hashing**:
*   Raw successor IDs (e.g. `EMP-0020`) are parsed and mapped to an opaque token format (e.g. `SUCC-0001` or a salted deterministic token).
*   No initials, names, employee numbers, or raw IDs are displayed or stored in analytical tables.
*   Standard dashboards display succession metrics as aggregate-only coverage (e.g., succession gap counts).
*   Authorized Talent leadership may access row-level pseudonymous successor tokens for planning, but the actual re-identification map is handled outside the analytics dashboard.

---

## 2. Exception 2: Payroll Deductions Breakdown (EXP-002)

### 2.1 Resolution Plan
To protect detailed payroll deduction categories:
*   Ingest only the single aggregate numeric value from NetSuite into the canonical field `deductions`.
*   All detailed deduction lists (social insurance, loan repayments, absences) are out-of-scope and will not be ingested.
*   Deduction charts and tables display aggregate deductions only.
*   Row-level aggregate deduction totals are restricted to payroll-authorized roles.
