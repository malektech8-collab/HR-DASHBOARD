# Phase 2 P0 — Steps 1–2 Execution Report

**Branch:** `phase-2/p0-onboarding-safety` off `main` @ `ffb2212` · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.**
**Plan:** [`p0-onboarding-safety-plan.md`](p0-onboarding-safety-plan.md) §0–§1, §5 steps 1–2
**Scope:** steps 1 and 2 only. Steps 3–6 remain planned, not started.

---

## (a) Rulings applied

| # | Ruling | Applied |
|---|---|---|
| 1 | Registry **file only**, no env var | `data/onboarding/declared_domains.yml`; `.gitignore` extended for `data/onboarding/*` and `data/staging/*`. No env-var path exists in the code. |
| 2 | 15 uncontracted tables → gate off via provenance | **Step 6.** Not started, correctly — it is presentation-layer work. Nothing in steps 1–2 pretends to cover it. |
| 3 | Uploads in demo → block, bilingual | **Step 4.** Not started. |
| 4 | dbt severity → guard-based simplification, no spike | Applied — all 11 tests untouched. **Conditional verification below: passed, but for a different reason than the plan stated.** |
| 5 | Staged-upload retention | **Step 4.** Not started. |
| — | Commit auto-declares, response must say so | `onboarding.declare()` is implemented and unit-tested, ready for step 4 to call. |

---

## (d) The cross-domain dbt finding — required before step 2

### Which tests sit on cross-domain marts

All 11 tests, and the upstream domains of each mart:

| # | Mart | Column | Test | Upstream refs |
|---|---|---|---|---|
| 1–2 | `mart_exec_kpis` | `report_month` | unique, not_null | **`stg_employees`, `stg_payroll`, `stg_attendance`, `stg_data_quality`** |
| 3 | `mart_exec_kpis` | `active_headcount` | not_null | (employees) |
| 4 | `mart_exec_kpis` | `payroll_cost` | not_null | (payroll) |
| 5 | `mart_data_quality_summary` | `data_quality_score` | not_null | `mart_exec_kpis`, `stg_data_quality` |
| 6–7 | `mart_payroll_kpis` | `total_payroll_cost`, `employees_paid` | not_null | `base_payroll_current/previous` |
| 8–9 | `mart_attendance_kpis` | `attendance_compliance_pct`, `absence_days` | not_null | `base_expected_attendance` (**employees × calendar**), `base_attendance_payroll_overtime` |
| 10–11 | `mart_compliance_kpis` | `saudization_pct`, `saudi_headcount` | not_null | **`base_active_workforce` (employees) + `base_compliance_current` (compliance)** |

**Three of the five tested marts are cross-domain**, and `mart_exec_kpis` carries tests on columns from two different domains (3 = employees, 4 = payroll). This is exactly the shape that could produce a false abort.

### Measured behaviour

Both directions tested by emptying the other contracted domains' silver tables and rebuilding.

**`declared: [employees]`** — payroll, attendance, compliance, hr_requests, employee_relations empty:

```
dbt run  -> PASS=157 ERROR=0
dbt test -> PASS=11  ERROR=0
```

**`declared: [payroll]`** — employees (the join hub) empty:

```
dbt run  -> PASS=157 ERROR=0
dbt test -> PASS=11  ERROR=0
```

**No false aborts. No null rows. Ruling 4 holds and no spike is needed.**

### But the plan's reasoning was wrong

§0.3 argued the tests are safe because *"an undeclared domain's mart is zero-row, so `not_null` passes vacuously."* **That is false.** Every tested mart emits **exactly one row**:

```
declared:[employees]
  mart_exec_kpis            1 row  -> ('2026-06', 19, 0.0)
  mart_payroll_kpis         1 row  -> (0.0, 0)
  mart_attendance_kpis      1 row  -> (0.0, 494.0)
  mart_compliance_kpis      1 row  -> (50.0, 9)
  mart_data_quality_summary 1 row  -> (0.90625,)

declared:[payroll]
  mart_exec_kpis            1 row  -> ('2026-06', 0, 446175.0)
  mart_compliance_kpis      1 row  -> (0.0, 0)
```

The tests pass because aggregates are `COALESCE`d to zero, **not** because the marts are empty. The conclusion survives; the reasoning does not.

**And one value is not even zero.** At `declared: [employees]`, `mart_attendance_kpis.absence_days = 494.0`. `base_expected_attendance` cross-joins active employees with the workday calendar, so with no attendance rows *every expected workday counts as an absence*. A client who has uploaded only their employee master would be told they had **494 absence days and 0% attendance compliance** for a period they simply have not provided data for.

That is a fabricated number presented as real — the very thing P0-1 exists to prevent — reached by a different route. It is not fixed by steps 1–2, and it is **not** merely cosmetic:

- **Step 6 (per-domain provenance + empty states) is load-bearing safety, not polish.** A zero is a claim, and `494` is a louder one.
- The stop condition in the ruling (*null rows → false abort*) was **not** met, so I proceeded as authorised. Flagging this as a distinct finding rather than folding it into "step 6 as planned", because its severity is higher than the plan implied.

---

## (b) Unified diffs

### New: `scripts/onboarding.py` (182 lines)

Registry loader (`load_declared`, `declare`, `registry_path`), typed empty-table writer (`empty_frame_schema`, `write_empty_table`), and the guard (`assert_declared_matches_populated`). File-only by ruling 1; unknown domain names raise.

### `scripts/ingest_raw.py`

```diff
-import canonical_schema as _cs
+import canonical_schema as _cs
+import onboarding as _onb
+
+NEWLINE = chr(10)
+
+
+class OnboardingIncompleteError(RuntimeError):
+    """Real mode cannot proceed: contracted domains are missing or undeclared."""
```

```diff
     if data_mode == "real":
-        for table in sorted(real_sourceable):
-            raw_path = f"data/raw/{table}.csv"
-            if original_exists(raw_path):
-                ...validate and load...
-            else:
-                print(f"[real] {table}: no {raw_path}; falling back to sample.")
+        declared = _onb.load_declared(contracted=set(real_sourceable))
+        present = [t for t in real_sourceable if original_exists(f"data/raw/{t}.csv")]
+
+        if not declared:
+            missing = [t for t in real_sourceable if t not in present]
+            if missing:
+                raise OnboardingIncompleteError(...all missing, bilingual...)
+            targets = real_sourceable
+        else:
+            missing = [t for t in sorted(declared) if t not in present]
+            if missing:
+                raise OnboardingIncompleteError(...declared but no file...)
+            targets = sorted(declared)
+            empty_domains = [t for t in real_sourceable if t not in declared]
+
+        for table in targets:
+            ...validate and load (unchanged)...
+
+        for table in empty_domains:
+            # Non-existent path so the per-table blocks below skip entirely.
+            files[table] = f"data/raw/__undeclared__/{table}.csv"
```

```diff
+    for table in empty_domains:
+        _onb.write_empty_table(table)
+        print(f"[real] {table}: not declared; empty table written (no sample fallback).")
+
     os.path.exists = original_exists
```

The string `"falling back to sample"` no longer appears anywhere in the file.

### `scripts/build_warehouse.py`

```diff
+sys.path.append(os.path.dirname(os.path.abspath(__file__)))
...
+    if os.getenv("DATA_MODE", "demo") == "real":
+        import onboarding as _onb
+        row_counts = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
+                      for t in sorted(_cs_available_tables())}
+        _onb.assert_declared_matches_populated(row_counts)
+        print(f"Declared-domain guard passed. Row counts: {row_counts}")
+
     conn.close()
```

### `.gitignore`

```diff
 data/gold/*
+# Deployment state and in-flight uploads: client data, never repo content.
+data/onboarding/*
+data/staging/*
```

---

## (c) Unit tests — all four guard states

**57 passed** (45 existing + 12 new in `backend/tests/test_onboarding.py`).

| State | Test | Asserts |
|---|---|---|
| declared + rows | `test_state_1_declared_and_populated_is_fine` | passes |
| **declared + zero rows** | `test_state_2_declared_but_empty_aborts` | raises; message contains "declared but EMPTY" and "load failure" |
| undeclared + zero rows | `test_state_3_undeclared_and_empty_is_fine` | passes |
| **undeclared + rows** | `test_state_4_undeclared_but_populated_aborts` | raises; message contains "populated but NOT declared" |

Plus: both arms reported in one run; absent registry declares nothing; round-trip; unknown domain is a hard error; `declare()` adds and is idempotent; `declare()` rejects an uncontracted domain; empty tables are typed and zero-row; empty tables overwrite previous rows.

### The guard caught a real defect in this cycle

Worth recording, because it is the mechanism validating itself. My first implementation wrote the empty tables **in the resolver**, before the 21 per-table ingest blocks — which then re-ingested from sample and overwrote them. The run aborted:

```
onboarding.OnboardingError: Declared-domain guard failed.
  populated but NOT declared: ['attendance', 'compliance', 'employee_relations',
  'hr_requests', 'payroll']. Either the registry is stale or data reached these
  tables by an unintended path.
```

Arm 4, doing exactly its job, on a bug that would otherwise have shipped as a silent sample-fallback through a different code path. Fixed by pointing the resolver at a non-existent path so those blocks skip, and writing the empty tables after them.

---

## (e) A missing contracted domain aborts, listing ALL missing

Only `data/raw/employees.csv` supplied, no registry:

```
[real] contracted domains: ['attendance', 'compliance', 'employee_relations',
                            'employees', 'hr_requests', 'payroll']
OnboardingIncompleteError
  Real-data mode requires a file for every contracted domain. Missing:
  attendance, compliance, employee_relations, hr_requests, payroll. To onboard
  incrementally, declare the domains you are providing in
  data\onboarding\declared_domains.yml.
  يتطلب وضع البيانات الحقيقية ملفاً لكل نطاق متعاقد عليه. الملفات الناقصة:
  attendance، compliance، employee_relations، hr_requests، payroll. …
```

All five reported at once, bilingually, naming the registry path. Nothing was ingested.

---

## (f) Declared partial onboarding — undeclared tables empty, never sample-filled

`declared: [employees]`, with a synthetic 3-row `data/raw/employees.csv`:

```
[real] declared domains: ['employees']
[real] employees: ingesting from data/raw/employees.csv (contract-validated).
[real] attendance:         not declared; empty table written (no sample fallback).
[real] compliance:         not declared; empty table written (no sample fallback).
[real] employee_relations: not declared; empty table written (no sample fallback).
[real] hr_requests:        not declared; empty table written (no sample fallback).
[real] payroll:            not declared; empty table written (no sample fallback).
Declared-domain guard passed. Row counts: {'attendance': 0, 'compliance': 0,
  'employee_relations': 0, 'employees': 3, 'hr_requests': 0, 'payroll': 0}
dbt run 157/157 · dbt test 11/11 · reconciliation PASSED · exit 0
```

Warehouse contents:

```
table                    rows  verdict
employees                   3  REAL client rows (sample would be 21)
payroll                     0  EMPTY - no sample fallback
attendance                  0  EMPTY - no sample fallback
compliance                  0  EMPTY - no sample fallback
hr_requests                 0  EMPTY - no sample fallback
employee_relations          0  EMPTY - no sample fallback

NO FABRICATED ROWS PRESENT: True
```

Dashboard, before and after:

```
before P0-1 : (19, 446175.0, 50.0)   <- 19 and 50.0 FABRICATED from sample
after       : (3,  0.0,     100.0)   <- 3 real employees, all synthetic-Saudi
```

The fabricated headcount and Saudization are gone. **`payroll_cost = 0.0` remains a claim** — see the finding in (d): step 6 must render it as *not provided*, not as zero.

All synthetic files were removed afterwards and demo rebuilt. No real client data was accessed or generated; nothing was written outside gitignored paths.

---

## (g) Demo byte-identity

Full pipeline from an empty warehouse, committed defaults:

```
dbt run  -> Done. PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157
dbt test -> Done. PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11
Validation complete. Generated 15 issues
Command Center integration reconciliation checks PASSED.

values: (19, 446175.0, 50.0) | exceptions 667 | DQ 15
DEMO IDENTICAL: True
```

No `[real]` lines and no guard output in demo — the guard is real-mode only by construction, since in demo nothing is declared and everything is sample-populated, which would trip arm 4 on every run.

---

## Carried forward

| Item | Target |
|---|---|
| **`absence_days = 494` and other confident zeros for undeclared domains** | **Step 6 — reclassified as safety, not polish (see (d))** |
| Format rule for `payroll_period` / `compliance.period` | Step 3 |
| Staging resource, validate, commit-to-`raw`, block uploads in demo | Step 4 |
| Retire the `.uploaded` freeze | Step 5 (must not precede step 4) |
| Per-domain provenance + empty states; gate the 15 uncontracted tables | Step 6 |

One correction to the plan text itself: §0.3's stated rationale ("the mart is zero-row") should be replaced with the measured behaviour ("the mart emits one COALESCE'd row; the guard is what makes that safe"). The ruling it supports is unaffected. Not edited this cycle, since the plan is a merged artefact and the correction belongs with the reader's attention here.

---

**Not merged. Awaiting review.**
