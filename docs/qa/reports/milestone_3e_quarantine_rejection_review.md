# Milestone 3E - Quarantine & Rejection Review

This report audits the operational handling and routing of invalid synthetic dry-run files.

---

## 1. Quarantine Routing Audit
*   **Duplicate ID / Null ID**: Routed to `data/synthetic_dry_run/quarantine/`. Logs written to `quarantine.log`.
*   **Tardy Check-out / Closed Date Out of Range**: Routed to `data/synthetic_dry_run/quarantine/`.
*   **Status**: Passed.

---

## 2. Rejection Routing Audit
*   **Net Pay / Gross Mismatch**: Routed to `data/synthetic_dry_run/rejected/`.
*   **Raw Successor ID Exposed**: Routed to `data/synthetic_dry_run/rejected/`. Ingestion loops blocked.
*   **Real Data Pattern / Credential Exposed**: Routed to `data/synthetic_dry_run/rejected/`.
*   **Status**: Passed.
