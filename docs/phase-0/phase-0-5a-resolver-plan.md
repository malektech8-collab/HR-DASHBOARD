# Phase 0 — Cycle 5a: Report-Month Resolver (PLAN ONLY)

**Status:** proposed. Nothing implemented this turn. Builds on the committed foundation batch (`data_mode` switch).
**Guardrail restated:** on the committed `data/sample` set the derivation MUST still yield `report_month = '2026-06'`, so demo/CI output stays byte-identical.

## Problem statement (verified this cycle)

`report_month` is a static `dbt_project.yml` default (`'2026-06'`), and the API's `get_configured_report_month()` never actually runs. Two independent defects were confirmed against the built warehouse:

1. **Dead code (Depends-vs-bare-call).** All 4 copies are declared `def get_configured_report_month(conn = Depends(get_db_connection))` but called **bare** — `get_configured_report_month()` — at [attendance.py:142](../../backend/app/api/attendance.py), [compliance.py:64](../../backend/app/api/compliance.py), [er.py:66](../../backend/app/api/er.py), [recruitment.py:70](../../backend/app/api/recruitment.py). Outside FastAPI's dependency pipeline `conn` is the `Depends(...)` marker object; `conn.execute(...)` raises `AttributeError`, caught by the bare `except Exception: return "2026-06"`. The dynamic lookup has **never executed**.

2. **`module_key` mismatch (would keep 2 of 4 broken even after fixing #1).** The resolvers filter the freshness mart by literal keys `'attendance'` / `'compliance'`, but that mart builds those rows via `'{{ ref(...) }}'`, so the stored keys are the relation-expanded names. Confirmed by querying `mart_command_center_data_freshness`:

   ```
   module_key                                | max_source_date
   '"hr_analytics"."main"."stg_attendance"'  | '2026-06-04'   ← attendance resolver looks for 'attendance'  → 0 rows
   '"hr_analytics"."main"."stg_compliance"'  | '2026-06'      ← compliance resolver looks for 'compliance' → 0 rows
   '"hr_analytics"."main"."stg_payroll"'     | '2026-06'
   'er'                                      | '2026-06-10'   ← er resolver matches ✓
   'recruitment'                             | '2026-06-10'   ← recruitment resolver matches ✓
   'talent'                                  | '2026-06-26'
   'workforce'                               | '2025-04-01'
   ```

   So a naive "fix the Depends bug only" would silently leave attendance and compliance on the `'2026-06'` fallback. This is why the fix must **consolidate onto the single source**, not patch four per-module lookups.

## Single-source-of-truth design

**The DATA is the source.** `build_warehouse.py` derives `report_month` from the latest complete period in the loaded data and injects it into the existing dbt `--vars` channel. dbt writes it into `base_command_center_report_context.report_month`. **Both** consumers then read from that one resolved value:

```
   data/silver/payroll.parquet ──(MAX payroll_period)──►  build_warehouse.py derives report_month
                                                                    │
                                        injected via --vars '{"report_month": ...}'
                                                                    ▼
                                         all dbt marts key off {{ var('report_month') }}
                                                                    │
                                        materialized into base_command_center_report_context
                                                                    ▼
                     API reads SELECT report_month FROM base_command_center_report_context  (one query, no per-module keys)
```

This guarantees API `report_month` == the value every mart was built with, and eliminates the `module_key` lookup entirely.

---

## Numbered plan

### 1. Derive `report_month` from data in `build_warehouse.py`
- **File:** `scripts/build_warehouse.py` (lines ~86–94, 137–144).
- **Exact change:** Replace the current `cc_rules = rules.get("command_center_rules", {})` block (which reads a `command_center_rules` key that does **not** exist in `config/business_rules.yml`, so it always defaults to `'2026-06'`) with a derivation that runs on the already-open `conn` **before** `conn.close()` (line 129), after the source tables are created from parquet (lines 63–68):
  - Primary: `SELECT MAX(payroll_period) FROM payroll` — payroll is the canonical monthly HR close and is always a complete `YYYY-MM` period string (avoids mid-month partials like attendance's `'2026-06-04'`).
  - Fallback chain if that is NULL/absent: `MAX(period) FROM compliance` → the `dbt_project.yml` default `var('report_month')` (`'2026-06'`). Wrap in try/except; any failure → keep the static default (satisfies "fallback if derivation yields nothing").
  - Normalize to `YYYY-MM` via `str(value)[:7]`.
  - Derive `report_month_start = f"{rm}-01"` and `report_month_end` via `calendar.monthrange` (the correct last day — **not** a hardcoded `-30`).
- **Flow to dbt:** set `dbt_vars["report_month"]`, `["report_month_start"]`, `["report_month_end"]` from the derived values (the `--vars` JSON already flows to both `dbt run` and `dbt test`).
- **Sample-data proof (guardrail):** `MAX(payroll_period)` on `data/sample` = `'2026-06'` (verified) → identical to today. Byte-identical demo/CI output.
- **Risk:** Low. If payroll is empty on some real drop, the fallback chain prevents a crash. Choosing payroll (not a max across mixed date columns) avoids selecting an incomplete month.

### 2. Fix `report_anchor_date` to track the resolved period end
- **File:** `scripts/build_warehouse.py` (line 142); default in `dbt_analytics/dbt_project.yml` (`report_anchor_date: "2026-06-30"`).
- **Exact change:** `build_warehouse.py` already sets `dbt_vars["report_anchor_date"] = cc_report_month_end`. Once item 1 makes `report_month_end` data-derived (via `monthrange`), the injected anchor is automatically correct. Leave the `dbt_project.yml` literal `'2026-06-30'` **only** as the no-injection fallback default; add a comment that it is a fallback, superseded by the resolver.
- **Flow:** anchor is consumed by `base_command_center_report_context.report_month_end` and by `mart_er_kpis` overdue math (`report_anchor_date > effective_target_due_date`). Correct anchor → correct ER overdue counts on real data.
- **Risk:** Low. On sample, `report_month_end` = `'2026-06-30'` — unchanged.

### 3. Consolidate the 4 API resolvers into one shared, correctly-injected helper
- **Files:** new `backend/app/api/_report_period.py` (or add to an existing shared module such as `app/db/`); edits to `attendance.py`, `compliance.py`, `er.py`, `recruitment.py`.
- **Exact change:**
  - Add one function:
    ```python
    def get_report_month(conn = Depends(get_db_connection)) -> str:
        try:
            row = conn.execute(
                "SELECT report_month FROM base_command_center_report_context"
            ).fetchone()
            return str(row[0])[:7] if row and row[0] else "2026-06"
        except Exception:
            return "2026-06"
    ```
    This reads the **actual resolved period** dbt built the marts with — no `module_key`, so the mismatch in defect #2 disappears.
  - **Delete** all 4 local `get_configured_report_month` copies (removes the duplicated, per-module logic — satisfies "no duplicated resolver logic left behind").
  - Repair the **Depends-vs-bare-call**: make each endpoint that needs the period take it as a FastAPI dependency, e.g. `def get_er_summary(conn = Depends(get_db_connection), report_month: str = Depends(get_report_month)):`, and delete the bare `report_month = get_configured_report_month()` line. FastAPI then injects a real connection into the helper.
- **Flow:** API and marts now both originate from the single injected var → guaranteed agreement.
- **Risk:** Medium (touches 4 routers). Mitigation: the response field `report_month` is display-only (verified in prior audit — not used in any SQL filter), so a wrong value is cosmetic, not data-corrupting. Each edited endpoint must be smoke-tested.

### 4. Carry-forward: align `mart_attendance_trend` live row to the var
- **File:** `dbt_analytics/models/marts/mart_attendance_trend.sql` (the ungated current-period `SELECT`, `'2026-06' AS month`).
- **Exact change:** `'2026-06' AS month` → `'{{ var('report_month') }}' AS month`, matching the 4 already-gated trend marts.
- **Flow:** current-period label now follows the resolved period.
- **Risk:** Very low. On sample, `var('report_month')` = `'2026-06'` → byte-identical. (Row-count gating from the foundation batch is unaffected.)

### 5. (Flag / recommend) Align `talent_month_*` to the resolved period
- **Files:** `scripts/build_warehouse.py` (lines 96–97, 143–144).
- **Observation:** `talent_report_month` reads `talent_rules.default_report_month` (static `'2026-06'`) and `talent_month_end` is built as `f"{talent_report_month}-30"` — a **hardcoded `-30`** (wrong for 31-day months / February). `talent_month_end` is consumed by `mart_talent_exceptions` (goal-overdue: `due_date < talent_month_end`), so on real data it desyncs from `report_month` and mis-dates the last day.
- **Recommended change (in scope of "all marts key off the real period"):** set `talent_month_start/end` from the same derived `report_month` using `monthrange` (drop the separate `talent_report_month`/`-30`). On sample this stays `'2026-06-01'`/`'2026-06-30'` → byte-identical.
- **Risk:** Low. If the architect prefers to keep talent on its own period signal, this can be deferred — flagging so it is a conscious decision, not an oversight.

---

## Tests that could break (and why they should not, with the guardrail)

- **dbt:** `not_null_mart_exec_kpis_report_month`, `unique_mart_exec_kpis_report_month` — `report_month` stays non-null/unique (single derived value). Should pass.
- **dbt build of all 157 models** — items 1–4 keep the same var *names*; only the *source* of the value changes. On sample the value is unchanged (`'2026-06'`), so every mart's output is identical. The full-refresh dbt build in CI should stay green.
- **pytest (`backend/tests/`)** — `test_data.py` (upload/refresh) and `test_auth.py`/`test_governance.py` do not assert domain `report_month` values; the 2 governance failures are the known pre-existing 404s unrelated to this cycle. Main watch-item: item 3 edits 4 router signatures — if any endpoint's dependency wiring is done wrong it would surface as a 500 on that endpoint. Smoke-test `/api/{attendance,compliance,er,recruitment}/summary` after implementation.
- **Byte-identity proof to capture at execute time:** (a) `build_warehouse` prints derived `report_month == '2026-06'` on sample; (b) `git diff` of a demo-mode full refresh shows no mart value changes; (c) `curl /api/{er,compliance,attendance,recruitment}/summary` returns `report_month: "2026-06"` — now from the mart, not the fallback (confirm by temporarily pointing at a period-shifted fixture in a scratch DB, never real data).

## Out of scope (later cycles, do not touch here)
- Ingestion path / `data/raw/` wiring (separate cycle).
- The parallel dead config `config/business_rules.yml` + `command_center_rules` key — item 1 stops reading the non-existent key; a broader decision to delete/reconcile `business_rules.yml` vs `dbt_project.yml` is deferred.
- The `mart_exec_trends` / `mart_workforce_headcount_trend` historical anchors (`trend_m1/m2`) — already parameterized in the foundation batch; the report_month-relative derivation of those anchors is explicitly the resolver cycle's *successor*, not this item.

---

**Plan file:** `docs/phase-0/phase-0-5a-resolver-plan.md`

STOP — plan only. Awaiting chief-architect approval before implementation.
