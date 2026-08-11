# P0-3 Category F — Period-Level Fabrication (PLAN ONLY)

**Branch:** `phase-2/p0-3-category-f` off `main` @ `7d60d7d` (2b merged) · **Date:** 2026-08-11
**Status:** plan only. Nothing implemented.
**Builds on:** the three rulings recorded in `5505304` ([plan §F](p0-3-mart-fabrication-plan.md)) · **Prior:** [`p0-3-step-2b-report.md`](p0-3-step-2b-report.md)

Step 2b answers *"was this domain provided?"*. Category F asks *"was it provided **for this period**?"* — a question nothing in the current design can hold an answer to.

---

## 0. Priority, and why it is not the trend charts

`base_expected_attendance` goes first, alone if necessary.

It is the only member that **passes every gate the system has**: attendance declared, populated, silver correct, covering the reporting period, declared-domain guard green, 2a.5 period-coverage gate green, dbt 157/157, step-2b suppression satisfied — and it still fabricates an absence for every working day the client has not reported on. Measured in 2b, 2 employees over July 2026 with a 2-row attendance file:

```
attendance rows uploaded : 2      (both valid, both inside the period)
expected-attendance rows : 52     (26 working days × 2 employees)
marked absent            : 51
```

A mid-month upload is ordinary onboarding, not misuse.

**The grounds are not chart quality.** In KSA an absence record feeds Article 80 dismissal grounds and payroll deduction. A client acting on 51 phantom absences is a harm vector. `mart_exec_trends` produces a misleading chart; this produces a record that can be cited in a termination file.

Sequence within the step:

| | Work | Why here |
|---|---|---|
| **1** | `base_expected_attendance` + declared coverage plumbing | Phase 2 blocker; must land before any real attendance data is loaded |
| 2 | `mart_exec_trends`, `mart_workforce_headcount_trend` | rulings 1 & 2; misleading, not harmful |
| 3 | Nullable series points through schema → API → charts | shared by 1 and 2 |

Step 1 is independently shippable. If the cycle is cut short, it is the part that ships.

---

# Part 1 — `base_expected_attendance`

## 1.1 The inversion at the centre of the design

Today the model reads a missing attendance row as an absence. That inference is **correct inside declared coverage and meaningless outside it**:

> Within a period the client says they have reported, a missing row means the employee did not come in. Outside it, a missing row means *we have not been sent that week*.

The model cannot currently tell those apart, so it calls both an absence. Declared coverage is the fact that makes the inference valid — and it is exactly what ruling 3 says must be **declared, never inferred from `MIN`/`MAX(attendance_date)`**. Inference would silently drop the uncovered half instead of flagging it, which is the `.uploaded`-marker failure in a third costume.

## 1.2 What `absence_days` must be outside declared coverage

**`NULL`.** Not `1.0`, not `0.0`, and not a sentinel.

**`1.0` asserts the employee was absent.** That is the fabrication, and the one with legal consequence.

**`0.0` asserts the employee was present**, and is worse than `1.0` in three specific ways:

1. **It is silent.** A fabricated absence at least surfaces as a `Missing Workday Attendance` exception that somebody may question. A fabricated *presence* produces nothing to look at.
2. **It flatters the number precisely when the data is thinnest.** `attendance_compliance_pct` counts days with a problem over all expected days; zero-filling unreported days pushes compliance toward 100%. The dashboard would look best when it knows least.
3. **It converts a coverage problem into a compliance claim** — the opposite of what the client needs, which is to know what is still missing.

**`NULL` says "not measured"**, which is the true statement, and SQL aggregate semantics then do the right thing without a single special case: `SUM` skips it, `COUNT(absence_days)` counts only measured days, `AVG` divides by measured days. The compliance percentage stops meaning *"of every working day in the month"* and starts meaning *"of the days you reported"* — which is the only honest reading of a partial upload.

A sentinel (`-1`) is rejected outright: sentinels get summed.

**NULL is not the same as no row.** The row must still be generated, carrying `coverage_status = 'not_reported'`. If we simply narrowed the calendar to the declared window, the client would see a shorter month with no indication that anything was missing — the gap has to be countable ("10 of 26 working days reported") and renderable, not invisible.

### The full semantic

| Working day | Inside declared coverage | Attendance row | `absence_days` | `coverage_status` |
|---|---|---|---|---|
| yes | yes | present | the row's value (`0.0` or its own) | `covered` |
| yes | yes | **missing** | **`1.0` — a real absence** | `covered` |
| yes | **no** | — | **`NULL`** | `not_reported` |
| weekend | — | — | row not generated (unchanged) | — |

Row 2 is the point of the whole exercise: this design does **not** weaken absence detection. It makes it valid, by confining it to the window the client vouched for.

## 1.3 The flow — upload → registry → provenance → calendar

**(a) Upload declares its coverage.** `scripts/onboarding.declare()` gains `coverage_start` / `coverage_end`, and the upload commit step passes them. The operator states the window; nothing reads it off the data.

**(b) The registry carries it**, on the substrate that already exists — `data/onboarding/declared_domains.yml`, bumped to v2:

```yaml
version: 2
declared:
  - employees
  - attendance
coverage:
  attendance:
    start: 2026-08-01
    end: 2026-08-14
```

A v1 file (a bare `declared:` list) still loads — the loader is already tolerant, and there is no value in breaking it.

**Grain decides whether coverage is required.** `payroll` and `compliance` are *period-grained*: one label per month, and the 2a.5 membership gate already establishes that the label is present. `attendance` is *date-grained*, so a period label says nothing about which days arrived. Coverage is therefore **required for date-grained domains and optional for the rest** — a list in `onboarding.py`, not a heuristic. Attendance is the only date-grained domain today.

**(c) Two loud failures at ingest**, both per ruling 3:

- **Declared, date-grained, no coverage** → abort, naming the domain and the shape of the missing declaration. This is the ruling's *declared-but-not-covered fails loudly*.
- **Rows outside the declared window** → validation error naming both, because either the declaration or the file is wrong and neither may be guessed at. This is the symmetric arm, and it reuses `report_period.assert_period_is_covered`'s error shape.

Coverage that does not overlap the reporting period already errors — that is the 2a.5 gate, unchanged.

**(d) `domain_provenance` carries it to the API.** Two columns — `coverage_start`, `coverage_end` — written by the same `_write_domain_provenance` that 2b added. Null in demo, and null for period-grained domains, which means "the whole reporting period".

**(e) `build_warehouse` passes it to dbt** as `attendance_coverage_start` / `attendance_coverage_end`.

> These are **date-shaped vars**, so `test_no_date_shaped_var_reaches_a_model_as_a_repo_literal` (2a.5) will fail the build unless they are declared in `dbt_project.yml` *and* overridden in `dbt_vars`. That is the generalised pin catching work written after it — exactly what it was built for. The demo defaults are the sample's June window, and demo declares no coverage, so it resolves to the full reporting period and the gate stays byte-identical.

**(f) The model.** `base_expected_attendance` keeps its calendar and its CROSS JOIN — the row still exists for every working day — and changes what it says about days it cannot speak to:

```sql
CASE
    WHEN c.calendar_date < DATE '{{ var('attendance_coverage_start') }}'
      OR c.calendar_date > DATE '{{ var('attendance_coverage_end') }}'
        THEN NULL                                   -- not reported
    WHEN att.employee_id IS NULL THEN 1.0           -- a real absence
    ELSE COALESCE(att.absence_days, 0.0)
END AS absence_days,
CASE
    WHEN c.calendar_date BETWEEN DATE '{{ var('attendance_coverage_start') }}'
                             AND DATE '{{ var('attendance_coverage_end') }}'
        THEN 'covered' ELSE 'not_reported'
END AS coverage_status
```

Every other measure on the row — `calculated_late_minutes`, `missing_punch_count`, `overtime_hours` — takes the same treatment. They are all "we did not observe this", not "it was zero".

## 1.4 Downstream, where the work actually is

Six models read `base_expected_attendance`. Three need real changes; the rest inherit NULL-skipping for free.

**`mart_attendance_kpis`** — two edits, one of them subtle:

- `SUM(absence_days)` already skips NULL. But the surrounding `COALESCE(..., 0.0)` turns an all-unreported month into `0.0`, which is a fabricated *zero* replacing a fabricated 513. **Drop the COALESCE**; the metric is NULL when nothing was reported, and step 2b's suppression machinery already knows how to render that.
- `attendance_compliance_pct` divides by `COUNT(*)`. It must divide by `COUNT(absence_days)` — measured days only — or the unreported days silently inflate it. This is finding (2) of §1.2 made concrete.

**`mart_attendance_exceptions`** — 15 exception types, all of which must be confined to covered days. Two matter most:

- `Missing Workday Attendance` (`WHERE attendance_date IS NULL`) is the 494/513 generator. It becomes `WHERE attendance_date IS NULL AND coverage_status = 'covered'`.
- `Both Punches Missing` (`WHERE ... AND absence_days = 0`) already excludes NULL by SQL three-valued logic, but should carry the explicit predicate so the intent survives the next edit.

**`mart_attendance_by_department` / `_by_project`** — aggregates only; NULL-skipping is correct as written. They must be *checked*, not changed, and the check belongs in the report rather than in a comment nobody reads.

**A new coverage surface.** `coverage_status` makes the gap countable, so the API can say what it currently cannot:

```
attendance: 10 of 26 working days reported (2026-08-01 .. 2026-08-14)
```

This is a new sibling-block reason, `partial_coverage`, distinct from `not_provided`: the domain *was* provided, and part of it is real. Step 2b's `Provenance` already carries the block and the bilingual message machinery; this adds a reason code and a coverage read from `domain_provenance`.

## 1.5 Tests

| Test | Pins |
|---|---|
| mid-month upload | 2 employees, 2 rows, declared coverage 2 days → 4 covered rows, 48 `not_reported`, `absence_days` NULL outside, **`Missing Workday Attendance` count 0** |
| absence detection still works | a covered working day with no row → `absence_days = 1.0` and one exception. This is the test that stops the fix becoming a suppression of real signal |
| compliance denominator | `attendance_compliance_pct` computed over measured days only |
| declared-but-not-covered | attendance declared without coverage → abort, message names the domain |
| rows outside coverage | validation error naming both windows |
| the 2a.5 pin | the two new vars appear in the pin's output as `ok`, not `PINNED` |
| demo | coverage absent → full reporting period → byte-identical |

---

# Part 2 — the trend marts

Rulings 1 and 2 are settled; this is their application.

**`mart_exec_trends`.** Drop `COALESCE(pm.payroll_cost, 0.0)` — the LEFT JOIN's misses become NULL, which is ruling 1: three points, with nulls. The headcount axis takes ruling 2: derivation is legitimate, but a trend month ending before `MIN(joining_date)` emits **NULL, not 0**.

**`mart_workforce_headcount_trend`.** The same headcount rule. No join, nothing else to change.

Both are byte-identical on demo: payroll covers 2026-04/05/06 so every point joins, and the earliest joining date is well before the window.

**Part 3 — the plumbing they share.** `PayrollTrendItem.payroll_cost`, the exec chart arrays and the headcount series become nullable through the Pydantic models, the TypeScript types and the chart components. ECharts renders `null` as a gap, which is the correct picture: a line that stops rather than a line that dives to zero.

---

## Gate

Unchanged, plus the API surface 2b established:

```
demo byte-identical : 19 / 446175.0 / 50.0 / 667 / 15, dbt 157/157, 11/11, PASSED
demo API            : identical across all 78 endpoints
```

Demo declares no coverage, so every new code path resolves to "the whole reporting period" and demo cannot move. If it moves, the design is wrong.

---

## Risks

1. **This is the first change that weakens a number people already trust.** `absence_days` will fall on real data, and it should — but the drop must be attributable, which is why `coverage_status` and the coverage note are in Part 1 rather than deferred.
2. **15 exception types, one predicate each.** Mechanical, and mechanical at that scale is where one gets missed. Drive it from a query over the model source rather than by hand, and report the count — the same discipline as the 2a.5 var sweep.
3. **`COALESCE` removal is load-bearing and easy to re-add.** A future contributor "fixing a null" restores the fabricated zero. A test asserting the metric is NULL on an unreported month is the guard.

---

## Open questions

1. **Leaver completeness in the headcount derivation.** Ruling 2 makes point-in-time headcount legitimate because it reads client-provided `joining_date`/`termination_date`. That holds only if the employee master contains **leavers**. A common HRIS export contains active staff only, and against such a file the derivation silently understates every past month — a fabrication ruling 2 does not cover, because the data looks present. `MIN(joining_date)` does not detect it. **Recommend** an `as_of` / history-depth declaration for `employees` on the same coverage substrate — it is the same mechanism, one domain over. Flagging rather than assuming, because it changes ruling 2's scope.
2. **Coverage granularity.** One window per domain per upload, or a set of windows? A client uploading two non-contiguous weeks is plausible. A single window is simpler and covers the ordinary case; a list of windows is a small generalisation now and an awkward migration later. **Recommend** modelling it as a list from the start with the single-window case as its degenerate form.
3. **Should `attendance_compliance_pct` be suppressed entirely below a coverage threshold?** "97% compliant, over 2 of 26 days" is honest and still misleading at a glance. **Recommend** rendering the coverage alongside it rather than suppressing — a suppressed metric teaches the client nothing about what would unsuppress it — but this is a product call.

---

**Prepared for chief-architect review. No implementation performed.**
