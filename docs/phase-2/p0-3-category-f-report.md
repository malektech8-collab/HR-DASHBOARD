# P0-3 Category F — Period-Level Fabrication (Execution Report)

**Branch:** `phase-2/p0-3-category-f` off `main` @ `7d60d7d` (2b merged) · **Date:** 2026-08-11
**Status:** executed, committed, pushed, PR open. **Not merged.**
**Plan:** [`p0-3-category-f-plan.md`](p0-3-category-f-plan.md) (approved; ruling 2 amended at approval) · **Prior:** [`p0-3-step-2b-report.md`](p0-3-step-2b-report.md)

`base_expected_attendance` was the one member that passed every gate the system has — declared, populated, covering the period, guard green, dbt green, 2b suppression satisfied — and still fabricated an absence for every working day the client had not reported on.

---

## 1. The proof, end to end

19 employees, attendance uploaded for the first working week of August 2026 only, declared as covering `2026-08-01..2026-08-07`. Same fixture through three pipelines.

| | BEFORE | AFTER | AFTER, one real absence |
|---|---:|---:|---:|
| expected-attendance rows | 513 | 513 | 513 |
| — covered / not reported | 513 / 0 | **114 / 399** | 114 / 399 |
| **rows claiming an absence** | **399** | **0** | **1** |
| `absence_days` KPI | 399.0 | 0.0 | **1.0** |
| `Missing Workday Attendance` | 399 | 0 | **1** |
| `attendance_compliance_pct` | 22.2% | 100% | **99.1%** |
| total active exceptions | 725 | 326 | 327 |

**399 fabricated absences → 0.** Each one of those told a client their staff did not come in, when the truth was that we had not been sent that week — and in KSA an absence record feeds Article 80 dismissal grounds and payroll deduction.

**The third column is the one that matters most.** `EMP001`'s row for `2026-08-04` — a **covered** working day — was withheld, and the system reports exactly one absence, one exception, and compliance of 99.1%. **This change does not weaken absence detection.** It confines the inference to the window the client vouched for, which is what makes the inference valid rather than what removes it.

The row count never moves: 513 before and after. NULL is not the same as no row.

---

## 2. `absence_days` outside declared coverage is NULL

Not `1.0` — the fabricated absence. Not `0.0` either, and `0.0` is worse in three ways: it is **silent** where a fabricated absence at least raises an exception someone may question; it pushes `attendance_compliance_pct` toward 100% **exactly when the data is thinnest**; and it converts a coverage problem into a compliance claim.

`NULL` says "not measured", and SQL aggregate semantics then behave correctly with no special cases.

The row stays, carrying `coverage_status`, so the gap is **countable**: `114 / 399` above is the whole story in one pair of numbers, and it is available to the UI. Narrowing the calendar instead would have shown a shorter month with no indication anything was missing.

| Working day | In coverage | Row | `absence_days` | `coverage_status` |
|---|---|---|---|---|
| yes | yes | present | the row's value | `covered` |
| yes | yes | **missing** | **1.0 — a real absence** | `covered` |
| yes | **no** | — | **NULL** | `not_reported` |

---

## 3. The flow

```
upload declares coverage
  -> declared_domains.yml v2   coverage: {attendance: {start, end}}
                               history:  {employees: {since}}
  -> domain_provenance         + coverage_start, coverage_end, history_since
  -> dbt vars                  attendance_coverage_start / _end,
                               employees_history_since
  -> base_expected_attendance
```

Coverage is **required for date-grained domains and optional for period-grained ones**, from a list (`onboarding.DATE_GRAINED`) rather than a heuristic. `attendance` is the only date-grained domain today; `payroll` and `compliance` carry one label per month, which the 2a.5 membership gate already checks.

Undeclared coverage — and always in demo — resolves to the whole reporting period, which is the pre-Category-F behaviour and is what keeps the demo gate byte-identical.

**The 2a.5 pin caught the new vars, as predicted.** All three are date-shaped, so `test_no_date_shaped_var_reaches_a_model_as_a_repo_literal` required them in both `dbt_project.yml` and `dbt_vars`. It now reports 15 date-shaped vars, 14 consumed, **14 overridden, 0 pinned** — the guardrail working on work written after it, not weakened to accommodate it.

---

## 4. The three loud failures

```
--- attendance declared with no coverage
  Declared domain(s) with no coverage period: ['attendance'].
  A date-grained domain must state which days it covers, because a working day
  with no row is otherwise read as an absence. Add to …/declared_domains.yml:
    coverage:
      attendance:
        start: YYYY-MM-DD
        end: YYYY-MM-DD

--- attendance rows outside the declared window
  attendance: 3 row(s) fall outside the declared coverage window
  2026-08-01..2026-08-03. Dates: 2026-08-04, 2026-08-05, 2026-08-06.
  Either widen coverage.attendance or remove those rows. The window is not
  widened automatically: it is the declaration that makes a missing day mean
  'absent' rather than 'not sent yet'.

--- history declared deeper than the file
  History depth for 'employees' is declared as 2010-01-01, but the earliest
  record in the file is 2015-01-01. The file cannot speak to the period claimed.
  Either upload history back to 2010-01-01, or set history.employees.since to
  2015-01-01 or later.
```

All bilingual. The second is the symmetric arm of the first: if the declaration and the file disagree, one of them is wrong and neither may be guessed at — widening the window silently would restore the very inference the declaration exists to constrain.

---

## 5. Ruling 2, as amended

History depth is now **required input**, and the practitioner has confirmed the employee master does contain leavers, so the declaration is a statement about how far back that history reaches rather than about whether it exists.

- A trend month ending before the declared depth is **NULL**, never a derived-but-understated figure.
- Real mode with nothing declared resolves the depth to the reporting-period start, so every historical month is NULL until a depth is declared. Silence defaults to honesty.
- Declared deeper than the file can support fails loudly (§4).

Demo resolves to `1900-01-01`, so demo shows its history and the gate holds.

`mart_exec_trends` lost its `COALESCE(pm.payroll_cost, 0.0)` — ruling 1. A month with no payroll is a gap in the line, not a chart saying the client paid nobody. A test asserts the COALESCE has not come back, because "fixing a null" is exactly how it would.

---

## 6. The downstream six — and a plan correction

Both defects the architect named were confirmed and fixed in `mart_attendance_kpis`:

```sql
-- was:  COALESCE(SUM(absence_days), 0.0)      -> a fabricated 0 replacing a fabricated 513
-- now:  SUM(absence_days)

-- was:  CAST(COUNT(*) AS DOUBLE)              -> unreported days inflate compliance
-- now:  CAST(COUNT(absence_days) AS DOUBLE)

-- and:  WHEN COUNT(*) = 0 THEN 1.0            -> "100% compliant" over nothing
-- now:  WHEN COUNT(absence_days) = 0 THEN NULL
```

That third one was not in the plan. It is the same fabricated-favourable value in a different place, found while making the first two changes.

**The plan was wrong about `mart_attendance_by_department` / `_by_project`.** It said they were "aggregates only; NULL-skipping is correct as written — check, do not change". The check proved otherwise: both carry the identical `COUNT(*)` denominator and `COALESCE(SUM(absence_days), 0.0)`. Both fixed. Recording it because the plan told me to check and the check is what found it.

`mart_attendance_exceptions`: **7 branches read the calendar, 7 are now confined to covered days** — driven from a query over the model source, not hand-listed, and asserted by a test. `Missing Workday Attendance` is the 399/494/513 generator.

**A bug I introduced and caught in the same pass:** one branch reads `WHERE (A) OR (B)`. Prefixing `coverage_status = 'covered' AND` binds tighter than `OR`, so the guard would have applied to the first arm only. Parenthesised, with a comment saying why.

`mart_attendance_late_arrival` / `_missing_punches` are unchanged and that is deliberate: they total observed lateness and punches, which are NULL on any day without a row regardless of coverage, so an uncovered day contributes nothing either way.

---

## 7. Nullable metrics through the stack

A metric can now be genuinely **unmeasurable** — the domain was provided, just not for the days it needs. That is distinct from 2b's suppression, where the domain is absent, so it is rendered differently: the card stays, showing an em dash, because the label is still true and the reader should see the measure exists and has no answer yet.

`KPIItem.value` is `Optional[float]`; the attendance API no longer multiplies a possibly-null rate by 100; `attendance_compliance_pct` and `absence_days` are nullable on the breakdown items; `headcount_trend` and the exec chart series are `(number | null)[]`. `LineChartCard` / `BarChartCard` accept null points, which ECharts renders as a **gap** — a line that stops, never one that dives to zero.

---

## 8. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 157/157, 11/11, PASSED |
| Demo API byte-identity | all 78 endpoints identical to the pre-2b baseline; only `/openapi.json` differs |
| Covered day, no row | **still an absence** — 1 absence, 1 exception, 99.1% compliance |
| Uncovered working day | `absence_days` **NULL**, row retained as `not_reported` |
| Mid-month upload | fabricated absences **399 → 0** |
| Compliance denominator | measured days; `1 - 5/6`, not `1 - 5/27` |
| Date-shaped dbt vars pinned | **0 of 14 consumed** (was 0; 3 new vars added and overridden) |
| `tsc -b` / `npm run build` | 0 errors / passes |
| pytest | **167 passed** (144 + 23 new) |

---

## 9. Open

1. **The coverage surface is written but not yet rendered.** `coverage_status` and the `domain_provenance` columns exist; the `partial_coverage` sibling-block reason and the "10 of 26 working days reported" note are not wired into the API. The numbers are honest without it; the client cannot yet see *why* the month looks thin. Recommend it as the next small piece.
2. **Coverage granularity** — one window per domain. A client uploading two non-contiguous weeks needs a list. Plan §open-2 recommended modelling it as a list from the start; I did not, to keep this cycle to the blocker. It is a registry-shape migration if deferred much longer.
3. **`data_quality_score` and `total_active_exceptions`** still count across all domains (step 4).
4. **`mart_wps_status`** — unchanged, still failing loudly on purpose.

---

**Not merged. Awaiting review.**
