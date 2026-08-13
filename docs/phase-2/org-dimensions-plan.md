# Organisational Dimensions — location, project, department (PLAN ONLY)

**Branch:** `phase-2/org-dimensions` off `main` @ `b705194` · **Date:** 2026-08-12
**Status:** PLAN ONLY. Nothing implemented.
**Depends on:** mapping cycle A (merged, #26) for the profile mechanism; cycle B (#27, open) for the screen. Neither blocks this plan.

The brief is right about the defect and right about the direction. It is wrong in three factual particulars, and one of them changes what the first commit is. Those come first.

---

## 1. What the code says that the brief does not

### 1.1 `project` already MEANS location — the contract says so in writing

`employees_schema.yml`, `work_unit.description_en`, shipped and in force today:

> "Work unit within a department. **The organisational hierarchy is Location -> Department -> Work Unit: the location (the `project` column) is the physical site** and contains multiple departments, and each department contains one or more work units."

So the atomic organisational unit is not missing. It is present, it is named `project`, and a contract column's own description already tells a client that `project` means *the physical site*.

**This changes the shape of the work.** Direction 1 is not "introduce location"; it is **rename `project` to `location` so the column's name matches the meaning the contract already publishes**. And direction 2 is not "extract location out of project"; it is **add the project grouping that never existed** — today there is nothing above the site.

That is a better change than the brief describes, and a cheaper one: no employee's site assignment moves, because the column already holds sites. It also means the migration has an exact, checkable invariant (§5.1) rather than a judgement call.

### 1.2 `project` is on FOUR contracts, not one

| contract | has `project` | how the `*_by_project` mart groups |
|---|---|---|
| `employees` | yes, required | `mart_saudization_by_project` — `GROUP BY project` on the employee row |
| `payroll` | yes, required | `mart_payroll_by_project` — `GROUP BY project` on the **payroll** row |
| `attendance` | yes, required | `mart_attendance_by_project` — `GROUP BY a.project` on the **attendance** row |
| `hr_requests` | yes, required | (feeds `mart_er_cases_by_project` via `base_er_cases_current`) |
| `compliance`, `employee_relations` | no | — |

"`project` stops being an employee column" is therefore a four-contract change, and it raises a design question the brief does not settle:

> **Does a fact row carry its own site, or does it inherit the employee's?**

**Recommendation: every fact keeps its own `location`.** In construction and facilities work an employee based at Site 1 legitimately books a month of attendance and payroll at Site 2. Collapsing the fact's site into the employee's home site would invent an attribution the source data did not make — the same class of error as the `project` fiction this cycle exists to remove, arriving from the opposite direction. It also costs nothing: the column already exists on all four contracts and only needs renaming.

### 1.3 There are SEVEN `*_by_project` marts, and the brief's "four" is the right four for the wrong reason

```
mart_saudization_by_project    employees                          CONTRACTED
mart_payroll_by_project        employees, payroll                 CONTRACTED
mart_attendance_by_project     attendance, employees, payroll     CONTRACTED
mart_er_cases_by_project       employee_relations, employees, hr_requests   CONTRACTED
mart_learning_by_project       employees, talent                  uncontracted
mart_performance_by_project    employees, talent                  uncontracted
mart_recruitment_by_project    recruitment                        uncontracted
```

The four contracted ones are exactly the four to fix. The other three read `talent` and `recruitment`, which have no contracts and therefore already gate off entirely in real mode — so they cannot currently show a project fiction to a real client. **They will become in-scope the day those domains get contracts**, and the plan below leaves them working on the same reference table so that day is a no-op.

### 1.4 Two smaller facts that bear on the design

**`work_unit` and `end_of_service_type` are contract columns with no consumer anywhere.** Neither appears in `data/silver/employees.parquet` (21 columns against the contract's 23), in the warehouse, in dbt, in the API or in the frontend. Ingest writes whatever columns the file has — there is no projection — and the demo sample simply does not emit them. A real client supplying `work_unit` today would have it validated at the gate and then silently carried into silver and ignored by every model, because `stg_employees` is `SELECT *`.

**`mart_command_center_filter_options` already has a `locations` field, hardcoded to `CAST([] AS VARCHAR[])`.** The product anticipated this dimension and stubbed it. It is also, precisely, the `[]`-not-`null` anti-pattern three cycles of suppression work were spent removing: an empty array claims "this client has no locations" where the truth is "nothing has ever populated this".

---

## 2. The model

```
locations  (reference dimension, its own contract)
  location            PK, the atomic unit. Every deployment has one.
  project             optional. The grouping above the site.
  region              optional.
  phase               optional.

employees / payroll / attendance / hr_requests
  location            the site this row belongs to (renamed from `project`)
  department          orthogonal to both - see 2.2
```

### 2.1 Why `location` is required and `project` is optional

A flat-site organisation — one office, no project concept — provides a `locations` file with one row and an empty `project`. The `*_by_project` marts then have nothing to group by and **suppress**, which is correct: that organisation has no project analytics because it has no projects, and showing it a single bucket named after its office would be a fiction of the same family.

A hierarchical organisation provides `location -> project`, optionally with `region` and `phase`. Cross-cutting departments need no special handling at all: Safety staff are deployed to a site like anyone else, and `department = 'Safety'` spanning many sites is just a department spanning many sites.

### 2.2 Department is orthogonal — and the contract text disagrees, so the contract text is wrong

Direction 5 says department stays orthogonal. The **data agrees** — measured on the demo warehouse:

```
Engineering   PROJ-BETA 4   PROJ-GAMMA 1
HR            PROJ-ALPHA 3  PROJ-GAMMA 1
Operations    PROJ-ALPHA 1  PROJ-GAMMA 5
```

Departments already span sites. But the `work_unit` description quoted in §1.1 asserts a **nested** hierarchy — "the location … contains multiple departments" — which would make `Engineering@BETA` and `Engineering@GAMMA` different departments. That is false in the demo data and false for every cross-cutting function the brief names.

**The contract text is corrected in this cycle**, in place, with the original wording recorded beside it — the same treatment `PRODUCT-ARCHITECTURE` §4 got when its "sample values" instruction turned out to be wrong. Left alone it would be read by whoever builds the department rollup next.

### 2.3 What `work_unit` means in this model

Today: **nothing.** It is a column with a description asserting a hierarchy the system does not implement and no consumer that could implement it.

Three honest options:

| | |
|---|---|
| **A. Keep as free text under `department`** *(recommended)* | It is a real thing in real HRIS exports (`Payables` under `Finance`), it is already optional, and it costs nothing to leave. Its description is corrected to say `department -> work_unit` with **no** claim about location. |
| **B. Promote to a second reference dimension** | Premature. Nothing consumes department rollups yet, let alone work-unit rollups. |
| **C. Drop it** | Loses a column real exports carry and clients will want later; a removed contract column is a breaking change to anyone already mapping it. |

**Recommend A**, and record explicitly that `work_unit` remains unconsumed so nobody later reads its presence as a feature.

### 2.4 Matrix assignment stays possible (direction 6, confirmed)

Matrix assignment is `employee x project x allocation` over time. This design does not preclude it, and the reason is structural rather than hopeful: **`location` on a row is a statement about that row, not about the employee's identity.** A future `assignments` table (`employee_id, project, allocation_pct, valid_from, valid_to`) becomes a *second* path from a fact to a project, and the marts choose: `assignments` where one exists for that employee and period, `locations` otherwise.

Two things must hold for that to stay true, and both are cheap now:

1. **The join lives in a `base_` model, not repeated in seven marts.** A single `base_row_project` (or a macro) resolves row → project. Adding matrix assignment then changes one model. Repeating the join seven times is what would preclude it.
2. **`locations.project` must never be treated as an employee attribute.** No mart may write `employees.project`. A test can assert that: no model selects `project` directly off `stg_employees`.

What this design *does* preclude is an employee being at two sites simultaneously on one fact row — which is correct, because a payroll line or an attendance day happens at one place.

---

## 3. Suppression when no locations file is provided (direction 4)

Mechanically this is the existing machinery and needs no new concepts:

1. `data/contracts/locations_schema.yml` makes `locations` contracted, which makes it **real-sourceable automatically** — see §4.
2. `config/metric_provenance.yml`: `domains.contracted` gains `locations` (a test already enforces that this list equals the contracts directory), and each of the four contracted `*_by_project` marts gains `locations` to its `domains` list.
3. A deployment that does not declare `locations` gets a typed empty table via the existing `write_empty_table`, and `Provenance.payload()` suppresses the four marts — `null`, never `[]`, with the domain named in both languages on the sibling block.

**One decision the machinery does not make for us.** With a locations file present but a given site missing from it, the join yields NULL. Today the marts write `COALESCE(project, 'Unassigned')` and `COALESCE(a.project, 'Missing Project')` — two different sentinel strings for the same condition, both rendering an absence as a bucket that looks like a real grouping.

**Proposal: an unmatched site is a data-quality EXCEPTION, not a bucket.** The row is counted in totals, excluded from the project breakdown, and the client is told on the Data Quality page which sites are missing from their locations file. That is the established REJECT/EXCEPTION split: the file is well-formed, specific rows have a problem, and the client gets *"these 3 sites are not in your locations file"* rather than a pie slice labelled "Unassigned".

---

## 4. Should `locations` be contracted and REAL_SOURCEABLE?

**Yes, and it is not really a choice — the repo settled it.** `real_sourceable_tables()` derives eligibility from `data/contracts/`, and the docstring records why:

> "a contract is precisely the artifact that makes a table safe to real-source, because it is what the hard gate validates against. Keeping a second hand-maintained list meant a contract could exist that nothing could use — the gap `employee_relations` sat in."

So writing the contract makes `locations` real-sourceable, gives it a template from `GET /api/data/templates`, and gives it mapping-profile support, all with no further wiring. A client's export will say `الموقع` / `Site` / `Site Code`, so it needs the mapping path as much as any other domain.

**Three ways `locations` is unlike the other six, each needing a decision:**

| | |
|---|---|
| **No `employee_id`** | Every existing contracted table is employee-grained. `validate_schema` is generic, but `validate_data.py` and the declared/populated guard must be checked against a table with a different key. **Step 1 verifies this before anything else is built.** |
| **Not date-grained, not history-declaring** | It joins neither `DATE_GRAINED` nor `HISTORY_DECLARING`. It is a dimension, not a period of facts. |
| **It is a slowly-changing dimension** | A site's project assignment changes — phase 1 ends, the site moves to phase 2. This plan stores the **current** mapping only, and last month's numbers will silently re-group when it changes. **Named as out of scope, not solved.** Effective-dating it is a real piece of work and belongs with matrix assignment, which has the same shape. Until then, a re-mapped site rewrites history, and that is a known limitation, not an oversight. |

---

## 5. Migration and demo byte-identity

### 5.1 The invariant

Demo byte-identity is a guardrail, and here it is **not structural** — this cycle changes the pipeline. It holds only if the migration is designed to make it hold, and the invariant is exact:

> For every fact row, `locations[row.location].project` must equal the value that row's `project` column holds today.

The demo sample generator emits `location` where it emitted `project`, plus a `locations_sample.csv` mapping each site to itself as a project. Every `GROUP BY` then produces identical keys and identical aggregates, including the `NULL`-project employee that currently lands in `'Unassigned'`.

**Identity mapping in demo is deliberate and its cost is stated:** the demo will not exercise a real many-sites-to-one-project rollup. A dedicated test fixture covers that instead — several locations under one project, one location with no project, one site absent from the file — so the interesting behaviour is tested even though the demo does not display it. The alternative, giving the demo a real hierarchy, would change every `by_project` figure and forfeit the byte-identity gate that has caught regressions in six consecutive cycles. Not worth it for a nicer demo.

### 5.2 The rename, and what it breaks for a client mid-flight

`project` → `location` on four contracts is a **breaking change to the canonical schema**. A client who has already mapped `project` has a profile pointing at a column that no longer exists, and `_validate_targets` will refuse to load it — loudly, naming the unknown column, which is the correct failure.

Options considered:

- **Accept a `project` alias on the contract** — rejected. Two names for one column is exactly the ambiguity this cycle removes.
- **Silent rename inside `apply_profile`** — rejected outright. A silent schema rewrite is the whole family of defect this codebase has been closing.
- **Fail loudly with a message naming the change** *(recommended)* — `_validate_targets` already refuses unknown targets; the message gains a specific case for `project` telling the operator it became `location` and that `project` now lives in the locations file.

Since `data/mapping/` is gitignored deployment state and no real client is yet live, the practical migration cost is a message, not a script. **If a deployment does exist by then, its profile needs one edit, and the error will say which.**

### 5.3 Blast radius, measured

| surface | count | notes |
|---|---|---|
| contracts | **4** carry `project` | + 1 new `locations_schema.yml` |
| dbt models mentioning `project` | **33** `.sql` files | most propagate it; ~12 need real edits |
| `*_by_project` marts | **7** (4 contracted, 3 gated) | all move to the shared join |
| provenance registry | 7 mart entries + `domains.contracted` | plus `mart_command_center_filter_options` |
| API routers referencing project | **10** files | mostly pass-through of mart payloads |
| frontend files | **13** | pages, `types.ts`, `api.ts` |
| tests that will fail loudly | `test_contracted_domains_match_the_contracts_directory`, `test_registry_shape`, the dbt-var pins, the demo gate | all self-enforcing — this is the machinery working |

The frontend is the least of it: `project` is a label on payloads the marts produce. `mart_command_center_filter_options.locations` finally gets a real value, and that field already exists end to end (`command_center.py:128`, `types.ts:955`).

---

## 6. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 0 | **Verify a non-employee-grained contracted table works** end to end — `validate_data`, the declared/populated guard, `write_empty_table` — with a throwaway contract. If it does not, that is the cycle, and the rest waits. | yes: a finding either way |
| 1 | `locations_schema.yml` + template + provenance `domains.contracted` + demo `locations_sample.csv` (identity mapping). Nothing consumes it yet. | yes — demo provably unchanged |
| 2 | Correct the `work_unit` description (§2.2), recording the original wording | yes |
| 3 | `base_row_project`: the single row → project join, with the unmatched-site EXCEPTION | yes — nothing reads it yet |
| 4 | Rename `project` → `location` on the four contracts + sample generator + `_validate_targets`' message | **the breaking step**; demo gate must be byte-identical here |
| 5 | Move the 4 contracted `*_by_project` marts onto `base_row_project`; add `locations` to their provenance domains | yes |
| 6 | `mart_command_center_filter_options.locations` stops being `[]`; the 3 uncontracted marts move to the same join | yes |
| 7 | Frontend labels + the suppression path for a deployment with no locations file | yes |

Steps 0–3 are additive and cannot change a demo number. Step 4 is the one that can, and it is deliberately alone.

---

## 7. Risks

1. **Step 0 is a genuine unknown.** Every contracted table today is employee-grained. If the guard machinery assumes that, the cycle's shape changes. It is first for exactly that reason.
2. **Step 4 is a breaking schema change with the demo gate as its only witness.** The gate is strong (5 pinned figures, 158 models, reconciliation) but it is a *demo* witness: it proves the identity mapping preserves the identity case, not that a real hierarchy rolls up correctly. §5.1's fixture is the mitigation and must land with step 3, not after step 5.
3. **The SCD gap will be discovered by a client, not by us,** unless it is written down where they will meet it. A site re-assigned to a new project silently re-groups last month's numbers. It should appear in the locations template's instructions, not only in this document.
4. **Seven marts, three of them gated, is a partial migration by design.** If the three uncontracted ones are left on the old shape, the day `talent` gets a contract they start showing a fiction. Step 6 moves them even though nothing serves them today — cheap now, a latent defect otherwise.
5. **`COALESCE(project, 'Unassigned')` vs `'Missing Project')`** — two sentinels for one condition, live today. Replacing both with an exception changes what a client sees on a screen they already use. That is a product change, not just a refactor, and should be flagged to whoever owns the copy.

---

## 8. Out of scope

- **Matrix assignment** (`employee x project x allocation`). Confirmed additive in §2.4; the `base_row_project` seam is what keeps it so.
- **Effective-dated locations** (SCD Type 2). Same shape as matrix assignment; they should be done together.
- **Department and work-unit rollup marts.** `department` becomes cleanly orthogonal here; nothing yet groups by it.
- **`work_unit` gaining a consumer.**
- **`end_of_service_type` gaining a consumer** — noted in §1.4 as unconsumed, and worth its own cycle since Article 80 exposure is a Phase 2 selling point that nothing currently computes.
- **TD-007 / TD-008 / TD-009**, unchanged.

---

**PLAN ONLY. Nothing implemented. Stopping for review.**
