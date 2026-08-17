# Lateness is unmeasured without a schedule — Execution Report

**Branch:** `phase-2/attendance-load` off `main` @ `f01126b` · **Date:** 2026-08-17
**Plan:** [`attendance-load-plan.md`](attendance-load-plan.md) (approved with rulings) · **Status:** PR open, **not merged**

Per SP-003 this report carries magnitudes and vocabulary only.

---

## 1. §11 — the defect that blocked the load

`scheduled_start` became optional in the derived-columns cycle, correcting the inversion. The lateness calculation kept an `ELSE 0`, so every client without a roster would have got:

```
late minutes, OLD COALESCE(...,0) -> 0      "nobody was ever late"
late minutes, NEW (no coalesce)   -> None   not measured
```

**The second-order failure was the serious one.** `attendance_compliance_pct` is defined over three terms — lateness, missing punches, absence. With lateness permanently `0` the lateness term never fires, and `COUNT(CASE …)` skips NULL and FALSE alike, so the percentage **still computes**, from two of its three terms, under the same label:

```
compliance_pct computed anyway -> 0.333   served as "attendance compliance"
compliance_pct now             -> withheld by the schedule gate
```

That is the failure `mart_attendance_kpis`' own comment says it was designed to avoid — *"the figure would look best exactly when the data is thinnest"* — arriving by a different route.

**Fixed in two places, because one would not have been enough:**

- `base_attendance_current` returns **NULL** rather than `0` when there is no schedule. The zero stays only for the case it was always right for: a schedule exists and the employee was not late.
- `mart_attendance_kpis` drops the `COALESCE(…, 0)` wrappers that would have turned those NULLs straight back into zeros, and gates all four schedule-dependent figures — `attendance_compliance_pct`, `late_minutes`, `net_late_minutes`, `early_leave_minutes` — on `has_attendance_schedule_source_sql`.

`attendance_compliance_pct` is **withheld entirely**, not computed from what is left. A metric that quietly changes definition is worse than one that is absent, and this one moves in the flattering direction.

`excused_late_minutes` is deliberately **not** gated on the schedule — it is relaxed for a different reason and a client can supply it without a roster. A test pins that distinction.

## 2. Relaxations

**Attendance: 11 of 15 → 8 of 15.**

| column | why |
|---|---|
| `excused_late_minutes` | an **adjudication** — someone decides a lateness is excused. No pipeline can derive it. |
| `overtime_approved` | an approval-workflow flag; the same species |
| `late_minutes` | derivable **when its inputs exist** — §3 |

What stays required is what a biometric terminal actually produces: `attendance_date`, `employee_id`, `actual_check_in`, `actual_check_out`, plus `location`, `shift_name`, `absence_days`, `overtime_hours`.

## 3. SP-006's boundary condition (ruling 3)

Recorded in the register **as part of the rule, not an exception to it**.

*"Derive it always"* carries an assumption: that the inputs are always there. `late_minutes` is computable from the punch against the schedule less grace — the pipeline already computes it — but `scheduled_start` is itself optional. **Deriving unconditionally would move the fabrication one layer along**: every roster-less client getting `0` late minutes presented as a measurement, which is exactly what §1 just removed.

The rule now reads in full:

> **Derive it when its inputs exist. Withhold it when they do not. Reconcile against it when offered.**

And the test that separates the two absences: **`0` means measured and on time; NULL means there was nothing to measure against.** A missing *punch* is still `0` lateness — it is a missing punch, counted elsewhere — while a missing *schedule* is NULL. Both are tested.

### 3.1 One thing the implementation forced

`late_minutes` needs the **grace period**, which is not a column. It is now parameterised like `sla_breached`, and ingest reads it from `config/business_rules.yml` — **the same file `build_warehouse` passes to dbt**. Had ingest used its own default, the two would have disagreed about the same quantity, and the disagreement would have surfaced as *the client's system being wrong*. A test pins both the shared source and that the parameter actually changes the answer.

## 4. `absence_days` and `overtime_hours` — planned, not built

The plan proposed deriving these too. **They have no existing calculation** — `base_attendance_current` passes them straight through with `a.*`. Deriving them means deciding what counts as an absence day (half days? a row with no punches?) and what threshold makes an hour overtime (over scheduled_end? over eight? KSA Labour Law's daily and weekly limits?).

Those are **business rules, not arithmetic**, and inventing them inside a relaxation is how a contract acquires a rule nobody ruled on. The architect's *"plan first if the shape is unclear"* applies: they stay **required**, and their derivation is a ruling of its own.

## 5. Recorded in the referential-integrity plan (ruled)

Both attendance findings, ahead of that cycle:

**The cross-join drop.** `base_expected_attendance` builds from `CROSS JOIN base_employees_deduplicated`, so an orphan attendance row is in **neither the numerator nor the denominator** of any attendance metric. Payroll's orphan is mislabelled but *present*; attendance's is invisible — **the exception list looks manageable precisely because the figures dropped the evidence.** Recorded with the consequence: for attendance, "three cases need three messages" is not sufficient; the rows must also be **countable**.

**Copy, do not invent.** `base_attendance_current` already classifies the case as `'Unknown employee attendance'` — correct, and better than payroll's `COALESCE(status, 'Inactive/Terminated/Unknown')`. Per SP-007 the correct pattern is already in the codebase beside the defective one, so the RI cycle adopts it rather than designing a new one.

## 6. Runbook (ruling 4)

New section in [`CONTROLLED_REAL_DATA_LOAD_RUNBOOK.md`](../CONTROLLED_REAL_DATA_LOAD_RUNBOOK.md), stating the consequence explicitly rather than describing the mechanism:

> **Declare a window wider than the data and the system manufactures one absence per employee per uncovered working day — each indistinguishable from a real one.**

With four operator instructions: establish the true span from the file itself (not the month, the filename, or a phone call); declare exactly that; expect a hard stop if they disagree — *that is the gate working, not a broken upload*; and a partial upload is normal.

It also pre-empts the two conversations this load will otherwise produce: **attendance and payroll unlock each other's exception surfaces**, so the Attendance exceptions page stays empty until payroll loads; and a client with no rostering system will see no lateness figures at all, which is correct and is not a failed load.

## 7. Verification

| Check | Result |
|---|---|
| pytest | **645 passed** (623 + 22 new) |
| Isolation check | `PASSED - 62 file(s) byte-identical` |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` |
| flake8 (CI gate) | 0 |
| Client load | unchanged, `data/raw` byte-identical |

Demo supplies a schedule, so every gate is TRUE and the demo figures are unchanged — `attendance_compliance_pct`, `late_minutes`, `net_late_minutes` and `early_leave_minutes` all identical.

## 8. Two pinned tests updated

- **`test_category_f`** renders model SQL against a fixed variable dict and **refuses to render an unset var** rather than substituting silently. That is a good harness and it caught the new var immediately. Added as `"TRUE"`, with a comment pointing at where the FALSE case is proved.
- **`test_mapping_api`** pins the derivation registry exhaustively; `late_minutes` is the fifth entry. Kept exhaustive deliberately — a rule appearing there changes what a client is asked to upload.

Per SP-002 both are recorded as changes of **wording**, not of the claim.

## 9. Open

1. **`absence_days` / `overtime_hours` derivations** — business rules, need a ruling (§4).
2. **`shift_name` is still required** and needs a roster, like the schedule. It was not in the ruling's scope; flagged because it is the same species and the audit predicted it.
3. **The attendance load itself** — this cycle removed the blocker; the load has not been attempted.

---

**Not merged. Awaiting review.**
