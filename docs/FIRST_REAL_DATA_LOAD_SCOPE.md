# First Real Data Load Scope

This document registers the scope limits, owners, and exclusions mapped for the first controlled real-data load.

---

## 1. Initial Ingestion Scope (Low-Risk Domain)

To minimize operational risk, the first load is restricted strictly to the **Data Quality / Command Center Metadata** domain. No financial or employee-level data will be processed.

*   **Source Category**: Data Quality / Command Center Metadata
*   **Source System**: Metadata Audit Engine
*   **Business Owner**: VP of HR Operations
*   **Technical Owner**: IT Operations Director
*   **Data Steward**: Data Quality Engineer
*   **File Format**: CSV
*   **Delivery Method**: SFTP Secure Drop
*   **Expected Rows**: 9
*   **Date Range**: 2026-06-01 to 2026-06-30
*   **Included Fields**: `module_key`, `api_health_status`, `reconciliation_status`
*   **Excluded Fields**: All personal identity, payroll, ER, compliance, and talent columns.

---

## 2. Ingestion Rules & Masking
Since no PII columns are included in this scope, no masking rules are applied. Control totals verify the count of 9 module records.

---

## 3. Selection Rationale Reference
For details on why the Metadata Engine was selected as the sole recommended scope, refer to [FIRST_LOAD_DOMAIN_SELECTION_RATIONALE.md](file:///c:/tmp/HR-DASHBOARD/docs/FIRST_LOAD_DOMAIN_SELECTION_RATIONALE.md).
