# HR Command Center — Production Readiness Checklist

This checklist must be fully completed and signed off before the analytical engine is deployed into production or connected to real data.

---

## 1. Compliance and Governance Checklist
*   [ ] **Gate 1 Owner Sign-off**: Every technical and business owner has signed the delivery contract.
*   [ ] **Gate 2 Field Mapping Approved**: All mappings in `real_data_mapping.yml` are steward-validated and owner-approved.
*   [ ] **Gate 2 Exception Acceptance**: All mapping exceptions are officially approved by the Stewardship Board.
*   [ ] **Synthetic Test File Contract Audits**: Synthetic file schemas and formatting constraints are approved.
*   [ ] **Gate 3 Privacy & Access Approved**: RBAC permission matrix, visibility controls, and DPO audit logged.
*   [ ] **Gate 3 Security Risk Sign-off**: CISO has signed off on the Risk Register.
*   [ ] **Gate 3 Export & Audit Logs Approved**: Audit logging specifications and export control policy approved.
*   [ ] **Gate 4 Dry-Run Loop Verified**: All 8 categories of dry-run file ingest checks have run successfully with zero errors.
*   [ ] **Gate 4 No-Real-Data Audit Complete**: Audit script verified zero PII leaks in dry-run.
*   [ ] **Gate 5 Execution Readiness Decision Logged**: Decision log completed in configurations and docs.
*   [ ] **Gate 5 Pre-Execution Checklist Verified**: Verification of owner availability during window complete.
*   [ ] **Gate 5 Final Written Authorization Logged**: Written sign-off from both CISO and CHRO verified.
*   [ ] **Privacy Classification Approval**: Legal counsel has reviewed and signed off on `privacy_classification.yml`.
*   [ ] **Masking and Redaction Audit**: Data privacy officer has certified masking rules in `masking_rules.yml`.
*   [ ] **Access Role Audits**: Permission models checked in `access_roles.yml` against corporate policies.

---

## 2. Ingestion & Validation Checklist
*   [ ] **Test File validation**: Synthetic dry-run data has successfully run through `data/real_inbox/` with zero unexpected rejects.
*   [ ] **Control Totals Check**: Financial and headcount reconciliation scripts verified.
*   [ ] **Log Auditing**: Audit triggers confirm every database view access is logged.
*   [ ] **Backup and Rollback Plan**: Active DuckDB snapshots and data recovery routines certified.

---

## 3. Operations & Infrastructure Checklist
*   [ ] **Encryption Check**: Staging directories in `data/real_*` run on AES-256 encrypted drives.
*   [ ] **Export Restrictions**: Export buttons on frontend restricted to authorized roles.
*   [ ] **Data Retention Enforcement**: Automated script deletes archived raw files after 90 days.
*   [ ] **Incident Response Contact**: Listed security architect to handle data breach protocol.
*   [ ] **Final Go/No-Go Sign-off**: Signed by CEO, CIO, and HR VP.

---

## Milestone 3I Authorization Review Checkpoints

- [ ] Final authorization evidence reviewed and validated
- [ ] Go/No-Go decision recorded
- [ ] First-load scope confirmed (Data Quality / Command Center Metadata)
- [ ] All 22 stop criteria confirmed intact
- [ ] Owner availability confirmed
- [ ] No-real-data audit passed

See: [Milestone 3I Go/No-Go Summary](MILESTONE_3I_GO_NO_GO_SUMMARY.md)
