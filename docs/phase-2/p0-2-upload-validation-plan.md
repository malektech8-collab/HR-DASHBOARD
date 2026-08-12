# P0-2 — Upload Validation (PLAN ONLY)

**Branch:** `phase-2/p0-2-upload` off `main` @ `e9210b2` (coverage surface merged) · **Date:** 2026-08-11
**Status:** plan only. Nothing implemented.
**Prior:** [`p0-3-category-f-report.md`](p0-3-category-f-report.md), [`coverage-surface-report.md`](coverage-surface-report.md)

Every safeguard built since cycle 1b-i protects `data/raw/` + `build_warehouse`. `POST /api/data/upload` writes to `data/silver/` and protects nothing.

---

## 0. Verified state, with three corrections and two additions

The architect's reading is confirmed: `upload_data_file` contains no `validate_csv`, no staging, no contract check. Measuring it produced three things worth correcting before designing around it.

**Correction 1 — `is_saudi` is not bypassed; it is duplicated.** `compile_csv_to_parquet` carries its own copy of the derivation, with a comment saying *"The UI upload is a second ingest path … it must behave identically."* That is worse than a gap in one specific way: a gap is visible, and a second implementation that claims parity drifts silently. It has already drifted — `ingest_raw` **raises** when neither `is_saudi` nor `nationality` is present; the upload copy silently skips.

**Correction 2 — the divergence is much larger than one column.** Counted from source:

```
tables typed by scripts/ingest_raw.py : 21
tables typed by the upload path       :  5
typed by ingest and NOT by upload     : 17
```

The 17 include **`hr_requests`, which is contracted**. Upload writes it to silver as all-strings, and dbt reads it from there. The other 16 are the uncontracted domains — which, after step 2b, are never `provided` in real mode, so nothing serves them; the defect is real but currently harmless. `hr_requests` is not.

**Correction 3 — the `.parquet` branch is worse than "no schema inspection".** It is `shutil.copyfileobj` into `data/silver/{table}.parquet`. Any file with a `.parquet` extension becomes that domain's silver table. There is no read, so not even "is this a parquet file" is established.

**Addition 1 — no authentication.** `upload_data_file` has no `Depends(get_current_user)`. The project has auth (`app/api/dependencies/auth.py`, used by `/api/governance/*`); this endpoint does not use it. An unauthenticated POST replaces a domain's silver table. This is outside the stated scope of P0-2 and I am not folding it in silently — see §9.

**Addition 2 — nothing calls it.** `uploadFile()` exists in `frontend/src/lib/api.ts` and **no page invokes it**. The endpoint is reachable but unreached. That does not reduce the severity — an unauthenticated, unvalidated write path is a defect whether or not our own UI uses it — but it does make this cycle materially cheaper: there is no existing client flow to migrate, so the design is free to be the right one rather than a compatible one.

---

## 1. The guarantee inventory

What each path actually enforces today. This table is the argument for the whole cycle.

| Guarantee | `data/raw` + `build_warehouse` | `POST /api/data/upload` |
|---|---|---|
| Contract validation (`validate_csv`) | yes — REJECT aborts the run | **no** |
| Required columns / no unexpected columns | yes | no |
| Type conformance | yes | partial, 5 of 21 tables |
| `allowed_values`, `min_value`, `unique`, `required_when` | yes | no |
| DATE plausible range (1940 … today+2y) | yes | no |
| `is_saudi` derivation | yes, raises on ambiguity | duplicated, silently skips |
| EXCEPTION rows → data-quality layer | yes | no |
| Declared-domain registry | yes | no |
| Coverage / history declaration (Category F) | yes, fails loudly | **no** |
| Reporting-period coverage gate (2a.5) | yes | no |
| Fail-closed on sample fallback | yes | n/a — writes silver directly |
| Authentication | n/a (operator-run) | **no** |

Every "yes" in the left column was built in the last six cycles. Every "no" in the right column is reachable with one HTTP request.

---

## 2. The design

```
  POST /api/data/uploads            -> STAGE     bytes land in staging, nothing else happens
  GET  /api/data/uploads/{id}       -> PREVIEW   contract violations, row counts, inferred period
  POST /api/data/uploads/{id}/commit-> COMMIT    declare + move to data/raw + run the pipeline
  DELETE /api/data/uploads/{id}     -> DISCARD   staging is disposable by construction
```

**Nothing reaches silver except through `ingest_raw`.** That is the single invariant this cycle exists to establish, and every other decision below follows from it.

### 2.1 Stage

`POST /api/data/uploads` accepts a file and a declared `table`, writes the bytes to staging, and returns an id. **It does not validate.** Validation is a separate, repeatable read — a client who fixes their file re-uploads rather than re-runs a hidden step, and staging never holds a half-validated state.

The `table` is a **parameter**, not derived from the filename. Today `table_name = os.path.splitext(filename)[0].replace("_sample","")`, so `employees (3).csv` becomes the table `employees (3)`, and `payroll.csv` renamed to `employees.csv` silently replaces the employee master. A client picks the domain from a list of contracted tables; anything else is a 400.

### 2.2 Validate / preview

`GET /api/data/uploads/{id}` runs `validate_csv(staged_path, table)` — **the same function ingest runs** — and returns:

- REJECT violations, with row and column, capped at the existing `MAX_RENDERED_VIOLATIONS = 100`
- EXCEPTION violations, which do not block, so the client knows what will land in the data-quality layer
- row count, distinct period labels or date range, and the columns present versus contracted
- for a date-grained domain, the **suggested** coverage window from the file's date range — *suggested*, never applied: ruling 3 of Category F says coverage is declared, and a pre-filled field the client confirms is a declaration; a silently applied default is not

Read-only. It writes nothing, so it can be called repeatedly and cannot leave state behind.

### 2.3 Commit

`POST /api/data/uploads/{id}/commit` takes the declaration (§5) and:

1. writes the coverage / history declaration to `data/onboarding/declared_domains.yml` via `onboarding.declare()`
2. moves the staged file to `data/raw/{table}.csv`
3. runs the existing pipeline

**Then it does nothing else**, because everything else already exists. `ingest_raw` validates against the contract, derives `is_saudi`, routes EXCEPTION rows, enforces the coverage window and the period gate; `build_warehouse` runs the declared-domain guard and writes provenance. A REJECT at commit rolls back — the staged file is removed from `data/raw/`, the declaration is reverted, and the run aborts before dbt.

---

## 3. Where staged files live

`data/staging/{upload_id}/` — `upload_id` a UUID, containing the original bytes under a canonical name plus a small `manifest.json` (table, original filename, size, sha256, uploaded_at, uploaded_by).

Three constraints, each for a reason this codebase has already paid for:

- **Gitignored.** `data/staging/` joins `data/raw/` in `.gitignore`, and a test asserts it is ignored — client data must not be committable by accident.
- **Not `data/silver/`.** Silver is what dbt reads. A staged file in silver is served.
- **Not `data/raw/` either.** `data/raw/` is the real-mode resolver's input; anything there is ingested on the next run. Staging must be inert — a file that has been uploaded but not committed must have **no** effect on any pipeline run.

Staging is disposable: a retention sweep on commit and discard, and nothing downstream may ever read from it. A test walks `scripts/` and `dbt_analytics/` and fails on any reference to `data/staging`.

---

## 4. The `.parquet` path — refuse it

**Recommendation: reject `.parquet` at upload, with a named precondition for allowing it later.** Four reasons, in order of weight:

1. **The validator is CSV-shaped.** `validate_csv` reports `Row 7, column 'iqama_expiry'` because it reads a CSV with positions. Validating parquet properly means a frame-level validator — a *second* implementation of the contract rules, which is precisely the duplication that produced §0's corrections. Accepting parquet without that is accepting it unvalidated.
2. **Parquet is our artefact, not the client's.** An HRIS exports CSV or Excel. Accepting parquet is accepting our own intermediate format as an input, and the only party who has one is us.
3. **The current branch is the worst line in the file** — a binary copy straight into silver with no read at all. Deleting it removes more risk than any other single change in this plan.
4. **Refusing is reversible; accepting is not.** A 400 with a clear message costs a client nothing today. A parquet ingest path, once relied on, has to be supported.

**Named precondition, so this is a decision and not a permanent no:** parquet becomes acceptable when `validate_csv` has been refactored so its rule engine runs against a **polars frame**, with the CSV reader as one adapter and a parquet reader as another — *one* rule implementation, two readers. That refactor is worth doing on its own merits; it is not worth doing inside this cycle.

Interim: `.csv` only. Excel (`.xlsx`) is out of scope here and is the Phase 1 template deliverable's natural companion — worth noting because a client's real answer to "CSV only" will be "I have an .xlsx".

---

## 5. Coverage and history declaration at upload

Category F requires a coverage window for date-grained domains and, per amended ruling 2, a history depth for `employees`. Both are **declarations**, and the upload flow is the only place a human is present to make one.

`POST …/commit` body:

```jsonc
{
  "coverage": { "start": "2026-08-01", "end": "2026-08-14" },  // required for attendance
  "history":  { "since": "2020-01-01" }                        // required for employees
}
```

Rules, all inherited rather than invented:

- **Required, not optional, for the domains that need them.** `onboarding.DATE_GRAINED` and `HISTORY_DECLARING` already name them. A commit without the declaration is a 400 that names the field — the API-layer form of `assert_coverage_declared`.
- **Pre-filled from the file, confirmed by the operator.** The preview suggests the window from the data's date range; the commit body must still carry it. That distinction is ruling 3: a suggestion a human confirms is a declaration, an inferred value silently applied is not.
- **`declare()` already accepts both** (`coverage_start`, `coverage_end`, `history_since`), so the commit step calls the existing function. No second registry writer.
- The existing loud failures then do their job at ingest: rows outside the window, and history deeper than the file supports.

---

## 6. The `.uploaded` freeze marker — delete it

Today `upload` writes `{table}.parquet.uploaded`, and two readers act on it: `ingest_raw` skips that table's ingest, and `generate_sample_data` skips regenerating its sample. It exists to stop sample regeneration clobbering a manual upload.

**In the new design it has no purpose.** Committed data lives in `data/raw/`, and in real mode `ingest_raw` never loads sample at all — that is Phase 2 P0-1's fail-closed rule. There is nothing left for the marker to protect against.

It is also the single mechanism with a **known incident**: a stale marker froze employees ingest and zeroed four Attendance widgets while every check reported green. `scripts/ingest_raw.py` already names it in a comment as the pattern not to repeat, and `onboarding.py`'s module docstring cites it as the reason declared-ness is read from a registry rather than inferred.

Plan: remove the write, remove both readers, and add a test asserting no `.uploaded` file is created by any code path. Removing the readers is behaviour-neutral in demo — no marker exists in CI — which the gate will confirm.

---

## 7. Commit reuses the ingest path — the load-bearing decision

**Yes, and this is the point of the cycle.** §0's corrections are the evidence: a second implementation that *claims* parity in a code comment has already diverged on 17 tables and on the one behaviour it explicitly promised to match.

So the target state is not "two paths that agree". It is **one path**:

```
data/raw/{table}.csv  ->  ingest_raw  ->  validate_csv  ->  derivations  ->  silver
                              ^
                    upload commit moves the file here
```

`compile_csv_to_parquet` is **deleted**, not fixed. Fixing it means maintaining the 21-table type map twice; deleting it means the upload path has no opinion about types at all.

The mechanism for "commit runs the pipeline" is the existing `POST /api/data/refresh`, which already shells `scripts/refresh_all.py`. Commit should call the same code rather than a third invocation route. Two things about it need attention and are in scope:

- it runs the **whole** pipeline including `create_sample_data()`; in real mode that must not run, and today `refresh_all.main()` calls it unconditionally
- its 180-second timeout is a full dbt build plus ingest; on a real dataset that is optimistic, and a timeout mid-run leaves the warehouse in whatever state dbt reached

A rollback path matters more than either: commit must be able to leave the system exactly as it was. Simplest sufficient design — keep the previous `data/raw/{table}.csv` and the previous registry alongside the new one until the pipeline exits 0, then discard; on failure, restore both. Not a transaction, but recoverable, and recoverable is the requirement.

---

## 8. Tests

| Test | Pins |
|---|---|
| a file with a REJECT violation cannot be committed | the whole cycle in one test |
| nothing reaches silver without ingest | walk the API source; **no** write to `data/silver` outside `ingest_raw` |
| staging is inert | a staged, uncommitted file changes no pipeline output |
| `data/staging` is gitignored | client data cannot be committed by accident |
| `.parquet` is refused with a clear message | §4 |
| commit without coverage for a date-grained domain is a 400 | §5, naming the field |
| commit without history for `employees` is a 400 | amended ruling 2 |
| the declaration reaches the registry via `declare()` | one registry writer |
| rollback | a REJECT at commit leaves `data/raw`, the registry and silver untouched |
| no `.uploaded` file is ever written | §6 |
| `compile_csv_to_parquet` no longer exists | §7 — the second implementation is gone, not dormant |
| the table is a parameter, not the filename | `payroll.csv` renamed `employees.csv` cannot replace the employee master |

---

## 9. Out of scope, flagged rather than folded in

**Authentication on the upload endpoints.** `upload_data_file` has no `Depends(get_current_user)`; the project's auth exists and is used elsewhere. Upload, commit and discard all mutate client data and all should require an authenticated operator, and commit arguably a specific role.

I am **not** adding it inside this cycle without a ruling: it changes who can call an endpoint, it touches `MOCK_USER_DB` and the synthetic-JWT layer that no cycle has yet reviewed, and bundling an access-control change into a data-validation change makes both harder to review. It is a one-line dependency per route once ruled on. **Recommend a decision now and a separate, small cycle to apply it.**

---

## 10. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 1 | Refuse `.parquet`; make `table` a parameter | yes — two small changes, removes the worst two failure modes on day one |
| 2 | Stage / preview / discard | yes — new endpoints, nothing existing changes |
| 3 | Commit via `data/raw` + `declare()`; delete `compile_csv_to_parquet` and the old upload | the cycle's substance |
| 4 | Remove the `.uploaded` marker and both readers | yes |
| 5 | Frontend upload flow | separate; there is no existing UI to migrate |

Step 1 alone would have prevented the two most severe reachable outcomes, and it is a few hours. If the cycle has to be cut, cut from the bottom.

---

## 11. Risks

1. **A long-running commit inside an HTTP request.** A full pipeline is minutes on real data. The honest options are a background job with a status endpoint, or a synchronous call with an explicit and generous timeout. Recommend synchronous first — a client uploading a file is waiting for the answer anyway — and note that the current 180s is already too short.
2. **Rollback is a file-move, not a transaction.** A crash between the registry write and the pipeline exit leaves a declaration without data. The declared-domain guard catches exactly that on the next run (declared-but-empty aborts), so the failure is loud rather than silent — but it needs a documented recovery step, not just a test.
3. **Deleting `compile_csv_to_parquet` deletes the only upload path that works today.** Between steps 3 and 5 there is no UI, and the endpoint's shape changes. Acceptable only because §0's Addition 2 established that nothing calls it — that fact should be re-verified at execution rather than trusted from this document.

---

## 12. Open questions

1. **Excel.** A client's answer to "CSV only" will be "I have an .xlsx". Is xlsx in scope for this cycle, or does it follow the Phase 1 bilingual template? Recommend: follows the template, but the refusal message should say so rather than implying CSV is the only format we will ever take.
2. **Who may commit?** §9. A ruling on roles determines whether commit needs one dependency or three.
3. **Multiple domains in one upload.** A client is more likely to have five files than one. Staging by `upload_id` supports a batch naturally, but batch commit means all-or-nothing across five contract validations. Recommend per-file commit for this cycle, and note that a batch changes the rollback story significantly.

---

**Prepared for chief-architect review. No implementation performed.**
