# Audit Logging Requirements

This document defines the functional and technical logging requirements for auditing access within the HR Analytics Command Center.

---

## 1. Audit Log Schema

Every audit record must write the following fields:

*   `event_id`: Unique identifier (UUID).
*   `timestamp`: UTC execution timestamp.
*   `user_role`: Assigned active RBAC role (e.g. `payroll_manager`).
*   `user_identifier_placeholder`: Pseudonymized user identifier.
*   `action_type`: Action type (e.g., `READ_VIEW`, `EXPORT_EXCEL`, `REFRESH_DB`).
*   `module`: Affected sub-dashboard (e.g., `payroll`).
*   `resource_type`: Target database table or view (e.g., `mart_payroll_kpis`).
*   `sensitivity_level`: Data classification (e.g., `Financial Sensitive`).
*   `decision`: Action decision (`ALLOWED` or `DENIED`).
*   `export_file_reference`: File name and hash if export event.
*   `source_ip_placeholder`: Masked client source IP.
*   `reason_comment`: Required justification text for sensitive actions.

---

## 2. Event Audit Priorities

The system triggers logs for the following activity classes:

1.  **Access Attempts**: Login sessions and failed login attempts (Priority: High).
2.  **Sensitive Views**: Reading row-level salaries or ER details (Priority: High).
3.  **Data Extraction**: Exporting data grids (Priority: Critical).
4.  **Admin Updates**: Schema changes, pipeline refreshes, or configuration overrides (Priority: Critical).
5.  **Masking Override attempts**: Unauthorized request attempts to view unmasked values (Priority: Critical).

---

## 3. Real Data Ingestion Auditing
During Gate 5 operations, the ingestion daemon logs all file drops, naming standard checks, schema validations, and control total reconciliations in the audit log index.
