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

### TD-004 — Commit rollback does not restore `data/silver`

- **Status**: OPEN — recorded 2026-08-12, ruled record-only
- **Category**: Upload / ingest (P0-2)
- **Description**: `POST /api/data/uploads/{id}/commit` restores `data/raw/{table}.csv` and `data/onboarding/declared_domains.yml` when the pipeline fails, but not `data/silver`. Ingest has usually already written silver by the time a later stage (the declared-domain guard, the history-depth guard, dbt) fails, so a rolled-back commit leaves silver holding the rejected upload's rows.
- **Why it is currently survivable**: `build_warehouse` aborts before writing `domain_provenance`, and in real mode `_provenance.provided_domains()` then returns the empty set, so step 2b's default-deny suppresses **every** figure rather than serving data from a rolled-back commit. Verified end to end during P0-2 (`docs/phase-2/p0-2-upload-validation-report.md` §5).
- **Why it is still debt**: that is defence-in-depth working as intended, and **it should not be load-bearing**. Two independent mechanisms currently have to hold for a failed commit to be safe. Anything that makes `domain_provenance` survive a failed build — a partial write, a retry, a future incremental warehouse — removes the backstop silently.
- **Remediation**: make silver part of the rollback set, or make the pipeline write silver to a scratch location and promote it only on success. The second is the honest fix and is close to what staging already does one layer up.

### TD-005 — `uploadFile()` in `api.ts` targets a removed endpoint

- **Status**: **CLOSED** — 2026-08-12, upload UI cycle
- **Category**: Frontend
- **Description**: `frontend/src/lib/api.ts` still POSTs to `/api/data/upload`, which P0-2 replaced with the staged flow (`/api/data/uploads`, `…/{id}`, `…/{id}/commit`).
- **Impact**: None today — no page calls it, which is why P0-2 could redesign the endpoint freely. But it was previously dead and is now dead **and wrong**, so the first contributor to wire an upload UI from it would build against an endpoint that no longer exists.
- **Remediation**: rewrite alongside the upload UI (P0-2 sequencing step 5). The client needs three calls, not one: stage, preview, commit — and the preview is the step that makes the flow worth having.
- **Resolution**: replaced by `lib/uploads.ts` (`stageUpload` / `previewUpload` / `commitUpload` / `discardUpload`). Two structural tests hold it closed: no `uploadFile` symbol and no `/api/data/upload` literal anywhere in `frontend/src`. **A correction to the original entry**: it was not in fact unreachable — `useDataManagement.useUploadMutation` wired it into the Data Quality page's upload widget, which renamed the file client-side to force the target table and told the user the CSV would be "routed directly to the Silver layer". That widget is now a link to Data Onboarding.

### TD-006 — Synthetic JWT layer and plaintext password comparison

- **Status**: **CLOSED** — 2026-08-13, phase-3/auth cycle
- **Category**: Security
- **Description**: `app/core/security.py` holds `MOCK_USER_DB`, a dict literal of three users whose passwords are stored and compared in plaintext (the field is named `hashed_password` but is not hashed). `create_access_token` / `decode_access_token` are a synthetic JWT implementation that no cycle has reviewed.
- **Impact**: P0-2 put `Depends(get_current_user)` on six data-mutating routes, so this layer is now the only thing standing between an anonymous request and a client's data. It was not load-bearing before; it is now.
- **Deliberately out of scope of P0-2**: bundling a review of the auth implementation into a data-validation cycle would have made both harder to review, and the dependency is correct regardless of what sits behind it.
- **Remediation**: real password hashing, a real user store, a reviewed token implementation, and a decision on whether commit requires a specific role (`RoleChecker` already exists and is used by `/api/governance/*`).
- **Resolution**: argon2id, a SQLite store at `data/auth/auth.db`, per-deployment `JWT_SECRET` with real mode failing closed, `iss`/`aud`/`jti`, logout, lockout, and first-run bootstrap with no credential ever at rest. See [docs/phase-3/auth-report.md](phase-3/auth-report.md).
- **A CORRECTION TO THIS ENTRY, and the larger half of the fix.** The description above said this layer "is now the only thing between an anonymous request and a client's data". That was true of the six routes P0-2 protected and false of the product: 83 routes existed and `get_current_user` appeared in ONE file, so `/api/workforce/exceptions` returned `employee_name` to an anonymous caller. Strengthening the credential layer would not have moved that by one byte. Route coverage was folded into the same cycle for that reason — closing it without would have shipped a report that was true and misleading at once.
- **Carried forward**: the role POLICY is not decided (mechanism only). See the endpoint list in the report §6, whose sharpest entry is `/api/data/uploads/{id}/columns`.

### TD-007 — RTL / full Arabic localisation

- **Status**: OPEN — recorded 2026-08-12, scheduled immediately after the upload UI
- **Category**: Frontend / i18n
- **Description**: Arabic is currently schema-derived only: column labels (`name_ar`), domain labels, and validator messages (`message_ar`). The chrome — navigation, headings, buttons, the onboarding step copy — is English, and the layout is LTR throughout.
- **Why now**: the onboarding screen is where an Arabic-first HR user meets the product, and the violation list is the densest Arabic anywhere in it. Mixed Arabic/English in an LTR table renders legibly and not well: column alignment and punctuation both suffer. Keeping the worst of it in a downloadable CSV rather than on screen was a deliberate mitigation, not a fix.
- **Remediation**: a locale switch, `dir="rtl"` on the document, mirrored layout, and translated chrome. Deliberately scheduled *after* this cycle so it is evaluated against real screens rather than designed in the abstract.

### TD-008 — The template is 23 bare headers, not a template

- **Status**: OPEN — recorded 2026-08-12
- **Category**: Onboarding
- **Description**: `GET /api/data/templates?name=` serves a header-only CSV generated from the contract. `PRODUCT-ARCHITECTURE.md` §4 specifies something quite different: *"a formatted Excel file per domain: correct headers, an instructions sheet in Arabic and English, dropdown validation on enum columns, and 2–3 example rows."*
- **Impact**: this is the first artefact a non-technical HR user touches, and 23 bare column names in a CSV is not guidance. The upload UI makes the gap sharper rather than smaller — the flow now says "download the template, fill it, upload it", and the template does not carry enough to fill it correctly. Dropdown validation on enum columns would prevent the `allowed-values` rejections the UI now has to explain after the fact.
- **Deliberately not folded into the upload UI cycle**: it is a generator (openpyxl or similar), a bilingual instructions sheet, and per-column dropdowns driven by `allowed_values` — a body of work in its own right, and one that touches the contract loader rather than the UI.
- **Remediation**: its own cycle. The contract already carries everything needed (`name_en`, `name_ar`, `description_*`, `example`, `allowed_values`), which is the point of §4's "one definition generates all of".

### TD-009 — Generated TypeScript types from the OpenAPI schema

- **Status**: OPEN — recorded 2026-08-12
- **Category**: Frontend / backend contract
- **Description**: The frontend's request and response types are hand-written in `lib/api.ts`, `lib/uploads.ts` and `lib/types.ts`, mirroring the Pydantic models by convention. Nothing enforces that they still match.
- **What `test_path_contract.py` DOES catch** (added in the same cycle as this entry): a frontend path literal with no corresponding backend route — the P0-2 failure, where `/api/data/upload` was deleted and `uploadFile()`'s literal survived.
- **What it does NOT catch, stated explicitly so it is not rediscovered as an incident**:
  - a **renamed response field** — the backend renaming `can_commit` to `commit_allowed` leaves the path valid and every test green, and the commit button silently reads `undefined`, which is falsy, so it disables forever
  - a **changed type** — `covered_days` going from `int` to `str`
  - **changed semantics** — a payload returning `[]` where it used to return `null`, which is the exact distinction three cycles of suppression work were spent establishing, and which no path check can see
  - a **new required request field** — commit gaining a mandatory parameter the client does not send
- **Impact**: the two halves agree by convention and review. Convention has failed here before: `TemplateInfo` was missing `label` and `available` for two cycles because the endpoint returned fields the interface never declared, and it surfaced only when a new page tried to read one.
- **Remediation**: generate types from `app.openapi()` (`openapi-typescript` or similar) into a checked-in file, and fail CI when the generated output differs from the committed one — the same shape as the path contract, one level deeper. Worth doing before the client-facing surface grows further.

### TD-010 — Business rules restated in the reconciliation checks

- **Status**: OPEN (accepted cost, recorded 2026-08-13)
- **Category**: Analytics / verification
- **Description**: The reconciliation checks recompute their figures
  independently, which is what makes them checks rather than tautologies. Two
  of them therefore restate a business rule that also lives in a dbt model. A
  change to either rule must be made in **both** places or the check will fire
  on a correct pipeline.

| Rule | Model | Check |
|---|---|---|
| Category F attendance denominator — measured days only, `COUNT(absence_days)` not `COUNT(*)`, NULL when no day was measured | `dbt_analytics/models/marts/mart_attendance_kpis.sql` | `scripts/reconciliation.py`, `attendance_compliance_pct` |
| Saudization nationality exclusion — employees with no nationality excluded from **both** sides of the ratio, not counted as non-Saudi | `dbt_analytics/models/marts/mart_compliance_kpis.sql` | `scripts/reconciliation.py`, `saudization_pct` |

- **Impact**: a rule change edited in one place produces a red pipeline with a
  confusing message — the check reports a disagreement that is real but whose
  cause is the check itself being stale.
- **Why it is accepted**: an independent recomputation has to be independently
  written. Sharing a macro between the model and the check would restore the
  tautology in a more sophisticated form: both sides would move together, which
  is exactly the defect SP-001 exists to prevent.
- **Mitigation today**: the duplication is named in both files and here. Both
  restatements carry a comment saying the other half exists and why.
- **Closure criterion**: not "remove the duplication" — that would undo the
  fix. Either a test that asserts the two SQL fragments are semantically
  equivalent on a fixture designed to separate them, or a decision that the
  two-place edit is permanent and this item is documentation rather than debt.

## Standing practices

These are not debt items. They are rules adopted after a defect class appeared
more than once, recorded here because the register is where someone looks
before trusting a check.

### SP-001 — A verification line earns its place once someone has confirmed BOTH halves

- **Adopted**: 2026-08-13. **Amended the same day**, after the first half alone
  proved insufficient — see the worked example below.
- **Rule**: before a check, gate or figure is quoted as evidence, someone must
  have confirmed that:
  1. **it can fail** — tamper the input, watch it go red, restore; and
  2. **it asserts the thing that matters** — the tamper must be the defect you
     actually care about, not merely *a* defect it happens to notice.
- **Scope**: CI steps, reconciliation checks, pinned figures in cycle reports,
  and any assertion offered at review as proof that something works.

#### Why half the rule is not most of the rule

The first half is falsifiability. The second is relevance. **A check can be
perfectly falsifiable and still vacuous**, and one that is will survive review
indefinitely because it passes the obvious question.

**Worked example — reconciliation checks 9–11.** They asserted
`COUNT(*) = 9` on the Command Center module registry. Delete a row and they go
red, so they satisfy (i), and on that basis they were classified as *real* in
the org-dimensions report while the other eight were called tautologies.

They failed (ii) completely. Three of those nine rows carried
`module_key = '"hr_analytics"."main"."stg_payroll"'` and a matching broken
`route_path`, for the life of the project. All nine rows were present. They
were just wrong, and a row count cannot see the difference.

The checks now assert the nine module **keys** and that each route is `/` plus
its key. That is (ii): the tamper is the defect that actually occurred.

#### The two instances

| | What was quoted | What it actually did |
|---|---|---|
| **1** | `npx tsc --noEmit` — "0 errors", every cycle | Typechecked **zero files**. `frontend/tsconfig.json` is a solution file with `"files": []` and only project references, so bare `tsc` resolved no inputs and exited 0 on any error. `npx tsc --noEmit --listFilesOnly \| wc -l` returned `0`. Found only when the Docker gate, which runs `tsc -b`, failed on an unused variable. |
| **2** | `Command Center integration reconciliation checks PASSED` | Eight of eleven checks compared `command_center_overview_data` against the marts it had been **populated from fifteen lines earlier in the same connection**. Tampering `mart_workforce_kpis` with `+ 1` left the pipeline green. |
| **3** | the remaining three checks, described as *real* | Falsifiable (delete a row, they go red) and vacuous: `COUNT(*) = 9` while three of the nine rows were corrupt. This is the instance that produced half (ii) of the rule. |

Both were offered as evidence for many cycles and **accepted at review each
time**. Nobody asked what they covered, on either side of the review. That is
what makes this a class rather than two mistakes: a check nobody has
interrogated is not evidence, it is a habit that looks like one.

#### What the rule costs, and why it is worth it

One command, once, per check. `--listFilesOnly` would have answered the first
in seconds at any point in six cycles. A `+ 1` in a model would have answered
the second.

#### Where it is enforced

- `backend/tests/test_reconciliation.py` — every reconciliation check has a
  paired test that tampers its input and asserts it raises. Two structural
  tests additionally forbid a check from reading the artefact it validates.
- `backend/tests/test_demo_gate.py` — the five demo figures and the dbt counts
  are asserted rather than eyeballed; `HR_WAREHOUSE_PATH` exists so the gate
  itself can be pointed at a doctored warehouse and watched failing.
- CI Gate 1 runs `npx tsc -b`, which reads the project references.

#### A related failure mode: routing around a defect instead of tracing it

SP-001 is about checks. This is about findings, and it produced the same
outcome — something known to be wrong, left in place.

In cycle 5a the corrupted keys were **seen, described, and worked around**.
From `docs/phase-0/phase-0-5a-resolver-report.md`:

> "(Note: pre-cycle, `attendance` and `compliance` also had a `module_key`
> mismatch — they queried `'attendance'`/`'compliance'` but the freshness mart
> stores relation-expanded keys like `'"hr_analytics"."main"."stg_attendance"'`;
> reading `base_command_center_report_context` sidesteps that entirely.)"

and, in the same report:

> "which also fixes the second latent bug (the attendance/compliance
> `module_key` mismatch) **for free by not using `module_key` at all**"

The word "fixes" is doing work it had not earned. Nothing was fixed: one
consumer stopped reading a corrupt value. The corruption stayed in the data,
spread to a second set of models, and was found again two phases later — by
which point it had also reached **492 of 667 client-facing exception
messages**, which is where it had always been.

**The rule**: a defect that is routed around is not closed. Either trace it to
its cause and fix it, or record it as open debt with its blast radius unknown.
"Sidesteps that entirely" is a description of the workaround, not of the
defect.

#### Known gaps in the practice

Not every check in the repo has been tamper-proven — only those written or
touched since adoption. Applying it retroactively to the rest of the suite is
open work, not a completed sweep, and should not be implied otherwise.

## Exclusions

None of these legacy build warnings affect the functionality of the new `GovernanceWidget` or `/api/governance/status` API endpoint, both of which are fully compliant and bug-free.
