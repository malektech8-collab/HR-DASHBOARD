# Relaxing `company`, `job_family`, `cost_center` — Execution Report

**Branch:** `phase-2/contract-required-relax` off `main` @ `3a9dbb1` · **Date:** 2026-08-13
**Plan:** [`contract-required-relax-plan.md`](contract-required-relax-plan.md) (approved as written) · **Status:** PR open, **not merged**

Landed in the ruled order. Step 1 before step 2, because `required: false` alone accepts the file and then crashes.

---

## 1. (a) A file missing all three loads, and produces typed NULLs

```
columns in the file : 19  (canonical is 23)
absent              : ['company', 'job_family', 'cost_center']
validate_csv        : 0 reject(s), 0 exception(s)

after shape completion:
   added as typed NULL : ['company', 'cost_center', 'job_family']
   width               : 22
   company      dtype=String  nulls=2/2
   job_family   dtype=String  nulls=2/2
   cost_center  dtype=String  nulls=2/2

the crash this prevents, on the ORIGINAL frame:
   validate_data idiom      -> RAISES ColumnNotFoundError
   ...on the COMPLETED frame -> resolves, 2 rows
```

`complete_canonical_shape()` reuses `empty_frame_schema()` for the types, per ruling 1. A **required** column is never completed — its absence is still a REJECT, and filling it silently would be the fabrication this phase exists to remove.

### 1.1 A defect the proof caught, worth recording

The first run of the proof added **`is_saudi`** as a typed NULL. It is optional, so it qualified — and that would have been a silent, favourable-looking disaster: ingest derives `is_saudi` from nationality **only when the column is absent**, so pre-filling it as NULL makes the derivation skip itself, and every Saudization and Nitaqat figure would be computed from nulls.

Completion runs *after* derivation today, so it was latent rather than live. The fix excludes anything the contract marks `derived_from` / `derivation`, and it is belt and braces on purpose: the ordering is not obvious and the failure would have been quiet.

---

## 2. (b) An absent column is a coverage fact, not per-row exceptions

```
recorded absent      : ['company', 'cost_center', 'job_family']
provides cost_center : False
provides department  : True

has_cost_center_source_sql -> FALSE     (this client)
has_cost_center_source_sql -> TRUE      (a client who DOES supply it)
```

For a client with no cost-centre column, four surfaces would each have fired on **every employee** — `mart_workforce_exceptions`, `mart_compliance_exceptions`, `mart_payroll_exceptions`, and `validate_data` — plus a KPI equal to headcount. One row per person, on four surfaces, saying something true of their *export format* rather than their records, burying every real finding.

**Existing machinery, per ruling 2.** `build_warehouse` passes `has_cost_center_source_sql` from the onboarding registry, exactly as it already passes `has_gosi_source_sql` / `has_wps_source_sql`. `dbt_project.yml` defaults it `TRUE`, so every deployment that has not been through an upload behaves precisely as before.

**The two sentinels are deleted, not gated.** `COALESCE(e.cost_center, 'Missing Cost Center')` in `base_payroll_current` and `_previous` would have bucketed a client's payroll under a category literally named *Missing Cost Center* — `COALESCE(project, 'Unassigned')` in a second place. The NULL is kept and the exception mart tests for it directly.

`missing_cost_center_count` becomes **NULL rather than 0** when the column is absent. Zero reads as *"nobody is missing one"* — the fabricated-favourable answer.

### 2.1 Why provision is recorded rather than inferred

After completion the column exists and is NULL whether the client omitted it or supplied it blank. **Nullness can no longer answer the question**, so it is captured at ingest while it is still knowable. A test pins exactly that indistinguishability.

---

## 3. (c) A constant without `basis` or `asserted_by` is refused

```
company, no asserted_by and no basis  -> REFUSED: no asserted_by...
company, asserted_by but NO basis     -> REFUSED: no basis. State WHY...
company, basis but NO asserted_by     -> REFUSED: no asserted_by...
company, signed AND based             -> SAVED
```

A constant is **invisible once written** — the column ends up looking exactly like one the client supplied, and nothing downstream can tell the difference. `basis` is enforced as non-empty, which is all that can be enforced: *"single legal entity, confirmed with the HR manager"* is reviewable, and a constant with no basis is a guess that will later be mistaken for data. It is recorded in `evidence`, so accumulated profiles never teach an operator's assumption to the AI mapper as client data.

Two further guards: a constant may never **overwrite a mapped column**, and never targets a **required** column — otherwise it becomes a way past the required-columns gate, which is exactly what relaxing the three was meant to make unnecessary.

---

## 4. (d) The affirmation rule fires for `location`

```
company              affirmation=False   (free text)
cost_center          affirmation=False   (free text)
job_family           affirmation=False   (free text)
location             affirmation=True    (free text, feeds the locations join)
status               affirmation=True    (gated enum)
end_of_service_type  affirmation=True    (gated enum)
employment_type      affirmation=True    (gated enum)
```

A rule, not a list: **affirm wherever being wrong is not visible on the screen the client looks at.** `location` carries no `allowed_values`, so a type-based rule would let it through; it feeds the locations join, so a constant location for a multi-site client renders as a clean single-site chart.

Demonstrated on the only optional gated column, `end_of_service_type`: unaffirmed → **REFUSED**, affirmed → **SAVED**.

### 4.1 An honest limitation

**`location` is still `required: true`**, so the required-column guard refuses a location constant *before* the affirmation check is reached. The rule is implemented and unit-tested; it becomes **reachable** only if `location` is ever relaxed. Pinned by its own test so that two guards agreeing is not mistaken for one guard working.

---

## 5. `job_family` — stated, not worked around

Measured across `dbt_analytics/models`, `backend/app` and `frontend/src`: **zero consumers.** No mart, no KPI, no endpoint, no frontend. Relaxing it changes nothing observable because nothing observes it.

A test asserts it stays that way — if `job_family` gains a consumer, the contract's note saying it has none becomes wrong, and the test says so.

---

## 6. Parity delta

Measured with the pre-change contract taken from `main` via git:

```
case                                           BEFORE (main)             AFTER
------------------------------------------------------------------------------
missing all three                              REJECT (required-columns) ACCEPT  <- CHANGED
missing company only                           REJECT (required-columns) ACCEPT  <- CHANGED
missing a still-required column (department)   REJECT (required-columns) REJECT (required-columns)
all three present and populated                ACCEPT                    ACCEPT
all three present but BLANK on every row       ACCEPT                    ACCEPT
------------------------------------------------------------------------------
cases changed: 2 of 5

every other contracted table: identical before and after
```

The fifth row is the one that matters most: **relaxing `required` did not weaken the checks for clients who DO supply the column.** A blank cost centre in a provided column is still a data-quality exception.

---

## 7. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — identical, and asserted |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| pytest | **490 passed** (450 + 40 new) |
| flake8 | 0 on every changed file |

**One thing the demo revealed.** Shape completion reported that the *sample* data itself omits two optional columns:

```
[shape] employees: 2 optional column(s) absent from the client's file,
        added as typed NULL: ['end_of_service_type', 'work_unit']
```

Both were previously absent from silver entirely. They are now typed NULLs, the warehouse carries the full canonical shape, and the five pinned figures are unchanged — so this is a strict improvement rather than a behaviour change.

**Environmental note.** The repo `.env` is set for the real load (`DATA_MODE=real`, `REPORT_MONTH=2026-08`), so demo verification needs both overridden explicitly. Two `test_contract_exceptions` tests fail without that — they run the pipeline and hit the period-mismatch guard. Confirmed environmental, not caused by this change. GAP-002 in its benign form.

---

## 8. Open

1. **The mapping CLI and screen do not yet support `constants`.** The mechanism, its guards and its tests are in; the operator-facing half is not. A profile with constants must currently be authored by hand or by a script — which is the same position cycle A was in before the CLI.
2. **`location`'s affirmation is unreachable** (§4.1) until `location` is relaxed, which is not proposed here.
3. **Column-grain provision is not surfaced in the UI.** The checks consume it; the Data Quality page does not yet render *"this client does not track cost centres"* as a coverage note. That was step 4's minimum and is the honest gap — the exceptions are suppressed, but nothing yet explains their absence to the client.
4. **Three relaxations invite a fourth.** `grade`, `job_title` and `employment_type` are the next most likely to be missing from a small client's export. Step 1 makes each future relaxation a one-line contract change; none is pre-emptively made.

---

**Not merged. Awaiting review.**
