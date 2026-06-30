# Milestone 3K - Synthetic Evidence Dry-Run Protocol

## Input Boundary

The validator may read only `data/synthetic_dry_run/evidence/`.

The validator must refuse any path containing:

- `data/real_`
- `.env`
- `credentials`
- `secret`
- `token`
- `password`

## Deterministic Test Set

| Synthetic File | Expected Outcome |
|----------------|------------------|
| `valid_chro_evidence.yml` | pass |
| `valid_ciso_evidence.yml` | pass |
| `valid_it_operations_evidence.yml` | pass |
| `reject_prohibited_domain.yml` | reject |
| `reject_execution_approval.yml` | reject |
| `reject_load_scheduling.yml` | reject |

## Output

The validator writes `docs/qa/reports/milestone_3k_synthetic_evidence_dry_run_report.md`.
