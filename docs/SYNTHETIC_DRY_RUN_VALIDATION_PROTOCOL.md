# Synthetic Dry-Run Validation Protocol

This protocol defines the ingestion loop validation checks and execution stages for valid and invalid mock files.

---

## 1. Validation Execution Workflow

```mermaid
graph TD
    A[Inbound Mock File Drop] --> B[Stage 1: Naming & Format Check]
    B -- Match --> C[Stage 2: Schema & Header Audit]
    B -- Mismatch --> Z[Rejection Zone]
    C -- Valid --> D[Stage 3: Row-Level Constraint Check]
    C -- Invalid --> Z
    D -- Pass --> E[Stage 4: Control Totals Reconciliation]
    D -- Fail --> Y[Quarantine Zone]
    E -- Match --> F[Stage 5: Approved Database Ingest]
    E -- Mismatch --> Y
```

---

## 2. Testing Scenarios

### 2.1 Valid Scenarios Testing
*   Ensure that file ingest processes a valid CSV/XLSX template.
*   Reconcile control totals and confirm records match base DuckDB view mappings.

### 2.2 Invalid Scenarios Testing
*   **Duplicate ID / Null ID**: Triggers rule `INT-001` or `INT-002`, routing records to `quarantine/`.
*   **Net Pay / Gross Mismatch**: Triggers rule `LOG-002` or `LOG-003`, rejecting the entire file.
*   **Raw Successor ID Exposed**: Triggers rule `SAF-001`, rejecting the file immediately.
*   **Real Data Indicator**: Triggers rule `SAF-002` or `SAF-003`, blocking ingestion.
