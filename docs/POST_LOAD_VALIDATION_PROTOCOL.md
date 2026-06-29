# Post-Load Validation Protocol

This protocol defines the mandatory schema, privacy, and reconciliation checks required after any live data ingestion.

---

## 1. Post-Load Validation Checklists

### 1.1 Manifest Check
*   Verify the inbound file matches standard regex naming patterns.
*   Confirm the delimiter and encoding are correct.

### 1.2 Schema and Header Verification
*   Check that all columns match the targets in mapping configurations.
*   Validate datatypes for IDs, numbers, and date fields.

### 1.3 Privacy and Masking Audit
*   Confirm salaries are aggregated in views and hidden from unauthorized roles.
*   Confirm government IDs are partially redacted.
*   Confirm successor keys are mapped to opaque tokens.

### 1.4 Control Total Reconciliation
*   Reconcile row counts and headcount totals.
*   Run payroll net/gross verification checks.

---

## 2. Readiness checklist reference
For details on pre-execution check protocols and availability lists, refer to [REAL_DATA_LOAD_PRE_EXECUTION_CHECKLIST.md](file:///c:/tmp/HR-DASHBOARD/docs/REAL_DATA_LOAD_PRE_EXECUTION_CHECKLIST.md).
