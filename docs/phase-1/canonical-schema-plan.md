# Phase 1 — Bilingual Canonical Schema (PLAN ONLY)

**Status:** proposed. Nothing implemented. This document is the only file added on `phase-1/canonical-schema`.
**Branch:** `phase-1/canonical-schema` off `main` @ `2257d4a` · **Date:** 2026-08-10
**Governing reference:** [`docs/PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4 (canonical schema and template flow).
**Guardrails honoured:** plan only; no file touched; `data_mode=demo` unchanged; validator behaviour unchanged this cycle; no real data accessed or generated.

> **Correction (2026-08-10).** This document originally stated a total of **84 columns**, and listed `payroll` as 14. Both figures were wrong: the real total is **73** (employees 21, payroll 13, attendance 15, compliance 13, hr_requests 11). The per-column enumerations below were always correct — only the counts were not. Verified against `main`: column names and order are identical between the original and extended contracts, so nothing was lost. Corrected in place below; this note records what was originally claimed. Note that 73 is the total **as this cycle was executed** — PR #10 subsequently added two optional employees columns (`work_unit`, `end_of_service_type`), so the current total on `main` is **75**. The figures in this document describe the state it reports on and are not updated as the schema grows.

> **Housekeeping flag:** `docs/PRODUCT-ARCHITECTURE.md` is present in the working tree but **untracked** — it is not committed on `main` or any branch. The governing reference for every future cycle should be in version control. Recommend committing it before or alongside this plan. This document does not add it, since the deliverable was specified as the plan doc only.

---

## 0. Executive summary

The extension itself is straightforward and **fully backward compatible** — the four new keys are additive and `validate_schema.py` ignores unknown keys, so zero validator changes are required to land the format. The work is not in the format. It is in the four consumers, and the survey turned up three things worth deciding before we commit:

1. **The "template" a client downloads today is the sample CSV itself.** `GET /api/data/templates?name=employees` serves `data/sample/employees_sample.csv` — 21 rows of fabricated employees (`Ahmad Al-Sudairy`, `John Doe`, real-looking salaries). A paying client's onboarding artefact is currently synthetic HR records. This directly violates the architecture's *"never show a fabricated number as real"* principle, and it is the single strongest argument for the template generator.
2. **Two contract keys are silently inert.** `min_value` (5 columns across attendance and payroll) and `unique` (2 columns) are declared in the contracts but enforced nowhere — `validate_schema.py` reads only `name`, `required`, `type`, `allowed_values`. A contract author would reasonably assume they bind. They do not.
3. **The template list and the contract set disagree.** `employee_relations` has a template but no contract; `hr_requests` has a contract but no template. Neither is reachable from `REAL_SOURCEABLE`.

Blast radius for de-duplication is **moderate and well-bounded**: the employees column list is written out in **8 places**. Crucially, dbt staging models use `SELECT *`, so the 157-model analytics layer is not in scope.

The largest genuinely new build is not the schema — it is that **the frontend has no i18n layer at all**. No locale context, no RTL support, no translation mechanism. Arabic labels have nowhere to land yet.

---

## 1. Audit — the five existing contracts

### 1.1 Structure

All five share one flat shape and nothing else:

```yaml
columns:
  - name: <canonical_key>
    type: VARCHAR | INTEGER | DECIMAL | DATE | TIMESTAMP | BOOLEAN
    required: true | false
    # optional, sparse:
    unique: true
    min_value: 0
    allowed_values: [...]
```

No table-level metadata — no domain name, no description, no version, no primary key declaration, no cross-field rules. 73 columns total. Only **one** `allowed_values` list exists in the entire contract set (`employees.status`), which means enum-dropdown generation for Excel templates has almost nothing to work from today.

### 1.2 Every field, by domain

**`employees_schema.yml` — 21 columns** (`employee_id` ᵁ, `employee_name`, `nationality`, `is_saudi` ᴮ, `company`, `department`, `project`, `job_title`, `job_family`, `grade`, `manager_id` °, `cost_center`, `employment_type`, `contract_type`, `joining_date` ᴰ, `termination_date` °ᴰ, `contract_end_date` °ᴰ, `status` ᴱ, `basic_salary` $, `housing_allowance` $, `transport_allowance` $)

**`payroll_schema.yml` — 13 columns** (`payroll_period`, `employee_id`, `basic_salary` $ᴹ, `housing_allowance` $, `transport_allowance` $, `other_allowances` $, `overtime_amount` $, `deductions` $, `gross_pay` $ᴹ, `net_pay` $ᴹ, `project`, `cost_center`, `payroll_status`)

**`attendance_schema.yml` — 15 columns** (`attendance_date` ᴰ, `employee_id`, `shift_name`, `scheduled_start` ᵀ, `scheduled_end` ᵀ, `actual_check_in` °ᵀ, `actual_check_out` °ᵀ, `late_minutes` ᴵᴹ, `excused_late_minutes` ᴵ, `net_late_minutes` ᴵᴹ, `absence_days` #, `overtime_hours` #, `overtime_approved` ᴮ, `missing_punch_count` ᴵ, `project`)

**`compliance_schema.yml` — 13 columns** (`employee_id`, `period`, `qiwa_status`, `gosi_status`, `mudad_status`, `contract_authenticated` ᴮ, `gosi_salary` $, `payroll_basic_salary` $, `occupation_code`, `occupation_match_status`, `work_permit_expiry` °ᴰ, `iqama_expiry` °ᴰ, `insurance_status`)

**`hr_requests_schema.yml` — 11 columns** (`request_id` ᵁ, `employee_id`, `request_type`, `request_status`, `created_at` ᵀ, `closed_at` °ᵀ, `owner`, `sla_hours` ᴵ, `actual_hours` °ᴵ, `sla_breached` ᴮ, `project`)

*Key:* ° optional · ᵁ unique · ᴮ boolean · ᴰ date · ᵀ timestamp · ᴵ integer · $ decimal · # decimal · ᴱ has allowed_values · ᴹ has min_value

### 1.3 Audit findings

| # | Finding | Consequence |
|---|---|---|
| A1 | `min_value: 0` declared on `attendance.late_minutes`, `attendance.net_late_minutes`, `payroll.basic_salary`, `payroll.gross_pay`, `payroll.net_pay` — **never enforced** | A real payroll file with negative pay passes contract validation. Caught later by `validate_data.py` as a DQ exception, but the hard gate lets it through. |
| A2 | `unique: true` on `employees.employee_id` and `hr_requests.request_id` — **never enforced** | Duplicate employee IDs pass the gate. This is a known real-world defect class — `base_active_workforce` exists specifically to deduplicate them. |
| A3 | Only one `allowed_values` list in 73 columns | 7 status/enum columns (`qiwa_status`, `gosi_status`, `mudad_status`, `payroll_status`, `request_status`, `insurance_status`, `occupation_match_status`) have no vocabulary, so no dropdown and no enum validation. Mixed Ar/En vocabularies are a named real-world issue (architecture §4). |
| A4 | No table-level metadata | Nowhere to put a domain's own bilingual name/description for the Excel instructions sheet. |
| A5 | No cross-field rules | `gross_pay = basic + allowances + overtime − deductions` and `termination_date >= joining_date` live in `validate_data.py` and dbt, not the contract. Out of scope this cycle; noted so the format doesn't foreclose it. |
| A6 | Only 5 of 21 tables have contracts | Matches `REAL_SOURCEABLE` (4) + `hr_requests` (contracted, not real-sourceable). |

---

## 2. Proposed format

### 2.1 Column definition

Exactly as specified in architecture §4, with `allowed_values` handled carefully (see 2.3):

```yaml
version: 1                          # NEW, table-level
table: employees                    # NEW
label_en: Employees                 # NEW — Excel sheet name, UI section header
label_ar: الموظفون                   # NEW
description_en: One row per employee, current master record.
description_ar: صف واحد لكل موظف، السجل الرئيسي الحالي.

columns:
  - name: joining_date              # unchanged — canonical key, used everywhere internally
    type: DATE                      # unchanged
    required: true                  # unchanged
    name_en: Joining Date           # NEW
    name_ar: تاريخ الانضمام           # NEW
    description_en: Date the employee started employment
    description_ar: تاريخ بدء الموظف للعمل
    example: "2024-03-15"           # NEW
```

### 2.2 Backward compatibility — no validator change required

`validate_schema.py` reads exactly four keys per column (`name`, `required`, `type`, `allowed_values`) via `.get()`, and one top-level key (`columns`). Every proposed addition is a new key at column or table level. Unknown keys are ignored by construction.

| Proposed addition | Validator impact |
|---|---|
| `name_en`, `name_ar`, `description_en`, `description_ar`, `example` (column-level) | **None** — never read |
| `version`, `table`, `label_en`, `label_ar`, `description_en/ar` (table-level) | **None** — only `spec.get("columns")` is read |
| Existing keys unchanged | **None** |

**Verification gate before merge:** the contracts are only read on the real path, which CI never exercises, so CI passing is *not* evidence the extension is safe. Require an explicit check — run `validate_csv_against_contract` against a synthetic conformant CSV and against known-bad CSVs (missing column, unexpected column, bad type, bad enum) using the extended contracts, and confirm identical accept/reject behaviour and identical error strings to the pre-extension contracts. That is the honest test.

### 2.3 One trap: `allowed_values` must stay a flat list

The validator does `set(allowed)` and compares raw cell values. Turning entries into objects (`{value: Active, label_ar: نشط}`) **breaks it immediately** — every row would fail Rule 4.

So: `allowed_values` stays a list of canonical strings, and display/aliasing goes in **parallel, optional keys**:

```yaml
  - name: status
    type: VARCHAR
    required: true
    allowed_values: ["Active", "Inactive", "Terminated", "On Leave"]   # UNCHANGED shape
    value_labels:                    # NEW — display only (dropdowns, UI, errors)
      Active:      { en: Active,     ar: نشط }
      Inactive:    { en: Inactive,   ar: غير نشط }
      Terminated:  { en: Terminated, ar: منتهية خدماته }
      On Leave:    { en: On Leave,   ar: في إجازة }
    value_aliases:                   # NEW — reserved for Phase 2 mapping profiles; inert now
      نشط: Active
```

`value_aliases` is **declared but not consumed** in Phase 1. It belongs to mapping profiles (architecture §4) and must not become silent coercion in the validator — the hard-reject default stands.

### 2.4 `min_value` / `unique` — deliberately left inert

Both are unenforced today (A1, A2). Enforcing them is a validator behaviour change, which this cycle's guardrail forbids. Recommendation: **leave them inert in Phase 1 and enforce in a dedicated Phase 1b cycle** with its own before/after proof, rather than smuggling it in. Meanwhile the extended contracts should carry a comment marking them as not-yet-enforced, so no author is misled. Flagging for a ruling — the alternative (enforce now) is defensible but breaks the guardrail.

---

## 3. De-duplication survey — the blast radius

### 3.1 Where the employees column list is written out today — 8 places

| # | Location | What it duplicates | Should it read the schema? |
|---|---|---|---|
| 1 | `data/contracts/employees_schema.yml` | names, types, required | **Source of truth** |
| 2 | `scripts/generate_sample_data.py:80` | header row + row shape | Yes — generate from schema |
| 3 | `scripts/ingest_raw.py` (employees block) | 7 explicit casts | Yes — derive casts from `type` |
| 4 | `backend/app/api/data.py:57-67` `compile_csv_to_parquet` | same casts, again | Yes — same derivation |
| 5 | `data/sample/employees_sample.csv:1` | header row | Generated artefact |
| 6 | `config/privacy_classification.yml` | field list + classification | Later — merge as schema keys |
| 7 | `config/masking_rules.yml` | field list + masking | Later |
| 8 | `config/field_level_access_matrix.yml` | field list × 11 roles | Later |

Items 3 and 4 are the same casting logic written twice with different code — a live divergence risk today, not a hypothetical.

`config/real_data_mapping.yml` (83 lines) is a *third* field registry, in the synthetic-governance family. It anticipates mapping profiles and should eventually be reconciled with or superseded by them; out of scope now, flagged so it isn't forgotten.

### 3.2 Labels

| Location | Nature |
|---|---|
| `frontend/src/components/tables/ExceptionTable.tsx:63-107` | Hardcoded English headers (`'Employee ID'`, `'Employee Name'`, …) |
| `frontend/src/pages/*.tsx` | KPI/card/axis labels throughout, English only |
| `backend/app/api/data.py:116-124` | Template `description` strings, English only |
| `scripts/validate_schema.py` error strings | English only, not localizable |
| `validate_data.py` DQ messages | English prose, e.g. *"Employee contract has negative basic salary"* |

**There is no i18n layer.** Zero matches for i18n libraries, locale context, `dir="rtl"`, or `lang="ar"` in `frontend/src`. Bilingual labels are net-new frontend infrastructure, not a swap of existing strings — this is the largest single work item in Phase 1 and should be scoped as such.

### 3.3 Explicitly NOT in scope

- **dbt staging models** — all 23 are `SELECT * FROM {{ source(...) }}`. Schema-agnostic; no change.
- **dbt base/mart models** — reference columns by name in business logic (157 models). That is analytics SQL, not a duplicated column *list*; parameterising it from a loader would be harmful. Out of scope permanently.
- **`config/metrics_dictionary.yml` / `business_rules.yml`** — metric and rule definitions, a different axis from column schema. Leave alone.

---

## 4. Loader placement and frontend exposure

### 4.1 A constraint the obvious answer trips over

`backend/Dockerfile` uses build context `./backend`. **`data/contracts/` is not in it.** The backend can only read contracts today because `docker-compose.yml` bind-mounts `./data → /app/data`. So:

- A shared module at repo root (`shared/`, `libs/`) is **not visible to the backend image build** — it would work in compose and fail in any standalone container.
- The canonical schema is **code, not data**. It should be baked into the image, not mounted. Its current home under `data/` is a legacy of the local-first design.

### 4.2 Recommendation

**Phase 1a (this cycle's implementation):** add `scripts/canonical_schema.py` — a dependency-light loader (`yaml` only) exposing `load_schema(table)`, `all_tables()`, `columns(table)`, `labels(table, locale)`. Keep the YAML files at `data/contracts/` unchanged in location, so **zero validator change** and the existing bind-mount keeps working. `scripts/` is already mounted into the backend container and is importable from repo root by both `scripts/` and `backend/`.

**Phase 1b (separate, reviewed):** promote to a proper top-level package `hr_schema/` containing both the loader and the definitions, change the backend build context to the repo root (with `dockerfile: backend/Dockerfile`), and update `validate_schema.py`'s default `contracts_dir`. This is a Dockerfile + CI + validator-default change and deserves its own cycle with a Gate 3 verification, not a footnote in this one.

Rejected: putting the loader in `backend/app/` (scripts would import from the backend package — wrong dependency direction, and `scripts/` must run without the API installed).

### 4.3 Frontend exposure

**Recommended: a runtime endpoint.** `GET /api/meta/schema` → the canonical schema as JSON (labels, types, required, enums, descriptions — **no data**), served from the same loader. Additive, alongside the existing `/api/meta/app-config`.

Why runtime over build-time codegen: single-tenant-per-deployment means a client's schema may legitimately differ (extra enum values, custom labels), and a build-time TS module would freeze it at image build. An endpoint keeps one source of truth at runtime. Cost is a fetch on load — mitigate with an ETag keyed on the schema `version` plus file mtime, and cache in TanStack Query, which is already the app's data layer.

Frontend consumption needs (net-new): a locale context (`en` | `ar`) persisted to `localStorage` beside the existing `ThemeContext`; `dir="rtl"` handling; a `useSchemaLabel(table, column)` hook; and a decision on whether Arabic applies to chrome (nav, buttons) or only schema-derived labels in Phase 1. **Recommend schema-derived labels only in Phase 1** — full UI localisation is a much larger surface and can follow.

While `/api/meta/app-config` is being joined by a sibling endpoint, this is the cheap moment to give it its first consumer and close the open item in architecture §7 (a user cannot currently tell demo data from real). Flagging as an adjacent opportunity, not smuggling it into scope.

---

## 5. Domain gaps in the four `REAL_SOURCEABLE` tables

### 5.1 `employees` — `is_saudi` cannot survive contact with a real export

`is_saudi` is a **required BOOLEAN**. No HRIS exports that column; they export `nationality`. The sample data carries both (`nationality: Saudi, is_saudi: True`), which has hidden the problem — a real file will fail Rule 1 (missing required column) on day one of Phase 2.

Options: (a) make `is_saudi` optional and derive when absent; (b) keep required and force clients to add a column by hand; (c) introduce first-class **derived columns** in the schema.

**Recommend (c)**, with the derivation declared in the schema and computed at ingest:

```yaml
  - name: is_saudi
    type: BOOLEAN
    required: false            # was true — real exports do not carry it
    derived_from: nationality
    derivation: nationality_is_saudi   # named rule, implemented in code, not eval'd
```

Two hard constraints on this: the derivation must be a **named rule resolved from a registry**, never an expression string evaluated at runtime; and `nationality` vocabulary is itself messy (`Saudi`, `SAU`, `السعودية`, `Saudi Arabian`), so the rule needs its own alias table and must **fail loudly on unrecognised values** rather than defaulting to `false` — silently defaulting understates Saudization, the single most consequential number in the product.

Note this changes a `required` flag, which is a validator-visible change (it relaxes, so nothing that passes today would start failing). Still: **needs an explicit ruling**, and it should land with the derivation implemented, not before.

Also missing for KSA reality: `national_id_number` / `iqama_number` (referenced across `privacy_classification.yml`, `masking_rules.yml` and the access matrix, but **in no contract**), `gender`, `date_of_birth`, `location`/`region`.

### 5.2 `compliance` — no Nitaqat anything

**Zero occurrences of "nitaqat" in any `.sql`, `.py`, or `.yml` in the repo.** `mart_saudization_summary` computes a flat `saudization_pct` and nothing more. The architecture positions the Nitaqat what-if advisor (§5 Tier 1, item 2) as *"the capability nobody else is positioned to build as well"* — none of its inputs exist.

Missing, and not purely schema-level:

| Need | Where it belongs |
|---|---|
| Entity size class (Small/Medium/Large/Giant — headcount-banded) | Per-deployment config, not a column |
| Sector / activity classification (drives the band table) | Per-deployment config |
| Nitaqat band thresholds per sector × size | New `config/nitaqat_bands.yml` |
| Current band + distance to next band | New mart |
| Saudi headcount weighting rules (part-timers, disabled employees count differently) | Business rules + possibly new columns |

`config/business_rules.yml` has no `entity_size`, `sector`, or `band` key. **This is a Phase 1 schema gap only in part** — most of it is configuration and mart work. Recommend the schema cycle adds only what is genuinely per-employee (e.g. a weighting-relevant flag if the rules require one) and that Nitaqat gets its own cycle before or alongside Phase 2.

### 5.3 `payroll` — thin against WPS reality

No `iban` / `bank_name` (WPS submission), no `payment_date`, no `payment_status` vs `payroll_status`, no `gosi_employee_contribution` / `gosi_employer_contribution` (only `compliance.gosi_salary` exists), no `working_days` / `unpaid_leave_days`. `payroll_status` has no `allowed_values`.

### 5.4 `attendance` — plausible but leave-blind

The known limitation (`DOCUMENTATION.md` §15) that leave/holiday exclusions are structurally supported but inactive is a **schema gap**: there is no leave source table and no `leave_type` / `is_holiday` / `is_weekend_override` column. Absence and compliance denominators are therefore approximations. `shift_name` has no vocabulary. Public-holiday calendars are per-year KSA data with no home in the repo.

### 5.5 Summary

| Domain | Contract state | Gap severity | Blocking Phase 2? |
|---|---|---|---|
| `employees` | 21 cols | **High** — `is_saudi` derivation; missing national ID | **Yes** — first real file fails |
| `compliance` | 13 cols | **High** — no Nitaqat inputs at all | Blocks the Tier 1 advisor, not basic ingest |
| `payroll` | 14 cols | Medium — WPS/GOSI fields absent | No |
| `attendance` | 15 cols | Medium — leave/holiday blindness | No |

---

## 6. Proposed sequencing

| Step | Scope | Verification |
|---|---|---|
| **1a.1** | Extend the 5 contracts with bilingual keys + `example`, table-level metadata, `value_labels`, and enum vocabularies for the 7 bare status columns | Accept/reject parity harness (§2.2) — identical behaviour and error strings pre/post |
| **1a.2** | `scripts/canonical_schema.py` loader + unit tests | New tests; `pytest backend/tests` unaffected |
| **1a.3** | Template generator (Excel: headers, bilingual instructions sheet, dropdowns, 2–3 example rows) driven by the loader | Generated file opens; headers match contract exactly |
| **1a.4** | Repoint `GET /api/data/templates` at generated templates — **stops shipping sample data as the template** | Downloaded file contains no synthetic employee records |
| **1a.5** | `GET /api/meta/schema` + frontend locale context + `useSchemaLabel` | Labels render en/ar; RTL correct |
| **1b** | Enforce `min_value` / `unique`; `is_saudi` derivation; promote to `hr_schema/` package; backend build context | Own cycle, own before/after proof |

De-duplicating `generate_sample_data.py`, `ingest_raw.py`, and `compile_csv_to_parquet` onto the loader is deliberately **not** in 1a — each touches the demo path where byte-identity must hold, and each deserves its own empty-warehouse proof. Recommend a 1c cycle.

---

## 7. Decisions needed before implementation

1. **`min_value` / `unique`** — leave inert in 1a (recommended, respects the guardrail), or enforce now?
2. **`is_saudi`** — adopt derived columns (recommended), or keep required and push the burden to clients?
3. **Arabic scope in Phase 1** — schema-derived labels only (recommended), or full UI localisation including chrome?
4. **Nitaqat** — its own cycle before Phase 2 (recommended), or fold the config/mart work into Phase 1?
5. **Loader placement** — staged 1a → 1b (recommended), or go straight to `hr_schema/` with the Docker context change?
6. **`hr_requests` / `employee_relations`** — reconcile the contract/template mismatch now, or defer? Neither is real-sourceable.
7. **`docs/PRODUCT-ARCHITECTURE.md` is untracked** — commit it as the governing reference?

---

## 8. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| CI green is mistaken for "extension is safe" — contracts are never read on the demo path | **High** | The §2.2 parity harness is mandatory, not optional |
| `allowed_values` restructured into objects, breaking Rule 4 | Medium | Format pins it as a flat list; parity harness catches it |
| Arabic labels wrong or machine-translated | Medium | HR-practitioner review of all 73 `name_ar` values before merge — the operator is the domain expert |
| Adding enum vocabularies (A3) rejects data that passes today | Medium | Only affects the real path; derive vocabularies from observed sample values first and review each |
| i18n scope creep swallows the cycle | **High** | Cap Phase 1 at schema-derived labels; chrome localisation is separate |
| Encoding damage to Arabic text on Windows | Medium | UTF-8 without BOM enforced; `.gitattributes` review; verify rendering after round-trip |

---

**Prepared for chief-architect review. No implementation performed.**
