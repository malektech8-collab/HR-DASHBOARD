# `end_of_service_type: Unspecified` — Execution Report

**Branch:** `phase-2/eos-unspecified` off `main` @ `535a8ff` · **Date:** 2026-08-13
**Plan:** [`eos-unspecified-plan.md`](eos-unspecified-plan.md) (approved as written, all four positions) · **Status:** PR open, **not merged**

---

## 1. The contract

```yaml
allowed_values: [Resignation, Article 74, Article 75, Article 77,
                 Article 80, Article 81, Probation, Unspecified]

value_labels:
  Unspecified:
    en: Unspecified - grounds not recorded
    ar: غير محدد — لم يُسجَّل السبب النظامي
```

The Arabic keeps the existing *outcome — article* shape (`فصل دون مكافأة أو إشعار — المادة ٨٠`) and puts the **absence** where the article normally sits. A bare `غير محدد` reads as a shrug about the type; *"the grounds were not recorded"* states the fact, which is the sentence an HR manager needs when asked why an EOSB figure cannot be produced.

Unchanged, deliberately: `on_violation` stays absent so the column remains a **REJECT** enum, and `required_when` is untouched — **`Unspecified` is not a licence to leave the column blank.** Both pinned by test.

---

## 2. `flag_values` — the flag, and its limitation in the code

Rule 4 flags what is **outside** `allowed_values`. `Unspecified` is inside it, so adding the value made the validator silent on it *by construction* — leavers with an unknown end-of-service basis would commit without a word. That silence is what Rule 9 removes.

```
rejects   : 0
exceptions: 2
   [exception] row=2 rule=flagged-value
      en: Row 2, End of Service Type: Unspecified - grounds not recorded.
          The legal grounds for this termination were not recorded in your
          source system. No end-of-service entitlement can be derived from it.
      ar: الصف 2، نوع نهاية الخدمة: غير محدد — لم يُسجَّل السبب النظامي. ...
   [exception] row=4 rule=flagged-value
```

Per row, bilingual, correct row numbers, **and the file loads**.

**The limitation is recorded in `validate_schema.py`, not only in the plan:**

> A LIMITATION WORTH KNOWING, and it is not a defect: this fires on the **canonical** value, after any mapping profile has been applied. So it reports a **mapping decision, not a discovery**. When an operator maps a client's phrase to `Unspecified`, this is the system repeating that decision back with its consequence attached — it is not the system having found something in the data on its own. Read the count as *"the operator classified N rows this way"*, never as *"N rows were detected as incomplete"*.

---

## 3. Tamper-proof (SP-001)

A flag that fired on everything would carry no information, so the suite watches it **not** fire as much as it watches it fire. 21 tests:

| Watched NOT firing | Result |
|---|---|
| all seven article-bearing values (parametrised) | no flag, no reject |
| empty value on an **active** employee | no flag — that is the absence of a termination, not a gap in the grounds |
| **Terminated with an empty value** | still **REJECT** (`required_when`) |
| a genuinely unknown value (`Article 99`) | still **REJECT** (`allowed-values`) |

| Watched firing | Result |
|---|---|
| `Unspecified` | one EXCEPTION, file loads |
| rows 2 and 4 of a four-row file | violations at rows **3 and 5** — header is row 1 |
| more rows than `MAX_RENDERED_VIOLATIONS` | capped, plus an `"and N more"` tail carrying the true total |

Two tests use a **throwaway contract** so the assertions are about the mechanism rather than the one column that uses it today — including one proving `severity: reject` is expressible and blocks. **EXCEPTION here is therefore a decision, not the only option the mechanism offers.**

---

## 4. The affirmation text, and its pin

`end_of_service_type` is one of the three enums requiring an affirmation before a value mapping can be saved. Its consequence text enumerated outcomes that **all** carry an entitlement decision, so it was incomplete the moment `Unspecified` joined the enum.

Added, in both locales:

> **MAPPING TO `Unspecified` IS A DIFFERENT ASSERTION from the others:** the article-bearing values assert WHICH entitlement applies, while `Unspecified` asserts that the source did not record the grounds and therefore NO entitlement can be derived. Choose it when the grounds are genuinely absent — **never as a default for a value you have not looked up, because it withholds a figure the client may be owed.**

Pinned by `test_the_consequence_text_covers_the_Unspecified_case`, which asserts the wording in **both** locales plus the two clauses that carry the meaning — `"NO entitlement can be derived"` and `"never as a default"`. The original Article 80 pin is untouched beside it.

---

## 5. The forward note, where a mart author will meet it

On the **column description**, not only in the plan:

> FOR A FUTURE MART AUTHOR: `Unspecified` is an ABSENCE, not an eighth category. Grouping it beside Article 80 in a breakdown is the same defect as `COALESCE(project, 'Unassigned')` — it renders a gap as a slice. Report the seven real reasons as categories and `Unspecified` as a coverage note: *"N of M leavers have no recorded grounds"*.

Pinned by `test_the_column_description_warns_a_future_mart_author`, which asserts all three phrases survive an edit.

---

## 6. Parity delta

Measured with the **pre-change contract taken from `main` via git**, so "before" is shipped behaviour rather than a reconstruction:

```
case                                       BEFORE (main)            AFTER
------------------------------------------------------------------------------
end_of_service_type = Unspecified          REJECT (allowed-values)  ACCEPT + 1 EXCEPTION  <- CHANGED
the seven existing values                  ACCEPT                   ACCEPT
a genuinely unknown value (Article 99)     REJECT (allowed-values)  REJECT (allowed-values)
status Terminated, column empty            REJECT (required-when)   REJECT (required-when)
an active employee, column empty           ACCEPT                   ACCEPT
------------------------------------------------------------------------------
cases changed: 1 of 5

every other contracted table, conformant file:
  attendance / compliance / employee_relations / hr_requests / locations / payroll
  -> identical before and after
```

**Exactly the claim the plan made: previously-rejected files carrying this value now pass, and nothing else changes.**

`scripts/verify_contract_parity.py` also passes, with `bad_enum__end_of_service_type` still **REJECT** — the enum was widened by one value, not to anything.

---

## 7. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — identical, and asserted |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| pytest | **450 passed** (429 + 21 new) |
| flake8 | 0 on every changed file |

**Demo byte-identity is structural here**: the sample generator does not emit `end_of_service_type` at all, so the demo pipeline cannot produce or flag an `Unspecified`. The gate was run regardless.

### An environmental note worth carrying

The repository's `.env` is now configured for the first real load — `DATA_MODE=real`, `REPORT_MONTH=2026-08`. **The demo gate and the test suite therefore need those overridden explicitly**, because `Settings` reads that file and an unset environment variable falls back to its value. Verification here was run as CI runs it (`DATA_MODE=demo`, the demo period pinned). Not a defect — it is [GAP-002](../TECHNICAL_DEBT_REGISTER.md) in its benign form, and it will affect anyone running the demo suite on a machine prepared for real data.

---

## 8. Open

1. **`end_of_service_type` still has no consumer.** Plan §0 measured it: no mart, no KPI, no endpoint. This cycle makes the column *correct*, not *used*. The first real client will supply hundreds of leaver reasons into a column no figure derives from, and Article 80 exposure remains a stated Phase 2 selling point that nothing computes.
2. **The flag reports a mapping decision, not a discovery** (§2). Recorded in the code; worth repeating to whoever reads the first real DQ page.
3. **No value-alias table.** The client's Arabic phrases are mapped by hand in the profile. A value-alias table needs more than one client to be worth seeding.
4. `flag_values` is used by exactly one column today. It was built generically because the next legal-but-incomplete vocabulary member will want it, and that is a prediction, not a requirement met.

---

**Not merged. Awaiting review.**
