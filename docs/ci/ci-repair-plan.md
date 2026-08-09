# CI Repair Plan — make `.github/workflows/ci-cd-pipeline.yml` pass end-to-end

**Status:** PLAN ONLY. Nothing implemented. No workflow, lockfile, `package.json`, or script changed on this branch — this document is the sole file added.
**Branch:** `fix/ci-pipeline` (off `main` @ `a5998c6`) · **Date:** 2026-08-09
**Guardrails honoured:** committed default behaviour (`data_mode=demo`) must stay byte-identical; no real data; ingestion branch untouched; nothing merged.

---

## 0. Executive summary — the diagnosis changed

The working hypothesis was *"`npm ci` omits the optional native binding."* The symptom matches, but the mechanism is not an npm optional-dependency bug and **not a lockfile defect**. The lockfile is correct and complete.

**Root cause: the CI runner uses Node 18. Every relevant frontend package requires Node ≥ 20.19.**

```
oxlint                        1.71.0   engines.node = ^20.19.0 || >=22.12.0
@oxlint/binding-linux-x64-gnu 1.71.0   engines.node = ^20.19.0 || >=22.12.0
vite                          8.1.0    engines.node = ^20.19.0 || >=22.12.0
@vitejs/plugin-react          6.0.3    engines.node = ^20.19.0 || >=22.12.0
vitest                        4.1.9    engines.node = ^20.0.0 || ^22.0.0 || >=24.0.0
jsdom                        29.1.1    engines.node = ^20.19.0 || ^22.13.0 || >=24.0.0
```

The workflow pins `node-version: 18` in **both** Gate 1 and Gate 2. npm filters `optionalDependencies` on `os`/`cpu`/`engines` and **silently skips** any that don't match — no error, exit code 0. So `npm ci` on Node 18 installs the `oxlint` JS wrapper but skips all 19 platform bindings, and `npm run lint` then dies at `require('./oxlint.linux-x64-gnu.node')`. The CI log even prints the culprit in its own stack trace footer: `Node.js v18.20.8`.

This is why it reproduces only in CI. Local dev is **Node 24.13.1**, where the matching binding installs correctly (`frontend/node_modules/@oxlint/binding-win32-x64-msvc` is present on this machine).

**Consequence:** the fix is a one-line change per job, not a lockfile regeneration. It also pre-emptively fixes a *second*, currently-invisible Gate 2 failure (`vitest` would refuse to run on Node 18 for the same reason).

Total scope to make CI green: **three edits in one workflow file, plus one new config file.** No application code changes.

---

## 1. Gate 1 — oxlint Linux binding failure

### 1.1 Evidence

The lockfile entry is present and correctly formed (`frontend/package-lock.json:649`):

```json
"node_modules/@oxlint/binding-linux-x64-gnu": {
  "version": "1.71.0",
  "resolved": "https://registry.npmjs.org/@oxlint/binding-linux-x64-gnu/-/binding-linux-x64-gnu-1.71.0.tgz",
  "integrity": "sha512-cFDaiR8L3430qp88tfZnvFlt3KotFhR/DlbIL0nHOMMYiG/9Wy4l+6f7t8G8pTa9bd8Lt8+M0y/qjRQ/xcB74g==",
  "cpu": ["x64"],
  "dev": true,
  "optional": true,
  "os": ["linux"],
  "engines": { "node": "^20.19.0 || >=22.12.0" }
}
```

`os: ["linux"]` and `cpu: ["x64"]` both match `ubuntu-latest`. The only failing predicate is `engines.node` against Node 18. `lockfileVersion: 3`; all 19 bindings declared `optional: true` under `node_modules/oxlint`'s `optionalDependencies`, which is the correct and intended layout for a napi-rs multi-platform package.

### 1.2 Recommended fix — bump the runner to Node 22

Two occurrences in `.github/workflows/ci-cd-pipeline.yml` (Gate 1 line ~22, Gate 2 line ~68):

```diff
       - name: Set up Node.js
         uses: actions/setup-node@v4
         with:
-          node-version: 18
+          node-version: 22
           cache: 'npm'
           cache-dependency-path: frontend/package-lock.json
```

**Why 22 and not 20:** `frontend/Dockerfile` already builds on `node:22-alpine`. Matching it means Gate 3 verifies the same major version the other gates lint and test on, and the deployed artifact is built by the same toolchain CI validated. Node 20.19+ would also satisfy every constraint, but leaves CI and the shipped image on different majors for no benefit.

**Why this is the minimal reproducible fix:** it changes no dependency, no resolved version, no integrity hash, and no lockfile byte. It aligns three environments (CI, Docker, local dev) that had silently diverged, and it fixes Gate 1's lint *and* Gate 2's vitest step with the same edit.

### 1.3 Alternatives considered and rejected

| Option | Verdict | Reason |
|---|---|---|
| `npm ci --include=optional` | **Rejected** | No-op. Optional deps are already included by default; the flag does not override `engines`/`os`/`cpu` filtering. Would not change the outcome. |
| Add `@oxlint/binding-linux-x64-gnu` as a direct `optionalDependency`/`devDependency` | **Rejected** | Hard-codes one platform into a repo developed on Windows and built on Alpine (musl, needs `-linux-x64-musl`). Under Node 18 the engine check still skips it, so it does not even fix the bug. Treats the symptom. |
| Regenerate lockfile with `--os=linux --cpu=x64` | **Rejected** | Produces a platform-locked lockfile that breaks `npm ci` for Windows developers and for the Alpine image. Also unnecessary — the lockfile is already correct. |
| Pin/downgrade `oxlint` to a Node-18-compatible release | **Rejected** | A downgrade to work around a stale runner. Does not help `vite@8`, `vitest@4`, `@vitejs/plugin-react@6`, or `jsdom@29`, which have the same floor. Would need a coordinated downgrade of the whole frontend toolchain. |
| Bump runner to Node 22 | **Recommended** | One line per job, no dependency changes, fixes two gates, aligns CI with the Dockerfile and local dev. |

### 1.4 Recurrence prevention (recommended, low cost)

The failure was possible because nothing declares the project's Node floor. Propose adding, in the same change:

- `"engines": { "node": ">=22.12.0" }` to `frontend/package.json`.
- An `.nvmrc` containing `22` at the repo root.

Deliberately **not** recommending `engine-strict=true` in an `.npmrc` — it converts warnings into hard install failures across all contributor machines, which is a heavier policy change than this repair warrants. Raise it separately if wanted.

### 1.5 Remaining Gate 1 steps — verified

- **`npx tsc --noEmit`** — verified locally, **exit 0, zero errors**. TypeScript 6.0.3 requires only `node >=14.17`, so it passes on any runner. Not a blocker.
- **`flake8 backend/app/ --select=E9,F63,F7,F82`** — **unverified**; flake8 is not installed in the local venv and installing it was out of scope for a read-only turn. Risk assessed as low (these codes cover syntax errors and undefined names; the package imports cleanly and the backend test suite passes 10/10). Confirm on the first CI run rather than pre-installing tooling. The second flake8 command is already `--exit-zero` and cannot fail the gate.

---

## 2. Gate 2 — constraining pytest collection

### 2.1 The problem

There is no `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` anywhere in the repo, so `pytest` invoked bare at the root recurses from the root and collects **15 tracked legacy scripts** matching `test_*.py`:

```
test_any_column.py            test_new_view_columns.py     test_query_times.py
test_cc_checks.py             test_overview_subqueries.py  test_table_overview.py
test_command_center_views.py  test_payroll_500.py          test_talent_api.py
test_fastapi_endpoints.py     test_payroll_api.py          test_talent_queries.py
test_loop.py                  test_payroll_kpis.py         test_new_overview_view.py
```

These are not tests — they are debug scripts with module-level side effects. Collection *imports* them, which executes them. Most open `warehouse/hr_analytics.duckdb` **read-write** at import time; one (`test_payroll_500.py`) issues a live `urlopen` to `http://127.0.0.1:8000`.

Measured locally, clean process table, nothing bound to :8000:

```
$ timeout 300 python -m pytest -q      →  EXIT=124   (stalled at 300s, no output)
$ python -m pytest backend/tests -q    →  10 passed in 1.69s
```

Gate 2 runs bare `pytest`. The moment Gate 1 goes green, Gate 2 inherits this — at best it executes 15 unintended scripts against the freshly built warehouse; at worst it hangs until the 6-hour job timeout. Either way it does not pass.

### 2.2 Recommendation — commit a config file, and make the CI step explicit

Do **both**, in this priority order.

**Primary — add `pytest.ini` at the repo root:**

```ini
[pytest]
testpaths = backend/tests
norecursedirs = .git .venv node_modules scratch dbt_analytics data warehouse frontend docs
```

**Why the config file is more robust than only editing the CI step:** the CI-step edit fixes exactly one invocation. The config file fixes *every* invocation — CI, a developer typing `pytest`, an IDE test runner, a future Docker test stage, a pre-commit hook. The trap that produced this bug is "bare `pytest` at root does something catastrophic," and only the committed config actually removes that trap. Editing just the workflow leaves a loaded gun in the repo and documents nothing.

**Why `pytest.ini` over `pyproject.toml`:** a root `pyproject.toml` implies this repo is an installable Python package and invites tooling (build backends, pip, uv, linters) to start treating it as one. `pytest.ini` is unambiguous, single-purpose, and has zero blast radius. If a `pyproject.toml` is ever added for other reasons, migrate the block to `[tool.pytest.ini_options]` then.

**Secondary — make the CI step explicit anyway** (defence in depth; also self-documenting in the workflow):

```diff
       - name: Run Backend Tests (Pytest)
         run: |
-          pytest
+          pytest backend/tests
```

Verified compatible: `backend/tests/*.py` each self-manage `sys.path` (`test_auth.py:6-8` appends `backend/` before `from app.main import app`), so no `conftest.py` is required and collection works with the repo root as CWD. This is exactly how the 10/10 local run was produced.

### 2.3 The 15 root debug scripts — recommendation

**Recommend: `git mv` them to `scripts/debug/`, dropping the `test_` prefix** (e.g. `test_cc_checks.py` → `scripts/debug/check_cc_reconciliation.py`).

Rationale, against the alternatives:

- **Move + rename (recommended)** — preserves history, keeps genuinely useful one-off diagnostics (several encode real reconciliation checks), removes them from every default pytest glob permanently, and puts them beside the existing `scratch/` convention. The rename is the load-bearing half: leaving the `test_` prefix anywhere in the tree means any future tool with a default glob rediscovers them.
- **Delete** — rejected. They document how past data bugs were diagnosed, and `test_cc_checks.py` in particular duplicates the Command Center reconciliation assertions in a runnable standalone form. Cheap to keep, irreversible to drop.
- **Rename in place** — rejected. Solves collection but leaves 15 debug scripts in the repo root, which is already cluttered with 8 loose top-level Python files.

**Sequencing note:** the move is *not* required to make CI pass — `pytest.ini` alone is sufficient. Recommend landing the config file in the CI-repair change and doing the file move as a **separate follow-up commit**, so the CI fix stays reviewable as a 4-line diff and the 15-file rename doesn't obscure it.

**Reopen TD-001.** `docs/TECHNICAL_DEBT_REGISTER.md` records TD-001 ("Test Suite Network Dependency") as `CLOSED/RESOLVED` with the note *"Python test boundaries have been refactored to use FastAPI TestClient, removing any network/local-server dependency."* That is true of `backend/tests/` and false of the repo root: `test_payroll_500.py` still calls `urllib.request.urlopen("http://127.0.0.1:8000/api/payroll/summary")` at module level. The remediation was applied to one directory and the item was closed as though it covered both. The register should reflect that until the scripts are moved.

---

## 3. Gate 2 — will `python scripts/refresh_all.py` succeed on `ubuntu-latest`?

**Assessment: yes.** No latent failure found. Checked specifically:

| Concern | Finding |
|---|---|
| `build_warehouse.py` hardcodes `.venv/Scripts/dbt.exe` | **Safe in CI.** `build_warehouse.py:150-152` falls back to `dbt` on `PATH` when the path is absent. CI has no `.venv`, so the fallback fires correctly and `dbt` comes from `pip install -r backend/requirements.txt` (`dbt-core==1.8.2`, `dbt-duckdb==1.8.1`). *(The local breakage is the inverse case — the file exists but is unrunnable, so the existence check passes and the fallback never fires. Out of scope here per instruction; separate local-tooling cycle.)* |
| Missing `data/` subdirectories in a fresh checkout | **Safe.** `.gitignore` ignores the contents of `data/{raw,bronze,silver,gold}` and no `.gitkeep` is tracked for them, so they do not exist after checkout — but every writer creates its own: `ingest_raw.py:31-32`, `validate_data.py:5`, `build_warehouse.py:26`, `generate_sample_data.py:28`, all with `exist_ok=True`. |
| `data/raw/` absent | **Safe.** Only referenced under `data_mode='real'`, which is unreachable in CI (no `.env`, `DATA_MODE` unset → `demo`). |
| Non-deterministic sample data | **Safe.** `generate_sample_data.py` imports `random` but never calls it — the CSV content is static and hardcoded. Confirms the observed byte-identity (a full local refresh on 2026-07-28 left `git status` clean against the 22 tracked `data/sample/*.csv`). |
| Stale `.uploaded` markers freezing ingest | **Safe in CI.** Markers live in gitignored `data/silver/`, so a fresh checkout has none. *(One has reappeared locally — `data/silver/test.parquet.uploaded` — affecting a throwaway table only. Local-state note, not a CI issue.)* |
| dbt profile path resolution | **Safe.** `dbt_analytics/profiles.yml` uses `path: "../warehouse/hr_analytics.duckdb"`, resolved relative to the dbt project dir, which `build_warehouse.py:177` sets explicitly via `cwd`. Platform-independent. |
| `data_mode` default | **Safe and byte-identical.** No `.env` in CI → `os.getenv("DATA_MODE","demo")` → `demo` → the 5 fabricated-trend marts stay ungated exactly as today. |
| Linux wheel availability | **Safe.** `polars==0.20.31`, `duckdb==1.0.0`, `dbt-core==1.8.2` all publish cp311 manylinux wheels. |

Expected runtime ≈ 1–2 minutes. Local execution of the same build on committed defaults produced:

```
Resolved report_month from data: 2026-06 (2026-06-01..2026-06-30)
dbt run  →  Done. PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157
dbt test →  Done. PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11
Command Center integration reconciliation checks PASSED.
```

**Observation (no action proposed):** `refresh_all.py` calls `create_sample_data()`, which rewrites the 22 tracked `data/sample/*.csv`. Harmless in CI (ephemeral checkout) and currently a no-op byte-wise, but it means CI cannot detect drift between the generator and the committed sample data. A `git diff --exit-code data/sample/` guard after the refresh step would close that gap. Out of scope for this repair; noting it for the backlog.

---

## 4. Gate 3 — Docker build verification (never executed)

**Assessment: expected to pass.** Gate 3 only *builds* both images (`push: false`); it never runs a container, so runtime wiring cannot fail it.

**Backend image** (`backend/Dockerfile`, context `./backend`) — `python:3.11-slim`, `apt-get install curl`, `pip install -r requirements.txt`, `COPY . .`, `groupadd`/`useradd`, `USER appuser`. All steps are build-time-safe on `ubuntu-latest`. No repo-root paths are referenced from inside the backend context.

**Frontend image** (`frontend/Dockerfile`, context `./frontend`) — `node:22-alpine` builder → `npm ci` → `npm run build` (`tsc -b && vite build`) → `nginx:alpine`.

- Node 22 satisfies every `engines` floor, so `npm ci` on Alpine installs `@oxlint/binding-linux-x64-musl` (declared optional in the lockfile, `os: ["linux"]`). `npm run build` does not invoke oxlint regardless.
- `tsc -b` verified clean locally (exit 0).
- `nginx.conf:2` is `listen 8080`, matching `EXPOSE 8080` and the rootless `USER nginx` — consistent, no privileged-port conflict.

**Two non-blocking findings, flagged not fixed:**

1. **No `.dockerignore` exists** (checked root, `frontend/`, `backend/`). CI is unaffected — a fresh checkout has no `node_modules` — but a developer running `docker compose build` on this Windows machine will have `COPY . .` overwrite the image's Linux `node_modules` with Windows binaries, producing a confusing build or runtime failure. Adding `frontend/.dockerignore` (`node_modules`, `dist`, `test-results`, `.env`) and `backend/.dockerignore` (`__pycache__`, `*.pyc`, `.pytest_cache`, `warehouse`, `data`) is cheap insurance. Recommend as a follow-up, not part of the CI-pass minimum.
2. **The backend image intentionally ships without `config/`, `scripts/`, `dbt_analytics/`, or a warehouse** — `docker-compose.yml` bind-mounts all four at runtime. Correct by design; recorded here so a future reader doesn't "fix" the Dockerfile by widening its build context.

**Also worth scheduling separately:** every run logs `Node.js 20 is deprecated … actions/checkout@v4, actions/setup-node@v4 … forced to run on Node.js 24`, and `docker/build-push-action@v5` is a major version behind. Action-version maintenance, not a blocker — keep it out of this change so the repair diff stays minimal.

---

## 5. Proposed change set

Everything required for a green pipeline, in one commit:

| # | File | Change | Lines |
|---|---|---|---|
| 1 | `.github/workflows/ci-cd-pipeline.yml` | Gate 1: `node-version: 18` → `22` | 1 |
| 2 | `.github/workflows/ci-cd-pipeline.yml` | Gate 2: `node-version: 18` → `22` | 1 |
| 3 | `.github/workflows/ci-cd-pipeline.yml` | Gate 2: `pytest` → `pytest backend/tests` | 1 |
| 4 | `pytest.ini` *(new)* | `testpaths = backend/tests` + `norecursedirs` | 3 |

Optional, same change or immediately after:

| # | File | Change |
|---|---|---|
| 5 | `frontend/package.json` | add `"engines": { "node": ">=22.12.0" }` |
| 6 | `.nvmrc` *(new)* | `22` |

Deliberately deferred to separate cycles: the 15-script move to `scripts/debug/`, `.dockerignore` files, the `data/sample` drift guard, GitHub Action version bumps, `DOCUMENTATION.md` §13 correction, and the local `.venv` shim repair.

**No application code, dbt model, lockfile, or `data/` content is touched.** `data_mode=demo` behaviour is unchanged by construction — nothing in the change set is read by the pipeline at runtime.

---

## 6. Verification plan

Order matters: gates are chained with `needs:`, so each one only becomes observable once the previous passes. Expect to learn something new at each step.

1. **Local pre-check** (before pushing): `pytest backend/tests -q` → expect `10 passed`; `cd frontend && npx tsc --noEmit` → expect exit 0. Both already confirmed at plan time.
2. **Push `fix/ci-pipeline` and open a PR against `main`.** The workflow triggers on `pull_request: [main]`, so the full three-gate run executes on the PR without touching `main`.
3. **Gate 1** — confirm `npm ci` installs the binding under Node 22 and `npm run lint` exits 0. This is also the first real test of the flake8 step (§1.5); if it fails on `E9,F63,F7,F82`, fix the flagged code rather than loosening the selector.
4. **Gate 2** — confirm `vitest run src/` passes (1 test file: `GovernanceWidget.test.tsx`), `refresh_all.py` reports `PASS=157` / `PASS=11` / reconciliation PASSED, and `pytest backend/tests` reports `10 passed`. Watch the Gate 2 duration: anything past ~5 minutes on the pytest step means collection is still unbounded.
5. **Gate 3** — first execution ever. Both images build; treat any failure here as new information, not regression.
6. **Only after all three are green:** update `DOCUMENTATION.md` §13, which currently describes this pipeline as working.

**Rollback:** revert the single commit. The change set adds one file and edits three lines in another; there is no migration, no data effect, and no state to unwind.

**Definition of done:** one complete green run of all three gates on the PR — the first in this repository's history.

---

## 7. Risks and open questions

| Risk | Likelihood | Mitigation |
|---|---|---|
| Node 22 surfaces new lint/type errors that Node 18 never got far enough to report | Medium | Expected and desirable — the gate has never run. Fix findings on this branch before merge. |
| flake8 `E9,F63,F7,F82` fails on first execution (§1.5, unverified) | Low | Fix the offending code; do not weaken the selector. |
| Gate 2 `refresh_all.py` behaves differently on Linux than the local Windows run | Low | Every path checked in §3; profile paths are relative and dirs are self-created. |
| Gate 3 fails for a reason not visible by inspection | Medium | It has literally never run. Budget one iteration for it. |
| `pytest.ini` alters an unrelated local workflow | Very low | It only narrows default collection to `backend/tests`; explicit paths (`pytest scratch/foo.py`) still work. |

**Open question for the chief architect:** should the 15 root debug scripts move in the same PR or a follow-up? This plan recommends **follow-up**, to keep the CI repair a 4-line reviewable diff. Say the word if you'd rather have one clean sweep.

---

**Prepared for review. No implementation performed.**
