# Derived columns, and two inversions — Plan

**Status:** PLAN ONLY. **Branch:** `phase-2/derived-columns` off `main` @ `a41c9b1` · **Date:** 2026-08-17
**Ruled:** outranks further relaxation. A correction of what the column *is*; four fewer required columns is the consequence.

---

## 1. The four are not one problem

The ruling names four columns as outputs of our analytics. They are — but they differ in **what they are derived from**, and that difference decides whether each is a contract edit or a mechanism change.

| column | contract | derived from | kind |
|---|---|---|---|
| `net_late_minutes` | attendance | `late_minutes`, `excused_late_minutes` | same file, 2 sources, both required |
| `missing_punch_count` | attendance | `actual_check_in`, `actual_check_out` | same file, 2 sources, **both currently optional** |
| `sla_breached` | hr_requests | `created_at`, `sla_hours`, `closed_at` **+ a reference time** | same file, 3 sources, one optional, **plus a parameter** |
| `occupation_match_status` | compliance | `occupation_code` **+ the employee's job title** | **cross-domain** (compliance × employees), enum-valued |

**`occupation_match_status` is not the same species as the other three.** Its comparison reaches into another domain, which is the boundary the [referential-integrity plan](referential-integrity-plan.md) is about. Deriving it at ingest would mean ingest reading a second silver table — a shape decision, not a contract edit.

**Recommendation: the first three this cycle; `occupation_match_status` moves to the referential-integrity cycle**, where the cross-domain boundary is already being designed. Doing it here would settle that boundary as a side effect of a contract edit.

## 2. The mechanism cannot express any of them yet

`derive_column` takes **one** source column:

```python
derived_from: nationality          # a single name
derivation: nationality_is_saudi
...
return resolve(rule)(source_values)  # one sequence
```

`is_saudi` is the only derived column in the repository and it is single-source. **All four candidates are multi-source**, and `sla_breached` additionally needs a reference time — *"breached"* for an open request means *now is past the deadline*, which no column carries.

So this cycle's first deliverable is **extending the mechanism**, not editing contracts:

- `derived_from` accepts a **list** of column names; the rule receives them by name.
- Single-name form keeps working unchanged — `is_saudi` must not be touched.
- A rule may declare a **parameter** it needs from the run (the report-period end for `sla_breached`), supplied by ingest rather than read from the file. It stays a registry lookup: **contracts still name a rule, never carry an expression.**

## 3. `net_late_minutes` is not simply a derived column — and this changes the ruling for it

`base_attendance_current` **already computes it**, as `calculated_net_late_minutes`. And `mart_attendance_exceptions` **compares the client's supplied value against ours**:

```sql
WHERE COALESCE(net_late_minutes, 0) != calculated_net_late_minutes
```
> *"Source net late minutes (X) does not match calculated (Y)"*

So the supplied column has a **second purpose**: it is evidence about the client's source system, and a disagreement is a real finding. Making it purely derived would **delete an existing reconciliation check**.

**The correct move is the `cost_center` pattern, not the `is_saudi` pattern**: make it **optional**, keep deriving `calculated_net_late_minutes` regardless, and keep the mismatch check **gated on the column being provided**. A client who supplies it gets the cross-check; a client who does not gets the derived figure and no noise.

That distinction — *derive it always, and reconcile against it when offered* — is worth stating as the general rule for this class. It applies to `missing_punch_count` too.

## 4. The payroll lesson, applied before relaxing (ruling 3)

Every consumer measured, not reasoned about.

### 4.1 Two checks fire MAXIMALLY when the column is absent

This is the `manager_id` shape — one exception per row about a fact of the client's export.

```
net_late_minutes mismatch check, column absent (all NULL):
   rows flagged: 2 of 3      <-- every row with any lateness

compliance occupation check, column absent:
   rows flagged: 3 of 3      <-- every row
```

`COALESCE(net_late_minutes, 0) != calculated` treats an absent column as a source system claiming zero, so every genuinely-late row becomes a "mismatch". `occupation_match_status IS NULL OR != 'Matched'` flags NULL explicitly. **Both must be gated on provision before either column is relaxed.**

### 4.2 One check falls SILENT when the column is absent

```
validate_data SLA filter with the column absent:
   rows matched by (sla_breached == True): 0 of 3
```

`NULL == True` is NULL, so the filter drops every row and **the file reports as having no SLA breaches**. The opposite failure to §4.1 and the more dangerous one: a clean bill of health for a domain whose whole purpose is SLA tracking. Deriving `sla_breached` fixes this at the root — but the filter should be NULL-safe regardless, because a *provided* column can also be sparse.

### 4.3 The OR-chain is safe — measured, and worth recording

The compliance-ratio expression looked like the payroll composite:

```sql
COUNT(CASE WHEN calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0 THEN 1 END)
```

Measured with `missing_punch_count` NULL and with it `0`: **identical results (2 of 3 both ways)**. `COUNT(CASE …)` skips NULL and FALSE alike, so a NULL in an OR chain does not shift the ratio.

Recorded because the payroll cycle established the opposite reflex, and SP-005 is exactly about premises that carry when they should not. **This one was checked and it does not.**

### 4.4 The zeroing shape

`COALESCE(SUM(missing_punch_count), 0)` in three marts → `0` when absent, reading as *"no punches were missed"*. Same treatment as `overtime_cost`: withheld, not zeroed.

## 5. The `is_saudi` trap — ordering (ruling 4)

`complete_canonical_shape` **excludes** any column carrying `derived_from` / `derivation`:

```
shape completion added: ['company', 'contract_end_date', 'cost_center', …]
is_saudi present after completion: False   <-- excluded, by design
```

The exclusion exists because pre-filling a derived column as typed NULL makes ingest's *"derive only when absent"* branch skip itself — every Saudization figure computed from nulls.

**The consequence for this cycle is a hard ordering constraint.** The moment a column is declared `derivation:`, it stops being shape-completed. If ingest has no branch that derives it, it is **neither completed nor derived**, and the first consumer raises `ColumnNotFoundError`.

So per column, in this order and not otherwise:

1. Add the rule to the registry and the ingest branch that calls it.
2. *Then* add `derived_from` / `derivation` to the contract.
3. *Then* relax `required`.

The contract-relax cycle learned the same lesson in the other direction — step 1 before step 2, because `required: false` alone accepts the file and then crashes. **This is that lesson with the steps in a different order, and getting it backwards produces the same crash.**

## 6. The two inversions

### Attendance — the schedule is required, the punches are optional

`scheduled_start` / `scheduled_end` are **required**; `actual_check_in` / `actual_check_out` are **optional**. Backwards: a biometric terminal certainly produces punches; a schedule needs a rostering system many clients do not export.

It is also **incoherent with §1**: `missing_punch_count` is derived *from the punches*, so the contract currently requires the derived figure while treating its own inputs as optional.

Proposed: punches **required**, schedule **optional**. With the schedule absent, `calculated_net_late_minutes` cannot be computed — its expression already guards `scheduled_start IS NOT NULL` and falls to `0`, which is the zeroing shape again and needs the same withheld treatment.

### Compliance — `iqama_expiry` optional, three platform statuses required

`iqama_expiry` is the most universally available compliance fact and feeds `iqama_expiring_30`; `qiwa_status`, `mudad_status`, `health_insurance_status` each require that the client uses that platform.

Proposed: relax the three platform statuses, keep `iqama_expiry` optional **but wire its absence to a coverage note** rather than a silent zero — `iqama_expiring_30` already returns `0` when the column is empty.

**This does not pre-empt the deferred shape question.** Whether compliance is one file or several ([deferred to A5](contract-audit.md), because it needs a real compliance export) is untouched: relaxing three statuses is correct under either answer, since a client using only Qiwa cannot supply Mudad status whatever file it arrives in.

## 7. Sequence

1. **Extend the derivation mechanism** — multi-source, and a rule-declared run parameter. `is_saudi` unchanged, pinned by test.
2. **`net_late_minutes`** — derive always, relax to optional, **gate the mismatch check**. The pattern the other two follow.
3. **`missing_punch_count`** — with the attendance inversion, since it derives from the punches.
4. **The attendance inversion**, including withheld treatment where the schedule is absent.
5. **`sla_breached`** — needs the run-parameter half of step 1; fix the silent filter regardless.
6. **The compliance status relaxations.**
7. **`occupation_match_status` → the referential-integrity cycle.**

Demo rebuild and byte-identity at each step; demo supplies every column here, so every gate is TRUE and demo must not move.

## 8. Test obligations (SP-001 — both halves)

1. Each derived column is computed when absent **and** taken at its word when supplied — the `is_saudi` rule, per column.
2. Both maximal-firing checks (§4.1) produce **zero** rows when the column is absent, and their real findings when it is present.
3. The SLA filter (§4.2) finds breaches in a sparse-but-provided column.
4. `is_saudi` still derives, and is still excluded from shape completion.
5. A column declared `derivation:` with **no** ingest branch fails loudly in a test rather than at a client's first upload (§5).
6. Multi-source and single-source `derived_from` both work; contracts still carry no expressions.
7. Demo byte-identity.

## 9. Cost and risk

Larger than it looks. The contract edits are trivial; **the mechanism extension and the consumer gating are the work**, and §5's ordering means each column is a small sequence rather than one line.

**The risk is §3**: `net_late_minutes` looks like the simplest of the four and is the one where the naive reading — *"it's derived, so stop requiring it"* — would silently delete a working reconciliation check. The other three have no such second purpose, which is exactly why it is worth naming.

---

**Not built. Awaiting a ruling — in particular on deferring `occupation_match_status` to the referential-integrity cycle (§1).**
