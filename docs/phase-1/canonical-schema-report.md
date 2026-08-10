# Phase 1 — Bilingual Canonical Schema (Execution Report)

**Branch:** `phase-1/canonical-schema` off `main` @ `2257d4a` · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.** Awaiting chief-architect review.
**Plan:** [`canonical-schema-plan.md`](canonical-schema-plan.md) · **Governing reference:** [`PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4

**Guardrails met:** `data_mode=demo` byte-identical (full pipeline from an *empty* warehouse: dbt 157/157, 11/11, reconciliation PASSED, no tracked-file drift). No validator behaviour change — proven by the parity harness, not asserted. No real data: every input synthetic, nothing written outside gitignored paths.

---

## 1. Commits

| # | Commit | Item |
|---|---|---|
| 1 | `eb40618` | Commit `PRODUCT-ARCHITECTURE.md` to version control |
| 2 | `90a56d3` | **Hotfix** — templates served from contracts, not sample data |
| 3 | `f0d77a6` | Bilingual canonical schema extension (5 contracts, 84 columns) + parity harness |
| 4 | `a7f37d7` | 1a loader in `scripts/` + `GET /api/meta/schema` |
| 5 | `89b0359` | Declared-derivation mechanism for `is_saudi` |

---

## 2. The mandatory gate — accept/reject parity

CI never reads the contracts (real path only), so CI passing is not evidence. `scripts/verify_contract_parity.py` is the evidence, and it is committed so cycle 1b can re-run it.

21 synthetic cases across the 5 contracted tables — conformant, missing-required, unexpected-column, bad-type, bad-enum — run twice: once against **`main`'s original contracts** (extracted with `git show main:…`), once against **the extended contracts on this branch**. Same synthetic inputs both times. The harness scrubs the absolute case path out of recorded errors so runs compare semantics, not temp directory names.

```
########## BEFORE — main's original contracts ##########
contracts: .../scratchpad/contracts_main
[BEFORE] cases=21 accept=6 reject=15 error=0

########## AFTER — extended contracts on this branch ##########
contracts: data/contracts
[AFTER] cases=21 accept=6 reject=15 error=0

########## PARITY VERDICT ##########
PARITY CONFIRMED - 21 cases, identical outcomes AND identical error strings
```

Per-case outcomes (identical in both runs):

```
employees    bad_enum__status                   REJECT
employees    bad_type__is_saudi                 REJECT
employees    conformant                         ACCEPT
employees    missing_required                   REJECT
employees    unexpected_column                  REJECT
payroll      bad_type__basic_salary             REJECT
payroll      conformant                         ACCEPT
payroll      missing_required                   REJECT
payroll      unexpected_column                  REJECT
attendance   bad_type__attendance_date          ACCEPT     <-- see §6, finding F1
attendance   conformant                         ACCEPT
attendance   missing_required                   REJECT
attendance   unexpected_column                  REJECT
compliance   bad_type__contract_authenticated   REJECT
compliance   conformant                         ACCEPT
compliance   missing_required                   REJECT
compliance   unexpected_column                  REJECT
hr_requests  bad_type__created_at               REJECT
hr_requests  conformant                         ACCEPT
hr_requests  missing_required                   REJECT
hr_requests  unexpected_column                  REJECT
```

---

## 3. Template hotfix — proof it no longer serves fabricated records

**Before.** `GET /api/data/templates?name=employees` returned `data/sample/employees_sample.csv` verbatim:

```
employee_id,employee_name,nationality,is_saudi,company,...
EMP001,Ahmad Al-Sudairy,Saudi,True,Company A,...
EMP002,John Doe,British,False,Company A,...
   ... 21 fabricated employee records, with salaries
```

**After** — captured live from the running app:

```
status: 200 | content-type: text/csv; charset=utf-8
content-disposition: attachment; filename="employees_template.csv"
--- body (verbatim) ---
'employee_id,employee_name,nationality,is_saudi,company,department,project,
job_title,job_family,grade,manager_id,cost_center,employment_type,contract_type,
joining_date,termination_date,contract_end_date,status,basic_salary,
housing_allowance,transport_allowance\r\n'
data rows: 0
```

One header row, CRLF, zero data rows, headers straight from the contract.

**Domains without a contract fail loudly rather than falling back:**

```
--- employee_relations (no contract) ---
409 No contract defined at data/contracts/employee_relations_schema.yml. A template...
```

Regression locked in by tests: header-only assertion, an explicit check that `EMP001` / `Ahmad Al-Sudairy` do not appear, header-matches-contract, and the 409 path.

---

## 4. What was built

### 4.1 Extended contracts (commit 3)

Per column: `name_en`, `name_ar`, `description_en`, `description_ar`, `example`. Per table: `version`, `table`, `label_en`, `label_ar`, `description_en/ar`. 84 columns across employees (21), payroll (14), attendance (15), compliance (13), hr_requests (11).

`allowed_values` stays a **flat list of strings** — the validator does `set(allowed)` against raw cell values, so objects would fail Rule 4 on every row. Bilingual display lives in the parallel `value_labels` map.

### 4.2 Loader (commit 4)

`scripts/canonical_schema.py` — PyYAML only, mtime-keyed cache, importable from `scripts/` and `backend/`. `load_schema`, `columns`, `column_names`, `required_columns`, `column_label(s)`, `table_label`, `value_label`, `describe`, `describe_all`.

The hotfix's interim direct-YAML reader was repointed at it in the same commit, so the column list has one definition rather than two.

`GET /api/meta/schema?table=&locale=` returns localized labels/metadata, never row data:

```
status 200 | table employees | label الموظفون | cols 21
    employee_id   -> الرقم الوظيفي
    employee_name -> اسم الموظف
    nationality   -> الجنسية
    status allowed: ['Active', 'Inactive', 'Terminated', 'On Leave']
    status labels:  {'Active': 'نشط', 'Inactive': 'غير نشط',
                     'Terminated': 'منتهية خدمته', 'On Leave': 'في إجازة'}
```

### 4.3 Derivations (commit 5)

`scripts/derivations.py`. Registry lookup by name, never `eval` — a contract is operator-supplied data, and executing text from it would make a schema file an execution vector. Unrecognised nationality values raise `DerivationError` naming each one; a blank nationality returns `None` (unknown, a DQ exception), never `False`.

Arabic normalisation handles the noise the architecture doc names: tatweel, alef/ya/ta-marbuta variants, diacritics, inconsistent spacing.

9 new tests, all CI-visible. **They caught a real bug in the first cut:** the diacritics range was `0x0610–0x0652`, which strips the Arabic letters themselves (`0x0621–0x064A`) — every Arabic nationality silently normalised to an empty string and returned `None` instead of `True`. Now scoped to tashkeel, honorifics and the superscript alef.

---

## 5. Deviations from the plan — disclosed

**D1 — No new `allowed_values` were added.** Plan step 1a.1 included enum vocabularies for the 7 bare status columns; they are not in this cycle. Adding an enum changes what the validator rejects, and "no validator behaviour change" was an explicit guardrail. Deriving them from sample data would also have been actively wrong — the samples are near-single-valued:

```
payroll_status: ['Paid']            shift_name: ['Day Shift']
qiwa_status:    ['Active']          gosi_status: ['Registered']
mudad_status:   ['Compliant']       insurance_status: ['Active']
```

Locking `payroll_status` to `["Paid"]` would reject every unpaid line in a real file. Sample-observed values are recorded as inert `observed_values` documentation instead, clearly marked as non-exhaustive and never validated against, so the vocabularies can be authored properly in 1b with real inputs.

**D2 — `is_saudi` stays `required: true`.** The derivation is declared and implemented but **not active**. Flipping `required` to false changes what the validator accepts. Cycle 1b flips it and wires `derive_column()` into `ingest_raw.py`. Until then a real export lacking `is_saudi` is still rejected — which is correct behaviour, just not yet the convenient one.

**D3 — `GET /api/meta/schema` was added** though the five numbered items did not name it. It is the backend half of the "UI labels" consumer from plan §4.3 and is additive. Frontend consumption (locale context, `useSchemaLabel`, RTL) is **not** in this cycle, per the Arabic-scope ruling.

**D4 — `scripts/verify_contract_parity.py` was committed.** The harness was mandated; committing it makes it re-runnable by 1b rather than a one-off.

---

## 6. New findings

**F1 — the corrupted date serial is not caught.** `PRODUCT-ARCHITECTURE.md` §4 names *"corrupted date serials (year `0025` instead of `2025`)"* as a real-world case the pipeline must handle. It currently passes contract validation:

```
0025-01-26 -> 0025-01-26      (parses cleanly as year 25)
2025-01-26 -> 2025-01-26
not_a_date -> None            (correctly rejected)
```

`str.to_date("%Y-%m-%d")` accepts year 25, so type-conformance sees nothing wrong. Pre-existing, unchanged by this cycle (identical in both parity runs). **Recommend a plausible-range check on DATE/TIMESTAMP in cycle 1b** — e.g. year within 1900–2100 — alongside `min_value` and `unique`.

**F2 — `backend/data/` and `backend/warehouse/` are untracked runtime residue**, including a ~12 MB stale DuckDB, previously copied into the backend image. Already excluded by the `.dockerignore` added in PR #6; noted here because it is the same class of "local state leaking into an artefact" as the template defect.

---

## 7. `hr_requests` / `employee_relations` mismatch — recommendation only, not acted on

Per ruling, the template catalogue membership is unchanged. Current state:

| Domain | Contract | In template catalogue | Real-sourceable |
|---|---|---|---|
| `employees`, `payroll`, `attendance`, `compliance` | yes | yes | yes |
| `hr_requests` | **yes** | **no** | no |
| `employee_relations` | **no** | **yes** (now 409) | no |

**Recommendation: derive the catalogue from the contracts directory, and delete the hardcoded list.** That is the same de-duplication principle as the rest of the cycle — a template exists if and only if a contract exists. It would add `hr_requests` and drop `employee_relations` automatically.

Before doing so, decide the substantive question: **should `employee_relations` have a contract?** It is an established domain with a dashboard page, a sample file, and 15 exception checks, yet no contract, so it can never be real-sourced. Authoring one is the better fix; removing its template is only the tidy one. Either way the current state — a template offered for a domain that cannot accept real data — should not persist.

---

## 8. Verification summary

| Check | Result |
|---|---|
| Contract parity (main vs extended, 21 cases) | **identical outcomes and error strings** |
| Full pipeline, **empty** warehouse, `data_mode=demo` | dbt run 157/157, dbt test 11/11, reconciliation PASSED, exit 0 |
| `[real]` lines during demo run | **0** — resolver inert, as required |
| Tracked-file drift after full refresh | **none** |
| pytest | **19 passed** (10 existing + 9 new) |
| Template endpoint | 1 header row, 0 data rows, no sample identifiers |
| Uncontracted domain | 409, no sample fallback |

Local runs used the scratchpad driver that swaps the stale `.venv/Scripts/dbt.exe` shim for `python -m dbt.cli.main` (same args, vars, cwd) — the known local-tooling defect from Phase 0. No repo file touched by it.

---

## 9. Carried forward

| Item | Target |
|---|---|
| `min_value`, `unique`, DATE plausible-range (F1) | **1b — must land before Phase 2** |
| Flip `is_saudi` to `required: false`, wire `derive_column()` into ingest | 1b |
| Author real enum vocabularies (D1) | 1b, with real inputs |
| Promote loader to `hr_schema/`, widen backend build context | 1b |
| Frontend locale context, `useSchemaLabel`, RTL | separate cycle |
| Bilingual Excel generator (instructions sheet, dropdowns, examples) | remainder of Phase 1 |
| De-duplicate `generate_sample_data.py` / `ingest_raw.py` / `compile_csv_to_parquet` onto the loader | 1c, each with its own empty-warehouse proof |
| Nitaqat inputs, bands, entity size/sector | own cycle, immediately after Phase 1 |
| `employee_relations` contract decision (§7) | chief-architect ruling |
| Arabic label review by an HR practitioner | **before merge** — 84 `name_ar` values are engineer-authored |

---

**Not merged. Awaiting review.**
