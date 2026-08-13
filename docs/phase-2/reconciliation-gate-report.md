# Reconciliation Gate — Execution Report

**Branch:** `phase-2/reconciliation-gate` off `main` @ `0b30d0a` · **Date:** 2026-08-13
**Status:** PR open, **not merged**

Eleven checks, twelve now. Every one of them watched failing before it was trusted to pass.

---

## 1. What was wrong

```python
# scripts/build_warehouse.py, before this cycle
418:  cc_active_headcount = SELECT active_headcount FROM mart_workforce_kpis   # WRITE
433:  INSERT INTO command_center_overview_data VALUES (cc_active_headcount, ...)
...
439:  kpi_hc = SELECT active_headcount FROM mart_command_center_overview       # read back
440:  ref_hc = SELECT active_headcount FROM mart_workforce_kpis                # same source
441:  if kpi_hc != ref_hc: raise ValueError(...)
```

Eight of eleven checks compared the overview table against the marts it had been populated from, fifteen lines earlier, in the same connection. Measured: tampering `mart_workforce_kpis` with `+ 1` left the pipeline **green**.

---

## 2. A second defect, inside a check I called "real"

Checks 9–11 asserted `COUNT(*) = 9` against the module registry. They can fail, so I classified them as real. They passed for the life of the project while **three of the nine rows were corrupt**:

```
key="hr_analytics"."main"."stg_payroll"      route=/"hr_analytics"."main"."stg_payroll"
key="hr_analytics"."main"."stg_attendance"
key="hr_analytics"."main"."stg_compliance"
```

`'{{ ref('stg_payroll') }}' AS module_key` renders the quoted relation name into a SQL string literal. A find/replace that rewrote table names into dbt refs did not stop at `FROM` clauses — **27 literals across three models**. It reaches `backend/app/api/command_center.py:130`, which reads `module_key` from the registry, and the frontend from there: three Command Center modules had a garbage key and a broken route.

A row count cannot see that. The rows were all present; they were just wrong. **"Can it fail?" was the wrong question — "does it check the thing that matters?" is the second half**, and I had only asked the first.

Nothing had been coded around the corrupted values (`grep` for the quoted catalog name across `frontend/src` and `backend/app` returns nothing), so restoring them is a pure fix.

---

## 3. The rewrite

Extracted to [`scripts/reconciliation.py`](../../scripts/reconciliation.py). Each check recomputes its figure from the **base models one layer below the mart it validates** — never from the mart, never from the artefact being checked.

Each answers: *does the number the Command Center serves still equal the number you get by counting the underlying rows yourself?* That catches a mart aggregation bug, a stale view, and a wrong write. The old shape caught none.

**None was deleted — all eight could be made independent.**

| # | Check | Independent recomputation |
|---|---|---|
| 1 | Active Headcount | `COUNT(DISTINCT employee_id)` from `base_active_workforce` |
| 2 | Payroll Cost | `SUM(gross_pay)` from `base_payroll_current` |
| 3 | Attendance Compliance | Category F rule restated over `base_expected_attendance` — measured days as denominator, NULL when none |
| 4 | Saudization | Saudi / (Saudi + non-Saudi) from `base_active_workforce`, unknown nationality excluded from **both** sides |
| 5 | Open ER Cases | `base_er_case_population` by status |
| 6 | Open Requisitions | `base_recruitment_requisitions_current` by status |
| 7 | Review Completion | `base_performance_reviews_current` over `base_talent_employee_population` |
| 8 | Total Active Exceptions | the **eight UNION arms summed separately**, so an arm that stops contributing is caught — counting the union itself cannot do that |
| 9–11 | Module registry / freshness / navigation | the nine module **keys**, not a row count |
| 12 | Module routes | each route is `/` + its key |

Restating the Category F rule in check 3 is deliberate: if the mart ever loses it, this check is what notices.

---

## 4. (d) Every check, watched failing

### 4.1 Reconciliation — 32 tests in [`test_reconciliation.py`](../../backend/tests/test_reconciliation.py)

Each of the eight value checks is tampered **from both sides**:

```
test_every_value_check_fails_when_the_served_figure_is_wrong[8 checks]   RED
    tamper what the Command Center serves

test_every_value_check_reads_its_independent_side[8 checks]              RED
    tamper the underlying rows instead, and first assert the served
    figure did NOT move - a check whose "independent" query secretly
    read the same artefact would pass the first test and fail this one
```

Plus: a UNION arm deleted, a NULL on one side only, two simultaneous disagreements both reported, a corrupted module key in each of the three tables (the real defect, as a fixture), a missing module, a mismatched route, and a swapped module that keeps the count at nine.

Two structural tests forbid the regression outright: no check's independent side may mention `mart_command_center_overview`, or any `mart_` at all.

**Meta-proof, run once.** Reverting `active_headcount` alone to the tautological form:

```
5 failed, 27 passed          suite exit 1  [RED]
  test_every_value_check_fails_when_the_served_figure_is_wrong[active_headcount]
  test_every_value_check_reads_its_independent_side[active_headcount]
  test_every_disagreement_is_reported_not_just_the_first
  test_no_check_validates_a_mart_against_itself
  test_no_independent_check_reads_a_mart_at_all
```

The suite is not decorative.

### 4.2 Demo figures and dbt counts — [`test_demo_gate.py`](../../backend/tests/test_demo_gate.py)

```
baseline (untampered):     8 passed          GREEN, and NO SKIPS
active_headcount           delete an active employee        -> RED
payroll_cost               bump one gross_pay               -> RED
saudization_pct            flip one is_saudi                -> RED
exception_sources          delete a data_quality row        -> RED
data_quality_rows          delete a data_quality row        -> RED
dbt model count            add a model, dbt parse           -> RED
dbt data test count        add a data test, dbt parse       -> RED
manifest vs files on disk  add a model, stale manifest      -> RED
```

**The failure mode that mattered here was a silent skip, not a wrong number** — a skipped test is green — so the probe asserts the baseline run reports no skips. `HR_WAREHOUSE_PATH` exists so the gate can be pointed at a doctored warehouse copy and watched failing.

One correction to my own probe output: after regenerating the manifest, `manifest vs disk` returns to green. My probe labelled that "GREEN — NOT A GATE". That was wrong; it is the check working. It goes red exactly when disk and manifest disagree, which is the state a count read off stdout cannot distinguish from a healthy one.

The figures are pinned as **literals**, deliberately. A test that recomputed them from the same source the dashboard reads would agree with any drift and catch nothing — the tautology this project has now shipped twice. Changing one means editing the file, which is a reviewable act.

---

## 5. SP-001 — the standing practice

Recorded in [`TECHNICAL_DEBT_REGISTER.md`](../TECHNICAL_DEBT_REGISTER.md) as a standing practice, not a debt item, because the register is where someone looks before trusting a check.

> **A verification line earns its place only once someone has confirmed it can fail.**

| | Quoted | Actual |
|---|---|---|
| 1 | `tsc --noEmit` — "0 errors" | typechecked **zero files**; `--listFilesOnly \| wc -l` → `0` |
| 2 | `reconciliation PASSED` | 8 of 11 compared a value with the source it was copied from |

Both were offered as evidence for many cycles and **accepted at review each time**. The register records what the rule costs — one command, once — where it is enforced, and the gap: **only checks written or touched since adoption have been tamper-proven.** Applying it to the rest of the suite is open work, not a completed sweep.

---

## 6. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — identical, and now **asserted** |
| Reconciliation | `PASSED (12 independent checks)` |
| dbt | 161/161 models, 11/11 tests — both now asserted |
| pytest | **349 passed** (309 + 40 new) |
| vitest | 94 passed |
| `tsc -b` / `npm run build` | 0 errors / passes |
| flake8 | CI selection 0; `build_warehouse.py` is 19 findings against `main`'s 20 |

---

## 7. Open

1. **SP-001 is not retroactive.** The rest of the test suite has not been tamper-proven.
2. **The `'Unassigned'` / `'Missing Project'` sentinels** remain, and §1.4's mapping residual remains — unchanged, and not implied as done.
3. **The reconciliation checks restate business rules.** Check 3 restates the Category F denominator and check 4 the nationality exclusion. That is the point — an independent recomputation must be independently written — but it means a rule change needs editing in two places, and the second place is this module.
4. **`mart_wps_status`** still missing; `GET /api/compliance/wps` still 500s.

---

**Not merged. Awaiting review.**
