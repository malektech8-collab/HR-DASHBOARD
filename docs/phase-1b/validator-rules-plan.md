# Cycle 1b-i — Validator Behaviour Changes (PLAN ONLY)

**Status:** proposed. Nothing implemented. This document is the only file added on `phase-1b/validator-rules`.
**Branch:** `phase-1b/validator-rules` off `main` @ `7caa52d` · **Date:** 2026-08-10
**Governing reference:** [`docs/PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4 (canonical schema, template flow, known real-world data issues).
**Scope:** the five validator behaviour changes deliberately excluded from Phase 1. Schema/catalogue work (`employee_relations` contract, enum vocabularies, template-catalogue derivation) is **1b-ii** and is out of scope here.

> **This is the last gate before Phase 2.** After this cycle the validator is what stands between a client's real export and the warehouse.

---

## 0. Two things to decide before anything is built

### 0.1 BLOCKING PREREQUISITE — the inventory assertion is not on `main`

The brief requires the column-inventory assertion to land **before** these changes. It exists, but in **PR #11, which is open and unmerged**; `main` @ `7caa52d` does not have it.

This is not a formality. **Rule 5 renames a column.** Without the inventory assertion, the harness compares each contract against itself and cannot distinguish a rename from a silent drop — the precise blind spot PR #11 closes. **PR #11 must merge before Rule 5 is implemented.**

One gap in PR #11 surfaces here: `compare` treats any removed column as a hard `FAIL`. A deliberate rename is a removal plus an addition and will trip it. Recommend adding an explicit allowance so an intended rename is declared rather than argued with:

```
verify_contract_parity.py compare before.json after.json \
    --expect-rename compliance.insurance_status:compliance.health_insurance_status
```

An undeclared removal still fails. This keeps the assertion strict while letting a reviewed rename pass on the record.

### 0.2 The hard gate now conflicts with the product's differentiator

Running the proposed rules against the sample data — the reference dataset the whole product demonstrates on:

```
employees duplicate employee_id  : ['EMP005']
payroll negative basic_salary    : 3 row(s)
payroll negative gross_pay       : 3 row(s)
payroll negative net_pay         : 3 row(s)
employees negative basic_salary  : 1 row(s)
```

Every one of those is an **intentional** data-quality issue. The pipeline already handles them: `validate_data.py` writes them to gold, `base_active_workforce` deduplicates defensively, and `mart_*_exceptions` surfaces them on screen. That is the product's stated differentiator — *"it tells the client which of their records are wrong rather than silently averaging over bad data"* (architecture §1).

If `min_value` and `unique` become whole-file hard rejects, a client whose export contains four bad rows out of five thousand gets **"file rejected"** instead of **"here are your four bad records"**. The hard gate would suppress the feature the product is sold on.

**Recommendation: make violation severity a declared property of the rule, not a global policy.**

```yaml
  - name: basic_salary
    type: DECIMAL
    min_value: 0
    on_violation: exception     # exception | reject
```

- **`reject` (whole file, fail-closed)** for *structural* violations — the file is the wrong shape and nothing downstream can be trusted: missing required column, unexpected column, unparseable type, implausible date. Existing Rules 1–3 keep this behaviour unchanged.
- **`exception` (row-level, load continues, row surfaced in the DQ layer)** for *content* violations on a well-formed file — `min_value`, and `unique` on non-key columns.

Proposed defaults: `min_value` → `exception`. `unique` on a **primary key** (`employees.employee_id`, `hr_requests.request_id`) → **`reject`**, because a duplicate primary key is not one bad row, it corrupts every join and inflates every aggregate downstream. That distinction is defensible; a blanket policy in either direction is not.

**This needs an explicit ruling.** If the ruling is "everything rejects", say so and I will implement it — but the sample data will no longer be loadable through the real path, and the first real client file will almost certainly be rejected outright.

---

## 1. Rule inventory

| # | Rule | Columns affected today | Proposed severity | Demo impact |
|---|---|---|---|---|
| 1a | `min_value` | 5 (`payroll.basic_salary`, `gross_pay`, `net_pay`; `attendance.late_minutes`, `net_late_minutes`) | `exception` | none |
| 1b | `unique` | 2 (`employees.employee_id`, `hr_requests.request_id`) | `reject` | none |
| 2 | DATE plausible range | 12 DATE/TIMESTAMP columns | `reject` | none |
| 3 | `is_saudi` derivation | `employees.is_saudi` (+ `nationality`) | n/a | **none, if gated on absence** |
| 4 | `required_when` | `employees.end_of_service_type` | `reject` | none |
| 5 | Rename `insurance_status` | `compliance` (+3 dbt models, sample, generator) | n/a | **inputs and view schemas change — see §7** |

Rules 1, 2 and 4 touch only `validate_schema.py`, which is invoked **exclusively on the `data/raw/` real path**. The demo path never calls it, so `data_mode=demo` output is unaffected by construction.

---

## 2. Prerequisite change: collect all violations, with row numbers

Architecture §4 step 3 specifies the target error UX:

> *"Errors are reported per-cell, in the user's language: 'Row 47, تاريخ الانضمام: expected YYYY-MM-DD, found `0025-01-26`.'"*

The current validator cannot produce that. It raises `SchemaValidationError` on the **first** violation, reports **no row number**, and is **English-only**. A client with 30 bad cells fixes one, re-uploads, discovers the next — thirty round trips.

**Every rule below depends on fixing this first**, so it is the first implementation step, not a nice-to-have:

1. Replace first-failure-raise with a **violation collector**: `[{rule, table, column, row, value, severity}]`.
2. Attach **1-based row numbers** matching what the client sees in Excel (header = row 1, first data row = row 2). Off-by-one here produces confidently wrong guidance.
3. Render messages **bilingually from the canonical schema** — `name_en` / `name_ar` are already there for exactly this.
4. Cap rendered detail (proposal: first 50 violations per rule, with a total count) so a catastrophically wrong file returns a usable message rather than 50,000 lines.
5. Keep the existing structural short-circuit: if Rule 1 or 2 fails, the file is the wrong shape and per-cell checks are meaningless — report the structural failure alone.

**Backward compatibility:** the existing four rules must produce byte-identical outcomes and messages for the single-violation cases the harness already covers. That is what the parity run proves.

---

## 3. Rule specifications

Throughout, `{col_en}` / `{col_ar}` come from the canonical schema; `{row}` is the Excel-visible row number.

### Rule 1a — `min_value`

**Rule.** For a column declaring `min_value: N`, every non-null value must be `>= N`. Non-numeric values are already caught by type conformance and are not re-reported here.

**Messages**
```
EN  Row {row}, {col_en}: value {value} is below the minimum of {min}.
AR  الصف {row}، {col_ar}: القيمة {value} أقل من الحد الأدنى {min}.
```

**Newly affects.** `payroll.basic_salary`, `payroll.gross_pay`, `payroll.net_pay`, `attendance.late_minutes`, `attendance.net_late_minutes` — all currently inert.

**Parity delta.** A new harness case `min_value_violation` per affected table: `ACCEPT → REJECT` (or → `ACCEPT with exceptions`, per the §0.2 ruling). No existing case changes.

### Rule 1b — `unique`

**Rule.** For a column declaring `unique: true`, no non-null value may repeat. Nulls are not compared (absence is a `required` concern).

**Messages**
```
EN  {col_en}: value {value} appears {n} times (rows {rows}); it must be unique.
AR  {col_ar}: القيمة {value} مكررة {n} مرات (الصفوف {rows})؛ يجب أن تكون فريدة.
```

Reporting **all** offending row numbers matters — telling a client "EMP005 is duplicated" without saying where is unactionable.

**Newly affects.** `employees.employee_id`, `hr_requests.request_id`.

**Parity delta.** New case `unique_violation`: `ACCEPT → REJECT`.

### Rule 2 — DATE plausible range

**Rule.** For DATE and TIMESTAMP columns, a value that parses must also fall within a plausible range. Default `1900-01-01 .. 2100-12-31`, overridable per column via optional `min_date` / `max_date`.

**Why it is needed.** This is the architecture's named real-world corruption, and it passes today:

```
0025-01-26 -> 0025-01-26      (parses cleanly as year 25 — ACCEPTED)
2025-01-26 -> 2025-01-26
not_a_date -> None            (correctly rejected)
```

**Messages**
```
EN  Row {row}, {col_en}: date {value} is outside the plausible range
    ({min_date} to {max_date}). A year like 0025 usually means a corrupted
    Excel date serial — check the source export.
AR  الصف {row}، {col_ar}: التاريخ {value} خارج النطاق المعقول
    ({min_date} إلى {max_date}). سنة مثل 0025 تعني عادةً تلفاً في تنسيق
    التاريخ في ملف Excel — يرجى مراجعة الملف المصدر.
```

The hint is deliberate: the client's actual problem is almost never "the year is wrong", it is "Excel mangled the column", and naming that saves a support round trip.

**Newly affects.** All 12 DATE/TIMESTAMP columns: `employees` (3), `attendance` (5), `compliance` (2), `hr_requests` (2).

**Severity: `reject`.** A corrupted date silently poisons tenure, expiry aging, and attendance windows. Unlike a negative salary, it is not visibly wrong on a dashboard.

**Parity delta.** New case `implausible_date` per table with a date column: `ACCEPT → REJECT`. **Watch `attendance.bad_type__attendance_date`, which currently records `ACCEPT`** — it uses `0025-01-26` as its "bad type" value. This case flips `ACCEPT → REJECT`. That is an *expected, intended* delta and the only pre-existing case whose outcome changes anywhere in this cycle.

### Rule 3 — `is_saudi` derivation

**Rule.** Flip `employees.is_saudi` to `required: false`. When the column is absent, derive it from `nationality` via the registry rule `nationality_is_saudi` (already implemented and tested in `scripts/derivations.py`). When present, use it as-is and do not derive.

**Fail loudly.** Unrecognised nationality values raise; nothing defaults to `false`. Already enforced and tested — `is_saudi` drives Saudization and Nitaqat banding, and a silent `false` understates the most consequential number in the product.

**Messages**
```
EN  {col_en} could not be derived: unrecognised nationality value(s) {values}.
    Add each to the alias table or correct the source export. Saudization is
    calculated from this field, so no value will be guessed.
AR  تعذّر اشتقاق {col_ar}: قيم جنسية غير معروفة {values}. يرجى إضافتها إلى
    جدول المرادفات أو تصحيح الملف المصدر. تُحتسب نسبة السعودة من هذا الحقل،
    ولن يتم تخمين أي قيمة.
```

**Wiring — two ingest paths, not one.** Both must be handled or the behaviour is inconsistent:

| Path | File | Note |
|---|---|---|
| Real-data ingest | `scripts/ingest_raw.py:94` | casts `is_saudi`; needs derive-when-absent ahead of the cast |
| **UI upload** | `backend/app/api/data.py:78` | `compile_csv_to_parquet` casts `is_saudi` only `if "is_saudi" in df.columns` — a file without it currently loads with the column simply missing |

The upload path is easy to miss and is how a client will most often supply data.

**Demo impact: none — conditional on implementation.** `data/sample/employees_sample.csv` carries `is_saudi`, so the derivation branch must be gated on the column being **absent**. Implemented that way, demo is byte-identical. Implemented as "always derive from nationality", demo output could change wherever sample `is_saudi` disagrees with sample `nationality`. **Gate on absence; verify with an empty-warehouse run.**

**Parity delta.** `employees.missing_required` currently drops `transport_allowance` (the last required column) — unchanged. New case `is_saudi_absent`: `REJECT → ACCEPT`. New case `is_saudi_absent_unknown_nationality`: `REJECT → REJECT` with a different rule and message.

### Rule 4 — `required_when` (conditional validation)

**Rule.** New optional contract key:

```yaml
  - name: end_of_service_type
    required: false
    required_when:
      column: status
      equals: Terminated
```

When the condition holds for a row, the value must be present and non-empty. Resolution is **declarative and registry-like** — a `{column, equals}` pair, never an expression string. Same reasoning as derivations: a contract is operator-supplied data and must never be executable.

**Messages**
```
EN  Row {row}, {col_en} is required when {cond_col_en} is "{cond_value}".
AR  الصف {row}، {col_ar} مطلوب عندما تكون {cond_col_ar} "{cond_value}".
```

**Newly affects.** `employees.end_of_service_type` only. If the condition column is absent from the file, the condition cannot be evaluated — treat as a structural error naming `status`, not as a silent pass.

**Parity delta.** New case `required_when_violation`: `ACCEPT → REJECT`. No existing case changes — the harness's conformant row sets `status` to `allowed_values[0]` (`Active`), so the condition does not fire.

### Rule 5 — rename `insurance_status` → `health_insurance_status`

**Rule.** Health insurance (CCHI) and social insurance (GOSI) are legally distinct, separately mandated and separately audited. `insurance_status` is ambiguous; `gosi_status` already carries the GOSI side.

Supporting evidence that the intent was always CCHI: the exception text in `mart_compliance_exceptions.sql:113` already reads *"Medical insurance coverage status is not active"*. The rename makes the schema agree with what the product already tells the user.

Proposed labels: `name_en: Health Insurance Status`, `name_ar: حالة التأمين الصحي` (the earlier طبي → صحي also aligns with CCHI's own terminology).

**Every consumer — the full list:**

| # | File | Nature |
|---|---|---|
| 1 | `data/contracts/compliance_schema.yml` | the definition |
| 2 | `dbt_analytics/models/marts/base_compliance_current.sql:24` | `SELECT c.insurance_status` |
| 3 | `dbt_analytics/models/marts/base_government_platform_records.sql:16` | `SELECT c.insurance_status` |
| 4 | `dbt_analytics/models/marts/mart_compliance_exceptions.sql:116` | `WHERE insurance_status IS NULL OR != 'Active'` |
| 5 | `data/sample/compliance_sample.csv` | header (**tracked**) |
| 6 | `scripts/generate_sample_data.py` | 2 occurrences — header + row writer |
| 7 | `config/source_mapping_validation.yml` | governance-simulation registry |
| 8 | `docs/DATA_MODEL.md`, `docs/SOURCE_MAPPING_VALIDATION_PROTOCOL.md` | documentation |
| 9 | `backend/data/sample/compliance_sample.csv` | **untracked local residue** — will drift if not deleted |

**Not affected, verified by grep:** nothing in `backend/app`, nothing in `frontend/src`. It is **not an output column of any mart**, so no API payload and no dashboard field changes name.

**Recommend also updating the user-facing exception text** at `mart_compliance_exceptions.sql:113-114` from *"Insurance Inactive"* to *"Health Insurance Inactive"*, so the screen matches the schema. Small, but this is the string a client actually reads.

**Parity delta.** Inventory: `compliance` shows `removed: [insurance_status]`, `added: [health_insurance_status]`. With PR #11's `compare` as written this is a **FAIL** until the `--expect-rename` allowance from §0.1 exists. Case outcomes: unchanged in kind; the two `compliance` error strings that embed the column inventory change text.

---

## 4. Ordering

Each step is independently verifiable; do not batch them.

| Step | Work | Gate |
|---|---|---|
| **0** | **Merge PR #11**, then add `--expect-rename` to `compare` | inventory assertion live |
| 1 | Violation collector, row numbers, bilingual rendering (§2) | parity 21/21 byte-identical — pure refactor, zero behaviour change |
| 2 | Rule 2 (DATE range) | 1 pre-existing case flips (`attendance.bad_type__attendance_date`), + new cases |
| 3 | Rules 1a/1b (`min_value`, `unique`) — **after the §0.2 ruling** | new cases only |
| 4 | Rule 4 (`required_when`) | new cases only |
| 5 | Rule 3 (`is_saudi`) — both ingest paths | new cases + **empty-warehouse demo proof** |
| 6 | Rule 5 (rename) | inventory rename declared; **empty-warehouse demo proof** |

Step 1 first is the load-bearing decision: it is a pure refactor that must prove 21/21 unchanged, which establishes a trustworthy baseline before any rule actually changes behaviour.

---

## 5. Consolidated parity delta

**Pre-existing cases whose outcome changes: exactly one.**

```
attendance  bad_type__attendance_date   ACCEPT -> REJECT     (Rule 2)
```

It uses `0025-01-26` as its bad-type value, which the DATE range check now catches. Intended.

**Error-string-only changes:** the two `compliance` cases embedding the column inventory (Rule 5).

**Inventory delta:** `compliance` — one removal, one addition (Rule 5, declared rename).

**New cases** (~11): `min_value_violation` ×2 tables, `unique_violation` ×2, `implausible_date` ×4, `required_when_violation` ×1, `is_saudi_absent` ×1, `is_saudi_absent_unknown_nationality` ×1.

**Any other delta is a defect — stop and report.**

---

## 6. Demo impact — explicit

Per the guardrail, stated plainly rather than worked around.

| Rule | `data_mode=demo` byte-identical? |
|---|---|
| 1a, 1b, 2, 4 | **Yes, by construction.** `validate_schema.py` is called only on the `data/raw/` real path. |
| 3 (`is_saudi`) | **Yes — conditional on gating the derivation on column absence.** The sample carries `is_saudi`. If implemented as "always derive", demo output could change. Must be proven with an empty-warehouse run. |
| 5 (rename) | **No — and this is the one to be explicit about.** |

**Rule 5 in detail.** Dashboard values, dbt model/test counts (157/11) and reconciliation results are unchanged, and no API payload field changes. But three things *do* change and calling this "byte-identical" would be false:

1. `data/sample/compliance_sample.csv` — a **tracked** file — changes its header.
2. `data/silver/compliance.parquet` changes its column name.
3. Three dbt view definitions change their column lists (`base_compliance_current`, `base_government_platform_records`).

So: **demo *behaviour* is preserved; demo *artefacts* change.** The honest verification claim is "157/157, 11/11, reconciliation PASSED, dashboard values identical" — not "byte-identical". Requires an empty-warehouse rebuild plus a before/after comparison of the compliance KPI values specifically.

---

## 7. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| §0.2 ruling goes "reject everything" and Phase 2's first file is rejected wholesale | **High** | Get the ruling before building; if reject, invest in the error UX so the client can fix in one pass |
| Row numbers off by one against what the client sees in Excel | Medium | Header = row 1, first data row = row 2; assert explicitly in tests |
| Rule 5 misses the untracked `backend/data/sample/` copy | Medium | Delete it as part of the change; already excluded from images by `.dockerignore` |
| Arabic error strings damaged by encoding on Windows | Medium | UTF-8 no BOM; round-trip assertions; the Phase 1 diacritics bug is precedent |
| `is_saudi` derivation applied in demo, changing sample-derived Saudization | Medium | Gate on absence; empty-warehouse proof |
| Rename trips `compare` as a FAIL and is force-merged past | Medium | Build `--expect-rename` first, so the intent is declared rather than overridden |
| Violation collector changes existing messages | Medium | Step 1 must prove 21/21 byte-identical before any rule lands |

---

## 8. Decisions needed before implementation

1. **§0.2 — `reject` vs `exception` severity** for `min_value` and `unique`. My recommendation: `min_value` → exception; `unique` on a primary key → reject. This is the decision that most shapes Phase 2.
2. **PR #11 merge** — blocking prerequisite for Rule 5.
3. **`--expect-rename` allowance** — accepted as part of step 0?
4. **Violation cap** — is 50 per rule the right ceiling for the rendered message?
5. **DATE range bounds** — is `1900..2100` right, or should `joining_date` also reject future dates?
6. **Exception text update** — change *"Insurance Inactive"* to *"Health Insurance Inactive"* in the same cycle?

---

**Prepared for chief-architect review. No implementation performed.**
