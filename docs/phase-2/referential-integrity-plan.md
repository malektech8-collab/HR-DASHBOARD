# Referential integrity — Plan

**Status:** PLAN ONLY. Ruled its own cycle during A3. **Date:** 2026-08-17
**Trigger:** the payroll load. Employees never exercised this — it is the first domain that *references* another.

---

## 1. What happens today to an orphan payroll row

A payroll row whose `employee_id` matches no employee:

1. **Passes contract validation completely.** `validate_schema.validate_csv` is single-table by construction — it takes one CSV and one contract. There is no `references` key in any contract and no cross-table rule. Nothing in the upload path looks at the other file.
2. **Is caught by accident in `validate_data`**, whose payroll check LEFT JOINs to employees and filters `status IN ('Terminated','Inactive') OR status IS NULL`. `status IS NULL` is reachable *only* for an employee that does not exist.
3. **Is reported as the wrong thing:**

   > **Inactive Employee with Payroll Record** — *"Employee status is 'None' but has active payroll run record for period …"*
   > Severity **Critical**. Recommended action: *"Hold payroll run and check termination status/period logic."*

   The diagnosis and the advice are both wrong. The employee is not inactive; the employee is **absent**. Checking termination logic will not find them, because there is nothing to find.
4. **Is bucketed downstream, not flagged.** `base_payroll_current` and `base_payroll_previous` carry

   ```sql
   COALESCE(e.status, 'Inactive/Terminated/Unknown') AS emp_status
   ```

   so a broken reference becomes a *status category*. The row is counted in payroll totals under a label that reads like a status.

**Three distinct cases share one message**: employee terminated, employee inactive, employee absent from the master file. They have different causes, different owners, and different fixes.

## 2. Why it is the fifth instance of one defect

Absence rendered as a value, in this codebase's own history:

| # | site | absence rendered as |
|---|---|---|
| 1 | `COALESCE(cost_center, 'Missing Cost Center')` | a payroll category |
| 2 | `COALESCE(project, 'Unassigned')` | a project |
| 3 | `missing_cost_center_count = 0` | "nobody is missing one" |
| 4 | `payroll_variance_pct = 0.0` | "unchanged since last month" |
| 5 | `COALESCE(status, 'Inactive/Terminated/Unknown')` | **a status** |

The first three were fixed. The fourth is planned. **This is the fifth**, and it is the worst of them, because the fabricated value is not merely wrong — it names three real conditions and hides a fourth *inside* them.

## 3. Where the check belongs

Not in `validate_schema`. Making it cross-table would change the shape of every caller, and the contract is deliberately one-file-one-contract — the property that lets a preview validate a staged upload without a warehouse.

**The upload path already has what is needed.** At preview and commit, the other domains' silver parquets exist. A referential check reads the parent's key column and tests membership. It is a *coverage-aware* check, not a contract rule: if employees is not provided, there is nothing to reference and the check must not fire — the same `provides` question the column gates already answer.

Proposed shape, declarative and in the contract's idiom — the key is that a contract may *declare* a reference without the validator becoming cross-table:

```yaml
- name: employee_id
  references:
    table: employees
    column: employee_id
```

with resolution done by the upload path, which already knows what else the client has.

## 4. Severity — RULED

**A few orphans is a data-quality EXCEPTION. A mostly-orphan file is a wrong-file REJECT.** Both, separated by a threshold — not one severity applied to every orphan identically.

The reasoning behind the split, which is what the threshold has to encode:

- **A handful of orphans is a mis-keyed id.** The client can see it on the Data Quality page and fix it in their source system. Blocking a whole month's payroll for one bad reference would be the `manager_id` mistake in reverse — a real but small problem stopping everything.
- **A mostly-orphan file is not a payroll file for this client.** A payroll export from a different company, or ids in a different format entirely — a leading zero stripped by Excel, a branch prefix, a different id scheme. Loading it produces payroll totals attributed to nobody, and every figure downstream is wrong. That must not load.

**The threshold's basis must be stated in the code**, not merely chosen. It is a policy number and the next reader has to be able to see what it encodes: at what proportion does "some rows are wrong" become "this is the wrong file"? A value with no stated basis is a magic number, and the register already carries what happens to those.

Two things the implementation must not do:

- **Silently downgrade.** If the file rejects on proportion, the message must say *how many of how many* — not merely that it was refused.
- **Fire at all when employees is not provided.** With no master file, every row is an orphan by construction, and the check must withhold rather than reject the file. That is the `manager_id` lesson: a check about the client's *export coverage* firing as if it were about their data.

## 5. What must be said on screen

Three messages where there is now one:

| condition | message |
|---|---|
| status Terminated/Inactive | *terminated employee has a payroll record* — the existing message, correct for its actual case |
| `employee_id` absent from employees | **unknown employee** — naming the id, stating the row is not counted (or is, and why) |
| employees not provided at all | withheld with a coverage reason, not reported as thousands of unknown employees |

The third row is the trap. Without it this becomes `manager_id` again: a check firing once per row about a fact of the client's *export*, burying every real finding.

## 6. Test obligations (SP-001 — both halves)

1. An orphan `employee_id` is reported as a **reference** failure — and a genuinely terminated employee with payroll still reports as a **status** failure. The tamper: the two must not collapse back into one message.
2. With employees not provided, the check does not fire at all.
3. `emp_status` no longer renders a broken reference as a status category — an orphan is distinguishable from an inactive employee downstream, not only in the message.
4. The proportion case, once ruled: a mostly-orphan file behaves differently from a few-orphan one.

## 7. Scope

Every domain except employees and locations carries `employee_id`. The same check serves all of them, so this is one mechanism used six times rather than six checks — which is the argument for doing it as its own cycle rather than folding it into the payroll load.

---

**Not built. Severity is ruled (§4); the mechanism awaits a ruling.**
