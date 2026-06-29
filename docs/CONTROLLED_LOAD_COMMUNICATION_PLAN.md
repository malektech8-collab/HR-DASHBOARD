# Controlled Load Communication Plan

This plan defines the messaging protocols and alerts for scheduling live data load windows.

---

## 1. Notification Schedules

*   **24 Hours Pre-Load**: Send alert to technical stakeholders notifying them of the scheduled load window.
*   **1 Hour Pre-Load**: Temporary session lock warning displayed on the dashboard for active users.
*   **Load Start**: Log transaction start in the command center.
*   **Load Complete**: Re-enable dashboard metrics, send confirmation summary, and update freshness status logs.
*   **Ingest Fail Alert**: Trigger emergency rollback warning.

---

## 2. Notification Templates

```text
SUBJECT: [NOTICE] Scheduled HR Command Center Data Update - 2026-06
BODY:
Please note that a controlled data load is scheduled to take place on [DATE] at [TIME] UTC.
The dashboard views will be temporarily locked during this off-peak window.
```
