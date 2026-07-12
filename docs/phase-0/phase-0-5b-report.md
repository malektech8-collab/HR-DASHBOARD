# Phase 0 — Cycle 5b: Fold the 3 remaining `report_month` emitters into the shared resolver (Execution Report)

**Status:** executed on branch `phase-0/5a-report-month-resolver` (working tree, uncommitted). **Not committed, not pushed. Awaiting review.**
**Date:** 2026-07-12 · **Guardrails met:** all 3 endpoints still return `report_month="2026-06"` on `data/sample`; no new fallback literals; only the 3 planned files touched.

---

## (a) Plan

From `docs/phase-0/phase-0-5b-plan.md` (approved as written):

1. **`talent.py`** — delete `get_talent_report_month` (including the `DuckDBClient` `NameError` dead path that made it always return its `"2026-06"` literal), delete the now-unused `import os` / `import yaml`, add `from app.api._report_period import get_report_month`, inject it into `get_talent_summary`'s signature, delete the bare `report_month = get_talent_report_month()` call.
2. **`payroll.py`** — add the `get_report_month` import + dependency to `get_payroll_summary`; replace the hardcoded `report_month="2026-06"` with the injected value.
3. **`workforce.py`** — same as payroll for `get_workforce_summary`.

After this cycle, every API `report_month` emitter flows through the single `get_report_month` dependency, and the only `"2026-06"` fallback literal in `backend/app` is `settings.DEFAULT_REPORT_MONTH`.

---

## (b) Unified diffs

### `backend/app/api/talent.py` (largest — deletes the 5th dead resolver)
```diff
 from app.schemas.kpi import KPIItem, DQExceptionItem
-import os
-import yaml
+from app.api._report_period import get_report_month

 router = APIRouter()


-def get_talent_report_month():
-    """Resolve the talent report month using the 5-tier priority."""
-    try:
-        config_path = "config/business_rules.yml"
-        rules = {}
-        if os.path.exists(config_path):
-            with open(config_path, "r", encoding="utf-8") as f:
-                rules = yaml.safe_load(f) or {}
-        talent_rules = rules.get("talent_rules", {})
-        configured = talent_rules.get("configured_report_month", None)
-        if configured:
-            return configured
-
-        conn = DuckDBClient.get_connection()
-        try:
-            row = conn.execute(
-                "SELECT max_source_date FROM mart_command_center_data_freshness WHERE module_key = 'talent'"
-            ).fetchone()
-            if row and row[0]:
-                return str(row[0])[:7]
-        except Exception:
-            pass
-        finally:
-            conn.close()
-    except Exception:
-        pass
-    return "2026-06"
-
-
 @router.get("/summary", response_model=TalentSummaryResponse)
-def get_talent_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
+def get_talent_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), report_month: str = Depends(get_report_month)):
     try:
         ...
         raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


-    report_month = get_talent_report_month()
-
     kpis = [
```

### `backend/app/api/payroll.py`
```diff
 from app.schemas.kpi import KPIItem, DQExceptionItem
+from app.api._report_period import get_report_month
 from typing import List

 @router.get("/summary", response_model=PayrollSummaryResponse)
-def get_payroll_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
+def get_payroll_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), report_month: str = Depends(get_report_month)):
     ...
     return PayrollSummaryResponse(
-        report_month="2026-06",
+        report_month=report_month,
         kpis=kpis,
         reconciliation=reconciliation
     )
```

### `backend/app/api/workforce.py`
```diff
 from app.schemas.kpi import KPIItem, DQExceptionsResponse, DQExceptionItem
+from app.api._report_period import get_report_month

 @router.get("/summary", response_model=WorkforceSummaryResponse)
-def get_workforce_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
+def get_workforce_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), report_month: str = Depends(get_report_month)):
     ...
     return WorkforceSummaryResponse(
-        report_month="2026-06",
+        report_month=report_month,
         kpis=kpis
     )
```

---

## (c) Grep proof — no residual `os.` / `yaml.` / `DuckDBClient` / `get_talent_report_month` in talent.py
```
$ grep -nE "\bos\.|\byaml\.|DuckDBClient|get_talent_report_month|import os|import yaml" backend/app/api/talent.py
  CLEAN
```
The deletion also removed the only reference to the never-imported `DuckDBClient` (the latent `NameError`), so talent.py is now free of that dead path entirely.

## (d) App boot confirmation — no ImportError
```
$ docker compose exec backend python -c "import app.main; print('app import OK (no ImportError)')"
app import OK (no ImportError)
$ curl -s http://localhost:8000/health
{"status":"ok"}
```
This is the critical tripwire the plan flagged (removing `os`/`yaml` could have left a dangling reference that 500s every endpoint). The app imports cleanly and health is green — verified against the **rebuilt** backend image, since `/app` is baked in, not bind-mounted.

## (e) pytest — unchanged (8 passed / 2 failed)
```
2 failed, 8 passed, 2 warnings in 66.35s
FAILED tests/test_auth.py::test_governance_access_granted        - assert 404 == 200
FAILED tests/test_governance.py::test_governance_status_endpoint - assert 404 == 200
```
Identical to the pre-5b baseline. The 2 failures are the known pre-existing governance-config 404s (`governance.py:41-45`, untouched file). As the plan noted, no test exercises talent/payroll/workforce, so the suite result is unchanged — the real proof is the smoke test below.

## (f) Smoke test — all 3 endpoints, plus resolver-live confirmation
```
/api/talent/summary    -> report_month = 2026-06
/api/payroll/summary   -> report_month = 2026-06
/api/workforce/summary -> report_month = 2026-06
```
Resolver primary path is **live** (value comes from the mart, not the fallback):
```
base_command_center_report_context.report_month = ('2026-06',)
```
Because the mart read returns a row, `get_report_month` returns the mart value and never reaches `settings.DEFAULT_REPORT_MONTH`. For talent specifically this is a genuine behavior change — its old `get_talent_report_month` always returned the hardcoded literal (via the `DuckDBClient` `NameError` → outer `except` → `return "2026-06"`), so on real data talent's `report_month` would have been stuck at `2026-06` regardless of the period; it now tracks the resolved month like every other endpoint. On sample the output is unchanged (`2026-06`), satisfying byte-identity.

## (g) Grep proof — `"2026-06"` in `backend/app` now appears ONLY at `config.py`
```
$ grep -rn --include=*.py "2026-06" backend/app | grep -v "__pycache__"
backend/app/config.py:21:    DEFAULT_REPORT_MONTH: str = "2026-06"
```
Exactly one source-level literal remains (the stale `__pycache__/*.pyc` hits are pre-edit bytecode, regenerated on rebuild — not source). Combined with cycle 5a, there is now a single report-month fallback constant across the entire backend, and every one of the 7 `report_month`-emitting summary endpoints (executive is derived; the 7 = attendance, compliance, er, recruitment, talent, payroll, workforce) resolves through the one shared `get_report_month` dependency.

---

## (h) Walkthrough

I applied the three edits exactly as approved. In `talent.py` I deleted `get_talent_report_month` wholesale — which the 5b planning had already established was effectively dead: it calls `DuckDBClient.get_connection()` but `DuckDBClient` is never imported into the module, so line 50 raised `NameError`, was swallowed by the outer `except Exception: pass`, and the function always returned its `"2026-06"` literal. Removing it let me drop the now-orphaned `os`/`yaml` imports (both were used only inside that function) and wire `report_month` in as a real FastAPI dependency on `get_talent_summary`, deleting the bare call. `payroll.py` and `workforce.py` were the simple case — no resolver ever existed there, just a literal in the response, so I added the dependency and swapped `"2026-06"` for the injected value. I verified against the running stack rather than by assertion: rebuilt the backend image (the code is baked into `/app`, not mounted), confirmed `import app.main` raises no ImportError and `/health` is green (the key risk from removing `os`/`yaml`), ran the full pytest suite (unchanged 8 pass / 2 fail — the two are the pre-existing governance-config 404s in an untouched file), and curled all three endpoints to confirm `report_month="2026-06"` with a direct mart query proving the value flows from `base_command_center_report_context`, not the fallback. Grep confirms talent.py has no residual dead-code references and that `"2026-06"` now appears in exactly one place in the backend source — `config.py`'s `DEFAULT_REPORT_MONTH` — closing out the "one fallback, whole system" goal that cycle 5a scoped and this cycle completes.

**Report path:** `docs/phase-0/phase-0-5b-report.md`

Not committed. Not pushed. Awaiting review.
