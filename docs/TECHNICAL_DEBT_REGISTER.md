# Technical Debt Register

## Overview

This register lists all known baseline technical debt, TypeScript compiler warnings, test suite network dependencies, and performance cleanups identified during the initial development closure phase.

## Technical Debt Items

### TD-001 — Test Suite Network Dependency

- **Category**: Backend Testing
- **Description**: Several legacy root tests (e.g. `test_payroll_api.py`, `test_talent_api.py`) make live HTTP requests (`urlopen`) targeting `http://127.0.0.1:8000`. These tests fail if the FastAPI server is not running on port 8000.
- **Impact**: Pytest runs fail globally when the local server is offline.
- **Remediation**: Refactor legacy tests to use FastAPI's `TestClient` or mock the requests.

### TD-002 — TypeScript Compilation Errors

- **Category**: Frontend Compilation
- **Description**: Running `npm run build` in the `frontend` folder reveals several missing type imports and parameter mismatches in other modules.
  - `src/lib/api.ts` misses type imports like `ErTrendsData`, `TalentSummaryData`, etc.
  - `Recruitment.tsx` has parameter mismatches on the `<KpiCard />` component (expects `id` but receives `title`).
  - `Talent.tsx` has parameter mismatches on `<KpiCard />` and `<ExceptionTable />` components.
- **Impact**: Standard production bundler commands (`tsc`) fail. Development hot-rebuild (Vite) works because it skips typechecking during bundling.
- **Remediation**: Align interface definitions in `types.ts` with component props. Fix the prop structures of `KpiCard` and `ExceptionTable` in legacy pages.

### TD-003 — Unused Variable Warnings

- **Category**: Frontend Hardening
- **Description**: Unused variables present in `CommandCenter.tsx` (`navStatus`), `EmployeeRelations.tsx` (`CheckCircle2`), `Recruitment.tsx` (`HelpCircle`), and `Talent.tsx` (`deptAvg`).
- **Impact**: Minimal impact, but causes warnings in compiler outputs.
- **Remediation**: Remove unused imports and local variable declarations.

## Exclusions

None of these legacy build warnings affect the functionality of the new `GovernanceWidget` or `/api/governance/status` API endpoint, both of which are fully compliant and bug-free.
