# P0-3 Step 2a.5 — Anchor Convergence (Execution Report)

**Branch:** `phase-2/p0-3-anchor-convergence` off `main` @ `959d9fb` (2a merged) · **Date:** 2026-08-10, extended 2026-08-11 (twice)
**Status:** executed, committed, pushed. **Not merged.**
**Scope:** dbt models, registry and tests — **plus, in the extensions, the report-month resolver** (§11) and **the dbt var surface it turned out to be only half of** (§13). The original "no application code" guardrail could not hold once the fix was the resolution policy itself; the API resolver change in §11.5 went beyond the stated scope and is called out there rather than buried. Step 2b not started.

> **Review outcomes, 2026-08-11.** Two rounds, same failure class each time.
>
> **Round 1** accepted the convergence and blocked the merge: with payroll *and* compliance absent, `var('report_month')` resolved to `settings.DEFAULT_REPORT_MONTH`, a literal in this repository. §11 closes it. §4.1 corrects the `0 → 2` proof, which was itself computed against that constant.
>
> **Round 2** accepted §11 and blocked again: `start_date_str` / `end_date_str` were never passed in `dbt_vars` at all, so the **attendance window** stayed pinned to the June literals no matter what period the resolver produced — and unlike the payroll case, **no operator override was needed to trigger it**. §13 closes that, generalises the pin so the next one is caught mechanically, and reports what the generalised pin found: **not two vars, six.**

---

## 1. Step 2a merged

```
mergeCommit: 959d9fb9fa1f3cc0be063b85914dacc87257fded
mergedAt:    2026-08-10T13:43:04Z
```

Green on all three gates (run 31393974559).

---

## 2. Convergence — 7 models, 9 sites, 1 deliberate exclusion

Every converged site now matches `base_document_expiry`'s existing idiom exactly:

```sql
last_day(CAST('{{ var('report_month') }}-01' AS DATE))
```

| Model | Site | Was |
|---|---|---|
| `base_payroll_current` | current-period filter | `= (SELECT MAX(payroll_period) …)` |
| `base_payroll_previous` | previous-period filter | `strftime(CAST(MAX(payroll_period)…) - 1 MONTH)` |
| `mart_payroll_exceptions` | anchor `month_start` / `month_end` | `CAST(MAX(payroll_period)…)` |
| `mart_payroll_exceptions` | current-period filter | `= (SELECT MAX(payroll_period) …)` |
| `mart_workforce_contract_expiry` | `anchor_date` | `last_day(CAST(MAX(payroll_period)…))` |
| `mart_workforce_exceptions` | `anchor_date` | same |
| `mart_workforce_exceptions` | current-period filter | `= (SELECT MAX(payroll_period) …)` |
| `mart_workforce_iqama_expiry` | `anchor_date` | same |
| `mart_workforce_kpis` | `anchor_date` | same |

### The eighth is not an anchor — excluded, with reasoning

`base_command_center_data_freshness` keeps its `MAX(payroll_period)`. There it is **the metric itself**: one of seven parallel per-module `max_source_date` measurements that tell the user how fresh each source is. Converging it would replace a measurement with a constant and destroy the feature.

The ruling said "all 8". Seven were anchors; the eighth was a measurement wearing the same syntax. A test pins the exemption, and a second test fails if `data_freshness` ever stops needing it — so the carve-out cannot quietly go stale.

### Why convergence is safe

`report_month` is itself derived as `MAX(payroll_period)`, falling back to `MAX(period)` from compliance, then `DEFAULT_REPORT_MONTH` (`scripts/build_warehouse.py`). So on demo the two idioms are the *same value by construction*, and when payroll is absent the var still resolves while the raw `MAX` goes `NULL`. That is exactly the divergence, and exactly why the fix is convergence on the existing var rather than a new mechanism.

> **Written before review, and incomplete as written.** "The var still resolves" was the whole problem: with payroll *and* compliance absent it resolved to a repo constant. The sentence describes the mechanism correctly and stops one link too early. §11 is the correction.

---

## 3. Demo byte-identity — the gate

```
dbt run  -> Done. PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157
dbt test -> Done. PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11
Command Center integration reconciliation checks PASSED.

headline: (19, 446175.0, 50.0) | exceptions 667 | DQ 15
BYTE-IDENTICAL: True
```

Per-mart spot checks on the seven converged models — `payroll_kpis` (446175.0 / 20), `payroll_exceptions` 15 rows, `workforce_exceptions` 25 rows, `contract_expiry` / `iqama_expiry` 1 row each — all unchanged. `data_freshness` still reports `2026-06` for payroll, confirming the exclusion left the measurement intact.

---

## 4. The before/after proof — and a correction to my own step-2a evidence

**My step-2a framing overstated the evidence, and I need to say so plainly.**

I cited `probation_count = 0` at `declared: [employees]` as a fabricated zero. It is not, on that data: no sample employee joined within 90 days of 2026-06-30, so **0 is the correct answer either way**. The observation was coincidental and proved nothing.

```
anchor (report_month end) : 2026-06-30
probation window starts   : 2026-04-01
employees joining in window: NONE      (max joining_date in sample = 2025-04-01)
```

The *mechanism* is real — a `NULL` anchor makes every window comparison `NULL` — but demonstrating it requires data with a non-zero answer. Synthetic employees, two inside both windows, at `declared: [employees]` with payroll absent:

```
########## BEFORE — anchor from MAX(payroll_period) ##########
  payroll rows        : 0        (undeclared -> empty)
  anchor via MAX()    : None
  employees rows      : 3
  probation_count     : 0        <- WRONG
  contract_expiring_30: 0        <- WRONG

########## AFTER — anchor from var('report_month') ##########
  payroll rows        : 0        (still empty)
  employees rows      : 3
  probation_count     : 2        <- 2 employees joined within 90 days
  contract_expiring_30: 2        <- 2 contracts expiring within 30 days
```

`0 → 2` on a **declared** domain with payroll still absent. That is the finding demonstrated properly.

Incidentally the fixture's first version used a `2030-01-01` contract end and was rejected by the 1b-i DATE range rule (`outside 1940-01-01 to 2028-08-10`) — the validator doing its job on my own test data.

### 4.1 A second correction: the `2` was the repo's answer, not the client's

**Added 2026-08-11, after review.** The run above resolved `report_month` to `2026-06`. With payroll absent and compliance absent, that did not come from the synthetic data — it came from `settings.DEFAULT_REPORT_MONTH` in `config.py`. So the anchor was `2026-06-30`, and the `2` is what those three employees look like *against a period this repository chose*.

The same fixture, same code, with the period stated explicitly:

```
REPORT_MONTH=2026-06  (the old repo constant) -> probation_count 2, contract_expiring_30 2
REPORT_MONTH=2026-08  (the actual month)      -> probation_count 0, contract_expiring_30 0
```

Two versus zero, from nothing but the period. It is August 2026, so `0` is the answer a client would have been owed and `2` is what the dashboard would have shown them.

Both statements in §4 stand: the NULL anchor was a real bug, and convergence is the right fix. What does not stand is treating the post-fix number as correct. `0 → 2` is more precisely **`0` (broken) → `2` (stale constant) → an answer only the operator can supply**, which is why this cycle could not merge without §11.

I have now had to correct the evidence in this section twice — first for citing a coincidental zero in step 2a, now for citing a constant-anchored two. Both times the mechanism was real and the number was not load-bearing in the way I claimed. The pattern is mine to fix: I was reading numbers that moved in the expected direction as confirmation, without asking what fixed the *other* variable.

---

## 5. Registry reversions

The payroll terms those metrics briefly carried were artefacts of the old idiom, not real dependencies:

| Entry | 2a | 2a.5 | Reason |
|---|---|---|---|
| `mart_workforce_kpis.probation_count` | `[employees, payroll]` | **`[employees]`** | payroll term was the anchor |
| `mart_workforce_kpis.contract_expiring_30` | `[employees, payroll]` | **`[employees]`** | same |
| `mart_workforce_kpis.iqama_expiring_30` | `[employees, compliance, payroll]` | **`[employees, compliance]`** | payroll reverted; **compliance is real** — it LEFT JOINs `stg_compliance` for `iqama_expiry` |
| `mart_workforce_contract_expiry` (payload) | `[employees, payroll]` | **`[employees]`** | anchor |
| `mart_workforce_iqama_expiry` (payload) | `[compliance, employees, payroll]` | **`[compliance, employees]`** | anchor |

`mart_workforce_exceptions` keeps `[compliance, employees, payroll]`: it genuinely reads payroll rows to flag pay for inactive employees, so that dependency survives the convergence.

The registry header records the resolution and the data-freshness carve-out.

---

## 6. `mart_data_quality_exceptions` — filter requirement encoded

Per ruling, "scope" now explicitly means **filter**:

```yaml
    scope_to_provided: true
    scope_filter: source_table   # rows are filtered by this column
```

with the reasoning inline — unfiltered, this surface becomes the route the entire fabricated exception set takes to the client (attendance 494, compliance 135, payroll 19 at `declared: [employees]`, against a demo baseline of 667), on the screen they read most closely during onboarding. Implementation is step 4.

---

## 7. Mode-aware Pydantic count

```
previous flat count (2a)                     : 180

OPTIONAL CONTAINERS needed (payload mode)    :  77
OPTIONAL SCALARS needed (column mode)        :  33
                                               ---
TOTAL FIELDS TO MAKE OPTIONAL                : 110

scalars INSIDE item models (no change needed): 147
```

Containers by file: `command_center` 13, `talent` 13, `recruitment` 11, `er` 9, `attendance` 8, `compliance` 8, `payroll` 8, `workforce` 5, `kpi` 2.

**110, not 180.** The expectation was ~66 containers; the measurement is 77, plus 33 scalars that sit on column-mode responses (including scalars alongside a list, such as a total beside its breakdown — those still need `Optional`). 147 item-model scalars need no change at all, because under payload mode the container goes `null` and they never surface.

On the split question: **2b does not look like it needs splitting.** 110 mechanical annotation changes across 9 files, with the suppression dependency itself being the only real logic, is a single cycle.

---

## 8. `mart_wps_status` diagnosis — report only, not fixed

**Verdict: lost in the dbt migration.** Not deleted deliberately, not renamed at the API layer, never re-created.

Evidence:

- The API reference dates from the initial baseline (`70af5ae`) — `GET /api/compliance/wps` has always queried `mart_wps_status`.
- In the pre-dbt era the view was created in `scripts/build_warehouse.py` as raw SQL (`print("Created view 'mart_wps_status'")` at line 1807 of `7b86cc8^`).
- Commit **`7b86cc8`** — *"Integrate dbt-duckdb and decouple raw SQL out of FastAPI layer"* — removed 4,300 lines from `build_warehouse.py` and **did not port `mart_wps_status` to a dbt model**. No file matching `*wps*` has ever existed under `dbt_analytics/models/`.
- The same commit also removed the reconciliation assertion that would have caught it:
  ```
  - wps_dist_sum = conn.execute("SELECT SUM(headcount) FROM mart_wps_status")…
  -     raise ValueError("CRITICAL: WPS distribution sum … does not match Active Headcount")
  ```
  The guard and the thing it guarded were deleted together, so nothing failed.
- The data survives under a different name and shape: `base_government_status.sql` exposes `mudad_status AS wps_status`. The endpoint was never repointed.

So the endpoint has returned 500 on every call since `7b86cc8`. Per ruling this is a separate hotfix branch; the fix is most likely a small `mart_wps_status` model over `base_government_status`, restoring the deleted reconciliation assertion alongside it.

**The wider audit this prompted is [`reconciliation-audit-7b86cc8.md`](reconciliation-audit-7b86cc8.md)** — see §12 for the headline.

---

## 9. Verification

| Check | Result |
|---|---|
| Anchor sites converged | 9 across 7 models |
| `MAX(payroll_period)` remaining | 1, in `data_freshness`, exempt and tested |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 157/157, 11/11, PASSED |
| `declared:[employees]` proof | `probation_count` 0 → **2**, `contract_expiring_30` 0 → **2** |
| Registry reversions | 5 entries |
| DQ filter requirement | encoded (`scope_filter: source_table`) |
| Mode-aware Pydantic | **110** (77 containers + 33 scalars) |
| Real mode fails closed on `report_month` | **yes** — §11, proven by an aborted run |
| Operator `REPORT_MONTH` honoured in both modes | **yes** — §11 |
| Operator/payroll period mismatch | **validation error at ingest**, naming both — §11 |
| `DEFAULT_REPORT_MONTH` reachable in real mode | **no** — swept, plus a structural pin on its readers |
| Date-shaped dbt vars pinned to a repo literal | **0 of 11 consumed** — was 6; §13.2 |
| Attendance window follows the reporting period | **yes** — §13.1, identity-tested |
| Period coverage gate | payroll, compliance, attendance — §13.4 |
| Category A re-measured with vars unified | `494 = 26 × 19`, `513 = 27 × 19` — §13.3 |
| pytest | **122 passed** (76 + 46 new) |
| Application code touched | `config.py`, `api/_report_period.py` — see §11.5 |

Synthetic artefacts removed; demo rebuilt and re-verified.

---

## 10. Open

1. **`mart_wps_status`** — separate hotfix branch; diagnosis above. Restore the reconciliation assertion with the model.
2. **2b scope** — 110 fields; recommend a single cycle.
3. `mart_workforce_exceptions` retains a real payroll dependency (inactive-employee pay checks), so it will suppress when payroll is absent. Correct, but worth knowing it behaves differently from its sibling workforce marts.
4. **Restoring the 63 deleted reconciliation assertions** — §12. Should not happen before 2b settles suppression semantics; a "breakdown sums to total" assertion is false by design once a payload is suppressed.

---

# The 2026-08-11 extension

## 11. The reporting period fails closed in real mode

### 11.1 The finding, restated in one line

`var('report_month')` had a third fallback, and it was a literal in this repository.

```python
MAX(payroll_period) -> MAX(compliance.period) -> settings.DEFAULT_REPORT_MONTH  # "2026-06"
```

At `declared: [employees]` — an entirely ordinary employees-first onboarding — the first two are absent and the third answers. Convergence is what makes it reachable, so convergence has to close it:

```
before 2a.5 : NULL anchor     -> 0, wrong and it LOOKS wrong
after  2a.5 : constant anchor -> 2, wrong and it LOOKS RIGHT
```

The second is strictly worse. Category C, self-inflicted, in the cycle whose purpose was to stop fabricated numbers reaching a client.

### 11.2 The resolver

New module `scripts/report_period.py` owns the decision. `build_warehouse._derive_report_month()` now returns `None` instead of a constant when it cannot derive — it reports what the data says, it does not decide what to do about it.

Precedence, **in both modes**:

| | source | behaviour |
|---|---|---|
| 1 | operator `REPORT_MONTH` | wins outright, over derivation too |
| 2 | client data | `MAX(payroll_period)`, then compliance `MAX(period)` — unchanged, and good: it self-tracks the HR close |
| 3 | neither | **real → ABORT**, demo → `DEFAULT_REPORT_MONTH` |

A malformed `REPORT_MONTH` is an error in both modes rather than a silent fall-through — falling back on a typo is the same substitution this removes. A derived value that is not a period (a `payroll_period` column that does not hold periods) is treated as no value at all, so real mode aborts on it.

### 11.3 The abort path

Real mode, `declared: [employees]`, `REPORT_MONTH` unset. Full pipeline, not a unit test:

```
##########################################################################
# ARM A - real mode, employees only, REPORT_MONTH unset
##########################################################################
  data/raw/employees.csv: 3 synthetic rows
  declared: ['employees']

  ABORTED with ReportMonthUnresolvedError:
    Cannot determine the reporting period. No payroll or compliance data is
    present to derive it from, and REPORT_MONTH is not set.
    Set REPORT_MONTH=YYYY-MM (for example REPORT_MONTH=2026-08) in .env or the
    environment, and re-run.
    It cannot be guessed: the reporting period decides every date window on the
    dashboard - probation, contract and Iqama expiry, payroll period. Defaulting
    it would anchor a client's numbers to a period nobody chose, and the result
    would look correct.
    تعذّر تحديد فترة التقرير. لا توجد بيانات رواتب أو التزام لاشتقاقها منها،
    والإعداد REPORT_MONTH غير محدد. الرجاء ضبط REPORT_MONTH=YYYY-MM
    (مثال REPORT_MONTH=2026-08) ثم إعادة التشغيل. لا يمكن تخمين الفترة لأنها
    تحدد كل النوافذ الزمنية في لوحة المعلومات.
```

It names the setting, gives the format and an example, says **why** it cannot be guessed rather than only that it failed, and is bilingual like every other operator-facing onboarding error. The abort happens before dbt, and closes the DuckDB connection first so a failed run does not leave the file locked.

Same fixture, period supplied:

```
ARM A'  REPORT_MONTH=2026-08 -> report_month 2026-08, probation_count 0, contract_expiring_30 0
ARM A'' REPORT_MONTH=2026-06 -> report_month 2026-06, probation_count 2, contract_expiring_30 2
```

That contrast is §4.1's evidence, and it is the whole argument for aborting: the period is not a detail of the answer, it *is* the answer.

### 11.4 The mismatch this created — caught at ingest

Every converged site now filters `payroll_period = '{{ var('report_month') }}'`. Under derivation the two agree by construction. Under an operator override they need not, and then the filter matches nothing.

**What that looks like without the guard** (same run, new check disabled — a counterfactual, not a repo state):

```
Declared-domain guard passed. Row counts: {... 'payroll': 3}
dbt run 157/157 · dbt test 11/11
Command Center integration reconciliation checks PASSED.

silver payroll rows       : 3
silver payroll periods    : [('2026-06',)]
report_month              : 2026-08
base_payroll_current rows : 0
total_payroll_cost        : 0.0
employees_paid            : 0
```

Payroll declared, payroll populated, silver correct, every guard green, **payroll cost zero**. Nothing in the system disagrees with anything else, because the KPI and everything it could be checked against sit downstream of the same filter (§12 is about exactly that).

**With the guard**, it never reaches dbt:

```
##########################################################################
# ARM B - operator period 2026-08 vs a payroll file covering 2026-06
##########################################################################
  REJECTED AT INGEST with ReportMonthMismatchError:
    Reporting period mismatch. REPORT_MONTH is set to 2026-08, but the uploaded
    payroll data covers 2026-06. Every payroll figure filters on the reporting
    period, so this run would report a payroll cost of 0 against a payroll file
    that is present and valid.
    Either set REPORT_MONTH to one of 2026-06, or upload the 2026-08 payroll file.
    عدم تطابق فترة التقرير: الإعداد REPORT_MONTH محدد بـ 2026-08 بينما ملف payroll
    المرفوع يغطي 2026-06. سيؤدي ذلك إلى عرض تكلفة رواتب صفرية رغم وجود ملف رواتب صالح.
```

Both periods named, both remedies offered, and it says what the client would otherwise have seen. Agreement passes cleanly:

```
ARM B' REPORT_MONTH=2026-06, payroll covering 2026-06
       -> report_month 2026-06, total_payroll_cost 15000.0
```

Design notes: the check runs in **both** modes (an operator override is just as capable of zeroing demo), but only when a period is explicitly set — derivation cannot disagree with itself. It compares against the **set** of periods in the file, not the max, because that is precisely what the SQL filter tests. An empty payroll file is not reported as a mismatch: zero rows is the declared-domain guard's job, and naming a period the file does not contain would be a worse message.

### 11.5 The API resolver, which had the same hole — and was outside scope

`get_report_month()` fell back to `DEFAULT_REPORT_MONTH` whenever `base_command_center_report_context` was unreadable — in real mode, labelling a client's page header with a period this repo chose.

Real mode now honours an explicit `REPORT_MONTH` and otherwise returns **503** naming the setting. Demo is untouched.

**This was outside the stated "no application code" guardrail and I took it anyway.** Recording it here rather than leaving it in a diff: the alternative was shipping a resolver that fails closed in the pipeline and open in the layer the client actually reads, which is fixing the visible half. Confirmed at review as the right call.

### 11.6 Tests — 28 new, 104 total

`backend/tests/test_report_period.py`. Beyond the four required behaviours:

- **`test_default_report_month_is_unreachable_in_real_mode`** sweeps every real-mode input shape (`None`, `""`, whitespace, `"garbage"`, `"2026-13"`, `"2026"`) and asserts each aborts; then, with an operator period set, asserts the answer is the operator's for every derived value **including `DEFAULT_REPORT_MONTH` itself**.
- **`test_the_demo_default_has_exactly_three_readers`** is a structural pin. "Demo-only" is a policy, and a policy is only durable if the set of code that reads the constant cannot quietly grow. It walks `backend/app`, `scripts` and `dbt_analytics` and asserts the readers are exactly the definition plus the two resolvers' demo branches. A fourth reader is a new fallback path and now has to be argued for in this test.
- The API resolver is covered in all three states — demo default, real-mode 503, real-mode operator override.

### 11.7 Demo gate — unchanged

```
headline: (19, 446175.0, 50.0) | exceptions 667 | DQ 15
BYTE-IDENTICAL: True
dbt run  -> PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157
dbt test -> PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11
Command Center integration reconciliation checks PASSED.
Resolved report_month: 2026-06 (2026-06-01..2026-06-30) [source: data]
```

Demo derives from sample payroll, so it never reaches the changed branch — `[source: data]`, not `demo-default`. The gate holds by not being touched.

---

## 12. The `7b86cc8` reconciliation audit

Full report: [`reconciliation-audit-7b86cc8.md`](reconciliation-audit-7b86cc8.md). The headline:

```
assertions BEFORE 7b86cc8 : 74
assertions AFTER          : 11      (unchanged today)
removed                   : 63
with a surviving equivalent: 0
```

The 11 survivors are the Command Center integration block, untouched. Every other block went whole: payroll 7, attendance 8, compliance 9, ER 11, recruitment 13, talent 13, warehouse 2. The dbt suite did not absorb them — it is 11 `not_null`/`unique` tests on 5 marts, and **`not_null` passes on a fabricated zero**.

Two findings worth more than the count:

1. **Only one guarded object actually disappeared.** The deleted suite referenced 62 distinct `mart_`/`base_` objects; 61 still exist. The single exception is `mart_wps_status`. So WPS is not the tip of an iceberg of lost marts — this audit is what establishes that rather than assuming it. The iceberg is that 61 surviving objects lost their guard anyway.

2. **None of the 74 ever compared a KPI to the uploaded rows.** Every check compares a mart to another mart or to a `base_` model — both sides downstream of the same filters. That makes the suite strong against a broken join and blind to a wrong shared upstream, which is exactly why §11.4's zero sailed past all 11 survivors. The gap the suite never covered is larger than the 63 it lost.

Report only, per ruling. Restoration is cheap and mostly mechanical as dbt singular tests, but additivity assertions must become domain-aware first: "breakdown sums to total" is false by design once 2b suppresses a payload, and a suite that fires on every partial onboarding gets switched off.

**The design brief for the rebuild is now recorded in the audit doc: SOURCE-TO-MART.** One assertion of that shape — uploaded row count and period reconciling to what the KPI reports — would have caught the payroll mismatch, the attendance window, and the 494. See the audit's §6.

---

# The second 2026-08-11 extension

## 13. The attendance window was pinned to a repo literal too

### 13.1 Worse than the payroll case, because nothing had to go wrong first

`dbt_vars` set six date vars. It never set `start_date_str` or `end_date_str`, so both stayed at the `dbt_project.yml` literals `2026-06-01` / `2026-06-30`. Two models read them:

```sql
base_attendance_current    WHERE a.attendance_date BETWEEN DATE '{{ var('start_date_str') }}'
                                                       AND DATE '{{ var('end_date_str') }}'
base_expected_attendance   range(DATE '{{ var('start_date_str') }}', DATE '{{ var('end_date_str') }}' + 1 DAY)
```

The payroll trap needed an operator override to fire. This one needs **nothing**. Under pure derivation, any client whose payroll close is not June 2026 gets a correctly resolved `report_month` and an attendance window this repository chose — attendance declared, populated, silver correct, guard green, dbt 157/157, attendance metrics wrong.

`start_date_str`/`end_date_str` now pass through as `cc_report_month_start`/`cc_report_month_end`. Not a parallel derivation — the same two values under the names those models happen to read, so there is no second idiom that can drift. A test asserts the identity rather than mere presence.

### 13.2 The generalised pin, and what it found

`test_no_date_shaped_var_reaches_a_model_as_a_repo_literal` states the class instead of the instance:

> a var declared in `dbt_project.yml` with a **date-shaped value**, **consumed** by at least one model, and **not overridden** in `dbt_vars` ⇒ every client's window is a period this repository chose.

Detection is by **value shape**, not name — a name-based rule only finds vars someone already thought to call a date. Run against the pre-fix pipeline, this is what it reports:

```
[dbt vars] date-shaped declared : 12
[dbt vars] of those, consumed   : 11
[dbt vars] of those, overridden :  5
[dbt vars]   PINNED   end_date_str         = 2026-06-30
[dbt vars]   ok       report_anchor_date   = 2026-06-30
[dbt vars]   ok       report_month         = 2026-06
[dbt vars]   ok       report_month_end     = 2026-06-30
[dbt vars]   ok       report_month_start   = 2026-06-01
[dbt vars]   PINNED   start_date_str       = 2026-06-01
[dbt vars]   ok       talent_month_end     = 2026-06-30
[dbt vars]   unused   talent_month_start   = 2026-06-01
[dbt vars]   PINNED   trend_m1             = 2026-04
[dbt vars]   PINNED   trend_m1_end         = 2026-04-30
[dbt vars]   PINNED   trend_m2             = 2026-05
[dbt vars]   PINNED   trend_m2_end         = 2026-05-31
```

**Six, not two.** The four extra are the trend anchors behind `mart_exec_trends` and `mart_workforce_headcount_trend`, and their own `dbt_project.yml` comment named the defect:

> *"Placeholder literals — to be replaced by report_month-relative derivation in the resolver cycle (5a)."*

Cycle 5a wrote the note and did not carry it out. I fixed all six rather than the two named. Exempting four known-pinned vars in the cycle whose purpose is closing this class would have made the pin's exemption list the place the class goes to survive.

The trend consequence is its own small Category C. Derivation, at a July close:

```
pre-fix  trend months: ['2026-04', '2026-05', '2026-08']   <- a "trend" that skips June and July
post-fix trend months: ['2026-06', '2026-07', '2026-08']
```

and `mart_exec_trends` LEFT JOINs payroll on that month label, so the two historical points also returned a payroll cost of 0 — a chart with two zeroes in it, which reads as a business collapse rather than as a bug.

`trend_m1`/`trend_m2` derive as `report_month` minus 2 and minus 1, tested across a year boundary and a leap February. On demo they reproduce the committed literals exactly, which is what keeps the gate byte-identical.

`talent_month_start` is passed every run and read by no model. Not a correctness risk, so a second test **names** it rather than failing — a var that looks live in `build_warehouse.py` while nothing reads it is how someone concludes a window is derived when it is not.

### 13.3 Re-measuring the 494

The 494 was measured at `report_month` 2026-06 — the one period where the pinned window agrees with the resolved one. Four arms, same 19-employee population, `declared:[employees]`:

| | pipeline | `REPORT_MONTH` | window | working days | attendance exceptions |
|---|---|---|---|---|---|
| A | pre-fix | 2026-06 | 2026-06-01 .. 2026-06-30 | 26 | **494** |
| B | pre-fix | 2026-08 | 2026-06-01 .. 2026-06-30 | 26 | **494** |
| C | fixed | 2026-08 | 2026-08-01 .. 2026-08-31 | 27 | **513** |
| D | fixed | 2026-06 | 2026-06-01 .. 2026-06-30 | 26 | **494** |

**A reproduces the original measurement exactly.** **B is the proof it was pinned:** the period moved to August and the number did not, because the window never left June. **C** is the number under a rig that cannot agree by coincidence. **D** shows the fix is a no-op when the period genuinely is June, which is why demo is untouched.

So the 494 is **confirmed real**, and now has an exact mechanism rather than a magnitude:

```
attendance exceptions = working days in the reporting period × active employees
494 = 26 × 19        513 = 27 × 19
```

`base_expected_attendance` CROSS JOINs the calendar with active employees and marks every row with no matching attendance as `absence_days = 1.0`. With attendance undeclared and empty, **every** row is an absence. It is not a distorted measurement of anything; it is 100% manufactured, and its size is set by a calendar. That is Category A at its purest, and it is what step 2b/3 has to suppress.

Two incidental confirmations from the same rig: `talent` exceptions moved 28 → 44 between arms A and B and `recruitment` 25 → 23, because `talent_month_end` was already overridden and correctly tracks the period. The vars that were wired up behaved; the ones that were not, did not.

### 13.4 Item 4 — attendance needed an equivalent guard, so it has one

The question was whether the payroll mismatch guard needs an attendance counterpart once the window derives from the same resolver. **It does**, and the reasoning is worth stating because it is the opposite of the payroll case:

- **Payroll can only disagree under an operator override.** Derivation takes the period *from* payroll, so `MAX(payroll_period)` is in the file by construction.
- **Attendance can disagree under pure derivation.** The period is the payroll close. Nothing obliges a client's attendance file to be that same month, and a mid-cycle onboarding where payroll is closed for July and attendance is exported for August is ordinary, not perverse.

Unifying the vars fixes *"the window is a repo constant"*. It does not fix *"the window is the payroll close and the attendance file is a different month"* — and after §13.1 that second case is live, because the window now actually moves.

**Compliance turned out to have the same exposure**, found while reasoning about attendance: `base_compliance_current` LEFT JOINs on `c.period = var('report_month')`, so a compliance file from another month makes every employee read as unregistered for GOSI, Qiwa and insurance.

So the guard is now one rule over three domains, replacing the payroll-only check:

| domain | how the model narrows | rule |
|---|---|---|
| `payroll` | `payroll_period = report_month` | the period must be **present** |
| `compliance` | `c.period = report_month` (JOIN) | the period must be **present** |
| `attendance` | `attendance_date BETWEEN start .. end` | the period must **overlap** |

Overlap rather than membership for attendance because the filter is a range: a mid-month upload is legitimate, and only *zero* overlap is the failure.

**This widens the guard the review accepted.** It previously ran only when an operator period was set; it now runs against the resolved period whichever way it resolved. That is not a new special case — under derivation the payroll check is *vacuous*, because the period is payroll's own latest close. The same rule covers both paths without an exemption for either. Membership semantics are unchanged.

Each message names the consequence, because "period mismatch" does not tell an operator what they were about to look at:

```
##########################################################################
# ARM C - payroll close 2026-07, attendance file 2026-08, NO override
##########################################################################
  declared: ['employees', 'payroll', 'attendance']

  REJECTED AT INGEST with ReportMonthMismatchError:
    Reporting period mismatch. The reporting period is 2026-07, but the uploaded
    attendance data covers 2026-08. Attendance is filtered to the reporting
    period and absence is inferred from its absence, so this run would show
    every employee absent on every working day.
    Either set REPORT_MONTH to one of 2026-08, or upload the 2026-07 attendance file.
    عدم تطابق فترة التقرير: فترة التقرير هي 2026-07 بينما ملف attendance المرفوع
    يغطي 2026-08. سيؤدي ذلك إلى إظهار جميع الموظفين كغائبين في كل أيام العمل.
```

Agreement passes and the run proceeds:

```
ARM C' - the same run with a 2026-07 attendance file
  [report_month] period 2026-07 [data] covered by: attendance, payroll.
  report_month        : 2026-07
  attendance window   : 2026-07-01 .. 2026-07-30      (07-31 is a Friday)
  attendance rows kept: 2
```

The gate resolves the period the same way the pipeline will — operator, then payroll close, then compliance — over the files about to become silver. Any divergence between the two would make the gate test a period the marts do not use, so it reads the same columns in the same order rather than approximating.

### 13.5 Demo gate — unchanged

```
[report_month] period 2026-06 [data] covered by: attendance, compliance, payroll.
Resolved report_month: 2026-06 (2026-06-01..2026-06-30) [source: data]
Derived trend anchors: 2026-04, 2026-05

headline: (19, 446175.0, 50.0) | exceptions 667 | DQ 15   BYTE-IDENTICAL: True
dbt run 157/157 · dbt test 11/11 · reconciliation checks PASSED
pytest: 122 passed
```

Demo's three period-bearing sample files all cover 2026-06, so the new gate passes there rather than being skipped — the check is exercised by the gate, not merely absent from it.

### 13.6 Tests added

| Test | Pins |
|---|---|
| `test_no_date_shaped_var_reaches_a_model_as_a_repo_literal` | the whole class, by value shape; prints the full classification every run |
| `test_date_shaped_vars_that_nothing_reads_are_named` | `talent_month_start`, so dead vars stay visible |
| `test_the_attendance_window_is_the_reporting_period` | identity with `report_month_start`/`_end`, not just presence |
| `test_the_trend_anchors_are_the_two_months_before_the_period` | year boundary, leap February, and the demo literals |
| 14 further cases in `test_report_period.py` | attendance/compliance coverage, consequence text in both languages, ingest-side period resolution precedence, the vacuous-under-derivation property, undeclared-domain skip |

**122 pass**, up from 104.

---

**Not merged. Awaiting review.**
