# Relaxing `company`, `job_family`, `cost_center` (PLAN ONLY)

**Branch:** `phase-2/contract-required-relax` off `main` @ `3a9dbb1` · **Date:** 2026-08-13
**Status:** PLAN ONLY. Nothing implemented.
**Assessment adopted:** these are contract defects, not client gaps. `company` assumes a multi-entity client; `job_family` is a derived taxonomy, not a source field; `cost_center` usually lives in finance, not HR.

The assessment is right, and the fix is larger than the contract. **`required: false` on its own does not make the file load — it makes the pipeline crash later instead of rejecting early.** That is measured, not predicted, and it comes first.

---

## 0. BLOCKING FINDING — the pipeline assumes these columns EXIST, not merely that they are populated

`required: true` guaranteed two different things at once, and only one of them is being relaxed:

1. the column is **present** in the file, and
2. it therefore **exists** in every downstream frame and table.

Relaxing to `required: false` removes the first. Nothing downstream was ever written for the second. Measured on synthetic frames:

```
1) validate_data's idiom - pl.col('cost_center') on a frame without it
     -> RAISES ColumnNotFoundError: unable to find column "cost_center"

2) dbt's idiom - COALESCE(e.cost_center, 'Missing Cost Center') on a table without it
     -> RAISES BinderException: Table "e" does not have a column named "cost_center"
```

So a client who simply does not have the column would get, in order: no rejection at the gate (good), then a crash in `validate_data.py:135`, or — if that were guarded — a dbt binder error at `base_payroll_current`. **The client's file would be accepted and then break the pipeline**, which is worse than today's honest rejection.

This is the same failure the org-dimensions cycle hit when `project` was renamed: `pl.col("project")` on a frame that no longer had it. It is a known shape in this codebase and it will recur every time an optional column is added.

### 0.1 The fix — complete the canonical shape at ingest

**Recommendation: after mapping and before writing silver, add any absent OPTIONAL canonical column as a typed NULL column.**

| | |
|---|---|
| Why here | Silver then always carries the full canonical shape. dbt binds, `validate_data` finds the column, and the value is `NULL` — which every consumer already handles, because `NULL` was always possible for the optional columns |
| Why not guard each consumer | 12 dbt references for `cost_center` alone, plus `validate_data`. Guarding each is 13 places to get right and one to forget; completing the shape is one place |
| Precedent | `onboarding.empty_frame_schema()` already builds a typed 23-column frame for exactly this reason — an undeclared domain must produce an EMPTY table, not a MISSING one, because "a missing parquet is skipped by build_warehouse and dbt then fails with a catalog error." Identical reasoning, one level down |
| What it must NOT do | complete a **required** column. A missing required column is still a REJECT at the gate, and silently filling it would be the fabrication this whole phase removes |

---

## 1. Consumer assessment, per column

Measured by grep across `dbt_analytics/models`, `backend/app`, `frontend/src`, `scripts`.

### 1.1 `company` — 5 references, none load-bearing. Cheapest of the three.

| Consumer | What it does with a null |
|---|---|
| `base_compliance_current`, `base_er_cases_current` | pass-through `e.company`. Null flows, nothing branches on it |
| `mart_command_center_filter_options.companies` | `WHERE company IS NOT NULL` — **already honest**; the filter list is simply empty |
| `mart_exec_trends`, `mart_workforce_headcount_trend` | comment text only, no code |

**No exception check, no KPI, no frontend.** Relaxing `company` needs only §0's shape completion.

### 1.2 `job_family` — zero consumers

Not one reference in dbt, backend or frontend. The only hit anywhere is the sample generator's own column list. It reaches the warehouse and is read by nothing — the same state `end_of_service_type` was in before the last cycle.

Relaxing it is free, and the honest note is that **making it optional changes nothing observable**, because nothing observes it.

### 1.3 `cost_center` — 12 references, and this is where the work is

| Consumer | What it does with a null |
|---|---|
| `base_payroll_current` / `_previous` | **`COALESCE(e.cost_center, 'Missing Cost Center')`** — the sentinel-bucket defect, twice |
| `mart_payroll_exceptions` | one EXCEPTION per row where null, empty, **or** the sentinel |
| `mart_compliance_exceptions` | one EXCEPTION per row where null or blank |
| `mart_workforce_exceptions` | one EXCEPTION per row where null or blank |
| `mart_workforce_kpis.missing_cost_center_count` | counts them as a KPI |
| `validate_data.py:135` | a per-employee "Missing Cost Center" data-quality issue |
| `mart_command_center_filter_options.cost_centers` | `WHERE cost_center IS NOT NULL` — already honest |
| `base_government_platform_records`, `base_requisition_source_records` | pass-through / recruitment's own column |

**The consequence, stated plainly.** For a client who has no cost-centre column, every one of these fires on **every employee**. Four separate surfaces would each report, per person, that a cost centre is missing — plus a KPI equal to headcount and a payroll bucket literally named `'Missing Cost Center'`.

That is thousands of data-quality rows telling the client something that is true of their *export format*, not of their *records*, and it would bury every real finding on the page. It is the `COALESCE(project, 'Unassigned')` defect in a new place: **an absence rendered as a per-row defect.**

### 1.4 The distinction the codebase does not currently draw

> **A missing VALUE in a column the client provided** is a data-quality exception: this record is incomplete, and someone should fix it.
>
> **An entirely ABSENT column** is a coverage fact: this client does not track that concept, and no amount of HR work will change it.

Today the checks conflate them, and they were entitled to — `required: true` meant the column was always there, so a null could only be the first kind. Relaxing that makes the distinction real and the checks wrong.

**Recommendation: the exception checks must be scoped to columns the client actually provided.** The `domain_provenance` / suppression machinery already carries "what did this client give us" at domain grain; this is the same question at column grain. Concretely: record which optional canonical columns were present in the uploaded file, and have the four cost-centre checks skip when the column was absent — while continuing to fire, unchanged, when it was present and a row is blank.

**Suppression must withhold, not bucket.** Per the ruling, `COALESCE(e.cost_center, 'Missing Cost Center')` must not become the answer for an absent column. A payroll breakdown by cost centre for a client with no cost centres should be **withheld with a coverage note**, exactly as the by-project marts are withheld when no locations file is supplied.

---

## 2. Constant mappings

The mapping profile can rename, map values and derive. It cannot say *"this client is one legal entity; `company` is `'X'` for every row"* — which is precisely the single-entity case that makes `company` a contract defect.

### 2.1 Shape

```yaml
constants:
  company:
    value: "Acme Contracting Co."
    asserted_by: operator@client.example
    asserted_at: 2026-08-13T09:14:22
    basis: >-
      Single legal entity. Confirmed with the client's HR manager; their Jisr
      deployment holds one company and the export therefore has no column.
```

Applied in `apply_profile` after renaming and before derivation, so a derived column can read a constant. **Row-preserving** like every other step: it adds a column, it does not filter.

### 2.2 A constant is an ASSERTION, and needs the same treatment as a value mapping

This is the substance of the ruling and I agree with it entirely.

A value mapping asserts *"this client's word means that canonical value"*. A constant asserts *"this fact is true of every employee in this file"* — a claim about the client's organisational structure, made by an operator, applied to every row, and **invisible thereafter**: once written, `company` looks exactly like a column the client supplied. Nothing downstream can tell the difference.

So it takes the same controls, and for the same reasons:

- **`asserted_by` is required**, enforced at the write like `created_by`. An unsigned claim about a client's legal structure is not reviewable.
- **`basis` is required** — free text, and the requirement is that it is non-empty. *"Single legal entity, confirmed with the HR manager"* is a reviewable claim; a constant with no stated basis is a guess someone will later mistake for data.
- **Recorded in `evidence`**, so the accumulated profiles show which values were supplied by the client and which were asserted by us. Without that, the training substrate for §5's AI mapper would learn an operator's assumption as though it were a client's data.

### 2.3 Does it need an affirmation?

**Recommendation: yes for a constant on a REJECT-enum column; no for a free-text column — with one exception.**

The affirmation exists because a value mapping into a gated enum is *silent and consequential*. Apply the same test:

| Constant on… | Affirmation? | Why |
|---|---|---|
| `company`, `cost_center`, `job_family` | **no** | Free text. Wrong is visible — every row reads the same wrong company name, on screen, and the client notices immediately |
| any column with `allowed_values` | **yes** | Same silence as a value mapping: a constant `status: Active` would mark every leaver active, and nothing would look odd |
| `location` | **yes**, and this is the exception | Free text, but it feeds the `locations` join and therefore every project figure. A constant location for a multi-site client is a fabrication that renders as a clean single-site chart — silent, and exactly the family the org-dimensions cycle removed |

The general rule that generates the table: **require an affirmation wherever being wrong is not visible on the screen the client looks at.**

### 2.4 What a constant must never be allowed to do

- **Fill a required column to get a file past the gate.** That is the failure mode this whole mechanism could become: the gate says `company` is required, and a constant makes it stop complaining. `company` is being relaxed to optional precisely so a constant is a *choice* rather than a *workaround*. Worth a guard: refuse a constant on a column the operator has also mapped, so it cannot silently override real data.
- **Be confused with client data downstream.** §2.2's `evidence` record is the mitigation; there is no runtime marker on the column itself, and I would not add one — a `company_is_asserted` column would spread through 12 marts and be ignored by all of them.

---

## 3. Parity delta

**Claim: files previously rejected for missing these three now pass; nothing else changes.**

To be **run and quoted in the report**, not asserted, with the before-contract taken from `main` via git as in the last cycle:

| Case | Before | After |
|---|---|---|
| file missing all three columns | REJECT (`required-columns`) | **ACCEPT** |
| file missing `company` only | REJECT | **ACCEPT** |
| file missing a still-required column (`employee_id`, `department`, …) | REJECT | **REJECT**, unchanged |
| file with all three present and populated | ACCEPT | ACCEPT, unchanged |
| file with all three present but blank on some rows | ACCEPT + exceptions | ACCEPT + the same exceptions |
| every other contracted table | unchanged | unchanged |

The fifth row is the one that matters most: **relaxing `required` must not weaken the checks for clients who DO supply the column.** A blank cost centre in a provided column is still a data-quality exception.

### 3.1 Demo byte-identity

**Structural, and verified in advance.** Measured on the demo warehouse: `company` missing on 0 of 21 employees, `cost_center` missing on 1 of 21 — that one row is an existing, pinned data-quality exception. The sample generator supplies all three columns, so relaxing `required` changes nothing the demo does, and §0's shape completion never fires because no canonical column is absent.

The five pinned figures are asserted by `test_demo_gate.py`, so this is enforced rather than eyeballed. The gate is still run, with `DATA_MODE=demo` overridden explicitly — the repo `.env` is now set for the real load.

---

## 4. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 1 | Complete the canonical shape at ingest: absent **optional** columns become typed NULLs; absent **required** columns still REJECT | **yes, and it must land first** — without it the other steps produce a crash instead of a rejection |
| 2 | `required: false` on the three, with descriptions saying what absence means | yes |
| 3 | Record which optional columns the upload actually provided | yes |
| 4 | Scope the four cost-centre exception checks to provided columns; replace the `'Missing Cost Center'` COALESCE with a withheld breakdown + coverage note | yes — and it is the step that stops thousands of false exceptions |
| 5 | `constants:` in the profile: `asserted_by`, `basis`, evidence, affirmation for gated and `location` | yes |
| 6 | CLI + mapping screen support for constants | the operator-facing half |

**Steps 1 and 2 together unblock the first real load** if the operator is willing to accept the cost-centre exception noise for one cycle. Step 4 is what makes the Data Quality page usable for that client. If the load is urgent, 1–2 ship and 4 follows immediately; **shipping 2 without 1 must not happen**, and that is the only hard ordering constraint here.

---

## 5. Risks

1. **Shape completion is a silent change to what silver contains.** A column that was absent now exists and is null. That is the intent, but it means "the column is missing" stops being expressible downstream — which is exactly why step 3 records provision separately rather than inferring it from nullness.
2. **Step 4 changes what an existing client sees.** Any deployment already relying on "Missing Cost Center" exceptions would see them disappear for absent columns. Correct, and worth saying out loud rather than discovering.
3. **Constants will be used to skip mapping work.** The `basis` requirement is the whole defence, and it is a text field — enforceable as non-empty, not as true. Attribution is a record, not an authentication, exactly as with `created_by`.
4. **Three relaxations invite a fourth.** `manager_id` and `work_unit` are already optional; `grade`, `job_title` and `employment_type` are the next most likely to be missing from a small client's export. The plan does not pre-relax them — but the shape-completion work in step 1 is what makes each future relaxation a one-line contract change instead of a cycle.

---

## 6. Out of scope

- **Relaxing any other column.** Three, assessed individually, on the evidence of one real export.
- **A runtime marker distinguishing asserted values from client data** (§2.4).
- **`job_family` gaining a consumer.** Recorded as unconsumed; not this cycle's problem.
- **Column-grain provenance in the API/UI.** Step 3 records provision for the checks; surfacing it on the Data Quality page as a coverage note is step 4's minimum, and a fuller treatment is its own cycle.

---

**PLAN ONLY. Nothing implemented. Stopping for review.**
