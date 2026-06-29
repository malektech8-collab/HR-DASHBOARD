# Masking Enforcement Specification

This document details the technical requirements for enforcing masking and pseudonymization rules at ingestion, database view, and API response levels.

---

## 1. Masking Rules by Data Category

### 1.1 Employee Identity
*   **National ID / Iqama**: Partially redacted using `REDACT_PARTIAL` rules. Shows first 4 characters and pads the rest with asterisks (e.g. `1098******`).
*   **Passport Number**: Fully redacted using `REDACT_FULL` rules for all non-authorized roles.
*   **Phone Number**: Masked to `+966*****5678` in lists.

### 1.2 Payroll & Financials
*   **Salary**: Standard users see sum or average values at the department or project level. Individual salaries are restricted to authorized roles.
*   **Deductions**: Aggregated to corporate total deduction metrics. Operational details are restricted.
*   **Bank Account / IBAN**: Redacted fully at ingestion using a placeholder string (`[REDACTED_FINANCIAL_DETAIL]`). Raw IBAN details are never stored.

### 1.3 Succession Candidate Keys (Mandatory)
*   **Successor Employee Key**: Pseudonymized using opaque deterministic tokens (e.g. `SUCC-0001` or a salted deterministic hash).
*   **Initials**: Strictly prohibited from display.
*   **Employee Number / Raw ID**: Strictly prohibited from display.
*   **Dashboard Display**: Default visualizations show succession coverage metrics at aggregate-only levels. Row-level pseudonymous lists are restricted to Talent Leads.
