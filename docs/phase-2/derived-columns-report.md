# Derived columns and two inversions — Execution Report

**Branch:** `phase-2/derived-columns` off `main` @ `a41c9b1` · **Date:** 2026-08-17
**Plan:** [`derived-columns-plan.md`](derived-columns-plan.md) (approved with rulings) · **Status:** PR open, **not merged**

Per SP-003 this report carries magnitudes and vocabulary only.

---

## 1. What actually changed

Three columns stopped being things a client is asked to compute for us:

| column | contract | derived from |
|---|---|---|
| `sla_breached` | hr_requests | `created_at`, `sla_hours`, `closed_at` **+ the run's reference time** |
| `net_late_minutes` | attendance | `late_minutes`, `excused_late_minutes` |
| `missing_punch_count` | attendance | `actual_check_in`, `actual_check_out` |

**This is a correction of what the column is.** Fewer required columns is the consequence:

| contract | before | after |
|---|---|---|
| `attendance` | 13 / 15 | **11 / 15** |
| `compliance` | 11 / 13 | **8 / 13** |
| `hr_requests` | 9 / 11 | **8 / 11** |

`occupation_match_status` moved to the referential-integrity cycle (§6).

## 2. The mechanism, extended without disturbing what used it

`derive_column` took **one** source column; `is_saudi` was the only derived column in the repository and remains single-source. The extension is additive:

- `derived_from` accepts a name **or a list**. The single-name form is unchanged and pinned by test.
- A rule may declare it needs a **run parameter**. `sla_breached` is the case: *"breached"* for a still-open request means the deadline is behind us, and **no column carries "now"**.
- The parameter is declared in `_PARAMETERISED`, in reviewed code — **contracts still name a rule and never carry an expression or a parameter.**

## 3. Ordering — the relax cycle's lesson with the steps reversed (ruling 4)

`complete_canonical_shape` **excludes** anything carrying `derivation:`, because pre-filling a derived column as typed NULL makes ingest's derive-when-absent branch skip itself — the `is_saudi` disaster, where every Saudization figure would compute from nulls.

So the moment a column is declared derived it stops being shape-completed. **If the contract key lands before the ingest branch, the column is neither completed nor derived, and the first consumer raises `ColumnNotFoundError`.**

The contract-relax cycle learned the mirror image: `required: false` alone accepts the file and *then* crashes, so shape completion had to land first. **Here the order is inverted** — registry rule and ingest branch first, then the contract keys, then relax. Same crash from the opposite direction.

A test asserts every column declaring `derivation:` has a matching ingest branch, so the trap cannot be re-entered silently.

## 4. The three absent-column behaviours (ruling 5)

Each handled explicitly, ranked as ruled.

### 4.1 SILENT — fixed first

```
validate_data SLA filter, column absent (all NULL):
   rows matched by (sla_breached == True): 0 of 3
```

`NULL == True` is NULL, so every row was dropped and **the file reported as having no SLA breaches** — a clean bill of health for the domain whose entire purpose is SLA tracking. Ranked first because a check that goes quiet is worse than one that gets noisy: **noise gets noticed.**

Now `eq_missing(True)`, gated on provision, with an explicit coverage line when the column is neither supplied nor derivable. A sparse *provided* column still yields its real breaches — tested.

### 4.2 MAXIMAL — the `manager_id` shape, twice

```
net_late mismatch check, column absent : 2 of 3 rows flagged
compliance qiwa / health arms, absent  : 3 of 3 rows flagged
```

`COALESCE(net_late_minutes, 0) != calculated` reads an absent column as the source system claiming zero, so every genuinely-late row became a "mismatch". The compliance arms flag NULL explicitly.

All three gated. The `mudad` arm was already gated on `has_wps_source_sql` — that was the precedent, and it had two ungated siblings.

### 4.3 SAFE — checked, and it does not carry

The compliance-ratio expression looked exactly like the payroll composite that discarded real allowances:

```sql
COUNT(CASE WHEN calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0 THEN 1 END)
```

**Measured with the column NULL and with it `0`: identical.** `COUNT(CASE …)` skips NULL and FALSE alike, so a NULL in an OR chain does not shift the ratio.

Recorded and tested **because the payroll cycle established the opposite reflex**. SP-005 is exactly about a premise that carries when it should not; this one was checked rather than assumed, and it did not.

## 5. `net_late_minutes` — relaxed, not removed (ruling 2)

`base_attendance_current` already computes `calculated_net_late_minutes`, and `mart_attendance_exceptions` **compares the client's supplied figure against ours**. The supplied column is evidence about their attendance engine — whether it agrees with our arithmetic — and that reconciliation is worth more than the required flag.

So it follows the `cost_center` pattern: **derive when absent, take the file at its word when supplied, and gate the mismatch check on provision.** Comparing our derivation against our derivation would agree by construction and say nothing.

The general rule for this class, worth carrying: **derive it always; reconcile against it when offered.**

## 6. The two inversions (ruling 6)

**Attendance was internally incoherent, not merely backwards.** It required `missing_punch_count` while treating `actual_check_in` / `actual_check_out` — the columns that figure is computed from — as optional. Punches are now **required**, the schedule **optional**: a biometric terminal certainly produces punches; a schedule needs a rostering system many clients do not export. A test asserts the punches are required *because* a derivation reads them, so the two cannot drift apart again.

**Compliance**: the three platform statuses are now optional. A client using only Qiwa cannot supply Mudad status whatever file it arrives in. `iqama_expiry` stays optional and `employee_id` / `period` stay required.

**The A5 shape question is untouched** — whether compliance is one file or several is unaffected by this, since the relaxation is correct under either answer.

## 7. `occupation_match_status` moved (ruling 1)

Recorded in [`referential-integrity-plan.md` §7](referential-integrity-plan.md), where that cycle will meet it. Its comparison crosses a domain boundary that plan is designing; settling it as a side effect of a contract edit is how payroll reached 13-of-13.

**It stays required until the derivation lands there** — relaxing it first would leave the maximal firer running on a column nothing produces, which is worse than the present state.

## 8. Proof the derivations work

```
attendance without net_late_minutes / missing_punch_count:
   net_late_minutes    -> [25, 0]      (30-5, and 10-20 floored)
   missing_punch_count -> [0, 2]       (row 2 has neither punch)

hr_requests without sla_breached:
   sla_breached -> [False, True, None] (closed in time / open past deadline /
                                        no target, so unknowable)

a file that SUPPLIES the column:
   supplied 999 -> ['999','999']       derived flag: False
```

The last line is the `is_saudi` rule holding: a file that supplies the column is taken at its word, which is what keeps the reconciliation in §5 meaningful.

## 9. Verification

| Check | Result |
|---|---|
| pytest | **623 passed** (594 + 29 new) |
| Isolation check | `PASSED - 62 file(s) byte-identical` |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` |
| flake8 (CI gate) | 0 |
| Client load | unchanged, `data/raw` byte-identical |

Demo supplies every column touched here, so no derivation fires and every gate is TRUE — which is the check that this is a correction and not a behaviour change.

## 10. One pinned test updated

`test_the_workspace_returns_their_columns_with_samples` asserted the derivation registry exhaustively as `["nationality_is_saudi"]`. It now lists four. The exhaustive form is kept deliberately: a rule appearing there changes what a client is asked to upload, so it should be a reviewed change rather than an incidental one. Per SP-002, recorded as a change of **wording**, not of the claim.

## 11. Open

1. **CARRIED INTO A4 (attendance load), ruled 2026-08-17.** `scheduled_start` / `scheduled_end` are now optional, and `calculated_net_late_minutes` falls to `0` when they are absent — its expression already guards `scheduled_start IS NOT NULL`. That is the zeroing shape and wants the withheld treatment. It is a consequence of this change rather than a pre-existing defect, and it is not client-visible until an attendance file loads — so it is **tested against a real file rather than reasoned about**, which is why it belongs to A4 and not here.
2. **`occupation_match_status` remains required** until the referential-integrity cycle.
3. **The A5 compliance shape question** stays deferred with its recorded reasoning.

---

**Not merged. Awaiting review.**
