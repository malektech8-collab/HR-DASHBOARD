# Milestone 3K - Synthetic Evidence Dry-Run Report

**Validation Scope**: Synthetic evidence files only.
**Input Directory**: `data/synthetic_dry_run/evidence/`

## Summary

| Metric | Count |
|--------|-------|
| Total synthetic evidence files | 6 |
| Passed files | 3 |
| Rejected files | 3 |
| Negative test cases rejected as expected | Yes |

## File Results

| File | Expected | Actual | Rejection Reasons |
|------|----------|--------|-------------------|
| `data/synthetic_dry_run/evidence/reject_execution_approval.yml` | reject | reject | real_data_execution must remain Not Approved |
| `data/synthetic_dry_run/evidence/reject_load_scheduling.yml` | reject | reject | load_scheduling must remain Not Approved |
| `data/synthetic_dry_run/evidence/reject_prohibited_domain.yml` | reject | reject | approved_source_category is not allowed |
| `data/synthetic_dry_run/evidence/valid_chro_evidence.yml` | pass | pass | N/A |
| `data/synthetic_dry_run/evidence/valid_ciso_evidence.yml` | pass | pass | N/A |
| `data/synthetic_dry_run/evidence/valid_it_operations_evidence.yml` | pass | pass | N/A |

## Governance Confirmation

- Synthetic validation results do not update or imply real authorization evidence approval.
- Real evidence remains `Not Provided`.
- Decision recommendation remains `Hold`.
- Real-data execution remains `Not Approved`.
- Load scheduling remains `Not Approved`.
