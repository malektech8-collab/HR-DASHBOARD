# Cycle 1b-ii — Exception Plumbing, `employee_relations` Contract, Catalogue Derivation, Enum Vocabularies (PLAN ONLY)

**Status:** proposed. Nothing implemented. This document is the only file added on `phase-1b/schema-catalogue`.
**Branch:** `phase-1b/schema-catalogue` off `main` @ `a7deac2` · **Date:** 2026-08-10
**Governing reference:** [`docs/PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4
**Predecessor:** [`validator-rules-report.md`](validator-rules-report.md) (cycle 1b-i, merged at `a7deac2`)

> This is the last gate before Phase 2. Priority 1 exists because 1b-i shipped a severity that currently does nothing.

---

## 0. Summary of what is being fixed

1b-i classifies a `min_value` or non-PK `unique` violation as **EXCEPTION** — the file loads and the offending rows are supposed to reach the client. They do not. The validator returns them and `ingest_raw` drops them on the floor. Until Priority 1 lands, EXCEPTION is functionally **ignore**, which is worse than REJECT because it is silent.

Priorities 2–4 close the remaining gaps that stop a domain being real-sourceable or a template being trustworthy.

---

## 1. PRIORITY 1 — contract violations must reach the Data Quality page

### 1.1 The existing exception model

Three layers, each with a fixed shape:

```
scripts/validate_data.py        -> data/gold/data_quality_report.parquet
  {employee_id, employee_name, issue_type, description, severity, recommended_action}
        |
  stg_data_quality (SELECT *)
        |
  mart_data_quality_exceptions  -> selects those 6 columns explicitly
        |
  base_command_exception_data_quality
    module_key='data-quality', module_label='Data Quality',
    source_mart='mart_data_quality_exceptions', entity_id=employee_id,
    entity_name=employee_name, route_path='/data-quality'
        |
  base_command_center_exception_sources  (UNION of all 8 domains)
    severity normalised: CASE LOWER(TRIM(severity)) -> Critical | Warning | Info | Unknown
```

15 checks currently populate it. Two constraints fall out of this and shape everything below:

- **Severity must be exactly `Critical`, `Warning` or `Info`.** Anything else renders as `Unknown`. A contract violation carrying `severity='exception'` would surface as `Unknown` on the Command Center.
- **The model is employee-centric.** `entity_id` is an employee ID. A contract violation is *cell*-centric — table, row, column — and may not have an employee ID at all (the broken cell might *be* `employee_id`).

### 1.2 Shared shape or separate source?

**Recommendation: shared shape, separate provenance.** Contract violations render as ordinary Data Quality exceptions — same table, same page, same actioning — but carry enough extra fields to be traceable to a file, row and column.

Rejected alternatives:

- **A new `module_key='contract'` with its own page.** Splits "what is wrong with my data" across two screens. A client does not care whether a bad value was caught at ingest or by a downstream check; they care which record to fix.
- **Reusing the 6-column shape with no additions.** Loses row and column, which are the only things that make a contract violation actionable. *"Net Pay is below the minimum"* without a row number is a worse message than the validator already produces.

### 1.3 Proposed changes

**(a) Extend the gold schema additively.** `validate_data.py` writes five new columns, defaulted for the existing 15 checks:

| new column | existing checks | contract violations |
|---|---|---|
| `source` | `"validation"` | `"contract"` |
| `source_table` | the table checked | `employees`, `payroll`, … |
| `source_row` | `null` | Excel-visible row number |
| `source_column` | `null` | canonical column name |
| `rule` | `null` | `min-value`, `unique`, … |

Safe by construction: `stg_data_quality` is `SELECT *`, and both `mart_data_quality_exceptions` and `base_command_exception_data_quality` select their six columns **explicitly**. Adding columns upstream changes no mart output and no API payload. Surfacing `source_row` / `source_column` on the page is a follow-up UI change, deliberately not in this cycle.

**(b) Severity mapping, declared not inferred.** Contract severity is a *validator* concept; DQ severity is a *presentation* concept. Map explicitly:

| rule | DQ severity | why |
|---|---|---|
| `min-value` on a pay column | `Critical` | negative pay is a payroll defect, not a nuance |
| `min-value` elsewhere | `Warning` | |
| `unique` (non-PK) | `Warning` | |

Never emit the raw string `exception` — it renders as `Unknown`.

**(c) Entity resolution.** If the violating row has a usable `employee_id`, use it as `employee_id` and resolve `employee_name` from the employees silver table where available. Otherwise `employee_id = ""` and `employee_name = "Unknown"`, which is what the existing helper already does for unattributable issues. Do **not** invent an ID.

**(d) The transport.** `ingest_raw` writes EXCEPTION-severity violations to `data/gold/contract_exceptions.parquet` (gitignored); `validate_data` merges the file if present. `refresh_all` already runs ingest → validate in that order, so no orchestration change is needed.

> **Staleness trap — this must be designed in, not discovered later.** If the file is not deleted at the start of every run, yesterday's exceptions persist forever and re-appear against data that has since been fixed. This is precisely the `.uploaded` marker bug from Phase 0, which froze a table's ingest indefinitely and zeroed out four Attendance widgets. **`ingest_raw` must unlink the file at the start of every run, in every mode, before deciding whether to write it.** A demo run must actively clear a file left behind by a previous real run.

**(e) Recommended action text**, bilingual, per rule — e.g. *"Correct the value in the source file and re-upload"* / *"صحّح القيمة في الملف المصدر وأعد الرفع"*. The gold schema has no `_ar` column today; recommend adding `description_ar` and `recommended_action_ar` in the same additive pass so the DQ page can localise later without a second migration.

### 1.4 Demo impact

**Byte-identical.** `data/gold/contract_exceptions.parquet` is only ever written on the real path, and the demo run deletes-then-does-not-create it. Gold gains columns, but the parquet is gitignored and every downstream model selects explicitly. Verification: empty-warehouse run → dbt 157/157, 11/11, reconciliation PASSED, **15 DQ exceptions and 667 total unchanged**.

---

## 2. PRIORITY 2 — a contract for `employee_relations`

### 2.1 Why it is a gap, not clutter

The domain has a dashboard page, a sample file, 15 exception checks in `mart_er_exceptions.sql`, and an ingest block — but no contract, so it can never be real-sourced. Phase 0 Decision-1 set `REAL_SOURCEABLE` to tables that are *named **and** contracted*; `employee_relations` fails only the second test.

### 2.2 Proposed contract — 14 columns

From `data/sample/employee_relations_sample.csv` (11 rows) and the casts already in `ingest_raw` / `compile_csv_to_parquet`:

| # | column | type | required | notes |
|---|---|---|---|---|
| 1 | `case_id` | VARCHAR | yes | `unique: true`, **`primary_key: true`** |
| 2 | `employee_id` | VARCHAR | yes | |
| 3 | `case_type` | VARCHAR | yes | **enum — see 2.3** |
| 4 | `case_status` | VARCHAR | yes | `Open`, `Closed` |
| 5 | `priority` | VARCHAR | yes | `High`, `Medium`, `Low` |
| 6 | `created_date` | DATE | yes | |
| 7 | `target_due_date` | DATE | no | derived from SLA when absent |
| 8 | `closed_date` | DATE | no | `required_when` `case_status` = `Closed` |
| 9 | `owner_id` | VARCHAR | yes | |
| 10 | `escalated` | BOOLEAN | yes | |
| 11 | `escalation_reason` | VARCHAR | no | |
| 12 | `legal_reference` | VARCHAR | no | |
| 13 | `case_number` | VARCHAR | no | |
| 14 | `description` | VARCHAR | no | |

Bilingual labels for all 14 to be authored, then **practitioner-reviewed before merge** — the Phase 1 precedent.

### 2.3 `case_type` is a genuinely closed vocabulary

`config/business_rules.yml` keys SLA days by exactly `Disciplinary`, `Grievance`, `Labor Case`. A fourth value would silently fall through to the default SLA and mis-classify every breach calculation on that case. This is one of the few enums that is safe to enforce as **REJECT** today, because the configuration already depends on it.

`closed_date` + `required_when case_status = Closed` is the same pattern as `end_of_service_type`, and closes a real hole: a closed case with no closing date breaks every ageing and SLA metric.

### 2.4 Should it join `REAL_SOURCEABLE`?

Authoring the contract makes it *eligible*; membership is a separate one-line change in `ingest_raw.REAL_SOURCEABLE`. **Recommend yes, in this cycle** — a contract that nothing can use reproduces the current gap in a new form. Flagged for an explicit ruling because it widens the real-data surface from 4 tables to 5.

### 2.5 Demo impact

**Byte-identical.** A new contract is only read on the real path. Adding the table to `REAL_SOURCEABLE` changes nothing in demo, where no `data/raw/employee_relations.csv` exists and the resolver falls back to sample.

---

## 3. PRIORITY 3 — derive the template catalogue

### 3.1 Current state

`backend/app/api/data.py` hardcodes `TEMPLATE_CATALOGUE` — five names with English-only descriptions. It is the **third** place the domain list is written down, after the contracts directory and `REAL_SOURCEABLE`. It disagrees with both: `hr_requests` is contracted but absent; `employee_relations` is listed but returns 409.

### 3.2 Proposal

Derive from `canonical_schema.available_tables()`, and take the display text from the contract, which already carries it:

```python
for table in cs.available_tables():
    spec = cs.describe(table, locale)
    {"name": table,
     "filename": f"{table}_template.csv",
     "label": spec["label"],            # label_en / label_ar
     "description": spec["description"],# description_en / description_ar
     "available": True}
```

The hardcoded list, the hardcoded descriptions and the `available: false` branch all disappear — a template exists **iff** a contract exists, which is the invariant the endpoint should have enforced from the start. With Priority 2 landed, the catalogue becomes six domains automatically.

Add `?locale=` so the catalogue is bilingual like `/api/meta/schema`. English stays the default, so existing callers are unaffected.

### 3.3 Consequences to handle

- `backend/tests/test_data.py` asserts `employee_relations` has `available: false` and returns 409. That assertion becomes wrong by design and must be updated — with the *reason* recorded, not silently deleted.
- The frontend reads `name`, `filename`, `description`; `label` is additive. No UI change required, though `label` is a better display string than `t.name.replace("_", " ")` and is worth adopting.
- Descriptions become the contract's `description_en`, which are one-line and factual (*"One row per employee. The workforce master record."*) versus today's marketing-ish strings. Acceptable and more accurate; worth a glance before merge.

### 3.4 Demo impact

**Dashboard byte-identical**, but the **`/api/data/templates` response changes**: six entries instead of five, different descriptions, no `unavailable_reason`. That is an API-visible change on the demo deployment — stated rather than glossed. No dbt model, mart or KPI is touched.

---

## 4. PRIORITY 4 — enum vocabularies

### 4.1 The trap, restated with evidence

Eleven columns carry inert `observed_values` from Phase 1. Deriving `allowed_values` from them would be actively harmful, because the sample is a fixture, not a population:

```
payroll_status          ['Paid']                    <-- rejects every unpaid line
shift_name              ['Day Shift']               <-- rejects every night shift
qiwa_status             ['Active']
gosi_status             ['Registered']
mudad_status            ['Compliant']
health_insurance_status ['Active']
employment_type         ['Full-time']               <-- rejects every part-timer
```

`allowed_values` is a **REJECT** rule. A wrong vocabulary does not warn — it refuses the client's file.

### 4.2 Classification

| Column | Recommendation |
|---|---|
| `employee_relations.case_type` | **Enum now, REJECT** — `business_rules.yml` already depends on the three values (§2.3) |
| `employee_relations.case_status`, `priority` | **Enum now, REJECT** — small closed sets, low risk |
| `hr_requests.request_status` | **Enum now, REJECT** — `Open`/`Closed` plus practitioner additions |
| `compliance.qiwa_status`, `gosi_status`, `mudad_status`, `health_insurance_status` | **Enum, EXCEPTION severity** — government-platform vocabularies are knowable but not from a fixture; get them from the practitioner, and let an unexpected value surface rather than reject |
| `employees.employment_type`, `contract_type` | **Enum, EXCEPTION severity** — practitioner-authored |
| `payroll.payroll_status` | **Enum, EXCEPTION severity** — practitioner-authored, never derived |
| `hr_requests.request_type` | **Leave free text** — a per-client service catalogue, not a standard vocabulary |
| `attendance.shift_name` | **Leave free text, permanently** — client-specific naming (`A/B rotation`, `Night`, `Ramadan hours`) |

### 4.3 The mechanism this needs

Enforcing a vocabulary we are not certain of should not reject a client's file. 1b-i already built the machinery — reuse it:

```yaml
  - name: payroll_status
    allowed_values: [Paid, Pending, Unpaid, Hold, Cancelled]
    on_violation: exception     # surfaces as a DQ exception, does not reject
```

`allowed_values` currently hard-codes REJECT. Making severity declarable per rule is a small validator change and lets a vocabulary be introduced safely, tightened to REJECT once real files confirm it. **This is the single most useful thing in Priority 4** — without it, every enum is a gamble against data we have not seen.

Every vocabulary must be **practitioner-authored and reviewed before merge**. None may be derived from `data/sample`.

### 4.4 Demo impact

**Byte-identical.** `allowed_values` is only evaluated on the real path.

---

## 5. Sequencing

| Step | Work | Gate |
|---|---|---|
| 1 | `on_violation` severity for `allowed_values` (§4.3) | parity: no delta — no vocabulary added yet |
| 2 | Gold schema extension + severity mapping + transport + **staleness unlink** (§1) | empty-warehouse demo: 15 DQ / 667 unchanged; synthetic real run shows a `min_value` row on the DQ page |
| 3 | `employee_relations` contract (§2) | inventory: one table added; parity otherwise unchanged |
| 4 | `REAL_SOURCEABLE` += `employee_relations` — **pending ruling** (§2.4) | synthetic real-mode dry run |
| 5 | Catalogue derivation + test updates (§3) | templates endpoint returns 6 contracted domains, 0 data rows each |
| 6 | Enum vocabularies, practitioner-reviewed (§4) | parity: new enum cases only |

Priority 1 first after step 1, because it is the gap that makes 1b-i's severity meaningful.

---

## 6. Demo impact — consolidated

| Priority | Byte-identical? |
|---|---|
| 1 — exception plumbing | **Yes.** Gold gains columns (gitignored artefact); every downstream model selects explicitly; the transport file is real-path only and unlinked each run. |
| 2 — ER contract | **Yes.** Read only on the real path. |
| 3 — catalogue derivation | **Dashboard yes; `/api/data/templates` no.** Six entries instead of five, contract-sourced descriptions, no `unavailable_reason`. API-visible on demo. |
| 4 — enum vocabularies | **Yes.** Real path only. |

Priority 3 is the only item that cannot be called byte-identical, and it is an API response shape, not a number.

---

## 7. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Stale `contract_exceptions.parquet` resurrects fixed exceptions | **High if not designed in** | Unlink at the start of every run, in every mode; assert in a test |
| Contract severity leaks through as `Unknown` on the Command Center | Medium | Map to `Critical`/`Warning`/`Info` explicitly; assert no `Unknown` rows |
| An enum vocabulary rejects a valid real file | **High if derived** | Never derive from samples; default new vocabularies to EXCEPTION severity |
| `employee_relations` labels are engineer-authored | Medium | Practitioner review before merge, as in Phase 1 |
| Catalogue derivation silently drops a domain if a contract file is malformed | Low | `available_tables()` is a directory listing; a malformed contract raises on read — assert the count |
| Test asserting the 409 path is deleted rather than updated | Medium | Update with the reason recorded in the test docstring |

---

## 8. Decisions needed

1. **`REAL_SOURCEABLE` += `employee_relations`** in this cycle (§2.4)? Recommended yes.
2. **`on_violation` for `allowed_values`** (§4.3) — approve the mechanism? Recommended yes; it is what makes Priority 4 safe.
3. **Which enum vocabularies** you can author now (§4.2) — the four government-platform ones, `employment_type`, `contract_type` and `payroll_status` need real values.
4. **Gold `_ar` columns** (§1.3e) — add now for a future localised DQ page, or defer?
5. **Surfacing `source_row` / `source_column` in the UI** — this cycle or a follow-up? Recommended follow-up.

---

**Prepared for chief-architect review. No implementation performed.**
