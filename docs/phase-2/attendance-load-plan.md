# Loading a real attendance export — Plan

**Status:** PLAN ONLY (A4). **Branch:** `phase-2/attendance-load` off `main` @ `690aa7f` · **Date:** 2026-08-17
Per SP-003 this plan carries magnitudes and vocabulary only.

Attendance is the hardest domain remaining, and the first real exercise of three mechanisms built but never run against a client's file.

---

## 1. What the operator must do that no previous load required

**Attendance is the only `DATE_GRAINED` domain.** The commit endpoint refuses it without `coverage_start` and `coverage_end`:

> *"A working day outside the declared window is not an absence, it is unreported — so the window cannot be guessed from the file."*

Employees needed `history_since`; payroll needs nothing. **This is the first domain that requires the operator to vouch for a date range**, and the declaration is not a formality: it is the input that decides whether a missing row means *absent* or *not sent*.

Two gates fire at ingest, both before anything loads:

- `assert_coverage_declared` — declared but no window is a hard error.
- `check_rows_within_declared_coverage` — a row **outside** the declared window aborts the run, naming the offending dates. Declaring 1–14 August and shipping the 20th is a contradiction, and neither arm may be guessed at: widening silently restores the inference the declaration exists to constrain; dropping the row silently loses real attendance.

**The operator must know the export's true date span before declaring**, and the two must agree exactly. This is the most likely first-attempt failure of the whole load.

## 2. Category F fires for the first time on real data

`base_expected_attendance` cross-joins the working calendar with active employees, then left-joins the client's rows. The `absence_days` expression is the mechanism:

```sql
CASE
  WHEN calendar_date < coverage_start OR calendar_date > coverage_end THEN NULL
  WHEN att.employee_id IS NULL THEN 1.0
  ELSE COALESCE(att.absence_days, 0.0)
END
```

- **Outside the declared window → NULL.** Not measured. `SUM`/`AVG` skip it with no special case.
- **Inside the window, no row → 1.0.** A real absence. *This is the inversion the whole design exists for.*
- The row is kept either way, so the gap stays **countable** — `mart_attendance_coverage` reports `covered_days` of `expected_days`.

**A partial upload is the ordinary case, not an edge case.** A client sending one week of a month is normal, and the design already handles it — but it has never run against a real file, and the failure mode if the declaration is wrong is severe in a specific direction: **declaring a window wider than the data manufactures one absence per employee per uncovered working day.** At this client's headcount that is thousands of fabricated absences, each of which looks exactly like a real one.

The guard against that is the operator's declaration, and nothing else. Worth stating plainly in the runbook.

## 3. §11's zeroing consequence lands here — carried from the derived-columns cycle

`scheduled_start` / `scheduled_end` became **optional** in the last cycle, correcting the inversion. The consequence arrives now:

```sql
CASE WHEN a.actual_check_in IS NOT NULL AND a.scheduled_start IS NOT NULL THEN
       GREATEST(date_diff('minute', a.scheduled_start, a.actual_check_in) - grace, 0)
     ELSE 0
END AS calculated_late_minutes
```

With no schedule, **every row's lateness is `0`**. Then:

- `late_minutes` renders `COALESCE(SUM(calculated_late_minutes), 0)` → **0**, reading as *"nobody was ever late"*.
- `attendance_compliance_pct` flags a row when `calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0`. With lateness permanently 0, **the lateness term never fires**, and the percentage rises toward 100% — *"pushes the figure toward 100% exactly when the data is thinnest"*, which is the failure `mart_attendance_kpis`' own comment says it was designed to avoid. It returns here by a different route.

**This must be fixed before a real attendance file loads, and it must be tested against one rather than reasoned about** — that was the ruling for carrying it here. The shape of the fix is settled precedent: withheld, not zero, gated on `scheduled_start` being provided.

Note the interaction: `late_minutes` **is required** while `scheduled_start`, which it is computed from, is optional — the same incoherence the derived-columns cycle corrected for `missing_punch_count`, still present one column along. §4 returns to it.

## 4. What the contract requires that a real export may not carry

Attendance is **11 of 15 required** after the last cycle. Two shapes of source system, and they differ sharply:

| required column | raw biometric export | HR platform (e.g. Jisr) |
|---|---|---|
| `attendance_date`, `employee_id` | yes | yes |
| `actual_check_in`, `actual_check_out` | **yes** — this is what the device produces | yes |
| `location` | sometimes (device site) | usually |
| `shift_name` | **no** — needs a roster | usually |
| `late_minutes` | **no** — computed | usually |
| `excused_late_minutes` | **no** — an adjudication | sometimes |
| `absence_days` | **no** — computed | usually |
| `overtime_hours` | **no** — computed | usually |
| `overtime_approved` | **no** — a workflow flag | sometimes |

**A raw biometric export plausibly carries 5 of the 11.** That is the same discovery payroll made, one domain along, and the audit predicted it.

**Three of these are derivable and are the same species the last cycle corrected**: `late_minutes` (punches vs schedule, minus grace — the pipeline already computes it as `calculated_late_minutes`), `absence_days`, `overtime_hours`. Each is an output we compute anyway.

**The circularity to resolve before relaxing them**: they are computable *only when the schedule is present*, and the schedule is now optional. So the honest arrangement is not "derive them" but **derive them when their inputs exist, and withhold when they do not** — which is §3's fix generalised. Deriving them unconditionally would reintroduce the zeroing in a new place.

`excused_late_minutes` and `overtime_approved` are **not** derivable — they are human decisions — and should simply be relaxed.

## 5. What attendance specifically exposes about the `employee_id` join

Referential integrity is [its own cycle](referential-integrity-plan.md), but attendance exposes something payroll did not, and it should be recorded there before that cycle builds.

**Attendance has two different orphan behaviours in two models:**

1. `base_attendance_current` classifies the row: `'Unknown employee attendance'`. **This is correct and is better than payroll's** `COALESCE(status, 'Inactive/Terminated/Unknown')`, which renders a broken reference as a status. Attendance already separates the case — a precedent the RI cycle should copy rather than invent.
2. `base_expected_attendance` builds from `CROSS JOIN base_employees_deduplicated` and left-joins attendance onto it. **An attendance row for an unknown employee is not in the calendar at all** — it appears in neither the numerator nor the denominator of any attendance metric. It is silently dropped.

So the same orphan is **named** in one model and **invisible** in another. A client whose attendance file uses a different id scheme would see `'Unknown employee attendance'` exceptions while every headline attendance figure quietly excluded those rows — the totals would look clean and be computed from a subset.

**This is the more dangerous of the two and it is specific to the cross-join design.** It should be recorded in the RI plan now.

## 6. What changes on screen

**13 metrics un-suppress. 21 stay blocked.**

Un-suppressed by attendance alone: `mart_attendance_coverage`, seven `mart_attendance_kpis` figures (`absence_days`, `attendance_compliance_pct`, `late_minutes`, `net_late_minutes`, `excused_late_minutes`, `early_leave_minutes`, `missing_punch_count`, `overtime_hours`), `mart_attendance_late_arrival`, `mart_attendance_missing_punches`, `mart_command_center_overview.attendance_compliance_pct`, and `mart_exec_kpis.absence_days`.

**Still blocked, and this is the first question a reader will ask:**

| still suppressed | also needs |
|---|---|
| `mart_attendance_exceptions` | **payroll** |
| `mart_attendance_trend` | payroll |
| `mart_attendance_by_department` | payroll |
| `mart_attendance_overtime` | payroll |
| `mart_attendance_by_project` | payroll, locations |

**The Attendance exceptions page does not light up with attendance alone** — it reconciles against payroll. Attendance and payroll unlock each other's exception surfaces; neither is complete without the other. Worth telling the client before they upload, because "I sent you attendance and the attendance exceptions page is still empty" is the reasonable complaint.

## 7. Sequence

1. **Fix §3 first** — the zeroing, before any real file. It is the one defect that makes a *served* figure wrong rather than absent.
2. **Inspect the export's header line** against §4 and rule on the relaxations. Per SP-007, when gating one of these read its siblings — `mart_attendance_kpis` has several figures of the same shape.
3. **Establish the true date span** of the export, and declare coverage to match exactly (§1).
4. **Preview only.** Expect the coverage gates to be the first failure.
5. Commit, run the pipeline, report in magnitudes and vocabulary.
6. **Record §5 in the referential-integrity plan** — independent of this load, and useful to that cycle whenever it runs.

## 8. Test obligations, when built

1. A file with no schedule renders lateness as **withheld**, not `0`, and `attendance_compliance_pct` does not rise because lateness stopped being measurable.
2. A file *with* a schedule renders lateness exactly as today (the tamper).
3. A partial upload with a correctly declared window: uncovered days are NULL, covered days with no row are absences, and `mart_attendance_coverage` reports the ratio.
4. A row outside the declared window aborts, naming the dates.
5. An attendance row for an unknown employee is visible in **both** models, or its exclusion from the calendar is deliberate and stated.
6. Demo byte-identity.

## 9. Cost and risk

The load mechanics are well built — Category F is the most carefully reasoned thing in the repository, and its comments show it.

**The risk is concentrated in two places.** §3 is a served figure that is wrong, and it is live the moment a schedule-less file loads. §1 is an operator declaration with no safety net: declare a window wider than the data and the system manufactures absences by design, correctly, from a wrong premise. The first is ours to fix; the second is a runbook and a conversation with the client.

---

**Not built. Awaiting a ruling.**
