# Cycle 1b-ii — Execution Report

**Branch:** `phase-1b/schema-catalogue` off `main` @ `a7deac2` · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.**
**Plan:** [`schema-catalogue-plan.md`](schema-catalogue-plan.md) · **Predecessor:** [`validator-rules-report.md`](validator-rules-report.md)

---

## 1. Priority 1 — contract violations reach the Data Quality page

### 1.1 Proof, end to end

A synthetic real-mode payroll file with one `min_value` violation on row 3:

```
[real] payroll: ingesting from data/raw/payroll.csv (contract-validated).
[contract] payroll: 1 exception-severity violation(s) -> data quality layer.
[contract] wrote 1 exception row(s) to data/gold/contract_exceptions.parquet
Validation complete. Generated 14 issues (+1 from contract validation) …
```

It arrives on the page, with the right severity:

```
rows on mart_data_quality_exceptions: 1
  Contract: min-value | Critical | Row 3, Net Pay: value -500 is below the minimum of 0.
on the Command Center feed  : [('data-quality', 'Critical', 'Contract: min-value')]
rows rendering as Unknown   : 0   (must be 0)
```

The file **loaded** — the violation did not block it — and the row is now actionable, with the Excel-visible row number in the message.

### 1.2 Severity mapping — explicit, never inferred

`base_command_center_exception_sources` normalises severity with `CASE LOWER(TRIM(severity)) … ELSE 'Unknown'`. A raw `'exception'` would have rendered as **Unknown** on the Command Center. `dq_severity()` maps every rule into `Critical`/`Warning`/`Info`, with negative pay as `Critical` and everything else `Warning`. A test asserts no rule — including an unrecognised future one — can produce anything outside that set.

### 1.3 No invented identifiers

A contract violation is cell-centric; the DQ model is employee-centric, and the broken cell might *be* `employee_id`. Unattributable rows get `employee_id = ""`, `employee_name = "Unknown"` — matching what the existing helper already does. Asserted in `test_unattributable_rows_never_invent_an_employee_id`.

### 1.4 The staleness guard

Unlinked at the **start** of every run, in **every** mode, before anything decides whether to write:

```
[contract] cleared stale data/gold/contract_exceptions.parquet
…
transport file after demo run:  gone (cleared) ✓
```

`test_transport_file_is_cleared_at_the_start_of_every_run` plants a stale file, runs a **demo** ingest, and asserts it is gone. Without this, yesterday's exceptions resurrect against data since fixed and a demo run inherits a previous real run's exceptions — the `.uploaded` marker bug in a new costume.

### 1.5 Gold schema

Five provenance columns added additively: `source`, `source_table`, `source_row`, `source_column`, `rule`. Safe because `stg_data_quality` is `SELECT *` and both `mart_data_quality_exceptions` and `base_command_exception_data_quality` select their six columns explicitly — asserted by `test_gold_keeps_the_six_columns_the_marts_select`. Per ruling, `_ar` columns are **deferred** to the RTL/i18n cycle and row/column are **not** surfaced in the UI this cycle.

---

## 2. Priority 2 — `employee_relations` contract

14 columns, bilingual, types matching the casts already in both ingest paths. `case_id` is `primary_key`. `closed_date` carries `required_when: {column: case_status, equals: Closed}` — a closed case with no closing date breaks every ageing and SLA metric.

`case_type` is **REJECT** severity, justified rather than assumed: `config/business_rules.yml` keys `er_rules.sla_days` on exactly `Disciplinary` / `Grievance` / `Labor Case`, so a fourth value would silently take the default SLA and mis-classify every breach on that case.

`REAL_SOURCEABLE` now includes `employee_relations` (ruling 1), taking the real-data surface from 4 tables to 5.

**Labels are engineer-authored and need practitioner review before merge**, as in Phase 1.

---

## 3. Priority 3 — derived catalogue

`TEMPLATE_CATALOGUE` is deleted. The catalogue is now `canonical_schema.available_tables()`, with labels and descriptions from the contract's own bilingual text, plus `?locale=`.

```
domains: 6
   attendance           Attendance             One row per employee per attendance day.
   compliance           Compliance             Government platform status per employee …
   employee_relations   Employee Relations     One row per employee relations case …
   employees            Employees              One row per employee. The workforce master…
   hr_requests          HR Requests            Employee service requests and their SLA …
   payroll              Payroll                One row per employee per payroll period.

employee_relations: 200 | rows: 1     (header only)
hr_requests       : 200
unknown           : 404
ar label sample   : attendance -> الحضور والانصراف
```

A template now exists **iff** a contract exists. `hr_requests` appears; `employee_relations` resolves.

`test_data.py` asserted the old 409 behaviour. Updated, with the reason recorded in the test rather than deleted, and strengthened to assert the catalogue equals the contracts directory listing.

---

## 4. Priority 4 — vocabularies

Authored, never derived. **3 REJECT**: `case_type`, `employees.status`, `end_of_service_type`. **11 EXCEPTION** via the new `on_violation` key, including `payroll_status` (`Paid/Pending/Unpaid/Hold/Cancelled`) and `employment_type` per ruling. `shift_name` and `request_type` deliberately left free text — client-specific naming and per-client service catalogues.

Had these been derived from samples, `payroll_status` would have locked to `["Paid"]`, `shift_name` to `["Day Shift"]` and `employment_type` to `["Full-time"]`.

---

## 5. Two harness gaps, found and fixed

Neither was in the plan; both were exposed by this cycle's changes.

**`TABLES` was hardcoded** — a *fourth* place the domain list was written down, after the contracts directory, `REAL_SOURCEABLE` and the template catalogue. It silently excluded the new `employee_relations` contract from the harness entirely. Now derived from the contracts directory, the same fix as Priority 3.

**Only the first enum column got a `bad_enum` case.** Adding a vocabulary earlier in the column order silently dropped coverage of every later one — which is exactly what happened: `employees.status` lost its case the moment `employment_type` gained a vocabulary. Now one case per enum column. **Enum coverage 2 → 14.**

The first parity run showed `employees.bad_enum__status REJECT -> None`, which looked like a regression and was actually this coverage hole. Fixing the harness and re-baselining was the only way to get an honest delta.

---

## 6. Parity delta

Fixed harness on both sides; baseline re-captured against `main`'s contracts.

```
[BASE3]  cases=22 accept=5  reject=17 | columns=75 across 5 tables
[FINAL3] cases=38 accept=17 reject=21 | columns=89 across 6 tables

== column inventory ==
  employee_relations added ['case_id', 'employee_id', 'case_type', …]   (14)
  all five pre-existing tables unchanged
== verdict ==
  PASS - no column or table lost (16 case difference(s))
```

Every one of the 16 differences is `None -> X` — a case that did not exist before:

```
pre-existing cases that changed or vanished: 0
new cases: 16
employees.bad_enum__status in BOTH and unchanged: True | outcome: REJECT
coverage: enum cases before = 2 -> after = 14
```

**Zero pre-existing cases changed.** 6 new cases from the new table, 10 from the new vocabularies.

---

## 7. Demo impact

**Dashboard values byte-identical**, from an empty warehouse:

```
dbt 157/157 · dbt test 11/11 · reconciliation PASSED
active_headcount 19 · payroll_cost 446175.0 · saudization_pct 50.0
attendance_compliance_pct 0.14777327935222673 · 667 exceptions · 15 DQ
contract rows in demo: 0 · transport file: cleared
ALL DEMO VALUES IDENTICAL: True
```

**Changed as approved:** the `/api/data/templates` response — six entries instead of five, contract-sourced descriptions, `label` added, `unavailable_reason` gone. Not claimed as byte-identity.

---

## 8. Tests

**43 passed** (34 + 9 new in `test_contract_exceptions.py`): severity never leaks a raw validator string for any rule including an unrecognised one; negative pay is Critical while late minutes is not; recommended action is bilingual; written rows match the gold schema exactly; no invented employee IDs; the transport file is cleared by a demo run; demo produces no transport file; validate merges contract rows into gold and restores cleanly; gold keeps the six columns the marts select.

---

## 9. Carried forward

| Item | Target |
|---|---|
| Practitioner review of the 14 `employee_relations` Arabic labels | **before merge** |
| Surface `source_row` / `source_column` on the DQ page | next cycle (ruling 5) |
| Gold `_ar` columns | RTL/i18n cycle (ruling 4) |
| Tighten EXCEPTION vocabularies to REJECT once real files confirm them | Phase 2 |
| Nitaqat inputs, bands, entity size/sector | own cycle |
| Loader promotion to `hr_schema/`, backend build context | later |

One observation for Phase 2: the synthetic real-mode run reported `dbt test PASS=9 ERROR=2`. That is the two-row synthetic payroll fixture failing not-null KPI tests, not a defect in this cycle — demo remains 11/11. It is a preview of something real though: **a client's first partial upload will fail dbt tests that assume a fully populated warehouse.** Worth planning for before Client Zero.

---

**Not merged. Awaiting review.**
