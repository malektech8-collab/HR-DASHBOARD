# First Ingestion Domain Selection Rationale

This document details the selection rationale for choosing the initial low-risk pilot ingestion scope.

---

## 1. Domain Risk Assessment

To guarantee that no sensitive employee details are exposed during initial interface tests, the steering committee audited all operational domains:

*   **Data Quality / Command Center Metadata**: **Lowest Risk**
    *   *PII Density*: Zero.
    *   *Allowed Fields*: `module_key`, `module_name`, `api_health_status`, `reconciliation_status`, `qa_artifact_status`, `refresh_status`, `freshness_timestamp`, `dashboard_route_key`, `exception_count_by_module`, `owner_role`.
    *   *Decision*: Recommended as the sole domain for the first controlled pilot load.

*   **HRIS Employee Master**: **Medium Risk**
    *   *PII Density*: High.
    *   *Decision*: Excluded from the first load scope; allowed as a secondary stage only with 100% pseudonymization rules applied.

*   **Payroll, ER, and Talent**: **High Risk**
    *   *PII Density*: High.
    *   *Decision*: Prohibited from pilot testing.
