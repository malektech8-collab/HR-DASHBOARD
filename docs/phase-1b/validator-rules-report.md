# Cycle 1b-i — Validator Behaviour Changes (Execution Report)

**Branch:** `phase-1b/validator-rules` off `main` @ `02cf3e4` · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.**
**Plan:** [`validator-rules-plan.md`](validator-rules-plan.md) · **Governing reference:** [`PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4

This is the last gate before Phase 2. After this, the validator is what stands between a client's real export and the warehouse.

---

## 1. Commits

| # | Commit | Item |
|---|---|---|
| 0 | *(PR #11 merged first)* | prerequisite — column-inventory assertion |
| 1 | `7dad2df` | `--expect-rename` allowance |
| 2 | `0c94bd9` | violation collector — **pure refactor, 21/21 byte-identical** |
| 3 | `8f7446a` | the five rules |

---

## 2. Verify-first gate — demo loadability

Required before implementing. **PASSED.**

**Static.** The only production call site of `validate_csv_against_contract` is `scripts/ingest_raw.py:79`, inside the `if data_mode == "real":` branch. `data/sample/*.csv` is never validated.

**Empirical.** Full demo pipeline from an empty warehouse, with the rules in place:

```
employees rows in silver->warehouse : 21
duplicate EMP005 present            : 2 rows
payroll rows with negative net_pay  : 3
employees with negative basic_salary: 1
DQ exceptions surfaced              : 15
```

Every intentional defect in the sample still loads and still surfaces as an exception. The rules do not touch the demo path.

---

## 3. Step 1 gate — the collector refactor

Architecture §4 requires per-cell, row-numbered, localized errors; the validator raised on the first violation, with no row number, in English. Every rule depends on fixing that, so it landed first as a pure refactor and had to prove it changed nothing:

```
[STEP1] cases=21 accept=6 reject=15 error=0 | columns=75 across 5 tables
== column inventory ==   all five tables unchanged
== case outcomes ==      all cases identical
== verdict ==            PASS - no column or table lost (0 case difference(s))
```

`validate_csv_against_contract` keeps its signature, exception type and exact message text. The richer API is `validate_csv() -> ValidationResult`.

---

## 4. The rules

### 4.1 Severity

| Severity | Rules | Behaviour |
|---|---|---|
| **REJECT** | missing/unexpected column, unparseable type, implausible date, **duplicate primary key**, `required_when` unmet | nothing loads |
| **EXCEPTION** | `min_value`, non-PK `unique` | file loads, rows flow to the exceptions layer |

`primary_key: true` is now declared on `employees.employee_id` and `hr_requests.request_id`, so the unique rule can distinguish *"this row is wrong"* from *"every join is now wrong"*.

### 4.2 Rule-by-rule

**DATE plausible range** — `1940-01-01 .. today+2y`, per-column overridable via `min_date`/`max_date`. Catches the corrupted Excel serial named in the architecture doc:

```
Row 2, Joining Date: date '0025-01-26' is outside the plausible range
(1940-01-01 to 2028-08-10). A year like 0025 usually means a corrupted
Excel date serial - check the source export.

الصف 2، تاريخ الانضمام: التاريخ '0025-01-26' خارج النطاق المعقول …
```

Future dates are accepted — an offer starting next month is routine. `1939-12-31` and `today+5y` are rejected.

**`min_value`** — EXCEPTION. `Row 3, Net Pay: value -500 is below the minimum of 0.` / `الصف 3، صافي الراتب: القيمة -500 أقل من الحد الأدنى 0.` The file still loads (`result.ok` is `True`).

**`unique`** — REJECT on a PK, reporting every offending row: `Employee ID: value 'EMP001' appears 2 times (rows [2, 3]); it must be unique.` Telling a client an ID is duplicated without saying where is unactionable.

**`required_when`** — declarative `{column, equals}`, never an expression. `Row 2, End of Service Type is required when Employment Status is "Terminated".` If the condition column is absent, that is reported as structural rather than silently passing.

**`is_saudi`** — flipped to `required: false`, derivation wired into **both** ingest paths. Live proof on synthetic data with no `is_saudi` column:

```
[real] employees: ingesting from data/raw/employees.csv (contract-validated).
[derive] employees.is_saudi derived from nationality (2 Saudi / 3 rows).

┌─────────────┬─────────────┬──────────┐
│ employee_id ┆ nationality ┆ is_saudi │
╞═════════════╪═════════════╪══════════╡
│ R001        ┆ Saudi       ┆ true     │
│ R002        ┆ British     ┆ false    │
│ R003        ┆ سعودي        ┆ true     │
└─────────────┴─────────────┴──────────┘
```

And it fails loudly rather than guessing:

```
DerivationError: nationality_is_saudi: unrecognised nationality value(s)
['Martian']. Refusing to guess — is_saudi drives the Saudization percentage
and Nitaqat banding. Add each value to the alias table…
```

All synthetic files were removed and demo restored (employees back to 21 rows).

**Rename** — `insurance_status` → `health_insurance_status` across all nine consumers: contract (+ labels → `حالة التأمين الصحي`), 3 dbt models, sample CSV header, generator, `config/source_mapping_validation.yml`, 2 docs, and the untracked `backend/data/sample/` residue copy, which was deleted. The user-facing exception now reads **"Health Insurance Inactive"** / *"CCHI health insurance coverage status is not active"*. `gosi_status` keeps the GOSI side.

**Article 53** applied to the Probation value: `Probation - Article 53` / `إنهاء خلال فترة التجربة — المادة ٥٣`.

---

## 5. A harness fixture defect, surfaced and fixed

The first parity run showed **three** outcome changes, not one — `employees.conformant` and `hr_requests.conformant` flipped `ACCEPT → REJECT`.

Cause: the conformant fixture wrote **the same row twice** (`write_csv(p, names, [row, row])`). Under a primary-key rule two identical rows duplicate the PK, so the fixture was never a conformant file. The rule was right; the fixture was wrong.

Fixed rather than worked around — the fixture now varies every `unique`/`primary_key` column per row — and the baseline was **re-captured with the corrected fixture against the pre-rules validator**, so both sides of the comparison use identical inputs. Anything less would have been comparing two different questions.

---

## 6. Final parity delta

Same fixture both sides, rename declared:

```
== column inventory ==
  attendance   unchanged (15 columns)
  compliance   RENAMED insurance_status -> health_insurance_status  (declared)
  compliance   unchanged (13 columns)
  employees    unchanged (23 columns)
  hr_requests  unchanged (11 columns)
  payroll      unchanged (13 columns)
== case outcomes ==
  attendance   bad_type__attendance_date      ACCEPT -> REJECT  (OUTCOME CHANGED)
  compliance   missing_required               REJECT -> REJECT  (error string only)
  compliance   unexpected_column              REJECT -> REJECT  (error string only)
== verdict ==
  PASS - no column or table lost (3 case difference(s))
```

**Exactly one outcome change, exactly as predicted in the plan** — `attendance.bad_type__attendance_date` used `0025-01-26` as its bad-type value, which the DATE range check now catches. The two error-string changes are the compliance messages embedding the column inventory. No other delta.

Without declaring the rename, the harness correctly refuses:

```
compliance   DROPPED ['insurance_status']  <-- FAILURE
FAIL - a column or table was dropped        exit=1
```

Two small harness fixes were needed along the way: the `compare` arg check rejected the extra flag, and a declared in-place rename was mislabelled "REORDERED".

---

## 7. Demo impact — values identical, artefacts changed

Not claimed as byte-identity, per the guardrail.

**Unchanged** — full pipeline from an empty warehouse:

```
dbt run  -> Done. PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157
dbt test -> Done. PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11
Command Center integration reconciliation checks PASSED.

active_headcount           expected 19                    got 19                    MATCH
payroll_cost               expected 446175.0              got 446175.0              MATCH
saudization_pct            expected 50.0                  got 50.0                  MATCH
attendance_compliance_pct  expected 0.14777327935222673   got 0.14777327935222673   MATCH
total active exceptions    expected 667                   got 667                   MATCH
DQ exceptions              expected 15                    got 15                    MATCH
ALL DASHBOARD VALUES IDENTICAL: True
```

No `[real]` and no `[derive]` line appears in demo — the resolver stays inert and the sample supplies `is_saudi`, so the derivation never fires.

**Changed, by design:** `data/sample/compliance_sample.csv` header (tracked), the silver parquet column name, three dbt view definitions, and one user-facing exception string.

---

## 8. Tests

**34 passed** (19 existing + 15 new in `backend/tests/test_validator_rules.py`), covering: `min_value` is an exception not a rejection; duplicate PK rejects with all row numbers; distinct PKs pass; `0025-01-26` rejected; future joining date accepted; `today+5y` and `1939` rejected; `required_when` in all three states; a file without `is_saudi` validates; unexpected column still rejects; structural failure short-circuits per-cell checks; `health_insurance_status` is canonical and `gosi_status` still distinct.

Row numbering is asserted explicitly — header is row 1, so the first data row is row 2.

---

## 9. Carried forward

| Item | Target |
|---|---|
| EXCEPTION-severity violations are computed and returned but **not yet written to the gold DQ report** — ingest raises on rejects and loads on exceptions, but the contract exceptions do not yet join `validate_data.py`'s output | **1b-ii — needed before Phase 2 for the exceptions to reach the screen** |
| `employee_relations` contract; enum vocabularies; template-catalogue derivation | 1b-ii |
| Loader promotion to `hr_schema/`, backend build context | later |
| Nitaqat inputs, bands, entity size/sector | own cycle |

**§9 row 1 is the one gap worth flagging loudly.** The severity ruling says exception rows "flow to the existing exceptions layer". The validator now classifies them correctly and the file loads, but the plumbing that merges contract exceptions into `data/gold/data_quality_report.parquet` is not built. Today a `min_value` violation on a real file loads silently rather than appearing on the Data Quality page. Scoping that was beyond this cycle's five rules; it must land before a client sees real data.

---

**Not merged. Awaiting review.**
