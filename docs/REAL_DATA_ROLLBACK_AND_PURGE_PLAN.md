# Real Data Rollback & Purge Plan

This plan outlines the recovery steps and purge actions in the event of an ingestion loop failure.

---

## 1. Failure Recovery Procedures

### 1.1 Ingestion File Error (Wrong file, period, or duplicate)
*   **Action**: Discard the transaction, remove the source file from staging, and restore the database from the pre-load DuckDB snapshot.

### 1.2 Schema/Mapping Failures
*   **Action**: Purge the generated base views and restore the last stable schema configuration.

### 1.3 PII Masking Leak
*   **Action**: Terminate active dashboard user sessions, purge the affected DuckDB table columns, rebuild views, and restore the last backup.

---

## 2. Verification and Restarts
Re-running an ingestion loop after rollback requires the explicit approval of the Data Quality Steward and CISO.

---

## 3. Rolback Owner Alignment
During execution windows, rollback actions are owned and executed by the **Systems Architect** as specified in the [REAL_DATA_LOAD_PRE_EXECUTION_CHECKLIST.md](file:///c:/tmp/HR-DASHBOARD/docs/REAL_DATA_LOAD_PRE_EXECUTION_CHECKLIST.md).
