# Controlled Load Scheduling Requirements

This document registers the scheduling parameters and window offsets required to execute a controlled pilot load.

---

## 1. Scheduling Parameters

To prevent impact on dashboard active sessions, the ingestion loop must follow these rules:

*   **Allowed Timeframe**: Ingestion must run during off-peak weekend hours (Friday 20:00:00 UTC to Saturday 02:00:00 UTC).
*   **Release Buffer**: A minimum buffer of 48 hours is required between signing approvals and beginning the load.
*   **Proposed Ingestion Window**: Friday, 2026-07-03 at 21:00:00 UTC.
*   **Fallback Window**: Saturday, 2026-07-04 at 21:00:00 UTC.
*   **Stop Conditions**: Any validation failure, schema header mismatch, or privacy exception logs will abort the load window immediately.

---

## 2. Scheduling Package Reference
For details on scheduling status and proposed slots, refer to [CONTROLLED_LOAD_SCHEDULING_PACKAGE.md](file:///c:/tmp/HR-DASHBOARD/docs/CONTROLLED_LOAD_SCHEDULING_PACKAGE.md).
