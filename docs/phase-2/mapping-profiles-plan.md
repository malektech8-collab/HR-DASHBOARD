# Mapping Profiles (PLAN ONLY)

**Branch:** `phase-2/mapping-profiles` off `main` @ `bc2d7c5` · **Date:** 2026-08-12
**Status:** plan only. Nothing implemented.
**Implements:** `PRODUCT-ARCHITECTURE.md` §4, *Mapping profiles* · **Prior:** [`upload-ui-report.md`](upload-ui-report.md)

The last mechanism before real client data. Today a real export hard-rejects on the first upload, correctly, and there is no sanctioned way to reconcile it.

---

## 1. Where mapping sits — §4 confirmed, with one requirement added

**Confirmed: mapping runs BEFORE validation, and the validator stays canonical-only.**

The alternative — teaching `validate_csv` about source columns — would double every rule. Fourteen enum checks, the type conformance pass, `required_when`, the date-range rule: each would need a canonical branch and a mapped branch, and the two would drift exactly as `compile_csv_to_parquet` drifted from `ingest_raw`. The validator has one job and one vocabulary, and that is worth protecting.

**The requirement §4 does not state, and the design fails without it: mapping must be row-preserving, and it must carry a back-map.**

If mapping produces a new file and validation runs on that, then every violation the client sees names a **canonical column they never wrote** and a **row number of a file they never made**:

> `Row 47, Joining Date: date '0025-01-26' is outside the plausible range`

when their column is `تاريخ التعيين` and their spreadsheet's row 47 may be a different record entirely. The error report — the artefact they open next to their file — becomes unusable, which undoes the upload-UI cycle.

So:

- **Row-preserving.** The mapped file has exactly the rows of the source, in order. Mapping renames and derives; it never filters, reorders, or deduplicates. A test asserts row counts and a row-identity check.
- **Back-map carried into the preview.** `ViolationOut` gains `source_column` and the UI renders *"`تاريخ التعيين` (Joining Date), row 47"*. One field, and it is the difference between an actionable report and a confusing one.

### Where the mapped file lives

```
data/staging/<uuid>/
    data.csv        the bytes exactly as received — never modified
    mapped.csv      canonical, produced by applying the profile
    manifest.json   + profile_version, mapping_applied
```

Preview validates `mapped.csv`. **The original is retained**, so re-mapping does not require re-uploading, and so the client can always be shown their own headers.

Commit moves `mapped.csv` to `data/raw/{table}.csv`, which is canonical — so `ingest_raw` validates it again, unchanged, and the single-ingest-path property from P0-2 survives intact.

**A consequence worth stating: the mapping profile is an upload-time concern only.** Nothing downstream knows it exists. `ingest_raw`, `build_warehouse`, dbt and the API are untouched by this cycle. That is a small blast radius for a mechanism this central, and it is the reason to keep the placement as §4 has it.

### Rule 2 stays a hard reject

Mapping does not weaken *"unexpected columns are rejected"* — it means the **mapped** file has none. A source column ends in one of three states, all explicit:

| state | recorded as | effect |
|---|---|---|
| mapped | `columns: {source: canonical}` | becomes a canonical column |
| deliberately ignored | `ignored: [source, …]` with a reason | dropped, and the drop is auditable |
| neither | — | **blocks**, listed in the preview as unmapped |

Ignoring must be explicit. A default-drop would mean a renamed export silently loses a column, which is the inference-over-declaration failure this codebase has removed three times.

---

## 2. The stored format

`data/mapping/{table}.yml`, gitignored (it contains client vocabulary). **Append-only versions**, never mutated in place: a client's export changes, and if the profile mutates, nobody can say which mapping produced last month's numbers — and the training substrate loses exactly the history that makes it valuable.

```yaml
table: employees
versions:
  - version: 3
    created_at: 2026-08-14T10:22:00
    created_by: admin@synthetic.local
    source_fingerprint: "sha256:… of the sorted header row"   # detects a changed export
    columns:
      "الرقم الوظيفي":        employee_id
      "الاسم":                employee_name
      "تاريخ التعيين":         joining_date
      "الجنسية":              nationality
    ignored:
      - header: "ملاحظات"
        reason: "Free-text notes; no canonical home."
      - header: "Column14"
        reason: "Empty in every row of the sample."
    derive:
      is_saudi:
        rule: nationality_is_saudi
        from: "الجنسية"
    values:
      status:
        "نشط":    Active
        "موقوف":  Inactive
        "A":      Active
    evidence:
      - source_header: "الرقم الوظيفي"
        normalised: "الرقم الوظيفي"
        matched_by: exact_name_ar
        confidence: 1.0
        chosen: employee_id
        rejected: []
      - source_header: "المسؤول"
        normalised: "المسؤول"
        matched_by: human
        confidence: null
        chosen: owner_id
        rejected:
          - candidate: manager_id
            proposed_by: normalised_label_match
            score: 0.71
            reason: "Human chose owner_id — this file's column is the case owner, not the line manager."
        value_profile:
          kind: redacted
          dtype: string
          cardinality: 12
          length_range: [6, 6]
          pattern: "EMP\\d{3}"
```

### What is recorded, and why each piece

| | why |
|---|---|
| verbatim `source_header` | the exact bytes, before normalisation — the model's actual input |
| `normalised` | what matching compared, so a match can be replayed |
| `matched_by` + `confidence` | distinguishes an exact hit from a guess a human accepted |
| **`rejected` candidates** | *"system proposed `manager_id`, human chose `owner_id`"* — the negative examples, which are the scarcest and most valuable training signal and are **unrecoverable if not captured now** |
| `ignored` with reasons | the columns a real export carries that the schema does not want |
| `source_fingerprint` | the next upload can say *"this export's headers changed"* instead of silently applying a stale profile |

### Sample values — and the privacy rule that has to come with them

§4 wants sample values as training substrate. **Sample values from an HR export are client PII**: names, national IDs, salaries. Writing them to a profile file would put personal data in an artefact whose stated purpose is to be accumulated, reused and eventually fed to a model — and this project has a `PRIVACY_AND_MASKING_POLICY.md` and a PDPL posture that this would sit badly against.

**The rule: verbatim sample values are stored only for columns mapped to a canonical column that declares `allowed_values`. Everything else stores a redacted profile.**

That is not a compromise, it is the right split on the merits:

- for an **enum** column the values *are* the signal (`نشط`, `A`, `Active` → `Active`) and they are vocabulary, not personal data
- for a **name or salary** column the header is the signal and the values add nothing a model can use — `dtype`, cardinality, length range and a format pattern carry the discriminating information without carrying a person

A test should assert no verbatim value is stored for a column without `allowed_values`. Privacy rules that live only in a comment do not hold.

---

## 3. Derived fields, without eval

**For `is_saudi`, no new mechanism is needed at all.**

The contract already declares `derivation: nationality_is_saudi` and `derived_from: nationality`, and `derivations.derive_column` already resolves the rule from `REGISTRY` — never `eval`. All the profile has to do is say **which raw header plays the role of `nationality`**:

```yaml
columns:
  "الجنسية": nationality
```

Map the source, and the existing derivation runs exactly as it does today. The `derive:` block above is only for the case where a derivation's input is **not itself a canonical column** — for example a project code that must be translated but has no canonical home of its own.

For that case the constraint is unchanged and must be stated in the profile loader, not assumed:

- a profile names a **rule** and a **source header**; it never carries an expression
- the rule is resolved through `derivations.resolve()`, which raises on an unknown name
- **a new rule is code**: reviewed, tested, added to `REGISTRY`. A client cannot introduce a transformation by editing config

A test should assert the loader rejects a profile containing anything expression-shaped, so the property is enforced rather than trusted. A schema file is operator-supplied data; treating it as code would make it an execution vector, and that argument has already been made once in `derivations.py` — the profile must not quietly reopen it.

`derivations._normalise` should be **promoted to a shared module** (`scripts/text.py`). It already handles tatweel, alef/ya/ta-marbuta variants, diacritics and whitespace collapse — precisely the *"Arabic column headers with inconsistent spacing and naming"* problem §4 names — and header matching and value matching both need it. Flagging the move; it is a rename plus an import, not a rewrite.

---

## 4. Value-level mapping, and the three REJECT enums

Fourteen canonical columns carry `allowed_values`. Measured:

```
REJECT     : 3   employees.status, employees.end_of_service_type,
                 employee_relations.case_type
EXCEPTION  : 11  qiwa_status, gosi_status, mudad_status, occupation_match_status,
                 health_insurance_status, case_status, priority, employment_type,
                 contract_type, request_status, payroll_status
```

Value mapping is `{source value → canonical value}` per canonical column, compared after normalisation, so `نشط` and `نشط ` need one entry rather than two.

**The interaction that matters.** An unmapped value in one of the three REJECT columns **blocks the upload** — correctly. But the fix belongs in the mapping screen, not in Excel: the preview must surface *"`status` has 2 unmapped values: `معلق`, `منتهي`"* as a **mapping task with the canonical options listed**, not merely as a rejection. Sending a client back to their spreadsheet to rename `معلق` when the product could learn it once is the friction §4 opens by saying onboarding friction kills these deals.

For the 11 EXCEPTION enums an unmapped value loads and appears on the Data Quality page. That asymmetry should be visible in the mapping UI too — *"unmapped values here will load and be flagged"* versus *"unmapped values here block the upload"* — for the same reason the upload UI separates REJECT from EXCEPTION.

### The risk this creates, and the guard

**Value mapping is the one place in the product where a client can change the meaning of their data with no trace.** Mapping `معلق` (suspended) to `Active` is a fabrication that every downstream check would accept: the value is legal, the type conforms, no rule fires. Headcount, Saudization and Nitaqat banding all move.

Two mitigations, and I would not ship this without both:

1. **Every value mapping is attributed** — `created_by` and `created_at` on the profile version, which the append-only format already gives.
2. **Mapping into a REJECT enum requires explicit confirmation**, the same shape as the coverage declaration: the value pairs are shown, and a human ticks *"I confirm these are equivalent"*. Same reasoning as Category F ruling 3 — a pre-filled suggestion nobody reads is not a decision.

---

## 5. The UI, honestly assessed — this does not fit one cycle

**It should be split, and the split is not close.**

An export with ~37 headers against a 23-column contract means roughly 14 columns to ignore or reconcile, plus value vocabularies on up to 14 enum columns, plus derivations — all in Arabic, for a user who does not know what a canonical schema is. Building the profile mechanism *and* that screen in one cycle would produce a rushed version of the hardest UI in the product.

| | Cycle | Contents | Value on its own |
|---|---|---|---|
| **A** | mechanism | profile format, loader, apply step, `mapped.csv` in staging, back-map into violations, value + derivation application, tests | **a technical operator can complete the first real load** by writing a profile by hand — which is what the first load will involve anyway |
| **B** | the screen | suggestion engine, the mapping table, value-vocabulary editor, unmapped-first ordering, the REJECT-enum confirmation | the client-facing half |

Cycle A is the one that unblocks real data. Cycle B is the one that makes it a product.

### What cycle B should be built on, sketched now because it shapes A's format

**The strongest lever already exists: the contract carries `name_en` AND `name_ar`.** A client whose headers are the canonical Arabic labels should match automatically, and even approximate Arabic headers will match after the normalisation in §3. The suggestion engine ladder:

1. exact match on `name` (canonical key)
2. exact match on `name_ar` or `name_en`
3. normalised match on either — this is where tatweel and alef variants get absorbed
4. alias table (`الرقم الوظيفي` / `رقم الموظف` / `الرقم` → `employee_id`), which the accumulated profiles then grow
5. nothing — a human picks

Every rung records `matched_by` and `confidence` into `evidence`, which is exactly the labelled data §4's AI mapper needs. **The manual UI is the data collection.**

Screen design principles worth fixing now: unmapped columns first (never a 37-row list where the 3 that need attention are in the middle); sample values shown beside each source column, because a header alone often will not settle it; and progress stated as *"14 of 37 mapped, 3 need attention"* rather than a percentage.

---

## 6. Sequencing (cycle A)

| | Step | Independently shippable |
|---|---|---|
| 1 | promote `_normalise` to `scripts/text.py` | yes — small, and both later steps need it |
| 2 | profile format + loader + no-expression guard | yes |
| 3 | apply step producing `mapped.csv`, row-preserving | yes |
| 4 | `source_column` on violations, back-map through the preview | yes — improves error reporting even with no profile present |
| 5 | value mapping + the REJECT-enum confirmation | the substance |
| 6 | evidence capture, including rejected candidates | last in build order, **first in importance** — see the risk below |

---

## 7. Risks

1. **Evidence capture is last in the sequence and the easiest thing to drop.** It is also the only part that is *unrecoverable*: a mapping done without recording its rejected candidates cannot have them reconstructed later, and those negatives are the scarcest training signal. If cycle A is cut short, cut step 5 before step 6 — a profile that maps headers and records why is worth more than one that also maps values and remembers nothing.
2. **Value mapping can fabricate, silently and legally** (§4). The confirmation gate and the attribution are not ceremony; they are the only trace.
3. **A stale profile applied to a changed export.** `source_fingerprint` detects it, and the response must be to *ask*, not to auto-remap — a client who adds a column should be told, not have it silently ignored by a profile written before it existed.
4. **This cycle's tests cannot use a real file.** The fixtures will be synthetic Arabic headers built from `name_ar`, which means they will be *cleaner* than reality. The messy cases — trailing spaces, mixed scripts in one header, `Column14` — must be constructed deliberately rather than hoped for.

---

## 8. Out of scope

1. **The AI column mapper** (`PRODUCT-ARCHITECTURE` §5). This cycle builds the manual version and the substrate it will learn from, which is the stated order.
2. **The mapping UI** — cycle B (§5).
3. **Multi-tenancy.** `data/mapping/{table}.yml` assumes one client, as the rest of the system does. A `client_id` dimension is a system-wide change, not a mapping one.
4. **Excel input** — still TD-008; a mapping profile does not help with a file the uploader will not accept.
5. **Bulk/template mapping across domains.** One table per profile.

---

**Prepared for chief-architect review. No implementation performed.**
