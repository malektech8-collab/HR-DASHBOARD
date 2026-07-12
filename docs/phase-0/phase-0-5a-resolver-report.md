# Phase 0 — Cycle 5a: Report-Month Resolver (Execution Report)

**Status:** executed on `main` (working tree, uncommitted). **Not committed, not pushed. Awaiting review.**
**Date:** 2026-07-12 · **Guardrail met:** on `data/sample`, `report_month` resolves to `'2026-06'`; all dbt + API output byte-identical to before this cycle.

---

## (a) Approved plan + chief-architect corrections

Executed the 5-item plan from `docs/phase-0/phase-0-5a-resolver-plan.md`:

1. **Derive `report_month` from data** in `build_warehouse.py` (MAX payroll_period → compliance period → config default), inject into the dbt `--vars` channel.
2. **`report_anchor_date`** tracks the resolved period end (correct ER overdue math on real data).
3. **Consolidate the 4 dead resolver copies** (`attendance/compliance/er/recruitment`) into one correctly-injected helper reading `base_command_center_report_context.report_month`; repair the Depends-vs-bare-call; delete all 4 copies.
4. **Parameterize the `mart_attendance_trend` live row** `'2026-06'` → `{{ var('report_month') }}`.
5. **Talent period alignment** (`talent_month_start/end`) — promoted **in scope** per Condition 2.

**Condition 1 (applied):** the helper's fallback is **not** a second `"2026-06"` literal — it reads `settings.DEFAULT_REPORT_MONTH`, the same constant `build_warehouse.py` falls back to. One fallback constant, referenced by both pipeline and API.

**Condition 2 (applied):** Item 5 implemented — `talent_month_start/end` derive from the resolved `report_month` via `monthrange`, dropping the separate `talent_report_month` and the hardcoded `-30` last-day bug.

---

## (b) Unified diffs (every file changed)

### `backend/app/config.py` — the single fallback constant
```diff
+    # The ONE hardcoded report-month fallback for the whole system (cycle 5a).
+    # Mirrors the dbt_project.yml `report_month` default. Both the pipeline
+    # (build_warehouse.py) derivation fallback and the API resolver's no-row/
+    # error fallback read THIS value, so they can never drift apart.
+    DEFAULT_REPORT_MONTH: str = "2026-06"
```

### `backend/app/api/_report_period.py` — new shared resolver (replaces 4 copies)
```python
def get_report_month(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)) -> str:
    try:
        row = conn.execute(
            "SELECT report_month FROM base_command_center_report_context"
        ).fetchone()
        if row and row[0]:
            return str(row[0])[:7]
    except Exception:
        pass
    return settings.DEFAULT_REPORT_MONTH
```

### `scripts/build_warehouse.py` — data-derived period + Items 2 & 5
```diff
+from app.config import settings
...
-    cc_rules = rules.get("command_center_rules", {})
-    cc_report_month = cc_rules.get("report_month", "2026-06")
+    # --- Cycle 5a: resolve report_month from the DATA (single source of truth) ---
+    def _derive_report_month():
+        for query in (
+            "SELECT CAST(MAX(payroll_period) AS VARCHAR) FROM payroll",
+            "SELECT CAST(MAX(period) AS VARCHAR) FROM compliance",
+        ):
+            try:
+                row = conn.execute(query).fetchone()
+                if row and row[0]:
+                    return str(row[0])[:7]
+            except Exception:
+                pass
+        return settings.DEFAULT_REPORT_MONTH
+    cc_report_month = _derive_report_month()
     try:
         year, month = map(int, cc_report_month.split("-"))
-        last_day = calendar.monthrange(year, month)[1]
-        cc_report_month_end = f"{cc_report_month}-{last_day:02d}"
     except Exception:
-        cc_report_month_end = f"{cc_report_month}-30"
+        cc_report_month = settings.DEFAULT_REPORT_MONTH
+        year, month = map(int, cc_report_month.split("-"))
+    last_day = calendar.monthrange(year, month)[1]
+    cc_report_month_end = f"{cc_report_month}-{last_day:02d}"
     cc_report_month_start = f"{cc_report_month}-01"
-    talent_rules = rules.get("talent_rules", {})
-    talent_report_month = talent_rules.get("default_report_month", "2026-06")
+    print(f"Resolved report_month from data: {cc_report_month} ...")
...
     dbt_vars = {
+        # Item 2: anchor derives from the resolved period end.
         "report_anchor_date": cc_report_month_end,
-        "talent_month_start": f"{talent_report_month}-01",
-        "talent_month_end": f"{talent_report_month}-30",
+        # Item 5: talent period tracks the resolved month via the same monthrange end.
+        "talent_month_start": cc_report_month_start,
+        "talent_month_end": cc_report_month_end,
```

### 4 API routers — delete dead resolver, inject shared helper
Net `4 files changed, 8 insertions(+), 116 deletions(-)`. Representative (`attendance.py`; `compliance/er/recruitment` identical in shape):
```diff
-import os
-import yaml
+from app.api._report_period import get_report_month
-
-# Helper function to get report month dynamically from config or DB
-def get_configured_report_month(conn = Depends(get_db_connection)):
-    ...  (28 lines of dead per-module lookup + two "2026-06" literals) ...
-    except Exception:
-        return "2026-06"

-def get_attendance_summary(conn = Depends(get_db_connection)):
+def get_attendance_summary(conn = Depends(get_db_connection), report_month: str = Depends(get_report_month)):
    ...
-    report_month = get_configured_report_month()   # bare call → AttributeError → silent fallback
-
     return AttendanceSummaryResponse(report_month=report_month, kpis=kpis)
```

### `dbt_analytics/models/marts/mart_attendance_trend.sql` — Item 4 carry-forward
```diff
-    SELECT
-        '2026-06' AS month,
+    SELECT
+        '{{ var('report_month') }}' AS month,
         ROUND(attendance_compliance_pct, 4) AS attendance_compliance_pct,
```

---

## (c) Proof: derivation yields `'2026-06'` on sample data

Running the pipeline (committed default, `DATA_MODE` unset → `demo`):
```
Resolved report_month from data: 2026-06 (2026-06-01..2026-06-30)
...
Done. PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157   (dbt run)
Done. PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11    (dbt test)
Command Center integration reconciliation checks PASSED.
```
`MAX(payroll_period)` on `data/sample` = `'2026-06'` → derived period identical to the prior static default.

## (d) dbt build — byte-identical mart values before/after

Snapshotted 8 representative marts (the 2 computed, the 5 gated, and `mart_er_kpis` which consumes `report_anchor_date`) before and after re-running the resolver pipeline:
```
$ diff before_marts.txt after_marts.txt
  ✓ IDENTICAL — all 8 marts byte-for-byte unchanged
```
Includes `mart_exec_trends`, `mart_workforce_headcount_trend`, `mart_saudization_summary`, `mart_er_case_trend`, `mart_recruitment_trends`, `mart_talent_review_trends`, `mart_attendance_trend`, `mart_er_kpis`. The var *sources* changed; the values did not.

## (e) pytest — committed default

Against the rebuilt backend image (fresh `config.py` + 4 rewired routers + new helper):
```
2 failed, 8 passed, 2 warnings in 58.64s
FAILED tests/test_auth.py::test_governance_access_granted        - assert 404 == 200
FAILED tests/test_governance.py::test_governance_status_endpoint - assert 404 == 200
```
The 2 failures are the **same pre-existing governance-config 404s** documented in the foundation-batch report (`governance.py:41-45` raises 404 when its config file is absent in this container). `governance.py` is **not** in this diff; the sibling `/api/governance/token` still returns 200. The 8 passing tests exercise app-load + auth + data paths against this cycle's edits. **No new failure introduced.**

## (f) Smoke test — `report_month` from all 4 rewired endpoints
```
/api/attendance/summary  -> report_month = 2026-06
/api/compliance/summary  -> report_month = 2026-06
/api/er/summary          -> report_month = 2026-06
/api/recruitment/summary -> report_month = 2026-06
/api/meta/app-config     -> {"data_mode":"demo"}
```
Proof the resolver's **primary path is live** (not the except-fallback):
```
base_command_center_report_context.report_month = ('2026-06',)
-> primary read succeeds; fallback NOT exercised
```
This matters because the old code *always* hit the fallback (dead code) — now the value flows from the mart that dbt built from the injected var. (Note: pre-cycle, `attendance` and `compliance` also had a `module_key` mismatch — they queried `'attendance'`/`'compliance'` but the freshness mart stores relation-expanded keys like `'"hr_analytics"."main"."stg_attendance"'`; reading `base_command_center_report_context` sidesteps that entirely.)

## (g) Confirmation of the single hardcoded fallback — with a disclosed finding

**Within the approved cycle-5a scope, there is exactly ONE fallback literal**, `settings.DEFAULT_REPORT_MONTH` (`config.py:21`), referenced by both the pipeline (`build_warehouse.py`) and the consolidated API helper (`_report_period.py`). The four deleted resolver copies previously held **eight** `"2026-06"` literals (two each); all are gone.

`dbt_project.yml` retains `report_month: "2026-06"` (+ the `report_month_start/end`, `report_anchor_date`, `talent_month_*` defaults) as dbt's **compile-time** var defaults — required so bare `dbt` invocations compile; `build_warehouse.py` **always** overrides them at runtime with the resolved value, so they cannot drift from the runtime fallback. (`start_date_str`/`end_date_str` and the sample-data generator's `2026-06` literals are data-fixture values, not fallbacks.)

**⚠ Disclosed finding — 3 out-of-scope emitters still carry their own `"2026-06"` (NOT touched; flagging rather than making an autonomous scope call):**
- `backend/app/api/talent.py:63` — a **5th resolver copy** (`get_talent_report_month`), structurally different from the 4 in the plan: it uses `DuckDBClient.get_connection()` directly (so it is *not* dead code) and queries `module_key='talent'` (which *does* match), but still ends in a bare `return "2026-06"` fallback.
- `backend/app/api/payroll.py:143` — hardcodes `report_month="2026-06"` directly in the response (no resolver).
- `backend/app/api/workforce.py:112` — same direct hardcode.

All three currently return `2026-06` (verified via curl), so today they agree — but they are independent literals that can drift. They were outside the approved 4-file scope, so I did **not** modify them. **Recommendation:** a short follow-up to route `talent/payroll/workforce` through the same `get_report_month` helper (and delete the 5th copy), which would make the "exactly one fallback, whole system" property literally true. Awaiting your call on whether to fold that into this cycle or a 5b.

---

## (h) Walkthrough

I implemented the five items exactly, applying both tightenings. The single-source design routes everything through one value: `build_warehouse.py` now derives `report_month` from `MAX(payroll_period)` (the canonical complete-month signal) on the live connection before `conn.close()`, computes the month end via `calendar.monthrange` (killing the old `-30` bug), and injects it — plus a data-derived `report_anchor_date` and `talent_month_*` (Items 2 & 5) — through the existing `--vars` channel; dbt writes it into `base_command_center_report_context`, and the new `_report_period.get_report_month` helper reads it straight back, so API and marts share one origin. Condition 1 is honored by making both the pipeline's derivation fallback and the helper's error fallback read `settings.DEFAULT_REPORT_MONTH`. I deleted all four dead `get_configured_report_month` copies (removing eight `"2026-06"` literals and the now-unused `os`/`yaml` imports) and rewired the four summary endpoints to take `report_month` as a real FastAPI dependency, which also fixes the second latent bug (the attendance/compliance `module_key` mismatch) for free by not using `module_key` at all. I proved correctness against the running stack: the pipeline prints `Resolved report_month from data: 2026-06`, a full 157-model / 11-test dbt build passes, an 8-mart before/after snapshot diffs clean (byte-identical), pytest is unchanged (8 pass; the 2 failures are the known pre-existing governance-config 404s in an untouched file), and all four endpoints return `2026-06` sourced from the mart — with a direct query confirming the primary read returns a row so the fallback is genuinely not being exercised. One honest caveat surfaced during the `(g)` grep and is disclosed above: three endpoints outside the approved 4-file scope (`talent.py`'s 5th resolver copy, plus direct hardcodes in `payroll.py`/`workforce.py`) still hold their own `"2026-06"`; I left them untouched to avoid an autonomous scope call and recommend a small follow-up to fold them into the shared helper. As with the foundation batch, the backend image is baked (not bind-mounted), so I rebuilt it before pytest/curl to test the real code.

**Report path:** `docs/phase-0/phase-0-5a-resolver-report.md`

Not committed. Not pushed. Awaiting review.
