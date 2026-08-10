# Phase 2 P0 — Onboarding Safety (PLAN ONLY)

**Status:** proposed. Nothing implemented. This document is the only file added on `phase-2/p0-onboarding-safety`.
**Branch:** `phase-2/p0-onboarding-safety` off `main` @ `ffb2212` · **Date:** 2026-08-10
**Governing reference:** [`docs/PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4 · **Context:** [`onboarding-plan.md`](onboarding-plan.md) §1, §3

Two verified defects that make a real client deployment unsafe today. Both are hotfixes. Mapping profiles and the full preview UI stay in the Phase 2 plan, after these.

---

## 0. The one mechanism

The declared-domain registry is the substrate for three separate problems, which is why it is described once, first:

| Problem | What the registry provides |
|---|---|
| P0-1 silent sample fallback | the explicit opt-in that distinguishes "onboarding incrementally" from "a domain is missing by mistake" |
| dbt test scoping | a **declared** signal, so scoping never rests on inference |
| per-domain provenance in the UI | which numbers are the client's and which are absent |

### 0.1 Shape

A deployment-level statement, not a derived artefact. It is an **input**: the client declares what they are onboarding.

```yaml
# data/onboarding/declared_domains.yml   (gitignored - deployment state, not repo content)
version: 1
declared:
  - employees
  - payroll
declared_by: "operator@client"
declared_at: "2026-08-10"
note: "Phase 1 onboarding: workforce and payroll only."
```

Absent file ⇒ nothing declared ⇒ real mode refuses to run (§1.2). Demo mode ignores it entirely.

Every entry must be a contracted table; an unknown name is a hard error, not a warning. An env override (`DECLARED_DOMAINS=employees,payroll`) is worth considering for containerised deployments where mounting one more file is friction — flagged as a decision, not assumed.

### 0.2 The guard — `declared == populated`

Run after ingest, before `dbt run`, and fail the build on divergence:

| Condition | Meaning | Action |
|---|---|---|
| declared, has rows | normal | proceed |
| **declared, zero rows** | **a real defect** — broken ingest, bad join, failed resolver | **abort** |
| undeclared, zero rows | expected; not onboarded yet | proceed, mark not-provided |
| **undeclared, has rows** | stale registry or a leaked path | **abort** |

This is the whole answer to the masking concern. Once divergence is a build failure, an empty mart for an undeclared domain is *provably* "not uploaded yet" rather than "silently broken" — and a declared domain that comes back empty fails loudly instead of being scoped out.

### 0.3 A simplification this enables

With the guard in place, **templated dbt test severity is probably unnecessary.**

An undeclared domain has an empty mart, so `not_null` passes vacuously. Normally that vacuous pass *is* the masking problem — but the guard has already proved the emptiness is declared and intentional. Declared-but-empty can never reach dbt, because the guard aborts first.

So the recommended approach is: **leave the 11 dbt tests exactly as they are.** No per-domain severity, no conditional configuration, no generated `schema.yml`.

The alternative — jinja-templated `severity` driven by a `declared_domains` dbt var — is more expressive but adds moving parts, and **I have not verified that dbt 1.8.2 renders jinja in a test's `severity` config**. I am not asserting that it does. If the guard-based approach is rejected, that capability needs a spike before it is planned around.

---

## 1. P0-1 — silent sample fallback

### 1.1 Verified behaviour

`scripts/ingest_raw.py`, real mode, missing raw file:

```python
else:
    print(f"[real] {table}: no {raw_path}; falling back to sample.")
```

Measured with a client supplying only payroll: `headcount 19` and `saudization 50.0` — fabricated, from sample — rendered beside their one real payroll figure with no indicator.

### 1.2 Proposed behaviour

**Default: fail closed.** In real mode, every contracted domain without a raw file aborts the run — reporting **all** missing domains at once, not the first:

```
EN  Real-data mode requires a file for every contracted domain. Missing:
    attendance, compliance, employee_relations, employees, hr_requests.
    To onboard incrementally, declare the domains you are providing in
    data/onboarding/declared_domains.yml.
AR  يتطلب وضع البيانات الحقيقية ملفاً لكل نطاق متعاقد عليه. الملفات الناقصة:
    … لبدء الإدخال التدريجي، عرّف النطاقات التي تقدمها في ملف
    data/onboarding/declared_domains.yml.
```

**Opt-in: declared partial onboarding.** With a registry present:

- **declared + file present** → validate and load (unchanged).
- **declared + file missing** → abort. A declaration is a promise; an unfulfilled one is an error, not a fallback.
- **undeclared** → **load nothing.** The table is empty. It is *never* filled from sample in real mode.

The `else` branch that prints "falling back to sample" is deleted, not softened. There is no configuration under which real mode serves sample data for a contracted domain.

### 1.3 The scope boundary this exposes

The fix covers the **6 contracted** domains. The other **15 tables have no contract and always load sample**, so in real mode a client's Recruitment, Talent, Succession and Learning pages render fabricated data — the same defect, wider.

`PRODUCT-ARCHITECTURE.md` §7 already names this: *"Must be gated or clearly labelled, never shown as real."* It is not fixed by P0-1 and should not be quietly assumed to be.

Options, needing a ruling: gate those modules off entirely in real mode; label them at module level as demo; or leave and accept until each domain is contracted. **Recommend gating them off in real mode** — a hidden module cannot be misread, whereas a label competes for attention with a plausible-looking number. Flagged as a decision because it removes visible functionality from a real deployment.

### 1.4 Demo impact

**Byte-identical.** Every change is inside `if data_mode == "real":`, and the registry is not consulted in demo. Verification: empty-warehouse demo run → dbt 157/157, 11/11, reconciliation PASSED, `19 / 446175.0 / 50.0 / 667 / 15`.

---

## 2. P0-2 — the upload endpoint bypasses validation

### 2.1 Verified behaviour

`POST /api/data/upload` contains no reference to `validate_csv`. It writes **straight to `data/silver/{table}.parquet`** and then creates a `.uploaded` marker. Every rule from 1b-i and 1b-ii — required columns, unexpected columns, types, date ranges, primary keys, `required_when`, vocabularies, `min_value` — applies to `data/raw/` and not to the path a client actually uses.

`table_name` is also derived from the *uploaded filename* (`os.path.splitext(...).replace("_sample", "")`), so the client's choice of filename decides which warehouse table is overwritten.

### 2.2 The design: upload → stage → validate → preview → commit

The key move is that **commit promotes to `data/raw/`, not to `data/silver/`.** The upload path then feeds the same validated ingest the real path already uses, and the two routes stop having different guarantees.

```
POST /api/data/uploads                 -> stage
   body: file + domain (explicit, not inferred from the filename)
   writes data/staging/{upload_id}/{domain}.csv        (gitignored)
   returns {upload_id, domain, rows, columns}

GET  /api/data/uploads/{id}/validation -> validate
   runs validate_csv against the staged file
   returns rejects + exceptions, bilingual, row-numbered
   nothing has moved anywhere

GET  /api/data/uploads/{id}/preview    -> preview
   row count, detected period, sample parsed rows, what will change

POST /api/data/uploads/{id}/commit     -> commit
   refuses if any REJECT-severity violation stands
   promotes data/staging/{id}/{domain}.csv -> data/raw/{domain}.csv
   adds {domain} to the declared registry
   triggers the existing refresh

DELETE /api/data/uploads/{id}          -> discard
```

Consequences worth stating plainly:

- **Nothing reaches silver unvalidated**, because nothing reaches silver at all except through ingest.
- **The domain becomes explicit.** It is a request parameter validated against the contracted set, not scraped from a filename.
- **Commit is the natural place to declare a domain**, which is how the registry stays current without a second manual step.
- Staged uploads need a TTL and a size cap; abandoned uploads must be reaped. This is a new directory that will accumulate client data — PDPL-relevant, so retention belongs in the design rather than after it.

### 2.3 Retiring the `.uploaded` freeze

The marker exists only because uploads wrote directly to silver and had to be protected from being overwritten by the next ingest. Once silver is always derived from `raw`/`sample`, the marker has no job.

Proposed: delete the `custom_exists` monkeypatch in `ingest_raw.py`, delete the marker write in the upload path, and **actively remove any existing markers on startup** — a marker left on a deployed instance would otherwise keep freezing a table forever with nothing left in the code to explain why.

This is the bug that froze `employees` ingest and zeroed four Attendance widgets while everything reported green. Removing the mechanism is the fix; removing only the writer would leave the landmine armed.

### 2.4 The demo consequence — needs a ruling

Today an upload in **demo** mode writes to silver and is visible immediately. After this change it writes to `data/raw/`, which demo mode never reads — so **uploading in demo mode would appear to do nothing.**

Options: block uploads in demo with a clear message; allow staging and preview but refuse commit; or treat a commit as switching that domain to real. **Recommend blocking upload in demo**, with the reason stated in the response — "silently does nothing" is the worst of the three, and it is what happens if this is not decided.

### 2.5 Demo impact

**Dashboard values byte-identical** — the pipeline is untouched. **API changes are substantial and intentional:** `POST /api/data/upload` is replaced by the `uploads` resource. `frontend/src/hooks/useDataManagement.ts` and the Data Quality page consume the old endpoint and must move with it. Not claimed as byte-identity.

---

## 3. Format rule for `payroll_period`

`payroll_period` is VARCHAR with no format rule; `"June 2026"` passes the contract, then downstream SQL concatenates and casts to DATE:

```
Conversion Error: date field value out of range: "June 2026-01", expected format is (YYYY-MM-DD)
```

The build fails with an unattributed database error instead of naming the cell.

**Proposed:** a `format` key resolved from a **named registry**, not a raw regex in the contract — the same principle as derivations and `required_when`: a contract is operator-supplied data and must never carry anything executable.

```yaml
  - name: payroll_period
    type: VARCHAR
    format: YYYY-MM
```

REJECT severity, with the message naming the row, the column and the expected shape:

```
EN  Row 12, Payroll Period: 'June 2026' is not in YYYY-MM format (e.g. 2026-06).
AR  الصف 12، فترة الرواتب: 'June 2026' ليست بصيغة سنة-شهر (مثال: 2026-06).
```

Applies to `payroll.payroll_period` and `compliance.period`. Both currently pass anything.

**Parity delta:** new `bad_format` cases only; no pre-existing case changes. **Demo byte-identical** — validation is real-path only.

---

## 4. Demo-vs-real indicator, driven by the registry

Per ruling, per-domain provenance rather than a global flag.

Extend `GET /api/meta/app-config`:

```json
{
  "data_mode": "real",
  "domains": {
    "employees": {"provenance": "client",       "rows": 1420, "last_loaded": "2026-08-10"},
    "payroll":   {"provenance": "client",       "rows": 1418, "last_loaded": "2026-08-10"},
    "attendance":{"provenance": "not_provided", "rows": 0,    "last_loaded": null},
    "talent":    {"provenance": "demo",         "rows": 12,   "last_loaded": null}
  }
}
```

Three states, because two are not enough: `client` (their data), `not_provided` (declared absent — show an empty state, never a zero), and `demo` (fabricated — the 15 uncontracted tables of §1.3 until they are gated).

Frontend work is small but not nil: consume the endpoint, and give each page a not-provided empty state rather than rendering `0`. **A zero is a claim.** "Absence of data" and "the value is zero" must not look the same, which is the whole point of the exercise.

The existing `ThemeContext`/`BrandingContext` pattern is the obvious place for a provenance context.

---

## 5. Ordering

| # | Step | Gate |
|---|---|---|
| 1 | Registry loader + `declared == populated` guard | unit tests for all four states in §0.2 |
| 2 | P0-1 fail-closed; delete the sample-fallback branch | synthetic real run: missing domain aborts; declared partial loads with empty undeclared tables; **demo byte-identical** |
| 3 | `format` rule (§3) | parity: new cases only |
| 4 | Staging resource + validate + commit-to-`raw` (§2) | a staged file with a REJECT cannot commit; committed file flows through ingest; nothing written to silver directly |
| 5 | Retire `.uploaded` (§2.3) | existing markers removed on startup; the monkeypatch is gone |
| 6 | `app-config` per-domain provenance + frontend empty states (§4) | a not-provided domain renders as absent, never as `0` |

Steps 1–2 are the safety fix and should land together. Step 5 must not ship before step 4, or uploads break.

---

## 6. Risks

| Risk | Likelihood | Note |
|---|---|---|
| Registry goes stale and silently mis-scopes | **Medium** | The `declared == populated` guard exists precisely for this; it is the fourth instance of this pattern here, after `.uploaded`, the contract-exceptions transport, and the dbt-model cache |
| The 15 uncontracted tables keep showing fabricated data in real mode | **High until §1.3 is ruled** | Not covered by P0-1 |
| A not-provided domain renders as `0` | **High if the frontend is skipped** | A zero is a claim; step 6 is not optional polish |
| Staged uploads accumulate client data | Medium | TTL, size cap, reaping — PDPL-relevant, design it in |
| Uploads silently no-op in demo | **High if §2.4 is not decided** | The default outcome of not deciding is the worst option |
| Frontend upload flow breaks on the new endpoints | High | `useDataManagement.ts` and the Data Quality page must move with the API |
| Templated dbt severity is planned around without verification | Medium | §0.3 — not asserted; needs a spike if the guard approach is rejected |

---

## 7. Decisions needed

1. **Registry location** (§0.1) — `data/onboarding/declared_domains.yml`, an env var, or both?
2. **The 15 uncontracted tables in real mode** (§1.3) — gate off (recommended), label, or accept?
3. **Uploads in demo mode** (§2.4) — block (recommended), stage-only, or auto-switch?
4. **dbt tests** (§0.3) — accept the guard-based simplification and leave the 11 tests untouched, or spike templated severity?
5. **Staged-upload retention** (§2.2) — TTL and size cap, given staged files contain client personal data.

---

**Prepared for chief-architect review. No implementation performed.**
