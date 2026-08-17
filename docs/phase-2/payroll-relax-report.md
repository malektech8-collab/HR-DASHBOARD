# Payroll relaxations and contract audit — Execution Report

**Branch:** `phase-2/payroll-relax` off `main` @ `c58aec9` · **Date:** 2026-08-17
**Plan:** [`payroll-load-plan.md`](payroll-load-plan.md) (approved with rulings) · **Status:** PR open, **not merged**

Per SP-003 this report carries magnitudes and vocabulary only.

---

## 1. The relaxations

**Payroll goes from 13 of 13 required to 8 of 13.**

| relaxed | reason (ruled) |
|---|---|
| `cost_center` | finance system, not the HR export — as on employees |
| `other_allowances` | simple exports fold these into gross |
| `overtime_amount` | " |
| `deductions` | " |
| `location` | may not be on a payroll line at all |

**Kept required**: `gross_pay`, `net_pay`, `employee_id`, `payroll_period`, `basic_salary`, `housing_allowance`, `transport_allowance`, `payroll_status`. A payroll file without gross and net is not payroll.

Each relaxed column's description now states, in both languages, **what absence means for the figure** — not merely that the column is optional.

### Parity

```
file with 8 of 13 columns        -> 0 reject(s), 0 exception(s)
same file WITHOUT gross_pay      -> 1 reject: required-columns,
                                    missing required column(s) ['gross_pay']
```

## 2. Why this was not a one-line contract change

`required: false` alone accepts the file and then **produces wrong numbers** — the employees lesson in a worse form, because there is no crash to notice. Two shapes, both measured in DuckDB rather than reasoned about:

**The composite sum discards its neighbours.**

```
SUM(housing + transport + other)  with other all NULL  ->  0.0
```

`a + b + NULL` is NULL for the whole row and `SUM` skips it. An absent `other_allowances` did not omit itself — it **took housing and transport with it** and reported a confident zero. Fixed by `COALESCE` inside the row expression, so the components the client did supply still count. Three marts carried this.

**The reconciliation check stops firing.**

```
ABS(gross - (basic + ... + NULL)) > 0.01  ->  0 rows flagged
```

Not reduced precision — **silence**. `NULL > 0.01` is not true, so every row passes. Gross cannot be reconciled against components the client did not send, so the check is now **withheld** on the source vars rather than passing every row.

**Whole-column sums are withheld, not zeroed.** `overtime_cost` and `deductions` become NULL when their column is absent, across five marts. `0.0` would read as *"no overtime was worked"* / *"nothing was deducted"* — claims the file does not make. Same precedent as `missing_cost_center_count`.

`mart_payroll_reconciliation`'s derived totals propagate NULL deliberately, and say so in a comment: a number there would be the difference between gross and an *incomplete* sum, presented as unexplained payroll.

## 3. The contract audit

Full findings: [`contract-audit.md`](contract-audit.md). Commissioned because 13-of-13 suggested the contract was written from the sample.

| contract | required / columns | |
|---|---|---|
| `employees` | 14 / 23 | after three relaxations |
| `payroll` | **8 / 13** | this cycle |
| `attendance` | **13 / 15** | worst remaining |
| `compliance` | **11 / 13** | |
| `hr_requests` | **9 / 11** | |
| `employee_relations` | 8 / 14 | healthiest |

**The systemic finding: four contracts mark DERIVED columns as required.** `net_late_minutes` (= late − excused), `missing_punch_count`, `sla_breached` (= created + sla vs closed), `occupation_match_status`. These are outputs of the analytics, not inputs a source system produces. The employees contract already has the mechanism — `derived_from` / `derivation` — and **none of the four use it.** That is a correction of what the column *is*, not a relaxation, and it removes four required columns as a side effect.

**Two inversions worth the ruling on their own:**

- Attendance marks `actual_check_in` / `actual_check_out` **optional** and `scheduled_start` / `scheduled_end` **required**. Backwards: a biometric terminal certainly produces punches; a schedule needs a rostering system.
- Compliance marks `iqama_expiry` **optional** while three government-platform statuses are required — though iqama expiry is the most universally available compliance fact, and feeds `iqama_expiring_30`.

**And a shape question, not a relaxation question:** `compliance` is modelled as one file from one system, but its columns come from at least three government platforms plus payroll. A client is unlikely to have a single export containing all of them.

**Stated limit:** the audit reads contracts against general knowledge of KSA HR exports, not this client's files. Only the employees export has been seen. Every row is a plausibility judgement to be confirmed against a real header line — which is exactly the check that turned payroll from a guess into these five relaxations.

## 4. Planned, not built

| | |
|---|---|
| [`referential-integrity-plan.md`](referential-integrity-plan.md) | the orphan `employee_id`, its own cycle |
| [`payroll-absence-rendering-plan.md`](payroll-absence-rendering-plan.md) | `payroll_variance_pct = 0.0`, and the three `'Missing Project'` sentinels |

The referential plan records this as the **fifth instance** of absence-rendered-as-a-value, and argues it is the worst: the fabricated value names three real conditions and hides a fourth inside them. It leaves **severity as an open ruling** — a few orphans is a data-quality problem, a mostly-orphan file is a wrong-file problem — rather than presuming it.

## 5. Verification

| Check | Result |
|---|---|
| pytest | **594 passed** (564 + 30 new) |
| Isolation check | `PASSED - 62 file(s) byte-identical` |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` |
| flake8 (CI gate) | 0 |

Demo supplies all five relaxed columns, so every var is TRUE and demo behaviour is unchanged — which is the check that this is a gate and not a behaviour change.

**Client load: unchanged.** The demo rebuild ran into an isolated root.

## 6. Open

1. **The four derived columns** (§3) — the highest-value item in the audit.
2. **Attendance**, before the client is asked for a file: it is next in the load order and it gates payroll reconciliation.
3. **Compliance's shape** — one file or several — decides which columns belong together at all.
4. **`location` on payroll is relaxed but `project` resolution still reads it.** With neither a payroll `location` nor a locations file, `project` is NULL twice over. Covered by the sentinel plan, not by this cycle.

---

**Not merged. Awaiting review.**
