# Phase 0 — Cycle 5b: Fold the 3 remaining `report_month` emitters into the shared resolver (PLAN ONLY)

**Status:** proposed. Nothing implemented this turn.
**Goal:** route `talent.py`, `payroll.py`, `workforce.py` through the existing `get_report_month` dependency (`backend/app/api/_report_period.py`) and delete `talent.py`'s `get_talent_report_month`, so there is exactly one report-month resolver and one fallback constant (`settings.DEFAULT_REPORT_MONTH`) system-wide.

**Guardrails restated:** byte-identical on `data/sample` (all 3 still yield `'2026-06'`); no new fallback literals anywhere; only these 3 files touched.

---

## Pre-implementation findings (verified this turn)

- **`get_talent_report_month` is effectively dead, not "live."** Cycle 5a's report assumed it resolves independently via `module_key='talent'`. In fact line 50 calls `DuckDBClient.get_connection()`, but `DuckDBClient` is **never imported** into `talent.py` (imports are `get_db_connection`, `duckdb`, schemas, `os`, `yaml`). So line 50 raises `NameError`, caught by the outer `except Exception: pass` (line 61), and the function always returns the `"2026-06"` literal (line 63). On real data it would have been stuck at `2026-06` regardless of the freshness mart — this change also **fixes** that latent bug, not just consolidates.
- **No test covers any of the 3 endpoints.** The only backend tests are `test_auth.py`, `test_data.py`, `test_governance.py`. `test_data.py`'s sole match is the string `"test_payroll"` in a table-cleanup loop (line 26) — unrelated. So the suite will stay green trivially; **smoke-testing is the real safeguard**, especially for talent whose executed code path changes.
- **Byte-identity holds:** `get_report_month` reads `base_command_center_report_context.report_month`, which is `'2026-06'` on sample → identical to the 3 current outputs (confirmed via curl in cycle 5a).
- **No new literals:** the shared helper's only fallback is the existing `settings.DEFAULT_REPORT_MONTH`. This cycle *removes* three literals (`talent.py:63`, `payroll.py:143`, `workforce.py:112`) and introduces none.

---

## Per-file plan

### 1. `backend/app/api/talent.py` (largest change — behavior changes, not just source)
- **Delete** `get_talent_report_month` entirely (lines 37–63), including its bare `return "2026-06"` and the latent `DuckDBClient` `NameError`.
- **Delete** the now-unused imports `import os` (line 31) and `import yaml` (line 32). Verified both are used *only* inside the deleted function (`os.path.exists`/`open` at 42–43, `yaml.safe_load` at 44); no other usage in the file. `duckdb` and `get_db_connection` remain (used by every endpoint).
- **Add** import: `from app.api._report_period import get_report_month`.
- **Change** the summary signature (line 67):
  `def get_talent_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):`
  → `def get_talent_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), report_month: str = Depends(get_report_month)):`
- **Delete** the bare call `report_month = get_talent_report_month()` (line 81). The response at line 163 (`TalentSummaryResponse(report_month=report_month, ...)`) now receives the injected value.
- **Risk:** Medium (highest of the three). The executed code path changes from "always fallback literal" to "read the resolved mart value." On sample the output is unchanged (`2026-06`); on real data talent's `report_month` becomes correct for the first time. Because nothing else in `talent.py` referenced `get_talent_report_month` (verified: only definition at 37 and call at 81), deletion is self-contained. Watch: the module must still import cleanly after removing `os`/`yaml` (a stray reference would surface as an `ImportError`/`NameError` at app load → smoke test catches it).

### 2. `backend/app/api/payroll.py`
- **Add** import: `from app.api._report_period import get_report_month`.
- **Change** the summary signature (line 26): add `report_month: str = Depends(get_report_month)`.
- **Change** line 143: `report_month="2026-06",` → `report_month=report_month,`.
- **Risk:** Low. Direct literal swap; no resolver logic ever existed here. `report_month` is used only in the `PayrollSummaryResponse` return.

### 3. `backend/app/api/workforce.py`
- **Add** import: `from app.api._report_period import get_report_month`.
- **Change** the summary signature (line 16): add `report_month: str = Depends(get_report_month)`.
- **Change** line 112: `report_month="2026-06",` → `report_month=report_month,`.
- **Risk:** Low. Same direct-literal swap.

---

## Tests to watch

- **pytest suite:** expected to stay 8 passed / 2 failed — unchanged. The 2 failures are the known pre-existing governance-config 404s (untouched file). No test exercises talent/payroll/workforce, so no assertion should flip; the risk is precisely that this change is *unverified by the suite*.
- **Talent import health (highest watch):** after deleting `os`/`yaml`, confirm `talent.py` imports with no residual `os.`/`yaml.`/`DuckDBClient`/`get_talent_report_month` reference (`grep` the file post-edit) and that the app boots (a broken import 500s *every* endpoint, so pytest's 8 passers would collapse — an easy tripwire).
- **Smoke test (the real proof), all 3 endpoints:**
  - `GET /api/talent/summary` → `report_month == "2026-06"`, HTTP 200 (proves the dead-code deletion didn't break the endpoint and the injected value flows through).
  - `GET /api/payroll/summary` → `report_month == "2026-06"`.
  - `GET /api/workforce/summary` → `report_month == "2026-06"`.
  - Optionally confirm the resolver's primary path is live (`SELECT report_month FROM base_command_center_report_context` returns a row), so `2026-06` is the mart value, not the fallback.
- **Single-fallback confirmation:** `grep -rn '2026-06' backend/app` should afterward show the literal only at `config.py` `DEFAULT_REPORT_MONTH` (no `"2026-06"` left in `talent.py`/`payroll.py`/`workforce.py`).
- **Frontend:** no change needed — `report_month` value is unchanged, so `frontend/src/lib/types.ts`/`api.ts` consumers are unaffected; not in scope, not touched.

---

**Plan file:** `docs/phase-0/phase-0-5b-plan.md`

STOP — plan only. Awaiting chief-architect approval before implementation.
