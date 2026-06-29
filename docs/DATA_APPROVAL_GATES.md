# HR Command Center — Data Approval Gates

This document defines the quality gates required to transition the project from synthetic data to a live database. It outlines the specific checklists, scoring rules, and signoff templates required for Gates 1, 2, 3, and 4.

---

## Gate 0 — No Real Data (Complete)
*   **Objective**: Develop and verify frontend elements, backend API endpoints, and DuckDB schemas purely using synthetic mock files.
*   **Verification Checklists**:
    *   [x] All automated reconciliation assertions in `build_warehouse.py` pass.
    *   [x] Integration QA regression reports run with zero errors.
*   **Sign-off**: System Architect.

---

## Gate 1 — Source System Inventory Approved (Complete)
*   **Objective**: Register technical/business owners, data stewards, delivery methods, file formats, latency, mapping validation status, and approval workflow.
*   **Checklist for Gate 1 Signoff**:
    *   [x] Each of the 8 source categories has an assigned Business Owner, Technical Owner, and Data Steward.
    *   [x] Delivery method, expected format, and refresh frequency are documented for all streams.
    *   [x] Data Mapping Validation Protocol has been defined and executed.
    *   [x] Privacy classifications and masking rules are applied to all fields.
    *   [x] Governance risk register is logged and mitigations planned.
*   **Readiness Scoring Rules**:
    *   **Score Calculation**:
        $$\text{Gate 1 Score} = 0.15 \cdot \text{Owners} + 0.10 \cdot \text{Tech} + 0.15 \cdot \text{Stewards} + 0.10 \cdot \text{Format} + 0.10 \cdot \text{Delivery} + 0.10 \cdot \text{Freq} + 0.15 \cdot \text{Fields} + 0.10 \cdot \text{Privacy} + 0.05 \cdot \text{Risks}$$
    *   **Gate 1 Thresholds**:
        *   **Ready**: score $\ge$ 90% and zero critical blockers.
        *   **Conditional**: score 70–89% or non-critical gaps remain.
        *   **Not Ready**: score < 70% or any critical blocker remains.
*   **Sign-off Template Reference**:
    *   Use [GATE_1_SIGNOFF_TEMPLATE.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_1_SIGNOFF_TEMPLATE.md) for sign-block submissions.
*   **Sign-off Roles**: Business Owners, Technical Owners, Data Stewards, Security Lead.

---

## Gate 2 — Field Mapping Approved (Complete)
*   **Objective**: Review data contracts mapping file column headers to database views, approve synthetic test-file contracts, define naming conventions and control totals.
*   **Checklist for Gate 2 Signoff**:
    *   [x] 100% of required canonical fields are mapped or have approved exceptions.
    *   [x] Synthetic test-file contracts approved for all 8 categories.
    *   [x] Source control totals specified for all operational domains.
    *   [x] Mapping exceptions (EXP-001, EXP-002) resolved under approved treatments.
    *   [x] Rejection paths and version numbers documented.
*   **Readiness Scoring Rules**:
    *   **Ready**: 100% of required fields mapped or exceptioned, all exception resolutions signed off, and zero critical blockers.
    *   **Conditional**: Gaps only on optional fields or non-critical documentation.
    *   **Not Ready**: Any required field unmapped without exception, missing privacy classification, or missing masking rule for sensitive fields.
*   **Sign-off Template Reference**:
    *   Use [GATE_2_SIGNOFF_TEMPLATE.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_2_SIGNOFF_TEMPLATE.md) for signoff approvals.
*   **Sign-off Roles**: Data Stewards, Source Owners, Information Security Officer.

---

## Gate 3 — Privacy, Security & Access-Control Approved (Complete)
*   **Objective**: Verify and sign off on fields flagged as sensitive, approve RBAC rules, establish export restrictions, audit logging schemas, and retention timelines.
*   **Checklist for Gate 3 Signoff**:
    *   [x] 100% of fields have assigned privacy classifications.
    *   [x] Masking rules defined for all sensitive columns.
    *   [x] RBAC permission matrix verified across all 11 roles.
    *   [x] Export control policy and rules approved.
    *   [x] Audit logging schemas and priorities defined.
    *   [x] Retention limits and archiving rules approved.
    *   [x] Security risks Mitigated, Accepted, or Resolved in Risk Register.
*   **Readiness Scoring Rules**:
    *   **Ready**: 100% classifications complete, all roles verified, export/logging/retention rules defined, and zero critical unmitigated/unaccepted security risks remain.
    *   **Conditional**: Minor formatting details or logging priority tweaks remain.
    *   **Not Ready**: Any sensitive field lacks masking, any role lacks visibility definitions, or any critical risk is open.
*   **Sign-off Template Reference**:
    *   Use [GATE_3_SIGNOFF_TEMPLATE.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_3_SIGNOFF_TEMPLATE.md) for approval sign-blocks.
*   **Sign-off Roles**: Data Privacy Officer (DPO), CISO, Chief Legal Counsel.

---

## Gate 4 — Staged Dry-Run Ingestion Approved (Milestone 3E)
*   **Objective**: Run the Python ETL pipeline on mock files that mimic the exact format of the incoming CSV/Excel files to verify schema validations.
*   **Verification Checklists**:
    *   [x] Auto-quarantine rules trigger correctly on invalid ID/Date ranges.
    *   [x] Database builds without locking conflicts.
    *   [x] 100% of dry-run files, schemas, and control totals reconcile successfully.
*   **Readiness Scoring Rules**:
    *   **Ready**: All 8 categories pass dry-run loops, control totals reconcile, and no-real-data audit successfully executes.
*   **Sign-off Template Reference**:
    *   Use [GATE_4_DRY_RUN_SIGNOFF_TEMPLATE.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_4_DRY_RUN_SIGNOFF_TEMPLATE.md) for loop verifications.
*   **Sign-off**: Technical QA Engineer.

---

## Gate 5 — Controlled Real-Data Pilot Load
*   **Objective**: Ingest real data for a selected department under full audits, checking GOSI matching, payroll components, and compliance calculations.
*   **Verification Checklists**:
    *   [ ] AES-256 file encryption at rest verified.
    *   [ ] Audit logging index registers all read/write activities.
    *   [ ] Rollback process tested and certified.
*   **Sign-off**: CEO, CIO, and HR VP.
