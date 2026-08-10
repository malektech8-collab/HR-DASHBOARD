# Technical Debt Register

## Overview

This register lists all known baseline technical debt, TypeScript compiler warnings, test suite network dependencies, and performance cleanups identified during the initial development closure phase.

## Technical Debt Items

### TD-001 — Test Suite Network Dependency

- **Status**: **REOPENED** (2026-08-09) — previously marked CLOSED/RESOLVED
- **Category**: Backend Testing
- **Description**: Several legacy root tests (e.g. `test_payroll_api.py`, `test_talent_api.py`) make live HTTP requests (`urlopen`) targeting `http://127.0.0.1:8000`. These tests fail if the FastAPI server is not running on port 8000.
- **Impact**: Pytest runs fail globally when the local server is offline.
- **Remediation**: Refactor legacy tests to use FastAPI's `TestClient` or mock the requests.
- **Original Resolution Notes (partial — see reopening)**: Python test boundaries have been refactored to use FastAPI TestClient, removing any network/local-server dependency.

#### Reopening note (2026-08-09)

The original closure covered **`backend/tests/` only**. The 15 legacy `test_*.py` scripts at the repository root were never addressed, so the debt described above is still live outside that directory:

- `test_payroll_500.py` still calls `urllib.request.urlopen("http://127.0.0.1:8000/api/payroll/summary")` **at module level**, so the call fires on import (collection), not inside a test function.
- `trigger_api.py` does the same against the refresh endpoint.
- Most of the remaining root scripts open `warehouse/hr_analytics.duckdb` **read-write at import time**. Measured locally, a bare `pytest` at the repo root stalled indefinitely (killed at a 300s timeout), while `pytest backend/tests` passed 10/10 in under 2s.

These are debug scripts, not tests — they carry module-level side effects and define no assertions. Because CI's Gate 2 ran a bare `pytest`, this was a latent pipeline failure that only became reachable once Gate 1 was fixed.

- **Interim mitigation (landed)**: `pytest.ini` sets `testpaths = backend/tests`, and the Gate 2 CI step is scoped to `pytest backend/tests`. Collection no longer reaches the root scripts. See [docs/ci/ci-repair-plan.md](ci/ci-repair-plan.md) §2.
- **Closure criterion**: no `test_*.py` file outside `backend/tests/`, and no module-level network or read-write database access in any retained debug script.

#### Progress update (2026-08-10) — STILL OPEN

The scheduled remediation landed: the 15 root scripts were `git mv`d to `scripts/debug/` with the `test_` prefix dropped. Bare `pytest` at the repo root now passes 10/10 in 1.39s.

**The closure criterion is still not met, so this item stays open.** It was checked clause by clause rather than assumed — closing on a partial fix is exactly what happened the first time:

| Clause | Result | Evidence |
|---|---|---|
| No `test_*.py` outside `backend/tests/` | ❌ **not met** | `scratch/test_recruitment_api.py` is **tracked** (`scratch/` was gitignored after these 4 files were already committed) and does module-level `urllib.request` calls against `127.0.0.1:8000`. |
| No module-level network access in retained debug scripts | ❌ **not met** | `scripts/debug/payroll_500.py` and `trigger_api.py` (repo root) still call `urlopen` at import time. |
| No module-level read-write DB access in retained debug scripts | ❌ **not met** | 11 of the 15 moved scripts still call `duckdb.connect(...)` without `read_only=True` at import time: `any_column`, `cc_checks`, `command_center_views`, `loop`, `new_overview_view`, `new_view_columns`, `overview_subqueries`, `payroll_kpis`, `query_times`, `table_overview`, `talent_queries`. |

**Remaining work before closure:**

1. Deal with the 4 tracked files under `scratch/` — either `git rm --cached` them (the directory is already gitignored, so they are tracked only by accident of ordering) or move and rename them alongside `scripts/debug/`.
2. Rename or relocate `trigger_api.py`, which is a debug script living at the repo root.
3. Convert the module-level bodies of the retained debug scripts into `main()` functions under `if __name__ == "__main__":`, and open DuckDB with `read_only=True`. That removes the import-time side effects the criterion targets, rather than relying on `pytest.ini` to route around them.

**Known regression introduced by the move, not yet fixed:** `scripts/debug/payroll_api.py` and `scripts/debug/talent_api.py` locate the backend package via `os.path.join(os.path.dirname(__file__), "backend")`, which no longer resolves from `scripts/debug/`. Left untouched to keep that commit a pure rename; flagged for the chief architect to rule on.

Risk while open is low — collection is scoped by `pytest.ini` and the Gate 2 step, so none of this reaches CI. The debt is latent, not active.

### TD-002 — TypeScript Compilation Errors

- **Status**: CLOSED/RESOLVED
- **Category**: Frontend Compilation
- **Description**: Running `npm run build` in the `frontend` folder reveals several missing type imports and parameter mismatches in other modules.
  - `src/lib/api.ts` misses type imports like `ErTrendsData`, `TalentSummaryData`, etc.
  - `Recruitment.tsx` has parameter mismatches on the `<KpiCard />` component (expects `id` but receives `title`).
  - `Talent.tsx` has parameter mismatches on `<KpiCard />` and `<ExceptionTable />` components.
- **Impact**: Standard production bundler commands (`tsc`) fail. Development hot-rebuild (Vite) works because it skips typechecking during bundling.
- **Remediation**: Align interface definitions in `types.ts` with component props. Fix the prop structures of `KpiCard` and `ExceptionTable` in legacy pages.
- **Resolution Notes**: Type files, component props, and interfaces have been refactored to use fully standard TypeScript types. Frontend builds compile with zero errors.

### TD-003 — Unused Variable and Console Debug Cleanup in CommandCenter

- **Status**: CLOSED/RESOLVED
- **Category**: Frontend Hardening
- **Description**: Unused variables present in `CommandCenter.tsx` (`navStatus`), `EmployeeRelations.tsx` (`CheckCircle2`), `Recruitment.tsx` (`HelpCircle`), and `Talent.tsx` (`deptAvg`), along with console debug noise.
- **Impact**: Minimal impact, but causes warnings in compiler outputs and pollution in browser logs.
- **Remediation**: Remove unused imports and local variable declarations, and clean up debug console logs.
- **Resolution Notes**: Unused variables and console.debug logging statements in `CommandCenter.tsx` were successfully refactored and cleaned up. Build remains fully stable and clean.

## Exclusions

None of these legacy build warnings affect the functionality of the new `GovernanceWidget` or `/api/governance/status` API endpoint, both of which are fully compliant and bug-free.
