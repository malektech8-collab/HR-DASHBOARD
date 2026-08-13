# `end_of_service_type: Unspecified` (PLAN ONLY)

**Branch:** `phase-2/eos-unspecified` off `main` @ `535a8ff` · **Date:** 2026-08-13
**Status:** PLAN ONLY. Nothing implemented.
**Ruling:** add `Unspecified` to `employees.end_of_service_type`, meaning *employment ended but the legal grounds were not recorded in the source*.

The ruling is right and the reasoning holds: `فسخ العقد من قبل صاحب العمل` states only that the employer ended the contract. Articles 74/75, 77 and 80 differ in whether an award is owed and how much, and the source did not record which applies. **Mapping it to any specific article would assert an entitlement the data does not support** — the same family as every fabrication this phase has removed, except that here the fabricated number would be somebody's terminal payment.

One finding changes what §3 can honestly say, so it comes first.

---

## 0. FINDING — `end_of_service_type` has no consumer anywhere

Measured on `main` @ `535a8ff`:

```
grep end_of_service_type  dbt_analytics/models  backend/app  frontend/src  scripts/
  -> two hits, both TEST FIXTURES using it as an example of a gated enum
     (frontend/src/lib/mapping.test.ts, frontend/src/lib/uploadFlow.test.ts)

warehouse `employees` table: end_of_service_type present? False
leaver-related columns:      ['termination_date']
```

**Nothing reads this column.** Not a mart, not a KPI, not an endpoint, not the frontend. It is validated at the gate and then goes nowhere. It is not in the demo warehouse at all, because the sample generator does not emit it.

This is not an argument against the ruling — the value must be accepted or the client's file is rejected outright. It changes two things:

1. **§3 has no mart to update.** The honest answer to "what groups by `end_of_service_type`" is *nothing does*, and a plan claiming otherwise would be inventing work.
2. **It sharpens a debt already on the register.** Article 80 exposure is a stated Phase 2 selling point, `end_of_service_type` is the column that would carry it, and nothing computes anything from it. Adding `Unspecified` makes that gap *bigger and better documented*: the first real client will supply several hundred leavers' reasons into a column no figure derives from. Worth naming in the report, not fixing here.

---

## 1. The contract change

### 1.1 `allowed_values`

```yaml
allowed_values: [Resignation, Article 74, Article 75, Article 77,
                 Article 80, Article 81, Probation, Unspecified]
```

Appended, not inserted. The list is compared as a set, so position carries no meaning — but a diff that only adds a line at the end is a diff a reviewer can check in one glance.

### 1.2 The bilingual label — proposed wording

| | |
|---|---|
| `en` | **Unspecified — grounds not recorded** |
| `ar` | **غير محدد — لم يُسجَّل السبب النظامي** |

**Why this wording.** The existing labels follow one shape: the outcome, then the article — `فصل دون مكافأة أو إشعار — المادة ٨٠`, `إنهاء بإشعار — المادة ٧٥`. This keeps the shape and puts the *absence* where the article normally sits, so a reader scanning the list sees immediately that this is the row with no legal basis attached.

`غير محدد` alone was the ruling's suggestion and would be understood, but on its own it reads as *"the type is unspecified"* — a shrug. `لم يُسجَّل السبب النظامي` says **the grounds were not recorded**, which is the fact: something did happen, the source simply did not capture what. That distinction is the whole reason the value exists, and it is the sentence an HR manager needs when they are asked why an EOSB figure cannot be produced.

Alternative considered and rejected: `إنهاء من صاحب العمل — السبب غير مسجّل` ("employer-initiated — reason not recorded"). More specific, and **wrong**: `Unspecified` is the canonical bucket for *any* unrecorded grounds, and a future client may leave a resignation-vs-dismissal case unrecorded too. Baking "employer-initiated" into the label would make the canonical value narrower than its definition, and someone would then need a ninth value.

### 1.3 `description_en` / `description_ar`

The column description gains a sentence naming what `Unspecified` does **not** mean, because that is where it will be misread:

> `Unspecified` means the source did not record the legal grounds. It is not a category of termination and must not be treated as one — no award, notice period or entitlement can be derived from it.

### 1.4 What does NOT change

- `on_violation` stays **absent** → the column remains a **REJECT** enum. A value outside the list still refuses the file, which is correct: an unrecognised termination reason is not something to load and sort out later.
- `required_when: {column: status, equals: Terminated}` is untouched. A terminated employee must still carry *something*; `Unspecified` is now a legal something.
- The column stays `required: false`.

---

## 2. Should `Unspecified` raise a data-quality EXCEPTION?

**Recommendation: yes — and at validation time, with EXCEPTION severity, so it appears in the upload preview *and* on the Data Quality page.**

### 2.1 Why it must be visible at all

Once `Unspecified` is in `allowed_values`, the validator is silent on it by construction: it is a legal value, Rule 4 passes, and the file commits with no signal. On the first real export that is **hundreds of leavers whose EOSB basis is unknown, accepted without a word.** The client would discover the gap when someone asks for an Article 80 figure and cannot get one.

That is the exact shape of defect this phase has spent itself removing — an absence that renders as acceptance. The value is honest; **silence about the value is not.**

### 2.2 Why EXCEPTION and not REJECT

The established split, from `validate_schema.py`'s own docstring:

> **REJECT** — structural. Nothing downstream can be trusted, so nothing loads.
> **EXCEPTION** — row-level content on a well-formed file. The file loads and the offending rows flow to the data-quality exceptions layer.

This is squarely the second. The file is well-formed; specific rows have a gap **the business already has** — the grounds were never recorded in Jisr, and refusing the upload would not create them. Rejecting would also make the client's only route a fabrication: pick an article to get the file in.

### 2.3 Why at validation time rather than in `validate_data.py`

Both would reach the Data Quality page. Only one reaches the **preview**.

`UploadPreview.exceptions` is rendered by `ViolationPanels` in its own region, above the commit button, with *"These do not block the upload."* So a contract EXCEPTION is seen **before committing** — at the one moment the operator can still go back to the client and ask whether the grounds exist somewhere else in Jisr. A `validate_data.py` check only surfaces after the pipeline has run, when that conversation is over.

There is also a mechanical reason: `validate_data.py` reads `data/silver/employees.parquet`, and would need a column-absent guard, because the column is absent in demo and for any client who does not provide it.

### 2.4 The mechanism it needs — a new declarative contract key

Rule 4 cannot express this: it flags values **outside** `allowed_values`, and `Unspecified` is now inside. The smallest honest addition:

```yaml
flag_values:
  Unspecified:
    severity: exception
    reason_en: >-
      The legal grounds for this termination were not recorded in your source
      system. No end-of-service entitlement can be derived from it.
    reason_ar: >-
      لم يُسجَّل السبب النظامي لإنهاء هذه الخدمة في نظامك المصدر، ولا يمكن
      اشتقاق أي مستحقات نهاية خدمة منه.
```

Properties that matter, each following an existing precedent in this repo:

- **Declarative only.** A mapping of value → severity + bilingual reason. No expression, ever — same rule as `required_when`, and for the same reason: a contract is operator-supplied data.
- **Per row.** Unlike Rule 4's file-level message, this emits one violation per offending row with the Excel row number, so the client gets *which* leavers, which is the product's stated differentiator.
- **Capped** at `MAX_RENDERED_VIOLATIONS` with the existing "and N more" tail. On an export with several hundred leavers this matters: a client with more flagged rows than the cap must not receive one message per row, and the error report already carries the true total.
- **Generic.** Nothing about this is EOSB-specific. `flag_values` will be wanted the next time a canonical vocabulary has a legal-but-incomplete member.

### 2.5 The honest limitation

`flag_values` fires on the **canonical** value, after mapping. So a client whose export uses a *different* unrecorded-grounds phrase gets it flagged only once the operator has mapped that phrase to `Unspecified`. **The flag reports a mapping decision, not a discovery.** Worth stating plainly, because it is easy to read the DQ count as "the system found these" when it is really "the operator said these".

---

## 3. Downstream marts and KPIs

**None. Nothing groups by `end_of_service_type`, because nothing reads it** (§0).

Stated as a table so the claim is checkable rather than asserted:

| Surface | Reads `end_of_service_type`? |
|---|---|
| `dbt_analytics/models/**` (161 models) | no |
| `backend/app/**` | no |
| `frontend/src/**` | only two test fixtures, as an example of a gated enum |
| `data/silver/employees.parquet` (demo) | column not emitted by the sample generator |
| warehouse `employees` table | not present |

**What this means for the cycle:** there is no mart to teach about `Unspecified`, no KPI to exclude it from, and no chart that would silently absorb it into a slice. That is a smaller change than the ruling anticipated and I would rather say so than manufacture work.

**What it means for later, and it should be recorded rather than fixed here:** when a leaver-reason mart *is* built, `Unspecified` must not be a category alongside the articles. It is an absence, and the established treatment for an absence in this codebase is **withheld, not bucketed** — the same rule that made `COALESCE(project, 'Unassigned')` wrong. A future `mart_leavers_by_reason` should report Article 74/75/77/80/81, Resignation and Probation as categories, and `Unspecified` as a **coverage note**: *"N of M leavers have no recorded grounds"*. Grouping it as an eighth slice would put an absence on a pie chart, which is the defect this project keeps paying for.

---

## 4. Parity delta

**Claim: files carrying `Unspecified` change from REJECT to ACCEPT. Nothing else changes.**

`scripts/verify_contract_parity.py` is the harness for exactly this, and its docstring states why it is needed:

> "CI never exercises the contracts (they are only read on the real path), so CI passing is NOT evidence the extension is safe. This harness is."

Expected outcomes, to be **run and quoted in the report** rather than asserted:

| Case | Before | After |
|---|---|---|
| `end_of_service_type = Unspecified` | **REJECT** (`allowed-values`) | **ACCEPT**, with one EXCEPTION per row |
| the seven existing values | ACCEPT | ACCEPT, unchanged |
| a genuinely unknown value (`Article 99`) | REJECT (`allowed-values`) | **REJECT**, unchanged |
| `status = Terminated`, column empty | REJECT (`required_when`) | **REJECT**, unchanged — `Unspecified` is not a licence to leave it blank |
| every other contracted table | unchanged | unchanged |

### 4.1 Demo byte-identity

**Structural, and stated as such.** The sample generator does not emit `end_of_service_type` at all, so the demo pipeline cannot produce or flag an `Unspecified`. The five pinned figures are now **asserted** by `test_demo_gate.py`, so this is enforced rather than eyeballed. The gate is still run.

### 4.2 The interaction the ruling did not name

`end_of_service_type` is one of the **three REJECT enums requiring an affirmation** before a value mapping into it can be saved (mapping cycle B, ruling 4). Adding `Unspecified` does not change that, and the consequence text already reads:

> *End-of-service type decides whether a leaver is owed money. Article 80 is dismissal for cause and carries NO end-of-service award; Resignation and Articles 74/75/77/81 do.*

That text is now **incomplete**: it enumerates outcomes that all carry an entitlement decision, and `Unspecified` carries none. It should gain a clause — *"`Unspecified` records that the grounds were not captured, and no entitlement can be derived from it"* — so the operator ticking the box to map `فسخ العقد من قبل صاحب العمل` → `Unspecified` is told what they are asserting. Pinned by test today (`"Article 80" in …`, `"owed money" in …`), so the test moves with it.

---

## 5. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 1 | `Unspecified` in `allowed_values` + bilingual label + description sentence | yes — this alone unblocks the client's file |
| 2 | Consequence text updated, and its test | yes |
| 3 | `flag_values` in the validator: per-row EXCEPTION, capped, bilingual | yes |
| 4 | `flag_values: {Unspecified: …}` on the contract | lands with 3 |
| 5 | Parity harness run; before/after quoted in the report | verification, not code |
| 6 | Alias entries for the Arabic phrases, so the mapping ladder proposes them | optional, see §6 |

**Step 1 alone unblocks the load.** If the cycle is cut, cut from step 6 upward — but note that shipping 1 without 3 is the silent-acceptance case §2.1 argues against, so 1–4 should land together unless the client is waiting.

---

## 6. Out of scope

- **The alias table.** The five Arabic phrases in the finding are *this client's* wording. `config/mapping_aliases.yml` is for **headers**, not values, so there is nowhere to put them today; a value-alias table is its own decision and needs more than one client to be worth seeding. The operator maps them by hand in the profile, which is what the mapping cycle built.
- **Any EOSB calculation.** Nothing computes end-of-service awards. Adding `Unspecified` does not move that; §0 records that the column feeds nothing at all.
- **A leavers-by-reason mart.** §3 states how `Unspecified` must be treated when one is built.
- **Widening any other enum.** `case_type` and `status` are untouched.

---

**PLAN ONLY. Nothing implemented. Stopping for review.**
