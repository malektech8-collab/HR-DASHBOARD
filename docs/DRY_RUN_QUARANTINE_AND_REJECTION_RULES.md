# Dry-Run Quarantine & Rejection Rules

This document outlines the routing actions, logs, and remediation paths for files failing validation checks.

---

## 1. Action Definitions

### 1.1 Quarantine
*   **Trigger**: Row-level formatting errors, missing optional values, out-of-range rating flags, or mismatching reference keys.
*   **Action**: Move row-level records to quarantine staging area `data/synthetic_dry_run/quarantine/`.
*   **Log Location**: `data/synthetic_dry_run/logs/quarantine.log`.
*   **Resolution Path**: Route to Data Steward for validation or manual record repair.

### 1.2 Reject
*   **Trigger**: File schema mismatches, missing required columns, wrong delimiter, failed control total balance equations, raw PII candidate leaks, raw IBAN indicators, or credentials.
*   **Action**: Stop ingestion of the file, send warning alert to dashboard, and move the entire file to `data/synthetic_dry_run/rejected/`.
*   **Log Location**: `data/synthetic_dry_run/logs/rejection.log`.
*   **Resolution Path**: Reject transfer loop and request clean export file from the source systems owner.
