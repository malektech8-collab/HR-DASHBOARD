# A per-column date ceiling, and a message that names the right fault — Execution Report

**Branch:** `phase-2/date-ceiling` off `main` @ `bec859f` · **Date:** 2026-08-16
**Ruling:** add `max_date` to `contract_end_date` rather than only splitting the message; split the message as well.
**Status:** PR open, not merged. **The real preview clears. Nothing was committed to the warehouse.**

Per SP-003 this report carries magnitudes and vocabulary only.

---

## 1. Why splitting the message alone was rejected, and the ruling was right

The global ceiling is `today + 2 years`. It is correct for a joining date — an accepted offer starting next month is routine, three years out is not. It is wrong for a contract **end** date, where a multi-year fixed term is ordinary in KSA and normal for senior staff.

A better-worded rejection is still a rejection. The client would have been told more clearly why they could not load a file that was never wrong. **A per-column ceiling states what is true; a split message only describes the fault more politely.**

## 2. `max_years_ahead`, not a literal date

The ruling said `max_date`, set to `today + 10y`. `max_date` exists and takes an **absolute** date, which cannot express that.

A literal written today — `2036-08-16` — is a ceiling that tightens by one year every year, until it is the same defect it replaced, arriving quietly and years after anyone remembers writing it. So the contract gains `max_years_ahead: <int>`:

```yaml
  max_years_ahead: 10
```

An integer, never an expression — the rule that already governs `derivation` and `required_when`, because a contract is operator-supplied data. Precedence is `max_date` → `max_years_ahead` → the global default, and that order is pinned by a test even though nothing declares both today.

**Ten years is deliberately generous, per the ruling.** The rule exists to catch **corruption** — a year like 0025, a stray Excel serial — not to audit whether a contract term is sensible. That judgement belongs to the client and the Labour Law. A ceiling tight enough to be interesting is a ceiling that blocks honest files.

## 3. The message, split by bound

| bound crossed | what it now says |
|---|---|
| below the floor | *"…is before 1940-01-01. A year like 0025 usually means a corrupted Excel date serial — check the source export."* |
| above the ceiling | *"…is after `<ceiling>`, the furthest ahead this column is expected to reach. Check the source export; if the date is genuinely correct, this column's ceiling is too tight and the contract needs raising."* |

Both bilingual, and **the Arabic splits too** — a split that reached only English would leave an Arabic-reading client with the wrong diagnosis, which is the whole defect, untouched.

### 3.1 A correction made during the work

The first draft of the above-ceiling message ended *"— it is not a corrupted export."* That is an over-claim: a date in 2099 may very well **be** corruption, and the rule cannot tell. Asserting otherwise repeats the original sin in the opposite direction. The message now names the second possibility instead of ruling out the first.

## 4. Two things fixed on the way past

- **`_years_ahead()` survives a leap day.** `datetime.date(today.year + n, today.month, today.day)` raises on 29 February, because the target year has none. A validator that crashes on one day in four years is not a bug anyone finds twice. The global default now uses the same helper.
- **A pinned wording was updated, not worked around.** `test_corrupted_date_serial_is_rejected` asserted `"outside the plausible range"` in both languages. That phrase is gone by design — it named no bound. The assertions now pin the below-floor text, which is the case that test covers. Per SP-002 the correction is recorded as a change of **wording**, and the test still fails if the corrupted-serial diagnosis disappears.

## 5. Verification

| Check | Result |
|---|---|
| pytest | **518 passed** (506 + 12 new) |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` after a **full rebuild** |
| flake8 | 14 findings on `validate_schema.py`, **down from 18** — no new finding |

Rebuilt end to end rather than tested against a stale warehouse, because this changes both the contract and the validator.

**Tampers, per SP-001.** Raising a ceiling must not remove it: a date beyond even ten years still rejects. And it must not raise anyone else's: a joining date six years out still rejects, which is the whole point of doing this per column rather than globally.

## 6. The real preview now clears

```
can_commit : True
REJECTs    : 0
EXCEPTIONs : 44   (flagged-value, two columns)
derived    : ['is_saudi']
unmapped headers: none    unmapped values: none
```

Every remaining finding is an EXCEPTION, which loads and surfaces on the Data Quality page — which is what an exception is for. **Not committed.**

## 7. Open

1. **TD-013 — the affirmation gate is narrower than the affirmation principle.** Ruled, deferred to its own cycle after the load, because it changes what every existing profile must carry.
2. **The preview summary defect** ([plan](preview-summary-grain-plan.md)) is still unbuilt, and is now the most visible remaining wrongness in the preview: it reports all 23 canonical columns as missing on a preview that has zero rejects and can commit.

---

**Preview clears. Nothing committed to the warehouse. Awaiting approval to load.**
