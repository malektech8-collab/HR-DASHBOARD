# Real Data Load Pre-Execution Checklist

This checklist registers the mandatory operational readiness verifications required immediately before starting the ingestion loop.

---

## 1. Operations Readiness Checks

*   [ ] **Written Sign-off**: Verify that final written approval is logged from the CISO and Chief HR Officer.
*   [ ] **Owner Availability**: Confirm that the Source Owner, Technical Owner, and Data Steward are available on-call during the scheduled window. Refer to [LOAD_WINDOW_OWNER_AVAILABILITY_MATRIX.md](file:///c:/tmp/HR-DASHBOARD/docs/LOAD_WINDOW_OWNER_AVAILABILITY_MATRIX.md).
*   [ ] **Infrastructure Checks**:
    *   Confirm target storage partition runs AES-256 disk encryption.
    *   Verify that `data/real_*` staging zones contain exclusively `.gitkeep` files.
*   [ ] **Rollback Checks**: Confirm pre-load DuckDB database snapshot has been successfully written and verified.
*   [ ] **Validation Protocols**:
    *   Reconcile control totals using synthetic configurations.
    *   Verify that audit logging index is active and logging view accesses.
*   [ ] **Stop Conditions**: Define fallback window offsets and triggers for aborting ingestion loops (e.g. any schema mismatch or PII leak warning).
