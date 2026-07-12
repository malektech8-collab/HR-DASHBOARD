# Phase 0 — Foundation Batch (Execution Report)

**Status:** executed on `main` (working tree, uncommitted). **Not pushed. Awaiting review.**
**Date:** 2026-07-09 · **Committed default:** `data_mode = "demo"` everywhere (`real` committed is forbidden and absent).

This batch establishes the single `data_mode` switch, gates the 5 fabricated-history marts, and parameterizes the 2 computed-history marts. It does **not** touch ingestion or the API report-month resolver (separate cycles).

---

## (a) Approved plan

### Backbone — single source of truth for `data_mode`
One env var, `DATA_MODE`, default `demo`, read from one uncommitted `.env` and flowing to both consumers:

- **Committed defaults (stay `demo`):** `dbt_project.yml` var `data_mode`, `backend/app/config.py` `Settings.DATA_MODE`, `.env.example` documented line.
- **Local override:** uncommitted `.env` (already gitignored via `.gitignore:19-21`) sets `DATA_MODE=real`.
- **Backend consumer:** pydantic `BaseSettings(env_file=".env")` auto-reads it → exposed via new additive `GET /api/meta/app-config`.
- **dbt consumer:** `build_warehouse.py` loads root `.env` (tightening A), reads `os.getenv("DATA_MODE","demo")`, injects it into the existing `--vars` channel → overrides the `dbt_project.yml` default.
- CI sets no `DATA_MODE` → everything resolves to `demo` → sample data + mock rows unchanged.

### Tasks
1. **AGENTS.md** — one additive scope clause permitting LOCAL, UNCOMMITTED, SINGLE-USER real-data use; all existing rules intact.
2. **data_mode foundation** — `dbt_project.yml` (`data_mode:"demo"`), `config.py` (`DATA_MODE:str="demo"`), `.env.example` (documented line), new `AppConfigResponse` schema + `GET /api/meta/app-config`.
3. **Gate the 5 HYBRID-FABRICATED marts** — `mart_attendance_trend`, `mart_saudization_summary`, `mart_talent_review_trends`, `mart_er_case_trend`, `mart_recruitment_trends`. Wrap the mock `SELECT … UNION ALL` prefix (with the `UNION ALL` **inside** the guard) in `{% if var('data_mode','demo')=='demo' %}…{% endif %}`. Current source-computed row ungated. Rows preserved, not deleted.
4. **Parameterize the 2 HYBRID-COMPUTED marts** — `mart_exec_trends`, `mart_workforce_headcount_trend`. Replace `'2026-04'/'2026-04-30'/'2026-05'/'2026-05-31'` with vars `trend_m1/trend_m1_end/trend_m2/trend_m2_end` defaulted to today's literals (byte-identical output).

### Chief-architect tightenings (all applied)
- **A.** `build_warehouse.py` loads root `.env` (via `python-dotenv`) **before** reading `DATA_MODE` — mandatory, no split-brain.
- **B.** `python-dotenv==1.2.2` pinned in `backend/requirements.txt` (declared, not relying on the pydantic-settings transitive).
- **C.** Both Task-4 marts carry a one-line comment: anchors are placeholders, to be replaced by report_month-relative derivation in the resolver cycle (5a).

---

## (b) Unified diffs (every file changed)

### Foundation + wiring

```diff
diff --git a/AGENTS.md b/AGENTS.md
@@ -12,3 +12,5 @@ All contributors and automation agents must follow these project governance rule
 - No actual real-data execution may be approved.
 - Human review is required before merge.
+
+**Scope of the above rules.** The prohibitions above govern (a) anything committed to this repository and (b) the shared synthetic governance simulation (`data/real_*`, `data/synthetic_dry_run/`, the Gate 1–5 artifacts). They do **not** prohibit a single operator running the dashboard **locally** on real HR data that is **never committed, never pushed, never deployed, and confined to gitignored paths** (`data/raw/`, `data/bronze/`, `data/silver/`, `data/gold/`, `warehouse/`). Local real-data use must leave the committed tree, CI, and `data/sample/` unchanged; the `data/real_*` directories remain simulation-only and stay `.gitkeep`-only.
```

```diff
diff --git a/dbt_analytics/dbt_project.yml b/dbt_analytics/dbt_project.yml
@@ -21,6 +21,10 @@ models:
 vars:
+  # Data mode: 'demo' shows synthetic sample data + mock historical trend rows;
+  # 'real' suppresses all fabricated rows. Committed default MUST stay 'demo'.
+  # Overridden locally (uncommitted) via the DATA_MODE env var / .env.
+  data_mode: "demo"
   report_month: "2026-06"
@@ -40,5 +44,12 @@ vars:
   start_date_str: "2026-06-01"
   end_date_str: "2026-06-30"
+  # Trend historical-anchor months for the 2 HYBRID-COMPUTED headcount marts.
+  # Placeholder literals — to be replaced by report_month-relative derivation in
+  # the resolver cycle (5a). Defaults equal today's hardcoded values (byte-identical).
+  trend_m1: "2026-04"
+  trend_m1_end: "2026-04-30"
+  trend_m2: "2026-05"
+  trend_m2_end: "2026-05-31"
```

```diff
diff --git a/backend/app/config.py b/backend/app/config.py
@@ -10,6 +10,10 @@ class Settings(BaseSettings):
     PORT: int = 8000
     DEBUG: bool = True
 
+    # Data mode: 'demo' (committed default) serves synthetic sample data;
+    # 'real' is set locally (uncommitted, via .env / env var) for real-data use.
+    DATA_MODE: str = "demo"
+
     # S3 / Cloud Storage configurations
```

```diff
diff --git a/backend/app/schemas/kpi.py b/backend/app/schemas/kpi.py
@@ -39,3 +39,6 @@ class DQExceptionsResponse(BaseModel):
 class RefreshStatusResponse(BaseModel):
     last_refresh_at: str
     status: str
+
+class AppConfigResponse(BaseModel):
+    data_mode: str
```

```diff
diff --git a/backend/app/main.py b/backend/app/main.py
@@ -2,7 +2,7 @@ from fastapi import FastAPI
 from app.api.endpoints import governance
-from app.schemas.kpi import RefreshStatusResponse
+from app.schemas.kpi import RefreshStatusResponse, AppConfigResponse
 from app.config import settings
@@ -45,6 +45,11 @@ def get_refresh_status():
         status=status_str
     )
 
+# Meta app-config endpoint (exposes the active data_mode to the frontend)
+@app.get("/api/meta/app-config", response_model=AppConfigResponse)
+def get_app_config():
+    return AppConfigResponse(data_mode=settings.DATA_MODE)
+
 # Include API routers
```

```diff
diff --git a/.env.example b/.env.example
@@ -4,5 +4,10 @@ HOST=127.0.0.1
 PORT=8000
 DEBUG=true
 
+# Data mode: 'demo' (default) serves synthetic sample data and mock historical
+# trend rows. Set to 'real' locally (this .env is uncommitted) to hide all
+# fabricated rows for real-data use. One .env drives both dbt and the backend.
+# DATA_MODE=demo
+
 # Frontend configuration (if needed)
 VITE_API_URL=http://localhost:8000
```

```diff
diff --git a/backend/requirements.txt b/backend/requirements.txt
@@ -4,6 +4,7 @@ fastapi==0.111.0
 uvicorn==0.30.1
 pydantic==2.7.4
 pydantic-settings==2.3.3
+python-dotenv==1.2.2
 pyyaml==6.0.1
```

```diff
diff --git a/scripts/build_warehouse.py b/scripts/build_warehouse.py
@@ -6,6 +6,11 @@ import calendar
 import json
 import subprocess
 
+# Load the repo-root .env BEFORE reading any env var, so a single uncommitted
+# .env drives both this pipeline and the backend (no split-brain on DATA_MODE).
+from dotenv import load_dotenv
+load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))
+
 # Local dev layout: scripts/../backend/app. ...
@@ -130,6 +135,7 @@ def build_warehouse():
     dbt_vars = {
+        "data_mode": os.getenv("DATA_MODE", "demo"),
         "report_month": cc_report_month,
```

### Task 3 — gate the 5 HYBRID-FABRICATED marts

```diff
diff --git a/dbt_analytics/models/marts/mart_er_case_trend.sql b/dbt_analytics/models/marts/mart_er_case_trend.sql
@@ -1,12 +1,14 @@
 {{ config(materialized='view') }}
 
--- Simulated historical trend for MVP visuals
+{% if var('data_mode', 'demo') == 'demo' %}
+    -- Simulated historical trend for MVP visuals (demo mode only)
     SELECT '2026-04' AS period, 4 AS new_cases, 3 AS closed_cases
     UNION ALL
     SELECT '2026-05' AS period, 5 AS new_cases, 4 AS closed_cases
     UNION ALL
+{% endif %}
     -- Live dynamic current period
-    SELECT 
+    SELECT
         '{{ var('report_month') }}' AS period,
```

```diff
diff --git a/dbt_analytics/models/marts/mart_recruitment_trends.sql b/dbt_analytics/models/marts/mart_recruitment_trends.sql
@@ -1,12 +1,14 @@
--- Simulated historical trend for MVP visuals
+{% if var('data_mode', 'demo') == 'demo' %}
+    -- Simulated historical trend for MVP visuals (demo mode only)
     SELECT '2026-04' AS period, 5 AS requisitions_opened, 3 AS hires
     UNION ALL
     SELECT '2026-05' AS period, 6 AS requisitions_opened, 4 AS hires
     UNION ALL
+{% endif %}
     -- Live dynamic current period
     SELECT
```

```diff
diff --git a/dbt_analytics/models/marts/mart_saudization_summary.sql b/dbt_analytics/models/marts/mart_saudization_summary.sql
@@ -1,9 +1,11 @@
--- Sample-mode simulated history (clearly documented as mock trend history)
+{% if var('data_mode', 'demo') == 'demo' %}
+    -- Sample-mode simulated history (mock trend history, demo mode only)
     SELECT '2026-04' AS period, 8 AS saudi_headcount, 10 AS non_saudi_headcount, 0 AS employees_missing_nationality, 44.44 AS saudization_pct
     UNION ALL
     SELECT '2026-05' AS period, 9 AS saudi_headcount, 10 AS non_saudi_headcount, 0 AS employees_missing_nationality, 47.37 AS saudization_pct
     UNION ALL
+{% endif %}
     -- Live dynamic data
     SELECT '{{ var('report_month') }}' AS period, saudi_headcount, non_saudi_headcount, employees_missing_nationality, saudization_pct FROM {{ ref('mart_compliance_kpis') }}
```

```diff
diff --git a/dbt_analytics/models/marts/mart_talent_review_trends.sql b/dbt_analytics/models/marts/mart_talent_review_trends.sql
@@ -1,9 +1,12 @@
-SELECT '2026-04' AS period, 12 AS total_reviewed, 10 AS completed_reviews, 85.0 AS completion_pct, 3.6 AS avg_rating
+{% if var('data_mode', 'demo') == 'demo' %}
+    -- Simulated historical trend for MVP visuals (demo mode only)
+    SELECT '2026-04' AS period, 12 AS total_reviewed, 10 AS completed_reviews, 85.0 AS completion_pct, 3.6 AS avg_rating
     UNION ALL
     SELECT '2026-05' AS period, 14 AS total_reviewed, 12 AS completed_reviews, 88.0 AS completion_pct, 3.7 AS avg_rating
     UNION ALL
+{% endif %}
     SELECT '{{ var('report_month') }}' AS period,
```

```diff
diff --git a/dbt_analytics/models/marts/mart_attendance_trend.sql b/dbt_analytics/models/marts/mart_attendance_trend.sql
@@ -1,6 +1,8 @@
 {{ config(materialized='view') }}
 
-SELECT 
+{% if var('data_mode', 'demo') == 'demo' %}
+    -- Simulated historical trend for MVP visuals (demo mode only)
+    SELECT
         '2026-04' AS month, 0.965 AS attendance_compliance_pct, 2.0 AS absence_days, 180.0 AS late_minutes, ...
     UNION ALL
-    SELECT 
+    SELECT
         '2026-05' AS month, 0.950 AS attendance_compliance_pct, 3.0 AS absence_days, 240.0 AS late_minutes, ...
     UNION ALL
-    SELECT 
+{% endif %}
+    SELECT
         '2026-06' AS month,
         ROUND(attendance_compliance_pct, 4) AS attendance_compliance_pct, ... FROM {{ ref('mart_attendance_kpis') }}
```

### Task 4 — parameterize the 2 HYBRID-COMPUTED marts (tightening C comment included)

```diff
diff --git a/dbt_analytics/models/marts/mart_workforce_headcount_trend.sql b/dbt_analytics/models/marts/mart_workforce_headcount_trend.sql
@@ -1,18 +1,19 @@
-SELECT 
-        '2026-04' AS month,
+-- Historical anchors are placeholders; to be replaced by report_month-relative derivation in the resolver cycle (5a).
+    SELECT
+        '{{ var('trend_m1') }}' AS month,
         COUNT(DISTINCT employee_id) AS active_headcount
     FROM {{ ref('stg_employees') }}
-    WHERE joining_date <= '2026-04-30' 
-      AND (termination_date IS NULL OR termination_date > '2026-04-30')
+    WHERE joining_date <= '{{ var('trend_m1_end') }}'
+      AND (termination_date IS NULL OR termination_date > '{{ var('trend_m1_end') }}')
     UNION ALL
-        '2026-05' AS month, ... WHERE joining_date <= '2026-05-31' ...
+        '{{ var('trend_m2') }}' AS month, ... WHERE joining_date <= '{{ var('trend_m2_end') }}' ...
     UNION ALL
     SELECT '{{ var('report_month') }}' AS month, ... FROM {{ ref('base_active_workforce') }}
```

```diff
diff --git a/dbt_analytics/models/marts/mart_exec_trends.sql b/dbt_analytics/models/marts/mart_exec_trends.sql
@@ -8,19 +8,20 @@ WITH payroll_months AS (...),
     headcount_months AS (
-        SELECT 
-            '2026-04' AS month, ... WHERE joining_date <= '2026-04-30' ...
+        -- Historical anchors are placeholders; to be replaced by report_month-relative derivation in the resolver cycle (5a).
+        SELECT
+            '{{ var('trend_m1') }}' AS month, ... WHERE joining_date <= '{{ var('trend_m1_end') }}' ...
         UNION ALL
-            '2026-05' AS month, ... WHERE joining_date <= '2026-05-31' ...
+            '{{ var('trend_m2') }}' AS month, ... WHERE joining_date <= '{{ var('trend_m2_end') }}' ...
         UNION ALL
         SELECT '{{ var('report_month') }}' AS month, ... FROM {{ ref('stg_employees') }} WHERE status = 'Active'
```

---

## (c) dbt run — BOTH modes, with row-count proof

Both runs: `dbt run --project-dir . --profiles-dir . -s <the 7 models>`, executed in the backend container against the live warehouse.

### demo (committed default) — `PASS=7 WARN=0 ERROR=0`
```
1 of 7 OK created sql view model main.mart_attendance_trend .......... [OK]
2 of 7 OK created sql view model main.mart_er_case_trend ............. [OK]
3 of 7 OK created sql view model main.mart_exec_trends ............... [OK]
4 of 7 OK created sql view model main.mart_recruitment_trends ........ [OK]
5 of 7 OK created sql view model main.mart_saudization_summary ....... [OK]
6 of 7 OK created sql view model main.mart_talent_review_trends ...... [OK]
7 of 7 OK created sql view model main.mart_workforce_headcount_trend . [OK]
Done. PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=7
```

### real (`--vars '{"data_mode":"real"}'`) — `PASS=7 WARN=0 ERROR=0`
```
1..7 OK created (all 7 views) ... Done. PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=7
```

### Row-count proof

**Gated marts — 3 rows (demo) → 1 row (real), fabricated 2026-04/2026-05 dropped:**

| Mart | demo rows / periods | real rows / periods |
|---|---|---|
| `mart_attendance_trend` | 3 · `[2026-04, 2026-05, 2026-06]` | **1 · `[2026-06]`** |
| `mart_saudization_summary` | 3 · `[2026-04, 2026-05, 2026-06]` | **1 · `[2026-06]`** |
| `mart_talent_review_trends` | 3 · `[2026-04, 2026-05, 2026-06]` | **1 · `[2026-06]`** |
| `mart_er_case_trend` | 3 · `[2026-04, 2026-05, 2026-06]` | **1 · `[2026-06]`** |
| `mart_recruitment_trends` | 3 · `[2026-04, 2026-05, 2026-06]` | **1 · `[2026-06]`** |

→ In `real`, only the source-computed current-period row survives. **No fabricated number is emitted.**

**Computed marts — byte-identical across both modes:**

| Mart | demo | real |
|---|---|---|
| `mart_exec_trends` | `(2026-04,20,435385.0)`, `(2026-05,19,446385.0)`, `(2026-06,19,446175.0)` | **identical** |
| `mart_workforce_headcount_trend` | `(2026-04,20)`, `(2026-05,19)`, `(2026-06,19)` | **identical** |

→ Task-4 var substitution is value-preserving (defaults equal the prior literals).

_Warehouse restored to committed default (`demo`) after the proof runs — final rebuild `PASS=7`._

---

## (d) pytest — committed default (`DATA_MODE=demo`)

Run against the **rebuilt backend image** (so it reflects this batch's `config.py`/`main.py`/`schemas` edits and the newly-pinned `python-dotenv==1.2.2`):

```
..F......F                                                     [100%]
FAILED tests/test_auth.py::test_governance_access_granted   - assert 404 == 200
FAILED tests/test_governance.py::test_governance_status_endpoint - assert 404 == 200
2 failed, 8 passed, 2 warnings in 68.59s
```

**The 2 failures are pre-existing and unrelated to this batch — evidence:**
- Both fail on `GET /api/governance/status` returning **404**, raised inside `backend/app/api/endpoints/governance.py:41-45` when its governance-config file (`CONFIG_PATH`) is absent in this container — an environment/data condition, not a routing regression.
- `git status --short` shows `governance.py` and `security.py` are **not in this batch's diff** (unmodified).
- The sibling route on the **same router**, `POST /api/governance/token`, returns **200** (login assertion passes) — proving `main.py` loads and the governance router is correctly included; only the `/status` handler's own file-existence guard trips.
- The **8 passing tests** include the app-loading, auth-token, and data-management paths that exercise this batch's `main.py`/`config.py`/`schemas` changes.

**Live confirmation of the new endpoint (committed default):**
```
$ curl -s http://localhost:8000/api/meta/app-config
{"data_mode":"demo"}
$ curl -s http://localhost:8000/api/meta/refresh-status
{"last_refresh_at":"2026-07-09T12:48:30.820745","status":"success"}   # untouched, still works
```

→ No test regression introduced by this batch; the suite is green except for the two pre-existing governance-config failures.

---

## (e) grep proof

**No `2026-0x` literal remains in the 2 computed marts:**
```
$ grep -n "2026-0" dbt_analytics/models/marts/mart_exec_trends.sql dbt_analytics/models/marts/mart_workforce_headcount_trend.sql
  NONE — fully parameterized
```

**Fabricated rows emit only under demo (guard present + balanced in all 5 gated marts):**
```
$ grep -rn "var('data_mode', 'demo') == 'demo'" dbt_analytics/models/marts/
mart_attendance_trend.sql:3:{% if var('data_mode', 'demo') == 'demo' %}
mart_er_case_trend.sql:3:{% if var('data_mode', 'demo') == 'demo' %}
mart_recruitment_trends.sql:3:{% if var('data_mode', 'demo') == 'demo' %}
mart_saudization_summary.sql:3:{% if var('data_mode', 'demo') == 'demo' %}
mart_talent_review_trends.sql:3:{% if var('data_mode', 'demo') == 'demo' %}

# guard balance (1 if / 1 endif per file):
mart_attendance_trend: 1 if / 1     mart_saudization_summary: 1 if / 1
mart_talent_review_trends: 1 if / 1  mart_er_case_trend: 1 if / 1
mart_recruitment_trends: 1 if / 1
```

Combined with the (c) row-count proof (fabricated periods present in demo, absent in real), fabricated numbers are provably emitted **only** when `data_mode='demo'`.

---

## (f) Walkthrough

I applied the four tasks and three tightenings as approved, then verified against the running stack rather than by assertion. For the wiring I confirmed the existing seams first: `build_warehouse.py` already passes a `--vars` JSON dict to dbt and `config.py` already uses `BaseSettings(env_file=".env")`, so `data_mode` needed only one new key in each plus the tightening-A dotenv load so a single `.env` drives both without split-brain; I pinned `python-dotenv==1.2.2` (tightening B) to the version already resolved in the image. The 5 fabricated marts are gated by wrapping the mock `SELECT … UNION ALL` prefix — with the `UNION ALL` *inside* the guard so `real` mode yields a clean single `SELECT` — and the rows are preserved, so flipping the var back is the only rollback needed. The 2 computed marts had their literal anchors swapped for vars defaulted to the same literals (tightening-C placeholder comment added). I proved correctness by building all 7 models in both modes: the gated five drop from 3 rows to exactly 1 (only the source-computed `2026-06` row) in `real`, while the two computed marts return byte-identical values in both — then restored the warehouse to the committed `demo` default. One environment nuance surfaced and is disclosed honestly: the backend `/app` is baked into the image, not bind-mounted, so my first pytest run tested stale code; I rebuilt the backend image (which also exercised the new pinned dependency) and re-ran. The suite is 8 passed / 2 failed, and I isolated the two failures to a pre-existing 404 in the untouched `governance.py` status handler (missing config file), confirmed via `git status` that the file isn't in this diff, and confirmed the sibling `/token` route on the same router returns 200 — so this batch introduces no regression. The new `/api/meta/app-config` endpoint returns `{"data_mode":"demo"}` live.

**Report path:** `docs/phase-0/phase-0-foundation-batch.md`

Not pushed. Awaiting review.
