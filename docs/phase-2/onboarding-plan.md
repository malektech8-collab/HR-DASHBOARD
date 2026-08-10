# Phase 2 Readiness — Onboarding a Real Client (PLAN ONLY)

**Status:** proposed. Nothing implemented. This document is the only file added on `phase-2/onboarding-plan`.
**Branch:** `phase-2/onboarding-plan` off `main` @ `ffb2212` · **Date:** 2026-08-10
**Governing reference:** [`docs/PRODUCT-ARCHITECTURE.md`](../PRODUCT-ARCHITECTURE.md) §4–§5
**Scope:** readiness assessment and options. No implementation, no rulings taken.

---

## 0. Correction first — my earlier flag was wrong

The 1b-ii report flagged `dbt test PASS=9 ERROR=2` as evidence that *"a client's first partial upload will fail dbt tests that assume a fully populated warehouse."* **That diagnosis was wrong**, and Priority 1 was framed around it, so it needs correcting before anything else.

The two errors were caused by my own test fixture. It put `X1` in `payroll_period`, and downstream SQL does `payroll_period || '-01'` cast to `DATE`:

```
Runtime Error in test not_null_mart_payroll_kpis_employees_paid
  Conversion Error: date field value out of range: "X1-01", expected format is (YYYY-MM-DD)
```

`ERROR`, not `FAIL` — the test query itself broke. I should have read that distinction at the time.

A **well-formed** partial upload passes cleanly:

```
A) partial payroll (2 rows, period 2026-06), nothing else supplied
   dbt run  -> PASS=157 ERROR=0
   dbt test -> PASS=11  ERROR=0        exit 0
```

So the failure mode I described does not exist. Investigating why it doesn't exist, however, surfaced something considerably worse.

---

## 1. PRIORITY 1 — incremental onboarding

### 1.1 The real problem: silent fallback to fabricated data

A partial upload passes cleanly **because missing domains fall back to sample data**. That is Phase 0's designed resolver behaviour, and in a client deployment it is a serious defect.

Measured — a client supplies **only payroll**, one real row:

```
[real] attendance:         no data/raw/attendance.csv; falling back to sample.
[real] compliance:         no data/raw/compliance.csv; falling back to sample.
[real] employee_relations: no data/raw/employee_relations.csv; falling back to sample.
[real] employees:          no data/raw/employees.csv; falling back to sample.
[real] hr_requests:        no data/raw/hr_requests.csv; falling back to sample.

DASHBOARD SHOWS:  headcount 19 | payroll_cost 1000.0 | saudization 50.0
  payroll rows real: 1
  employees rows   : 21   <- FABRICATED (sample)
```

The client sees their real payroll figure sitting between a fabricated headcount and a fabricated Saudization percentage, on one screen, with **no indicator distinguishing them**. `19` and `50.0` are invented numbers about invented people, presented as this client's HR data.

This is the direct violation of the project's own principle — *never show a fabricated number as real* — and it is live today the moment `DATA_MODE=real` is set with anything less than all six domains present. Given onboarding is explicitly incremental, that is the normal case, not an edge case.

**Everything else in this document is less urgent than this.**

### 1.2 The second finding: format-invalid values break the build

`payroll_period` and `compliance.period` are `VARCHAR` with no format rule. The contract validates *type*, and every string is a valid string. Downstream SQL then concatenates and casts to `DATE`.

A completely plausible client value:

```
contract verdict on payroll_period="June 2026":  ACCEPT
pipeline exit=1
  Conversion Error: date field value out of range: "June 2026-01", expected format is (YYYY-MM-DD)
```

The hard gate passes it, and the **warehouse build** fails with a database error instead of the client getting a validation message naming the cell. `2026/06`, `Jun-26` and `06-2026` all behave the same way. This is the same class as the `0025-01-26` date-serial case fixed in 1b-i, but on VARCHAR columns the DATE range rule never sees.

Likely remedy (not a ruling): a `format` / `pattern` key on the contract — e.g. `format: YYYY-MM` on the two period columns — enforced as a REJECT rule with a bilingual message. Small, and it converts a build crash into an actionable error.

### 1.3 What actually happens with an empty domain

Worth knowing before choosing among the options, because it determines whether the test problem exists at all:

```
C) header-only payroll (0 rows), everything else falling back to sample
   contract verdict on a 0-row file: ACCEPT
   dbt run 157/157 · dbt test 11/11 · exit 0
```

A zero-row domain is accepted and harmless **today** — again only because the other domains carry sample data. The null-KPI failure mode becomes live the moment fallback is removed, which every option below does.

### 1.4 Options

Presented with trade-offs, no recommendation taken.

**Option A — require all domains before any real load.** `DATA_MODE=real` refuses to build unless every contracted domain has a raw file.
*For:* trivially safe; no mixing possible; no test changes.
*Against:* forbids incremental onboarding, which is the actual onboarding model. A client cannot see anything until all six domains are clean — the longest possible time-to-first-value, on a product whose stated risk is onboarding friction.

**Option B — remove fallback; unsupplied domains are empty.** Missing raw file → empty table, not sample.
*For:* kills the fabrication problem at the root; the resolver stops lying.
*Against:* KPI marts over empty tables produce NULLs, so the `not_null` tests fail and the build breaks — turning "you haven't uploaded payroll yet" into a pipeline failure. Requires one of the test strategies below, and a UI answer for what an unsupplied domain renders as.

**Option C — explicit "domain populated" registry.** A per-deployment record of which domains the client has actually provided, written at ingest. Marts, tests and UI all consult it.
*For:* the populated state becomes *data* rather than something inferred; drives test scoping, UI gating and the demo/real indicator from one source; an unsupplied domain can render as "not yet provided" instead of a number.
*Against:* new state to keep correct, with a staleness failure mode of exactly the kind that has bitten this project twice (`.uploaded` markers, the contract-exceptions transport). Must be rebuilt every run, never incrementally patched.

**Option D — severity-tier the dbt tests.** Reclassify KPI `not_null` tests to `warn` for domains that may legitimately be absent, keeping `error` for domains that are present.
*For:* smallest change; keeps the build green during onboarding.
*Against:* the tier must still be decided per run from *something* — so it needs Option C's registry underneath, or it degenerates into the masking problem below.

**Option E — gate the marts.** A mart for an unsupplied domain returns no rows by construction, so `not_null` has nothing to test.
*For:* no test config changes; the absence is modelled in the data layer where the rest of the logic lives.
*Against:* `not_null` on zero rows passes vacuously — which is the masking problem in a different costume unless populated-ness is explicit.

### 1.5 On the masking concern — addressed directly

Your concern is right, and it has a sharp form worth stating: **the danger is not scoping, it is scoping on an inferred signal.**

If the rule is *"skip the payroll tests when payroll has no rows"*, then a genuine defect that drops every payroll row — a broken join, a failed ingest, a resolver regression — produces exactly the same signal as "the client hasn't uploaded payroll yet", and the tests go quiet precisely when they should fire. That is a real and likely failure, and this codebase has already produced one of its exact ancestors: the `.uploaded` marker that froze `employees` ingest and zeroed four Attendance widgets while everything reported green.

If instead the rule is *"test every domain the client has **declared** as provided"*, the signals separate. A declared domain that comes back empty **fails**, loudly, because emptiness contradicts the declaration. An undeclared domain is not tested because there is genuinely nothing to assert.

So the distinction that matters is not which of B–E is chosen, but whether populated-ness is **declared** or **inferred**. Any option built on inference carries the masking risk regardless of how the tests are tiered; any option built on an explicit declaration avoids it. That points at Option C as a substrate for B, D or E rather than as a competing choice — but it is a genuine trade against the new-state risk, and it is your call.

A cheap guard worth pairing with whatever is chosen: assert that **the set of declared domains equals the set of domains with rows**, and fail if they diverge. That single check catches both "declared but empty" (a real defect) and "populated but undeclared" (a stale registry).

---

## 2. PRIORITY 2 — mapping profiles

### 2.1 Why it is required, not optional

Rule 2 hard-rejects any column not in the contract. A real HRIS export will have its own headers — often Arabic, often inconsistently spaced — so the **first upload from any real client rejects entirely**. Today the only remedy is for the client to hand-rename every column, which is the onboarding friction the architecture names as the thing that kills HR SaaS deals.

The hard-reject default is correct and should stay: a surprise column usually *does* mean a wrong export. The mapping profile is the sanctioned way to reconcile a legitimately different file — architecture §4 is explicit that this must not become silent coercion.

### 2.2 Where it belongs in the pipeline

```
raw file
   -> [mapping profile]  rename headers, translate values, mark ignores
   -> contract validation (unchanged, operating on canonical names)
   -> preview
   -> commit
```

Applying the profile *before* validation keeps the validator canonical-only and untouched — it never learns about client vocabularies. Everything downstream of the mapping step already works.

### 2.3 What a profile must express

Four things, each observed in the architecture's list of real-world issues:

1. **Column mapping** — `الرقم الوظيفي` → `employee_id`.
2. **Value translation** — `نشط` → `Active`. The `value_labels` map already added in Phase 1 is the display half of this; a profile needs the inbound half. Note `value_aliases` was declared in Phase 1 and deliberately left inert for exactly this purpose.
3. **Derivations** — `is_saudi` from `nationality`, already implemented as a named registry rule.
4. **Explicit ignores** — a client export column with no canonical home, ignored *by decision* rather than silently dropped.

### 2.4 Storage format — this is the AI training set

Architecture §5 makes accumulated profiles the ground truth the column-mapper agent learns from, so the format is a data-collection decision, not just a config decision. Things that are cheap to record now and expensive to reconstruct later:

- **The source header verbatim** — exact spelling, spacing, casing. Normalising on write destroys the signal the mapper needs to learn from.
- **Sample values per source column** (privacy-screened) — a mapper distinguishes `date` columns by their contents, not their names.
- **Rejected candidates, not just accepted ones** — *"the system proposed `manager_id`, the human chose `owner_id`"* is a stronger training signal than the accepted mapping alone. A format that stores only the final answer throws away half the value.
- **Provenance** — who approved it, when, against which contract version. A profile written against a superseded contract must be detectable.
- **Per-domain, per-client, versioned** — one profile per client per domain, superseded rather than mutated, so a re-onboarding can be replayed and compared.

Open format questions for the ruling: one file per client-domain or one per client; where profiles live given they are client data rather than repo content (they cannot sit in `data/contracts/`); and whether they are PDPL-relevant, since sample values may embed personal data — that likely settles the storage location on its own.

### 2.5 Interaction with the contract

A profile must be **validated against the contract** when saved: every target must be a real canonical column, no two sources may map to one target, and required columns must be either mapped or derivable. Otherwise a broken profile turns a clean rejection into a confusing one.

---

## 3. PRIORITY 3 — preview

### 3.1 The specified flow versus what exists

Architecture §4: download template → fill → upload → **validate** → **preview** → **commit**.

| Step | State |
|---|---|
| Download template | **Done** (1b-ii: contract-derived, header-only, six domains) |
| Fill | client-side |
| Upload | **Exists, but see below** |
| Validate | **Exists on the `data/raw/` path only** |
| Preview | **Does not exist** |
| Commit | **Does not exist as a distinct step** |

### 3.2 The upload endpoint is worse than "missing preview"

`POST /api/data/upload` does not call the contract validator at all — verified: there is no reference to `validate_csv` anywhere in `backend/app/api/data.py`. It writes **straight to `data/silver/{table}.parquet`** and then creates a `.uploaded` marker.

Three consequences:

1. **The hard gate is bypassed.** Every rule built in 1b-i and 1b-ii — required columns, unexpected columns, types, date ranges, primary keys, `required_when`, vocabularies — applies to `data/raw/` and not to the UI upload, which is the path a client will actually use. Two ingest routes with different guarantees.
2. **There is no uncommitted state.** The file lands in silver on receipt. There is nothing to preview, because by the time a preview could render, the data is already in the warehouse layer.
3. **The `.uploaded` marker still freezes the table.** The monkeypatch in `ingest_raw.py` remains, so an uploaded table is pinned indefinitely. That marker is the origin of the bug that zeroed four Attendance widgets, and it is still live.

### 3.3 What preview requires

A staging area between receipt and commit — the missing concept, not the missing screen. Upload writes to a per-upload staging location, validation runs there, preview reads from there, and only an explicit commit promotes it to silver and triggers the rebuild. That also gives the mapping profile a place to be proposed and approved, and it retires the `.uploaded` marker, since freezing a table stops being necessary once promotion is explicit.

Preview content per architecture §4: row count, detected period, a sample of parsed records, a summary of what will change, and the validation result — rejects blocking the commit, exceptions shown but not blocking, per the 1b-i severity ruling.

**This is the largest single item in Phase 2** and is best treated as its own cycle. It is also the natural place to resolve Priority 1, since the commit step is exactly where "which domains has this client provided" gets recorded.

---

## 4. `/api/meta/app-config` — does it belong in this cycle?

**Yes — and §1.1 upgrades it from hygiene to a blocker.**

It has had no frontend consumer since Phase 0. Standing alone that was a modest gap. Measured against §1.1 it is the difference between a client seeing `headcount 19 · payroll_cost 1000.0 · saudization 50.0` and knowing that two of those three numbers are fabricated.

Two things are needed, and they are not the same:

1. **A global mode indicator** — the existing endpoint, consumed. Cheap, and it stops a client mistaking a demo deployment for their own data.
2. **Per-domain provenance** — *this* number comes from your data, *that* one does not. The global flag cannot express a partially-onboarded deployment, which is the state every client will spend their first weeks in. This needs Option C's registry from §1.4.

Recommendation: item 1 belongs in this cycle regardless of how Priority 1 is decided — it is small and strictly improves an unsafe status quo. Item 2 should follow whichever Priority 1 option is chosen, because it consumes the same populated-domain state. Neither substitutes for fixing the fallback: a label saying "some of this is demo data" is a mitigation, not a fix.

---

## 5. Suggested ordering

Dependency-driven, not a ruling:

| # | Item | Why here |
|---|---|---|
| 1 | Priority 1 decision + `format` rule (§1.2) | everything else assumes real numbers are real; the format rule is small and stops a build crash |
| 2 | `app-config` consumed — global indicator (§4 item 1) | small, immediate safety improvement, independent of the rest |
| 3 | Staging + validate + preview + commit (§3) | the largest item; retires the `.uploaded` marker and unifies the two ingest paths |
| 4 | Mapping profiles (§2) | needs the staging area to be proposed and approved in |
| 5 | Per-domain provenance in the UI (§4 item 2) | consumes the populated-domain state from item 1 |

Phase 2's stated exit criterion is real workforce, Saudization and payroll figures rendering correctly. Items 1 and 3 are the ones that criterion actually depends on.

---

## 6. Risks

| Risk | Likelihood | Note |
|---|---|---|
| A client is onboarded before §1.1 is fixed and reports fabricated numbers as their own | **High if not addressed first** | The failure is silent and the numbers are plausible |
| Test scoping built on inference masks a genuine ingest defect | **High** | §1.5 — declare, do not infer; assert declared == populated |
| Two ingest paths keep diverging | **High** | The upload path already bypasses every rule built in 1b-i and 1b-ii |
| Mapping profile format cannot train the §5 mapper | Medium | Verbatim headers, sample values and rejected candidates are cheap now, unrecoverable later |
| Profiles store personal data in sample values | Medium | PDPL-relevant; likely dictates storage location |
| A populated-domain registry goes stale | Medium | Third instance of this pattern here; rebuild every run, never patch |
| `.uploaded` marker continues to freeze tables | **Live now** | Retired naturally by the staging model |

---

## 7. Decisions needed

1. **Priority 1 option** (§1.4) — A, B, C, D, E, or a combination; and whether populated-ness is declared or inferred (§1.5).
2. **`format`/`pattern` contract key** (§1.2) — approve for `payroll_period` and `compliance.period`?
3. **Mapping profile storage** (§2.4) — location, granularity, and whether sample values may be retained given PDPL.
4. **Preview as its own cycle** (§3) — confirm, and confirm the upload path is unified onto the validated route.
5. **`app-config` global indicator in this cycle** (§4) — recommended yes.

---

**Prepared for chief-architect review. No implementation performed.**
