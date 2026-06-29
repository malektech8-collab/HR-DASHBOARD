# Data Export Control Policy

This policy outlines the security rules and checks governing data exports from the HR Analytics Command Center.

---

## 1. Core Export Restrictions

To prevent data leakage, the following rules are enforced:

*   **Government ID Exports**: Prohibited by default for all roles unless separately approved.
*   **Bank / IBAN Exports**: Prohibited from database extraction. IBAN fields are redacted at ingestion.
*   **Payroll Exports**: Restricted to `payroll_manager`, `hr_executive`, and `admin_system` roles.
*   **ER / Legal Exports**: Restricted to `employee_relations_manager`, `hr_executive`, and `admin_system` roles.
*   **Talent / Performance Exports**: Restricted to `talent_manager`, `hr_executive`, and `admin_system` roles.
*   **Free-Text Redactions**: Narrative case descriptions must run through NLP redaction before extraction to remove PII.
*   **Small Group Disclosure**: Executive aggregate exports must suppress categories with counts $\le$ 5 to prevent identifying individuals.
*   **Audit Logging**: Every export event must be logged with the user's role, timestamps, parameters, and justification comment.
