# Controlled Real-Data Ingestion Runbook

This runbook registers the operational checks, ingestion commands, and validation loops for executing a controlled real-data load.

---

## 1. Pre-Load Checklists
*   [ ] Verify Gate 4 dry-run verification loops have achieved "Ready" status.
*   [ ] Confirm AES-256 staging partition permissions are active.
*   [ ] Validate that target directories in `data/real_*` contain only `.gitkeep` files.
*   [ ] Verify the target ingestion file name matches standard regex rules.
*   [ ] Obtain the final written CISO and CHRO signoff token.
*   [ ] Confirm scheduling window parameters defined in [CONTROLLED_LOAD_SCHEDULING_REQUIREMENTS.md](file:///c:/tmp/HR-DASHBOARD/docs/CONTROLLED_LOAD_SCHEDULING_REQUIREMENTS.md) are met.

---

## 2. Ingestion Execution
*   **Step 1**: Place the inbound file in `data/real_inbox/`.
*   **Step 2**: Trigger the schema validator to scan column counts, delimiters, and formats.
*   **Step 3**: Verify control totals and run the no-real-data validation checks.
*   **Step 4**: Trigger view generation to compile canonical DuckDB schema updates.

---

## 3. Post-Load Checks
*   [ ] Validate headcount sums and record counts against source totals.
*   [ ] Run masking audits on employee identity, salaries, and candidate keys.
*   [ ] Check audit logs to confirm that view accesses were registered.
*   [ ] Archive source files under `data/real_archive/`.
