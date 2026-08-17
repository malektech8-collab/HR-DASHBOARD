# Loading a real payroll export — Plan

**Status:** PLAN ONLY (A3). **Branch:** `phase-2/payroll-load` off `main` @ `c58aec9` · **Date:** 2026-08-17
**Precedent:** the employees load. Per SP-003 this plan carries magnitudes and vocabulary only.

---

## 1. The blocker to settle before anything else

**All 13 payroll columns are `required: true`. Payroll has no optional columns at all.**

```
payroll_period  employee_id  basic_salary  housing_allowance  transport_allowance
other_allowances  overtime_amount  deductions  gross_pay  net_pay
location  cost_center  payroll_status
```

Employees was 14 required of 23 *after* three relaxations. Payroll has had none, so **a missing column is a REJECT, not an exception** — the file does not load at all.

**`cost_center` is the one that will bite.** This client's employees export does not carry it; it was recorded absent and its checks suppressed. A payroll export from the same HR system is unlikely to carry it either, and on payroll it is **required**.

Three columns are candidates for the same problem — `other_allowances`, `overtime_amount`, `deductions` — because a simple payroll export often folds these into gross rather than itemising them.

**This must be checked against the actual export before a mapping profile is written**, and it is a ruling, not an implementation choice: either the contract is relaxed (the `contract-required-relax` cycle established exactly how, and `complete_canonical_shape` already handles the downstream half), or the client supplies the columns. **Relaxing five of thirteen is a different proposition from relaxing three of twenty-three** and deserves to be decided deliberately.

## 2. The mapping profile shape

Same mechanism as employees, and simpler in three ways:

| | employees | payroll |
|---|---|---|
| `columns` | 18 mapped | ≤13, all required |
| `ignored` | 87, grouped reasons | however many the export carries beyond 13 |
| `values` | 2 vocabularies, affirmed | **1** — `payroll_status` |
| `derive` | `is_saudi` from nationality | none |
| `constants` | `company`, with basis | possibly `cost_center` — see §2.1 |
| `history_since` | **required** | **not required** |
| coverage window | n/a | **not required** |

`payroll_status` allows `Paid`, `Pending`, `Unpaid`, `Hold`, `Cancelled`. As with `contract_type`, **map to the contract's exact strings, not their English gloss** — and the value-target guard added in the vocabularies cycle now refuses a non-contract target at save time.

Payroll is neither `DATE_GRAINED` nor `HISTORY_DECLARING`, so the commit needs **no declaration beyond the file itself**. That is a genuinely smaller operator step than employees.

### 2.1 A constant for `cost_center` is available but is a decision

The constants mechanism would let an operator assert one cost centre for every row, with `asserted_by` and a `basis`. **It should not be reached for casually here.** The guard added in the relax cycle refuses a constant on a *required* column precisely so that a constant cannot become a way past the required-columns gate — which means using one here would require relaxing `cost_center` first anyway. The order is: relax, then decide whether a constant is honest.

## 3. The period — payroll is the primary source

`payroll_period` is the canonical derivation source:

```
operator REPORT_MONTH  ->  MAX(payroll_period)  ->  MAX(compliance.period)  ->  repo literal
```

Until now this client has had **no period-bearing domain at all** — employees carries none — so the period has come from the operator's `REPORT_MONTH`. Loading payroll changes that: the file itself starts to carry the answer.

**The interaction to brief the operator on.** `check_payroll_period_matches_report_month` runs at ingest and **rejects the upload** when an operator-set `REPORT_MONTH` is absent from the payroll file. The current setting is a month the payroll export may not cover. So before the load, one of two things must be true:

- `REPORT_MONTH` is set to a period the payroll file contains, or
- `REPORT_MONTH` is unset, and derivation takes over.

The check exists because the alternative is silent: the filter matches nothing, every gate passes, and payroll cost renders as zero. Its message names both periods, so the failure is self-explaining — but it is a **hard stop at ingest**, and an operator who has not been told will read it as a broken upload.

## 4. What changes on screen

**20 metrics un-suppress. 25 stay blocked.**

Un-suppressed by payroll alone: the whole of `mart_payroll_kpis` (`total_payroll_cost`, `basic_salary_cost`, `allowances_cost`, `overtime_cost`, `deductions`, `net_payroll`, `employees_paid`, `avg_cost_per_employee`, `payroll_variance_pct`, `payroll_exception_count`), `mart_exec_kpis.payroll_cost` and `.overtime_cost`, `mart_command_center_overview.payroll_cost`, `mart_data_quality_summary.invalid_payroll_count`, and five payload marts including `mart_payroll_trend` and `mart_payroll_components`.

**Still blocked, and worth saying plainly because it will be the first question:**

| still suppressed | also needs |
|---|---|
| `mart_payroll_reconciliation` | attendance |
| `mart_payroll_exceptions` | attendance |
| `mart_payroll_by_project` | locations |
| `data_quality_score` (three marts) | attendance, compliance |
| every Command Center overview panel | attendance, compliance, and more |

**Payroll reconciliation — arguably the product's headline payroll feature — does not light up with payroll alone.** It reconciles against attendance.

### 4.1 `payroll_variance_pct` will read 0.0, and 0.0 is a lie

```sql
WHEN COALESCE(prev.total_payroll_cost, 0.0) = 0.0 THEN 0.0
```

With a single month uploaded, `base_payroll_previous` is empty and variance renders **0.0%** — *"payroll unchanged since last month"*. It is the same fabricated-favourable shape as `missing_cost_center_count = 0`, and this cycle already has the ruling for it: **NULL, not 0**, with the suppression layer explaining why.

Either two consecutive periods are loaded, or this needs the same treatment `cost_center` got. **Flagged, not fixed here.**

### 4.2 Two sentinels survive on the payroll path

`base_payroll_current` and `base_payroll_previous` still carry:

```sql
COALESCE(e.project,    'Missing Project')    AS emp_project,
COALESCE(e.department, 'Missing Department') AS emp_department,
```

The `cost_center` sentinel next to them was deleted in the relax cycle for exactly this reason. **For this client, `project` is NULL for every employee** — no locations file — so **every payroll row will bucket under a category literally named "Missing Project"**, in every payroll breakdown. That is a client's payroll presented under a heading that describes our data model rather than their business.

## 5. What employees did not exercise

### 5.1 The `employee_id` join — and it is mislabelled today

**This is the substantive finding of the plan.** A payroll row referencing an unknown employee is a *referential* failure, not a bad value, and the system does not currently say so.

- **The contract cannot catch it.** `validate_schema.validate_csv` is single-table by construction. There is no `references` key and no cross-table rule. An orphan `employee_id` passes contract validation completely.
- **`validate_data` catches it by accident, and names it wrongly.** The check joins payroll to employees with a LEFT JOIN and filters `status IN ('Terminated','Inactive') OR status IS NULL`. `status IS NULL` is *only* possible for an employee that does not exist — yet the row is reported as:

  > **Inactive Employee with Payroll Record** — *"Employee status is 'None' but has active payroll run record for period …"*, severity Critical, recommended action *"Hold payroll run and check termination status/period logic"*.

  The diagnosis is wrong and so is the advice. The employee is not inactive; **the employee is not there**. Checking termination logic will not find them.
- **Downstream it is bucketed, not flagged.** `COALESCE(e.status, 'Inactive/Terminated/Unknown')` turns a broken reference into a status category, so an orphan row is counted in payroll totals under a label that reads like a status.

**Three distinct cases are currently one message**: employee terminated, employee inactive, employee absent from the master file. The third has a different cause, a different owner, and a different fix.

Proposed shape — **not built**: a distinct `Unknown Employee` issue type at REJECT or EXCEPTION severity (a ruling: an orphan payroll row may mean a mis-keyed ID, or a genuinely missing employee record), naming the id and stating that the row is not counted, or is counted and why.

### 5.2 Duplicate employee IDs on the join

`validate_data` already does `df_emp.unique(subset=["employee_id"])` before joining, with a comment naming a demo record as the reason. On real data, silently choosing one of several rows for a duplicated id changes which department and status a payroll row inherits. Employees has a `Duplicate Employee ID` check, so the condition is reported — but the *join* resolves it by arbitrary choice rather than by rule.

### 5.3 The rest, briefly

- **`min_value: 0` on `basic_salary`, `gross_pay`, `net_pay`** — the first contract rule of its kind this client's data will meet. Negative pay is an EXCEPTION, not a reject.
- **A second period.** Employees was one file with a declared history depth; payroll's trend and variance want two consecutive `payroll_period` values in the same file, or two loads.
- **Money columns and the read sweep.** `basic_salary` is the exact column that produced `could not parse '1584.91' as dtype 'i64'`. Payroll has **eight** decimal columns; all reads are now text and typed from the contract, so this path is already covered — but payroll is the domain that would have hit it hardest.
- **`location` is required on payroll** and is present on employees, so the client's system tracks it. Whether their *payroll* export carries it is a separate question.

## 6. Sequence for the operator

1. **Inspect the export's header only** and compare against the 13 required columns. Answer §1 before anything else.
2. **Ruling** on any missing required column: relax, or request from the client.
3. Resolve the `REPORT_MONTH` / payroll-close question (§3).
4. Author the profile via the CLI — `payroll_status` affirmed, everything else mapped or ignored with reasons.
5. **Preview only.** Expect `employee_id` orphans to appear as *"Inactive Employee with Payroll Record"* until §5.1 is ruled on; read that count as *unknown-or-inactive*, not as inactive.
6. Commit, run the pipeline, report — magnitudes and vocabulary only.

## 7. Test obligations, when this is built

1. An orphan `employee_id` is reported as a **reference** failure, not a status one — and a genuinely terminated employee with payroll still reports as a status failure (the tamper: the two must not collapse into one message again).
2. A single-period upload renders variance as **withheld**, not `0.0`; two periods render a real figure.
3. A payroll file missing a required column REJECTs, naming the column, with the client's own header in the message.
4. Demo byte-identity.
5. The client's employees load survives the payroll commit — same before/after check as the isolation cycle.

## 8. Cost and risk

The load itself is smaller than employees: no history declaration, no coverage window, one vocabulary, no derivation.

**The risk is entirely in §1 and §5.1.** Thirteen-of-thirteen required is a contract question that must be answered before a profile is worth writing, and the orphan-row mislabelling means the first real payroll preview will produce a count that reads as a payroll problem when it may be a data-integrity one. Both are rulings.

---

**Not built. Awaiting a ruling.**
