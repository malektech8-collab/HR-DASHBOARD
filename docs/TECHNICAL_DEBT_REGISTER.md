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

### GAP-001 — Every gate in this project is numeric. None can see wrong TEXT.

- **Status**: OPEN, named rather than solved (2026-08-13)
- **Category**: Verification coverage

#### The evidence

492 of 667 client-facing exception messages rendered a DuckDB relation name
into the sentence a client reads:

```
Hold "hr_analytics"."main"."stg_payroll" and verify termination status
Active employee has no "hr_analytics"."main"."stg_attendance" record
    for expected workday on 2026-06-25
```

They passed **every gate this project has**, for the life of the project:

| Gate | Why it was blind |
|---|---|
| Demo byte-identity (`19 / 446175.0 / 50.0 / 667 / 15`) | 667 was 667 before and after. Only the text was wrong. |
| Reconciliation (12 independent checks) | Compares numbers. No check reads a string. |
| dbt 161/161, 11/11 | Models built and tests passed; the SQL was valid. |
| pytest / vitest / `tsc -b` | Nothing asserts the content of a generated message. |
| Contract validation | Governs the client's INPUT, not our OUTPUT. |

The pipeline was, in the terms of every check it has, completely healthy.

#### What the new test does and does not cover

`backend/tests/test_no_jinja_in_sql_strings.py` covers the **class**: a dbt
`ref()` rendering inside a SQL string literal. It does not cover the
**category**: client-facing text being wrong. A typo, a placeholder left in, a
mis-merged sentence, an Arabic string that says something different from its
English pair — all still pass everything.

#### What would catch the category

Three candidates, with an honest read on each:

1. **A snapshot/approval test over generated client-facing text.** Extract the
   distinct `description` / `recommended_action` / label values the pipeline
   produces on demo data and check them into an approved file; any change is a
   reviewable diff. *Would have caught this on the commit that introduced it.*
   Cost: one fixture, and a diff to approve whenever a message legitimately
   changes. **This is the one worth building.**
2. **A lint on generated strings** — no `"`, no `{{`, no relation-shaped
   substrings, no `None`/`nan`/`null` in client-facing text. Cheaper and
   narrower; catches machine noise, not wrong English.
3. **Bilingual pair checking** — assert every `_en` has a non-empty `_ar` and
   that neither contains the other's script. Catches a real class this project
   is exposed to and is unrelated to (1).

#### Is it worth building?

**(1) and (2): yes, and they are small.** The exposure is not hypothetical —
this is a bilingual product whose differentiator is telling a client precisely
what is wrong with their data. The text IS the product surface, and it has
been unguarded while five numeric gates were built around it.

**(3): yes, but after TD-007 (RTL)**, which will move the Arabic surface
anyway.

**Not** a general "assert every string" sweep — that produces a test that
fails on every legitimate copy change and is deleted within two cycles.

- **Closure criterion**: (1) implemented, with its own tamper-proof per
  SP-001 — a deliberately corrupted message must turn it red.
- **Until then**: this gap is why "all gates green" on a text change means
  less than it appears to. Say so when reporting one.
### GAP-002 — A defect in `.env.example` is invisible to CI by construction

- **Status**: OPEN, named rather than solved (2026-08-13)
- **Category**: Verification coverage
- **Sibling of**: GAP-001 above — *"every gate in this project is numeric; none
  can see wrong TEXT"*. Same shape as this one: a whole class of defect that no
  gate is positioned to see, named rather than solved. GAP-001 is about what a
  gate cannot read; this is about what a gate never runs against.

#### The evidence

`.env.example` shipped two lines that broke the documented setup path:

| Line | Effect |
|---|---|
| `VITE_API_URL=...` | `Settings()` raised at import — the backend could not start at all |
| `DATABASE_PATH=../warehouse/hr_analytics.duckdb` | relative, correct only from `backend/`; from the repo root it resolves **outside the repo** and every endpoint 500s |

Measured on a developer machine that had followed the documented step
(`Copy-Item .env.example .env`):

```
pytest backend/tests   ->  397 passed, 7 errors     (with the .env in place)
pytest backend/tests   ->  404 passed               (DATABASE_PATH corrected)
```

**CI was green throughout, for both defects, for as long as they existed.**

#### Why CI cannot see it

`.env` is gitignored — correctly, it holds `JWT_SECRET`. So CI never has one,
and every setting falls back to the code default, which is right. **CI tests a
configuration no developer and no deployment actually uses.**

The consequence is not that CI was wrong; it is that the artefact CI verifies
and the artefact humans follow are different artefacts, and only one of them is
tested. Every developer following the documented setup ran a subtly broken
suite and had no way to know it was the setup rather than their change.

#### What would catch the class

A CI step that copies the **committed** `.env.example` to a throwaway `.env`
and runs against it:

```yaml
- name: The documented setup path
  run: |
    cp .env.example .env
    python -c "import sys; sys.path.insert(0,'backend'); from app.config import Settings; Settings()"
    pytest backend/tests -q
    rm .env
```

That is roughly ten lines and one extra suite run.

#### Is it worth building?

**Partly, and the cheap half is worth more than the expensive half.**

- **Worth it: the import check.** `cp .env.example .env` then constructing
  `Settings` is seconds, and it is the exact failure that stopped the backend
  starting. A test now does this in-process
  (`test_copying_the_committed_env_example_lets_the_backend_start`), which
  covers it without a CI change — so this half is **already done**.
- **Worth it: the declared-variable check.** Asserting every variable in
  `.env.example` is a field on `Settings` catches the next `VITE_API_URL`
  before it is committed. Also already done, in the same file.
- **Marginal: a second full suite run under the example `.env`.** It doubles
  the slowest gate to catch a narrower class — a *valid* variable with a
  *wrong value*, which is what `DATABASE_PATH` was. The two checks above would
  not have caught that one.
- **Not worth it: testing the operator's actual `.env`.** It is per-machine and
  secret. Out of scope by construction.

**Recommendation:** keep the two in-process checks that exist, and add the
`DATABASE_PATH`-shaped case to them — assert that every path-valued setting in
`.env.example` resolves inside the repository — rather than doubling the CI
suite. That closes the measured instance at proportionate cost and leaves the
general class named here.

- **Closure criterion**: the path-resolution assertion added, with a tamper
  proof per SP-001. Until then this gap is why "CI is green" says nothing about
  whether a new contributor can start the stack.

### GAP-003 — CI can verify a MECHANISM; a GUARANTEE about a run needs a second invocation

- **Status**: CLOSED for test isolation, 2026-08-17 — recorded because the
  *distinction* is general and will recur.
- **Category**: CI / verification
- **Sibling of**: [GAP-002](#gap-002--a-defect-in-envexample-is-invisible-to-ci-by-construction).
  Same family: a defect that can only bite where real operator state exists,
  and is therefore invisible to a CI run built from synthetic data.

**The defect that produced it.** A `pytest` run rebuilt the operator's
warehouse in demo mode and rewrote `data/onboarding/declared_domains.yml`,
leaving the registry internally inconsistent — a real client's `declared` and
`history_since` beside demo's `absent_columns`. `provides_column()` then
returns True and thousands of suppressed warnings come back. CI never saw it:
CI has no profile, no client load and no declared registry, so clobbering
those is indistinguishable from correct behaviour.

**The distinction, which is the reusable part.**

- **The MECHANISM is CI-verifiable.** That paths resolve through the state
  root; that a redirected run writes only inside it; that no module writes to
  a hard-coded repo-relative data path. These are ordinary tests.
- **The GUARANTEE is not, from inside the suite.** *"A full run leaves
  operator state untouched"* is a statement **about** a run. No test within
  that run can assert it: the writes it must observe happen in sibling tests,
  in arbitrary order, and some in subprocesses. It requires a **second
  invocation** — snapshot, run, compare — which is a **job step, not a test**.

**Why the CI step is worth having even though CI has no real data.** The bytes
are synthetic but the property is about **paths**: *"the suite does not write
to `data/` or `warehouse/`"* is true or false regardless of whose rows are in
them. That is what converts an operator-only failure into a CI-visible one.

**Implemented as**: [`scripts/check_test_isolation.py`](../scripts/check_test_isolation.py),
invoked twice in the Test Suite gate — once to run the suite and compare, once
with `--verify-detects` to prove the checker itself can go red. Per SP-001 a
guard nobody has watched fail is not a guard.

**The companion rule**: [SP-004](#sp-004--state-follows-the-data-root-source-never-does) records WHAT is isolated - state follows the root, source never does - and carries the `profiles.yml` incident as its worked example.

**The general rule this leaves behind**: when a property is about a *process*
rather than a *value*, ask whether any test could observe it from inside. If
not, it belongs in the pipeline beside the suite, not in it — and it must be
watched failing, because a comparison that cannot detect a change is green
forever.


### INC-001 — A committed secret, reintroduced by the cycle that removed committed secrets

- **Status**: CONTAINED 2026-08-13. Value permanently burned. Guarded by test.
- **Category**: Security / process
- **Severity of what happened**: a working 64-character `JWT_SECRET` reached
  `main` inside `.env.example` — **the exact file the first-real-load runbook
  instructs the operator to copy.**

#### What happened

| | |
|---|---|
| `ca1194a` (PR #32) | Removed the committed signing constant, added `JWT_SECRET=` to `.env.example` **empty**, with instructions to generate one per deployment. Correct. |
| `bbe126e` (PR #33) | *"fix(env): a shared .env must not stop the backend from starting"* — filled that line in with a real value. |
| merged | PR #33, and it sat on `main` until found. |

Anyone following the documented first step — `Copy-Item .env.example .env` —
would then have signed tokens with a key published in the repository. That is
**precisely the condition PR #32 was written to eliminate**, reintroduced
through the front door, in the file that teaches people how to set the thing
up. Two cycles apart, by the same author.

#### WHY it happened — the part worth keeping

The commit that did it was solving a real problem: the backend would not start
from a copied `.env`. Under that pressure, **a startup problem was solved by
filling in a value rather than by documenting how to generate one.** A
populated field makes the error go away immediately; an empty field plus
instructions requires the person to do something. The first is faster and
looks finished.

That is the whole mechanism, and it generalises past secrets: *making an error
stop is not the same as making the thing correct*, and the difference is
invisible in a green test run. Nothing in the pipeline distinguishes
`JWT_SECRET=<64 chars>` from `JWT_SECRET=` — both parse, both start, both pass
every gate this project has.

#### How it was found — and this belongs to GAP-002

Not by a gate. **By reading `.env.example` line by line while implementing
GAP-002's targeted path-resolution check.** No test, no lint, no reviewer, no
CI step saw it; the file is gitignored in its `.env` form, so
[GAP-002](#gap-002--a-defect-in-envexample-is-invisible-to-ci-by-construction)
applies exactly — CI verifies a configuration nobody uses, and the artefact
humans copy was unverified.

The argument for building that check is therefore stronger than the argument
made when it was proposed: it did not merely catch the defect it was scoped
for, it caused a second and worse one to be found. That is worth stating
because the proposal was nearly declined as disproportionate.

#### The value is BURNED

`DKILo9YWGHA4WyJZ627-CGuzZfmQz5fGwqfTeJzN5SFT1RFMRC64vzK0u5nHFILA` must never
be used as a signing key anywhere, in any environment, ever. It is recorded in
`backend/tests/test_env_and_login_failures.py` as `BURNED_SECRET` so the guard
can prove it catches this exact string, and so nobody reintroduces it believing
it is a harmless placeholder.

It was **not** a live production credential — it was absent from the operator's
own `.env` — so no deployment is known to have used it. "Not known to have been
used" is not "was not used", which is why it is burned rather than assessed.

#### Guarded now

`.env.example` may **name** a credential and must never **populate** one.
Enforced over `SECRET | PASSWORD | PASSWD | TOKEN | KEY | CREDENTIAL |
API_KEY | PRIVATE`. Per SP-001 the guard is watched failing: a test restores
the burned value into a throwaway copy and asserts it is caught, so the guard
passing means it looks rather than merely runs.

`CREDENTIAL` was absent from the first version of that pattern. A pattern that
has to be right the first time will be wrong eventually, which is the same
lesson in miniature.

#### DECISION — the git history is NOT rewritten

Recorded as a decision with its reasoning, so it reads as a choice rather than
an omission.

**The repository is public.** The value is therefore already in clones, in
forks, in GitHub's cached views of the old commit, and potentially in any
scraper that indexes public repositories. Given that:

1. **A rewrite removes it incompletely.** It cannot reach a fork or a clone,
   and GitHub retains unreferenced objects that stay reachable by SHA.
2. **A rewrite breaks every existing clone**, forcing a re-clone on anyone who
   has one, for no security gain.
3. **A rewrite manufactures false confidence.** The most likely outcome is
   someone later concluding the value was never exposed because the history
   looks clean — which would make un-burning it thinkable. The visible history
   is what keeps "burned" credible.

**Blank + burn + test is the honest posture.** The value is removed going
forward, marked never-usable, and guarded against return. The history records
that it happened, which is accurate and is the point.

This reasoning holds *because* the repo is public. For a private repository
with a genuinely limited blast radius, a rewrite plus rotation would be the
better trade, and this entry should not be cited as a general rule against
rewriting history.

### TD-011 — A `location` constant is unreachable while `location` is required

- **Status**: OPEN — recorded 2026-08-13, contract-required-relax cycle
- **Category**: Mapping / contracts
- **Description**: `constant_needs_affirmation()` returns **True** for
  `location`, and that is the rule working — `location` carries no
  `allowed_values`, so a type-based rule would let it through, but it feeds the
  `locations` join and a constant location for a multi-site client renders as a
  clean single-site chart. Confident, wrong, and indistinguishable from a
  client who genuinely has one site.
- **Why it is debt**: `location` is still `required: true`, so
  `_validate_targets`' required-column guard refuses a location constant
  **before** the affirmation check is ever reached. The affirmation rule for it
  is implemented and unit-tested but **cannot fire today**.
- **Why it is not simply removed**: the rule is right and the trigger is
  foreseeable. Two guards agreeing is not the same as one guard working, and
  deleting the unreachable one would leave nothing when the reachable one moves.
- **TRIGGER**: this becomes live the moment `location` is relaxed to optional —
  which is plausible, since `company`, `job_family` and `cost_center` were
  relaxed for exactly the reasons a small single-site client would produce.
  Whoever relaxes it inherits a working affirmation and should verify it fires.
- **Closure criterion**: either `location` is relaxed and a test proves the
  affirmation fires, or a reviewed decision that `location` stays required
  permanently, in which case the rule keeps its unit test and this item closes
  as documentation.

### TD-012 — Column-grain provision is consumed by the checks but not surfaced

- **Status**: OPEN — recorded 2026-08-13, contract-required-relax cycle
- **Category**: Onboarding / UI
- **Description**: `onboarding.record_provided_columns()` records which optional
  canonical columns a client's file did not carry, and the four cost-centre
  surfaces correctly stop firing when the column is absent. Nothing renders
  that fact to the client.
- **The gap, stated as the honest half of ruling 2's intent**: the client gets
  a **withheld breakdown without being told why**. Suppression is correct — an
  absent column is a coverage fact, not thousands of per-row exceptions — but a
  figure that is simply not there, with no note, is the same experience as a
  figure that is broken. The suppression work of Phase 2 P0-3 established that
  withholding must be *explained*, not merely performed; this withholds without
  explaining.
- **What is already there to build on**: `NotProvided` and `CoverageNote`
  components exist and are used for domain-grain absence. This is the same
  message at column grain, and should reuse them rather than invent a parallel
  presentation.
- **Impact**: first felt by the first real client, who will have no cost-centre
  breakdown and no sentence saying their export does not carry the column.
- **Closure criterion**: an absent optional column produces a visible coverage
  note naming the column and what it affects, with a test that a client
  who DOES provide it sees no such note.

### TD-013 — The affirmation gate is narrower than the affirmation principle

- **Status**: OPEN — **RULED, deferred to its own cycle after the first real
  load.** Recorded 2026-08-16, nationality/vocabulary cycle.
- **Category**: Upload mapping / evidence
- **The principle** (chief architect's ruling, restated): *affirm wherever
  being wrong is not visible on the screen the client looks at.*
- **The implementation**: `mapping.reject_enum_columns()` gates value mappings
  on whether an unmapped value would have **REJECTED** the file. Today that is
  `status` and `end_of_service_type`. A value map on `employment_type` or
  `contract_type` — both of which carry `allowed_values`, and both of which an
  unmapped value merely raises an EXCEPTION for — requires no affirmation at
  all.
- **Why the gate is the wrong one**: severity describes what happens when you
  **do not** map a value. The affirmation is about what happens when you map it
  **wrongly**. Those are different questions, and the second does not depend on
  the first: once a pair is applied, a wrong `contract_type` is exactly as
  silent as a wrong `status`. The column reads as clean canonical data and
  nothing downstream can tell it was ever anything else.
- **The ruled scope**: **any column with `allowed_values`, regardless of
  severity.** Not a wider list to maintain — the same one-line predicate the
  affirmation rule for constants already uses.
- **Why it is not being done now**: it changes what **every existing profile
  must carry**. A profile saved before the change and reloaded after it would
  be missing affirmations it was never asked for, so the cycle that widens the
  gate must also decide what happens to profiles already in the field —
  migrate, grandfather, or refuse. That is a design decision, not a predicate
  change, and it must not ride along with a client load in flight.
- **Seen, not predicted**: authoring the first real employees profile. Both
  vocabularies were affirmed voluntarily and the machinery accepted the extra
  affirmations without complaint, which is a useful signal that widening the
  gate is additive on the write path.
- **Closure criterion**: `constant_needs_affirmation` and the value-mapping
  gate resolve from one predicate over `allowed_values`; a value map on any
  vocabulary column is refused unaffirmed; a decision on pre-existing profiles
  is implemented and tested, not merely documented.


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

**And the part that matters most: this was APPROVED AT REVIEW.** The cycle-5a
report did not hide the defect or describe it vaguely. It quoted the corrupted
string in full — `'"hr_analytics"."main"."stg_attendance"'` — named the two
affected domains, and explained the workaround. It was read and accepted.

So the failure was **not in the reporting**. Both sides read an accurate
description of a live data corruption and accepted "fixes" as a synonym for
"stops reading". The word did the work: "fixes the second latent bug for free"
reads like closure, and nobody — author or reviewer — asked the one question
that would have separated them: *is the value still wrong in the database?*

This is why the rule is written as a rule and not as a lesson about diligence.
A process that depends on someone noticing an ambiguous verb in an otherwise
correct report will fail again. What is needed is the habit of asking, of any
claimed fix, **what changed in the data** — and if the answer is "nothing, we
stopped looking at it", that is a workaround with open debt behind it.

**Applies equally to a finding raised and deferred.** A defect the architect
rules out of scope is fine; a defect that quietly stops being mentioned because
a consumer moved is not.
#### An instance where the practice WORKED — caught before review, 2026-08-13

The three instances above are all cases where a claim survived review. This one
did not, and the register should show the difference.

**The claim.** Justifying `extra = "forbid"` on the `Settings` model, I wrote —
into a code comment *and* a test — that it protects against a typo like
`DATA_MODEE=real`, on the reasoning that a deployment silently serving demo
data while believing it is real would be the worst outcome.

**The measurement.** Before pushing, per SP-001(i), I ran the check I had
asserted:

```
DATA_MODEE=real    -> ACCEPTED, silently ignored
JWT_SECRETT=abc    -> ACCEPTED, silently ignored
VITE_API_URL=...   -> REFUSED
TOTALLY_UNRELATED  -> REFUSED
```

**The fact.** pydantic-settings matches an environment name that *prefixes* a
declared field against that field and discards the remainder. So:

> **`forbid` guards against MISPLACED variables, not MISSPELLED ones.**

A variable belonging to another component is refused — which is exactly the
defect it was being kept for. A trailing-character typo on a real field name is
accepted and dropped in silence, under `forbid` and `ignore` alike.

**What was done.** The comment was rewritten to state the measured behaviour and
name the limitation; the test asserting the false claim was replaced with a
parametrised test that pins the limitation, so nobody later relies on this for
typo protection. What does catch the misspelled case is real mode's own
fail-closed check — an unset `JWT_SECRET` refuses to start — by a different
mechanism, with a different message.

**Why it is recorded as a success rather than a near-miss.** The first two
instances cost a cycle each to find, because nobody asked what the check
covered. This one cost one command, because someone did. That is the entire
value of the rule, and the register should carry an example of it paying rather
than only examples of its absence.

**And the residue that makes it honest:** the false claim was written down
first. The practice is what caught it; it is not what stopped it being written.

#### Known gaps in the practice

Not every check in the repo has been tamper-proven — only those written or
touched since adoption. Applying it retroactively to the rest of the suite is
open work, not a completed sweep, and should not be implied otherwise.

### SP-002 — A correction records the WORDING of a claim, not the DATA it was about

- **Adopted**: 2026-08-13, caught in a first draft before review.
- **Rule**: this project corrects a wrong statement **in place, with the
  original wording recorded beside it**, so the correction is checkable rather
  than a silently different file. That convention says to preserve *what was
  claimed*. It does **not** say to reproduce *what the claim was about* — and
  where the correction exists to remove something, quoting it back undoes the
  fix in the act of documenting it.

#### The instance

A cycle report stated *"No client figures appear anywhere in this repo."* It
was wrong: the plan document carried a client's leaver count in three places.
The fix generalised all three to a magnitude.

The first draft of the correction then quoted the offending sentence in full,
figure included — reproducing the exact count the correction had just removed,
in the document that records the removal. Caught before review. It would have
left the repository in the state it started in, with an extra paragraph
explaining why it should not be.

The rule was then broken a second time, in the first draft of THIS ENTRY, which
quoted that sentence to illustrate the mistake. Also caught, and worth
recording: the pull toward quoting the example is strong precisely when the
subject is what makes the example vivid. That is the moment the rule is for.

#### The rule, stated generally because it will recur

> Record the **claim**: *"the report said no client figures appear anywhere in
> this repo"*.
> Describe the **subject**: *"the plan carried the client's leaver count in
> three places — §0, the cap sizing, and an illustrative coverage note"*.
> **Never reproduce the subject** when removing it was the point.

The test of a good correction is whether a reader can tell **what was wrong**
and **verify it is now right**. Neither needs the offending value. It applies
to any correction whose subject is a secret, a client figure, personal data, or
a credential — the classes where the correction and the disclosure would
otherwise be the same act.

Where the subject is harmless — a wrong table name, a mis-stated status code,
a bad path — quoting it in full is still correct and remains the norm. The
distinction is not "corrections are now vaguer"; it is that the subject's own
sensitivity decides whether it may be repeated.

### SP-003 — Real-data context stays in the ruling; the repo carries magnitudes

- **Adopted**: 2026-08-13, after a client's leaver count reached a plan
  document.
- **Rule**: when a cycle is given real-data context for sizing — counts,
  distributions, vocabulary frequencies — those figures inform the decision and
  **stay in the instruction**. Plans and reports state the **magnitude**:
  *"several hundred leavers"*, *"a small minority carry no article"*,
  *"N of M"*. Vocabulary values are the exception and may be quoted verbatim,
  because a status word is the client's terminology and not their people.
- **Why the habit rather than the sanitising**: had the plan said "several
  hundred" when it was written, there would have been nothing to find later.
  Removing a figure afterwards leaves it in the git history; not writing it
  never does.

#### This is UNGUARDED, by design

Stated plainly so nobody assumes a check exists:

**A guard on bare integers would be deleted.** `docs/` legitimately contains
hundreds of numbers — `161/161`, `450 passed`, `667`, `446175.0`, row numbers,
line numbers, Labor Law article numbers. Nothing in the text distinguishes a
figure of ours from a figure of theirs. The false-positive rate would get the
check suppressed or removed within two cycles, which is exactly the failure
mode [GAP-001](#gap-001--every-gate-in-this-project-is-numeric-none-can-see-wrong-text)
names for noisy checks.

**A per-engagement denylist would work and is worse.** Pinning each real
export's actual figures so they can be detected means **storing the client's
numbers in the repository in order to find the client's numbers in the
repository** — a control that creates the exposure it exists to prevent, in a
file that is easier to find than the prose it is guarding.

So the honest position is: this rests on a habit, the habit is written down
here, and **there is no automated backstop**. Per SP-001 an unenforced rule is
not evidence of anything, and the register should say so rather than let a
reader infer coverage that does not exist.

#### The failure it was adopted from

The self-check that reported clean grepped the figures supplied **in that
cycle's ruling** and found none. The figure that was actually present came from
the **previous** turn's context and had been written into the plan by the same
author. It was never in the search.

> **A grep for the figures you were GIVEN does not cover the figures you
> WROTE.**

Same shape as SP-001's third instance: the check ran, it was watched, and it
was scoped to the wrong input. *"Did I paste the numbers from this message"*
reads exactly like *"does this repository contain client figures"* when you are
the one who wrote the search.

### SP-004 — STATE follows the data root; SOURCE never does

**Recorded** 2026-08-17, test-isolation cycle. The companion rule to
[GAP-003](#gap-003--ci-can-verify-a-mechanism-a-guarantee-about-a-run-needs-a-second-invocation):
GAP-003 says how the guarantee is verified, this says what is being isolated.

**The rule.**

- **STATE** is generated or operator-owned and **follows `HRDASH_DATA_ROOT`**:
  `raw`, `bronze`, `silver`, `gold`, `sample`, `staging`, mapping profiles, the
  onboarding registry, and the warehouse. The pipeline writes it. A test must
  never touch the operator's copy.
- **SOURCE** is repository content and **never follows the root**:
  `data/contracts`, `config/`. Humans edit it, git tracks it, the pipeline only
  reads it.

**Why SOURCE must not move.** A suite pointed at a temp root has to keep
validating against the **real** contracts and config. Redirect those too and
the suite validates a copy of its own fixtures — every contract test passes by
construction, and a contract change ships unverified. The failure is total and
silent: a green suite that has stopped checking the thing it exists to check.

Stated as one line: **isolate WRITES, not reads.**

**The worked example, and it is the reason this is a standing practice rather
than a note.** During the isolation cycle itself, two paths were missed:

1. `dbt_analytics/profiles.yml` hard-coded `../warehouse/hr_analytics.duckdb`.
   The first redirected run had `build_warehouse` open the *redirected*
   warehouse while **dbt built its models into the operator's**. That one
   failed loudly — a missing table — which is the good case.
2. `build_warehouse` composed its parquet paths cwd-relative. The second run
   wrote its own silver correctly and then **loaded the operator's**. The
   result was a warehouse holding **a real client's rows under a demo label**,
   and it did not fail. It looked like a successful isolated build.

The second is the shape to remember: **a half-applied isolation is worse than
none**, because it produces a plausible artefact instead of an error. Nothing
in the run said anything was wrong.

**What caught it**: `test_demo_gate`, asserting the demo fingerprint — and only
because that gate had been made **self-sufficient in the same change**. Before
this cycle it read whatever warehouse sat at the repo root and *skipped* when
the anchor month did not match, so it would have gone green. The gate that
caught the bug was the one the same cycle had just stopped from being able to
skip.

**How to apply.** When adding any path that the pipeline writes, resolve it
through [`scripts/paths.py`](../scripts/paths.py) — never a literal, and never
a path composed against the process cwd. `test_no_script_hardcodes_a_state_path`
enforces this mechanically, because an artefact stays isolated by being *under
the root*, not by someone remembering it. When adding a path the pipeline only
reads, leave it in the repository and say so where it is defined.

**The generalisation worth carrying**: a partially-applied invariant is more
dangerous than an unapplied one. Prefer mechanisms where the incomplete case
*cannot* produce a plausible result — and pair every isolation change with an
assertion about the CONTENT of what was built, not merely that it built.

---

### SP-005 — A correct conclusion from a wrong premise is still a defect

**Recorded** 2026-08-17, ingest-read-sweep cycle. The companion to
[SP-002](#sp-002--a-correction-records-the-wording-of-a-claim-not-the-data-it-was-about):
SP-002 governs a claim whose **wording** was wrong; this governs a claim that
was **right for the wrong reason**.

**The instance.** The ingest-read-sweep plan argued that the boolean casts were
the dangerous half, because *"a blanket replace would pass CI — demo supplies
well-formed data for every domain — and break on the first real file."* It
recommended sequencing the three swallowed period probes first.

The sequencing was correct and was executed. The premise was false:
`Utf8 → Boolean` **raises** `InvalidOperationError` immediately, `strict=False`
does not change it, and demo supplies all six boolean columns — so a blanket
replace would have broken the demo build **loudly, in CI, on the first run**.
Those casts could never have reached a client.

The probes still deserved to go first, but for a reason the plan never gave:
they were not the smallest silent defect among several, they were **the only
silent defect in the file**.

**Why it is recorded rather than quietly amended.** *The outcome concealed the
error.* The work was ordered correctly, every gate went green, and nothing in
the result would have prompted anyone to re-read the argument. A wrong premise
that yields a right answer is not self-correcting — it survives review, it gets
cited, and next time it may carry the decision rather than merely accompany it.
The failure is invisible precisely because the result was good.

**The residue, stated concretely**: *"a blanket change would pass CI and break
on real data"* was **assumed, not measured**. It was measurable in one line, and
the one line disagreed:

```
naive .cast(pl.Boolean, strict=False) on TEXT:  raises InvalidOperationError
```

**How to apply.**

1. When a plan's recommendation rests on a claim about **how something fails** —
   loudly or silently, in CI or in production — that claim is a measurement, not
   a judgement. Measure it. It is usually one line.
2. When the work is done, check the recommendation against what was **learned**,
   not only against what was **delivered**. A green result is not evidence that
   the reasoning was sound.
3. Record the divergence even when nothing needs re-doing. That is the whole
   point: there is no other moment at which this class of error becomes visible.

**The general form**: a mechanism whose incorrect case still produces an
acceptable outcome will not be corrected by outcomes. It has to be checked
directly, or not at all — the same shape as
[SP-004](#sp-004--state-follows-the-data-root-source-never-does)'s
half-applied isolation, and of a skipped test reporting green.

---

### SP-006 — Derive it always; reconcile against it when offered

**Recorded** 2026-08-17, derived-columns cycle. The rule for a column that this
pipeline can compute AND a client's system may also supply.

**The rule.** Compute the value regardless. When the client's file supplies the
column, keep their value as **evidence** and compare the two — do not overwrite
it and do not skip the computation.

**Why it beats both patterns it came from.**

- **`is_saudi`'s derive-when-absent alone would delete a reconciliation.**
  `net_late_minutes` is computed by `base_attendance_current` as
  `calculated_net_late_minutes`, and `mart_attendance_exceptions` compares the
  client's figure against it. Treating the column as "derive it if missing,
  otherwise take it" is correct for `is_saudi`, which has nothing to compare
  against — but here it silently discards a working check.
- **A plain relaxation leaves a check comparing our derivation to our own.**
  If the column is relaxed and then filled by our derivation, the mismatch
  check reads *our* number on both sides. It agrees by construction and says
  nothing, while continuing to look like a check.

The combination is the only arrangement that keeps both properties: **the
figure always exists downstream, and a disagreement with the client's system
is still discoverable.**

**What the supplied column is FOR.** Not the number — we can compute that. It
is evidence about *their* system: whether their attendance engine, their SLA
clock, their payroll calculator agrees with our arithmetic. A disagreement is a
finding about the client's tooling, and it is the kind of finding this product
exists to surface. Discarding the column discards the finding.

**How to apply.** Ask two questions of any column being relaxed:

1. *Can we compute it?* If yes, derive it when absent so nothing downstream
   breaks — and see [SP-004](#sp-004--state-follows-the-data-root-source-never-does)'s
   ordering trap, because a column declared `derivation:` stops being
   shape-completed.
2. *Does anything compare it against our own value?* If yes, the comparison
   must be **gated on the column being provided**, or it becomes a tautology
   the moment the derivation fills in.

### The boundary condition — derive when the inputs exist, withhold otherwise

**Added 2026-08-17, attendance cycle. Part of the rule, not an exception to it.**

*"Derive it always"* carries an assumption: **that the inputs are always
there.** When a derivation reads a column that is itself optional, deriving
unconditionally moves the fabrication one layer along instead of removing it.

The instance. `late_minutes` is computable from the punch against the
schedule, less the grace period — and the pipeline already computes it. But
`scheduled_start` became optional in the same phase, because a biometric
terminal produces punches while a roster needs a rostering system. Deriving
`late_minutes` unconditionally would give every client without a roster **0
late minutes presented as a measurement** — which is precisely the defect that
cycle had just removed from `calculated_late_minutes`.

So the rule reads in full:

> **Derive it when its inputs exist. Withhold it when they do not. Reconcile
> against it when offered.**

And the test that separates the two absences: **0 means measured and on time;
NULL means there was nothing to measure against.** A missing *punch* is still
`0` lateness — it is a missing punch, counted elsewhere — while a missing
*schedule* is NULL. Two absences, two meanings, and collapsing them is the
whole family of defects this register keeps recording.

**A derivation that reads an optional column must state what it does when that
column is absent**, in the rule itself, or the answer defaults to whatever the
arithmetic happens to produce.

**Where it applies today**: `net_late_minutes`, and `late_minutes` for the
boundary condition. **Where it will**: any figure a source system computes that
we also compute — SLA clocks, overtime totals,
gross-versus-components. The general shape is *two independent calculations of
the same quantity*, and the value is in the disagreement.

---

### SP-007 — When you find an ungated check, read its siblings

**Recorded** 2026-08-17, derived-columns cycle. A search heuristic, not a
design rule — cheap enough that not doing it is the mistake.

**The instance.** `mart_compliance_exceptions` has three arms testing
government-platform statuses. The `mudad` arm was **already correctly gated**
on `has_wps_source_sql`. The `qiwa` and `health_insurance` arms beside it were
not, and each flagged **every row** when its column was absent — measured 3 of
3. The correct pattern was sitting in the same file, a few lines away, written
by whoever did the first one and not carried to the other two.

**Why it works.** Guards are added in response to a specific incident, and the
person adding one is thinking about the case in front of them. The sibling
cases — same file, same shape, same failure mode — are the ones most likely to
be missed and the cheapest to find. **A correct example nearby is evidence that
the pattern is known and evidence that it was not applied uniformly.**

**How to apply.** On finding an ungated check, before fixing it:

1. Read the whole file, not the failing arm. Look for the same shape.
2. Grep for the guard you are about to add — if it already exists elsewhere,
   the question is not *what should this be* but *why did it stop here*.
3. Check the reverse too: a file that gates one column and reads three is
   telling you about the other two.

**Its record so far**: it found the two ungated compliance arms. Earlier the
same reflex found `manager_id` ungated where `cost_center` was gated, and
`missing_project_count` disagreeing across two marts. Three finds, no cost
beyond reading a file that was already open.

---

### SP-008 — A threshold that is not a column has one source, read by every consumer

**Recorded** 2026-08-17, attendance cycle. Found while parameterising
`late_minutes`.

**The rule.** When a calculation needs a number that does not come from the
client's file — a grace period, an SLA target, a plausibility bound, a
proportion threshold — every component that uses it reads it from **the same
place**. Never a component-local default, never a literal repeated in two
languages.

**The instance.** `late_minutes` is computed twice: by dbt in
`base_attendance_current`, which reads `grace_period_minutes` from
`config/business_rules.yml` via `build_warehouse`; and now by ingest, when the
client does not supply the column. A Python default of `0` beside a config
value of `15` would have been the obvious shape and would have compiled.

**Why it is worse than an ordinary wrong number.** The two figures meet in
`mart_attendance_exceptions`, which compares the client's supplied lateness
against ours and reports a disagreement as a finding — *"source net late
minutes does not match calculated"*. So a disagreement between **our own two
components** would have surfaced as:

> **an accusation that the client's attendance system is wrong.**

That is the specific harm, and it is not symmetrical with a plain miscalculation.
A wrong number is discovered when someone checks it. A **false accusation** is
acted on: the client goes and audits a system that was correct, finds nothing,
and loses confidence in the product rather than in the figure. The defect
consumes their time and their trust before anyone doubts our arithmetic.

**How to apply.**

1. A threshold used by more than one component gets **one** source. Prefer the
   config file already read by whichever component is furthest downstream.
2. A function taking such a threshold takes it as a **required parameter**, not
   a defaulted one. A default is a second source wearing a different hat, and
   it is silent.
3. Test that the parameter **changes the answer**. A wiring that is read but
   ignored passes every test about where the value comes from.

**Its family**: this is [SP-006](#sp-006--derive-it-always-reconcile-against-it-when-offered)'s
reconciliation seen from the other side. SP-006 says keep the client's value so
disagreements are discoverable; SP-008 says make sure a discovered
disagreement is *theirs* and not ours.

---

### SP-009 — A default chosen to preserve existing behaviour silently disables every future gate that depends on it

**Recorded** 2026-08-17, attendance cycle. Distinct from
[SP-007](#sp-007--when-you-find-an-ungated-check-read-its-siblings): that one is
about a pattern *not carried to its siblings*; this is about a decision that was
**correct when made** and became wrong without anything announcing it.

**The instance.** `onboarding.provides_column()` returns `True` for any column
whose table has recorded no absences. Its docstring says so — *"Defaults to
True, deliberately"* — and the reasoning was right: only `employees` recorded
absences, and defaulting False would have blacked out every figure for every
other domain.

The moment a second domain relaxed a column, that default became the wrong
answer for it. **Nothing announced the transition.** Payroll, attendance,
compliance and hr_requests were each relaxed without recording, so every
`has_*_source_sql` gate reading them resolved `TRUE` — including the attendance
schedule gate built one cycle earlier specifically to withhold lateness. It was
present, correct, tested, and **unreachable**.

**Why this class is hard to see.**

1. **The default is documented, and the documentation is right** — about the
   world at the time it was written. A reader checking the docstring finds a
   justification, not a warning.
2. **It fails safe in the direction of "carry on as before"**, so nothing
   breaks, nothing logs, and no test fails. The gate's own unit tests pass:
   they test the gate, not whether anything reaches it.
3. **The transition is in a different file from the default.** Relaxing a
   column in a contract is what invalidates a Python default three directories
   away.

**The rule.** When a default exists to preserve behaviour during a migration,
it carries an **expiry condition** — the state of the world that made it
correct. Write that condition down as a **test**, not a comment, so the day it
stops holding is the day something goes red.

**Its test here**: any contracted table with a relaxed column must record its
absences, or the gates reading them are dark. It fails on the next table
relaxed without wiring — which is exactly how this was found, one cycle late.

**How to apply.** On writing a "safe" default, ask: *what would have to change
for this to become wrong, and would anyone notice?* If the answer to the second
is no, the default needs a test, not a comment. A default that cannot be wrong
needs neither.

---

### SP-010 — An authoritative query and a cached one disagree silently, and the cache never announces its age

**Recorded** 2026-08-19, compliance-split step 2. Both parties contributed; both
halves are recorded, because a one-sided entry would teach the wrong lesson.

**What happened.** A completed step was reported as pushed with three green
gates. The reviewer ran `git branch -r`, saw no branch for it, and raised a
blocker: *work existing in one place while the report says otherwise.*

`git ls-remote` — which queries the server rather than a local cache — showed
the branch present at the reported SHA, the file content present on the
server's copy, the PR open against that SHA, and the CI run bound to it. The
branch had never been missing. The reviewer had run `git fetch` without
`--prune` and read `refs/remotes/origin/*` as the server.

**Two modes, and they need different countermeasures.** This is the distinction
worth keeping:

| | STATE divergence | OBSERVATION divergence |
|---|---|---|
| what is wrong | the artefact genuinely is not there | one authoritative state, two readers, one stale |
| example | Phase 0's unpushed branch — thirteen days | this |
| fix | push, then verify | prefer the authoritative query |
| detection | the artefact is absent everywhere | the readers disagree |

Treating the second as the first produces a re-push that changes nothing and
leaves the real cause — a stale cache — in place to mislead again.

**THE INVERSION IS THE DIAGNOSTIC, and it is cheap.** The branch list showed a
branch that had been **deleted** on merge, and omitted the **live** one. That
combination cannot come from a failure to push:

- A genuinely unpushed branch would be absent — but the deleted branch would
  *also* be absent, because the server no longer has it.
- Seeing the dead one and missing the live one places the reader's view at a
  point in time **between** the two events. That is a cache, not a state.

So: **when a listing disagrees with a report, check whether it also contains
something that should be gone.** If it does, the listing is old.

**Both contributions, recorded.**

1. **The report quoted gate results without the SHA that binds them.** A PR
   number and three green rows cannot be reconciled against anyone else's copy
   — the only remaining way to check is to list branches, which is precisely
   the unreliable move. A gate result without its commit is unverifiable by
   construction.
2. **The reviewer read `git branch -r` as authoritative.** It reads a local
   cache refreshed only by `git fetch`, and it will list a deleted branch
   indefinitely without ever indicating that it is out of date.

**Convention adopted**: **gate reports carry the head SHA.** It costs seven
characters and converts an assertion into something the reader can verify
against the server themselves.

**The general rule.** Prefer the query that crosses the network over the one
that reads a cache — `git ls-remote` over `git branch -r`, `gh pr view` over
local refs. And when two readers disagree about whether something exists, the
first question is not *"was it done?"* but *"are we looking at the same
copy?"* — because the second question is answerable in one command and the
first is not.

---

### SP-011 — Withheld-when-it-can-serve: the mirror defect, and why review does not catch it

**Recorded** 2026-08-19, compliance split step 3.5. A **new species**, and the
first of its kind in this register.

**Every defect this phase has chased was SERVED-WHEN-IT-SHOULD-WITHHOLD.** A
sentinel rendering an absence as a category. A count of `0` reading as *nobody
is missing one*. A variance of `0.0%` reading as *unchanged since last month*. A
compliance percentage computed from two of its three terms. Thirty cycles of
finding figures that were shown when they should not have been.

**These two were the opposite.** After `iqama_expiry` moved onto the employees
contract, `mart_workforce_iqama_expiry` read `base_active_workforce` and nothing
else — yet the registry still declared `[compliance]`, so a client with no
compliance file had the whole mart **suppressed for a dependency that no longer
existed**. `mart_workforce_exceptions` and `mart_workforce_kpis.iqama_expiring_30`
carried the same stale claim, the latter kept alive by a **dead LEFT JOIN**
reading no column from the table it joined.

**Why the inversion is dangerous, and this is the whole entry.**

The review posture is tuned to catch fabrication. A wrongly-withheld figure
**looks exactly like the correct behaviour thirty cycles were spent building**:

- Nothing on the page is wrong. There is no bad number to spot.
- It **cites a reason** — *"Not yet provided: Compliance"* — and the reason is
  the very sentence this phase worked to make appear.
- It is **invisible to demo**, which provides every domain, so nothing ever
  suppresses.
- It is invisible to a reader of the page, who cannot know the figure was
  computable.

A fabricated figure is discovered by anyone who checks it. **A wrongly-withheld
one is discovered by nobody**, because the only person who would notice is the
client, and what they see is a product that politely declines to answer.

**And it is produced by doing the right thing.** Both instances were created by
a cycle that correctly moved a column to where it belonged, passed every gate,
and left a declaration behind. **Success is the mechanism.** Nothing about the
change looked like a defect, which is why it needed a structural check rather
than a review.

**The check** — [`test_registry_matches_refs.py`](../backend/tests/test_registry_matches_refs.py).
It builds the dbt ref graph, resolves each mart's reachable domains through the
registry's own domain→table mapping, and flags any **declared** domain that is
not **reachable**. It found a third instance nobody had noticed.

**What it deliberately does not do**, because a rule that over-reaches gets
switched off:

- It does not flag **under**-declaration. Reaching is not using: a model may ref
  a base touching six domains and read a column from one. That needs
  column-level analysis and would be mostly noise.
- It **abstains** where it cannot see — anything reading a warehouse table dbt
  does not build, and anything downstream of `data_quality`, which
  `validate_data` assembles from every domain at once. Abstention is paired
  with a guard asserting most of the registry is still inspected, so it cannot
  quietly abstain on everything.
- **Topical declarations are listed explicitly with a reason each.** A payload
  that is *about* modules without reading their tables is legitimately
  declared; the exemption is written down so it is a decision someone can
  re-examine rather than a silent hole.

**The general rule.** A declared dependency is a **claim about the code**, and
claims about code can be checked against the code. When a registry, a manifest
or an annotation says a thing depends on something, prefer a test that resolves
the actual dependency over a convention that it be kept in step — because the
day it stops being true, nothing else will say so.

**A third-order note worth keeping**: prose has now tripped three structural
rules in this repository — a comment mentioning `manager_id`, a comment naming
`base_compliance_current`, and the words *"from the"* parsed as a table. **A
rule about code must read code**, comments stripped, or its false positives
will get it weakened instead of narrowed.

---

## Open questions

Not debt, and not backlog. Questions whose answer is **not the engineer's to
give**, recorded so they are asked of the right person rather than resolved by
default.

### OQ-001 — What counts as an absence day, and what makes an hour overtime?

**Raised** 2026-08-17, attendance cycle. **Needs**: an HR practitioner familiar
with KSA Labour Law, not an engineer.

`absence_days` and `overtime_hours` stay **required** on the attendance
contract. Both look derivable — the pipeline has the punches, the schedule and
the calendar — and both were proposed for derivation and then held back.

**Why they were held back.** There is no existing calculation for either;
`base_attendance_current` passes them through unchanged. Deriving them means
first deciding:

- Is a day with no punches an absence, or an unreported day? Category F already
  answers that at the *calendar* level; this is the row level, and the two are
  not obviously the same question.
- Do half-days exist? Does a late arrival past some threshold become a partial
  absence?
- Is overtime measured against `scheduled_end`, against eight hours, or against
  the weekly limit? KSA Labour Law sets daily and weekly maxima and treats them
  differently by contract type and by Ramadan.
- Does unapproved overtime count as overtime hours, as cost, as neither?

**These vary by contract type and shift pattern**, so there is not one answer
even within a single client.

**Why it is recorded here rather than as a TD item.** A backlog item implies
the work is understood and merely unscheduled. This is not: **the engineering
is trivial and the ruling is the whole difficulty.** Filing it as debt would
invite someone to implement a plausible answer, and a plausible answer to this
question produces figures that look right and are wrong in a way no test would
catch.

**Closure**: a practitioner states the rules; they become a derivation with the
rules named in the registry, and the columns relax.

## Exclusions

None of these legacy build warnings affect the functionality of the new `GovernanceWidget` or `/api/governance/status` API endpoint, both of which are fully compliant and bug-free.
