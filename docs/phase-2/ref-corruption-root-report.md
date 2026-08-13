# The ref() Corruption, at its Root — Execution Report

**Branch:** `phase-2/ref-corruption-root` off `main` @ `773dd58` · **Date:** 2026-08-13
**Status:** PR open, **not merged**

I fixed 27 literals last cycle and called the corruption handled. That was the part I had looked at, not the root. There were **49 more**, and most of the damage was somewhere I had not thought to check.

---

## 1. The blast radius I missed

The find/replace rewrote bare domain words into `{{ ref('stg_x') }}` and did not stop at `FROM` clauses. Last cycle I found it in `module_key` and `route_path` — three rows. The same edit had also landed in **client-facing exception text**:

```sql
'Employee has status ' || p.emp_status ||
    ' but appeared in active {{ ref('stg_payroll') }} run'  AS description,
'Hold {{ ref('stg_payroll') }} and verify termination status' AS recommended_action
```

Which a client read on the Data Quality page as:

```
Employee has status Inactive but appeared in active
    "hr_analytics"."main"."stg_payroll" run
Hold "hr_analytics"."main"."stg_payroll" and verify termination status

Active employee has no "hr_analytics"."main"."stg_attendance" record
    for expected workday on 2026-06-25
Update "hr_analytics"."main"."stg_compliance" records with Iqama expiry date
```

**Measured before the fix: 492 of 667 exception rows** carried a rendered relation name in their description or recommended action. **164× the blast radius of the module keys, in the text a client actually reads.**

| | Before | After |
|---|---|---|
| Corrupted exception rows | **492 of 667** | **0** |
| String literals | 36 across 7 models | 0 |
| Comments | 13 across 5 models | 0 |
| Module keys / routes | fixed last cycle (27) | still correct |

Restoring `{{ ref('stg_x') }}` → `x` gives back the original sentence, because `x` is precisely the word that was replaced. *"Hold payroll and verify termination status"* reads as English again.

**The demo figures are unchanged** — 667 exceptions, same count — because only the **text** was wrong. That is also why no gate ever caught it: every count was right.

---

## 2. Why it survived: the cycle-5a routing-around

The architect's context is exact, and the evidence is in my own report. From `docs/phase-0/phase-0-5a-resolver-report.md`:

> "(Note: pre-cycle, `attendance` and `compliance` also had a `module_key` mismatch — they queried `'attendance'`/`'compliance'` but the freshness mart stores relation-expanded keys like `'"hr_analytics"."main"."stg_attendance"'`; reading `base_command_center_report_context` **sidesteps that entirely**.)"

and, in the same report:

> "which also **fixes** the second latent bug (the attendance/compliance `module_key` mismatch) **for free by not using `module_key` at all**"

The corrupted values were **seen, quoted verbatim, called fixed, and left in the data.** The word "fixes" is doing work it had not earned: nothing was fixed, one consumer stopped reading a corrupt value. The corruption then spread to a second set of models and survived until this cycle — by which point it had also been sitting in 492 client-facing messages the whole time, where it had always been.

Recorded in the register as a named failure mode: **a defect that is routed around is not closed.**

---

## 3. The structural test

`backend/tests/test_no_jinja_in_sql_strings.py`.

**Detection is not a grep.** A ref *contains* quotes — `{{ ref('x') }}` — so splitting a line on `'` tears the expression apart. Measured: my first attempt at this fix did exactly that and reported **0 corrupted literals in a file that had 26**. So every `{{ ... }}` span is masked to a quote-free sentinel first, and string state is tracked over the masked text.

**Ref-only, deliberately.** `{{ var('start_date_str') }}` inside a literal is the established idiom — it renders a **value**, and there are **140 of them**:

```sql
WHERE attendance_date BETWEEN DATE '{{ var('start_date_str') }}'
                          AND DATE '{{ var('end_date_str') }}'
```

A detector that flagged those would be noise, and noise gets deleted. A `ref` renders a **relation name**, which is never a value anyone wants in a string. A test asserts the distinction is deliberate: the same spans *are* found with `only_refs=False`, so we know the quote tracking sees them at all.

Six further tests cover the detector on known inputs — both shapes that actually occurred, a legitimate ref, several literals on one line, a ref in a comment, and an escaped quote.

### Tamper-proof (SP-001)

```
baseline                                        9 passed   GREEN
module_key literal restored to the corrupt form 1 failed   RED
client-facing description re-corrupted          1 failed   RED
comment re-corrupted                            1 failed   RED
restored                                        9 passed   GREEN
```

---

## 4. (2c) Other artefacts of the same shape

Swept, with results:

| Where | Result |
|---|---|
| `{{ ref(` inside SQL string literals | **36 found, all fixed** |
| `{{ ref(` inside SQL comments | **13 found, all fixed** |
| `{{ ref(` / `{{ var(` in `.py`, `.ts`, `.tsx`, `.json` | **none** (only `.venv` third-party docs) |
| `{{ ref(` in dbt `.yml` schema files | **none** |
| `"hr_analytics"."` string anywhere in source | **none** outside the tests and module docstrings that describe the defect |
| Frontend route tables | **none** — `route_path` is a passthrough type, nothing hardcodes a value |
| `dbt_project.yml` | **clean** |

Nothing had been coded *around* the corrupted values either, so restoring them is a pure fix rather than a coordinated change.

**One caveat on completeness**: this sweep covers the shapes I can name. The structural test now covers the `.sql` case permanently; the others were one-time greps, and I would not claim they exhaust every possible artefact of a find/replace nobody has the record of.

---

## 5. SP-001, amended the day it was adopted

```
(i)  it can fail                        - falsifiability
(ii) it asserts the thing that matters  - relevance
```

Half the rule turned out not to be most of the rule. **Checks 9–11 satisfied (i) and failed (ii)** — and I classified them as *real* on that basis in the previous report. `COUNT(*) = 9` goes red if you delete a row, so it is falsifiable; it stayed green while three of the nine rows were corrupt, so it was vacuous. Falsifiable and vacuous at once.

That is now the worked example in the register, because **a check that passes the obvious question survives review indefinitely.**

---

## 6. TD-010 — one rule, two places

Recorded as an accepted cost, per instruction.

| Rule | Model | Check |
|---|---|---|
| Category F attendance denominator — measured days only, NULL when none measured | `mart_attendance_kpis.sql` | `reconciliation.py`, `attendance_compliance_pct` |
| Saudization nationality exclusion — unknown nationality excluded from **both** sides | `mart_compliance_kpis.sql` | `reconciliation.py`, `saudization_pct` |

**Not fixable by sharing a macro** — that would restore the tautology in a subtler form, since both sides would then move together, which is precisely what SP-001 exists to prevent. Both restatements now name the other half in a comment. The closure criterion is deliberately *not* "remove the duplication".

---

## 7. Verification

| Check | Result |
|---|---|
| Corrupted client-facing rows | **492 → 0** |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — identical and asserted |
| Reconciliation | `PASSED (12 independent checks)` |
| dbt | 161/161, 11/11 |
| pytest | **358 passed** (349 + 9 new) |
| vitest | 94 passed · `tsc -b` clean |
| flake8 | 0 on all changed files |

---

## 8. Open

1. **The 2c sweep is not a proof of exhaustion** (§4). The `.sql` case is now permanently guarded; the rest were one-time greps.
2. **SP-001 is still not retroactive** — only checks written or touched since adoption have been tamper-proven.
3. **TD-010** is accepted duplication, not solved.
4. The `'Unassigned'` / `'Missing Project'` sentinels and §1.4's mapping residual remain open, unchanged.
5. **`mart_wps_status`** still missing; `GET /api/compliance/wps` still 500s.

---

**Not merged. Awaiting review.**
