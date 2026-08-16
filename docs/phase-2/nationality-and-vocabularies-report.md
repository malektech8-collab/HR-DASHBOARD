# Nationality aliases, enum vocabularies, and a P1 read defect — Execution Report

**Branch:** `phase-2/constants-cli` off `main` @ `c138340` · **Date:** 2026-08-16
**Rulings:** 1 (nationality aliases), 2 (enum vocabularies), 3 (commit the CLI fixes), 4 (plan the preview-summary fix)
**Status:** committed, PR open. The real preview was run and **nothing was committed to the warehouse.**

Per SP-003 this report carries **magnitudes and vocabulary only**. No client figure and no row appears here.

---

## 1. Ruling 1 — nineteen nationality values

All nineteen are non-Saudi and are added to `_NON_SAUDI_ALIASES` in [derivations.py](../../scripts/derivations.py), each with its English gloss on the line.

Five of them — British, Turkish, Kenyan, Bangladeshi, Nepali — **already had an English entry**. That did not help: the table matches the value as the client *wrote* it, and they wrote it in Arabic. Worth knowing before anyone reads the table's length as coverage.

### 1.1 A correction: the whitespace needed no handling

The ruling asked for the trailing whitespace on two values to be handled at normalisation rather than by padded variants. **It already is.** `_normalise` in [text.py](../../scripts/text.py) opens with `.strip()` and a whitespace collapse, before it touches tatweel or alef forms.

The padding appeared in the error message only because `DerivationError` reports `str(v)` — the **raw** value, deliberately, so an operator can find it in their file. So the report of the defect was accurate and the diagnosis of where it lived was one layer off.

No code changed for this. What changed is that the claim is now *checked*: `test_the_normaliser_is_what_absorbs_the_padding` asserts the mechanism, and `test_padded_values_resolve_although_no_padded_alias_exists` asserts the padded strings resolve **while asserting they are not in the table**. Without that pair, a later padded entry would make the behaviour pass for the wrong reason.

### 1.2 `غير سعودي` — a category where a nationality belongs

`false` is correct, so it sits in the non-Saudi table and Saudization is unaffected. But the nationality itself is unrecorded, and Nitaqat reporting is not only the Saudi/non-Saudi binary.

The derivation cannot say so — it returns booleans — so the observation is raised where a client will read it: **`flag_values` on `nationality`** in the employees contract, severity `exception`.

This is the **second user of `flag_values` and the first outside a closed vocabulary**. The eos-unspecified report predicted it would be wanted again and said so plainly as a prediction rather than a requirement met; it is now met.

**Its limitation, stated:** `flag_values` is exact-match. A client writing `غير سعودية` or `Non-Saudi` is not caught until that spelling is declared. On a free-text column a fuzzy match would flag real nationalities, so exact-match is the right trade — but it is a trade, not a general rule.

## 2. P1 — the CSV read defect (ruling 3)

`pl.read_csv` inferred `i64` from the leading rows of a salary column and then met a decimal, raising `ComputeError: could not parse '1584.91' as dtype 'i64'`. Fixed at four sites — the mapping CLI and three in [data.py](../../backend/app/api/data.py) — with `infer_schema_length=0`, which is the idiom [validate_schema.py](../../scripts/validate_schema.py) already used for the same reason.

**Stated plainly, because it is the most serious thing in this cycle:**

> This would have blocked **any real upload through the UI**, not only the CLI. Three of the four sites are on the browser path. The demo data never surfaced it and no synthetic fixture would have — it needs a salary column whose first rows are whole numbers and whose later rows are not, which is what a real payroll export looks like and what a generator does not produce.

Mapping is a **text** operation: it renames headers, replaces values, adds columns. Inferring dtypes there bought nothing and cost the upload path.

## 3. Ruling 2 — the two vocabularies, and the contract's words

| source | canonical | note |
|---|---|---|
| `دوام كامل` | `Full-time` | matches the ruling |
| `مدة محددة` | **`Limited`** | ruling said Fixed-term |
| `غير محددة` | **`Unlimited`** | ruling said Indefinite |

The ruling instructed that the contract wins where it differs, and it differs. عقد محدد المدة / عقد غير محدد المدة are the Labour Law's two forms, so the pairing is the same distinction under the contract's names.

### 3.1 A guard, because nothing in the code would have caught it

`_validate_targets` checked that a value map named a real *column*. It never checked the **right-hand side**. A profile mapping to `Fixed-term` would have saved cleanly and then produced a fresh allowed-values exception on every row — the exact violation the mapping existed to remove, now wearing the operator's chosen spelling and looking deliberate.

The check is added in [mapping.py](../../scripts/mapping.py), and its message names the values that *would* have worked.

Per SP-001 both halves are tested: a non-contract target is refused, the ruled maps pass the same guard, and a value map on a **free-text** column is left alone — a column with no vocabulary has nothing to check against and must not be refused for want of a list.

### 3.2 A gap in the affirmation gate, reported not patched

`reject_enum_columns` returns two columns — `status` and `end_of_service_type` — so a value map on `employment_type` or `contract_type` requires **no affirmation**. The gate is "would an unmapped value have REJECTED", but the ruled principle is *affirm wherever being wrong is not visible on the screen the client looks at*.

Once mapped, a wrong pair on `contract_type` is exactly as silent as a wrong pair on `status`. The gate is narrower than the principle.

Both were affirmed anyway when authoring this profile, and the machinery accepted the extra affirmations without complaint. **Not patched** — widening the gate changes what every existing profile is required to carry, which is a ruling.

## 4. Ruling 4 — planned, not built

[preview-summary-grain-plan.md](preview-summary-grain-plan.md). The summary is computed from the pre-mapping frame while the violations come from the mapped one; both are true of different files, and read together they say the mapping failed when it worked.

The plan records a **second consequence of the same root cause** that had not been seen: the suggested coverage window is also picked using pre-mapping headers, so a **mapped attendance upload** would silently receive no suggested window at all — on the one table where coverage is required.

## 5. Verification

| Check | Result |
|---|---|
| pytest | **506 passed** (492 + 14 new) |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — asserted by `test_demo_gate` after a **full rebuild** |
| flake8 | no new finding on any changed file |

The demo warehouse was rebuilt end to end rather than tested against a stale one, because this cycle changes the employees **contract**. The nationality flag does not fire in demo — the sample data's nationalities are English and the rule is exact-match — so demo output is unchanged.

**Environmental, not caused by this change.** The venv's `dbt.exe` console shim exits 1 with no output locally; `python -m dbt.cli.main` runs normally. CI is unaffected — `build_warehouse` falls back to `dbt` on PATH when the shim is absent, and here it is present but broken, which is the one case the fallback does not cover. Logged as a local-environment note, not a repo change.

## 6. Open

1. **`contract_end_date`'s plausible ceiling is `today + 2 years`, and it REJECTS.** See §7 — this is the only thing blocking the real load.
2. **The affirmation gate is narrower than the affirmation principle** (§3.2).
3. **`flag_values` is exact-match on a free-text column** (§1.2).
4. **The preview summary defect is planned, not fixed** (§4).

## 7. The one blocker, and why the message is wrong about it

The real preview's only REJECTs are `date-range` on `contract_end_date`, at single-digit magnitude. **Every one is above the ceiling, none below the floor.**

That matters, because Rule 5's message says:

> *"A year like 0025 usually means a corrupted Excel date serial — check the source export."*

That diagnosis is right for a date below the floor and **wrong for one above the ceiling**. A fixed-term contract ending more than two years out is ordinary in KSA, particularly for senior staff. The rule is telling a client to go fix a corruption that is not there, and it is a REJECT, so the file does not load.

Two candidate resolutions, neither taken here:
- declare a `max_date` on `contract_end_date` in the contract, which is a one-line change the existing rule already reads (`spec.get("max_date")`); or
- split the message by which bound was crossed, so a future date is not diagnosed as a corrupted serial.

The first is narrow and reviewable. The second is right regardless of the first. **Both are rulings, not fixes to make while stopping.**

---

**Preview run, nothing committed to the warehouse. Awaiting a ruling on §7.**
