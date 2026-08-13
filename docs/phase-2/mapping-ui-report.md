# Mapping Cycle B — Execution Report

**Branch:** `phase-2/mapping-ui` off `main` @ `b705194` · **Date:** 2026-08-12
**Plan:** [`mapping-ui-plan.md`](mapping-ui-plan.md) (approved, six rulings) · **Status:** PR open, **not merged**

Cycle A shipped the mechanism and left two gaps. Both are closed. The screen is built on top of them, in that order, because one of them was the only route by which a wrong number reached a client.

---

## 1. Priority 1 — the ruling-4 gap

### 1.1 Attribution

`save_version` now refuses a version with no `created_by`. Verified against the four cases that matter:

```
no created_by                              -> REFUSED
created_by: ""  /  "   "  /  None          -> REFUSED   (parametrised)
created_by: operator@synthetic.local       -> SAVED, name kept, created_at stamped
```

Not read from the JWT inside `mapping.py`: `scripts/` must stay importable without the backend, which is what lets the pipeline, the tests and a console session all use it. The API passes the session identity in; the module refuses if it arrives empty.

### 1.2 Affirmation, keyed by the pair

```
values only, no confirmations              -> REFUSED, names 'معلق', quotes the consequence
confirmed with a DIFFERENT pair            -> REFUSED
confirmed_by empty                         -> REFUSED
target changed under an old affirmation    -> REFUSED
pair added to a previously affirmed column -> REFUSED, names ONLY the new pair
affirmed exactly                           -> SAVED, and loads
```

The last two are the reason it is keyed by the pair rather than the column. A tick given in August must not bless a word that first appeared in September, and when it does block, only `منتهي` is named — `نشط` was already affirmed and re-litigating it would train the operator to skim.

**Enforced at `save_version` AND `load_profile`.** The load-side test proves it independently: it monkeypatches the save-side check away, writes an unaffirmed profile to disk, restores the check, and asserts `load_profile` refuses to apply it. Save-side alone would leave the hand-written YAML path open, and hand-written YAML is exactly the path that produced this gap.

### 1.3 The consequence travels with the contract (ruling 5)

`VALUE_MAPPING_CONSEQUENCE` lives in `scripts/mapping.py`, bilingual, keyed `table.column`. It is not UI copy: the CLI prints it, the refusal quotes it, and the API ships it as `reject_enum_consequences` so the tick can state what is being affirmed rather than merely asking for assent.

> **End-of-service type decides whether a leaver is owed money. Article 80 is dismissal for cause and carries NO end-of-service award; Resignation and Articles 74/75/77/81 do.**

Pinned by test — `"Article 80" in …` and `"owed money" in …` — so the wording cannot quietly soften into ceremony.

### 1.4 What is still unguarded (ruling 6)

Unchanged from the plan, and now **pinned by a passing test rather than left to a document**:

```python
def test_an_EXCEPTION_enum_mapping_needs_NO_affirmation(profile_file):
    """PINNED AS A DECISION, NOT AN OVERSIGHT (plan §1.4)."""
    version = _version(values={"contract_type": {"محدد": "Limited"}})
    assert mapping.save_version("employees", version, path=str(profile_file))
```

1. **The 11 EXCEPTION-severity enum columns** — `compliance.qiwa_status`, `gosi_status`, `mudad_status`, `occupation_match_status`, `health_insurance_status`; `employee_relations.case_status`, `priority`; `employees.employment_type`, `contract_type`; `hr_requests.request_status`; `payroll.payroll_status`. A profile may map any client word into any of these and it loads, appears on the dashboard, and is recorded as fact. `payroll_status` mapping a client's *held* to `Paid` misstates what they actually disbursed. Per ruling 3 this stays open: fourteen columns of ticking makes the tick a formality.
2. **A plausible mis-mapped header.** `القسم` → `project` instead of `department` passes every rule — both free-text VARCHAR, both required, no format constraint separates them. The ladder makes it less likely; nothing detects it.
3. **A derivation pointed at a second nationality-shaped column.**
4. **Attribution is a record, not an authentication.** The API fills it from the session; a console caller can write anything.

**After this cycle the three highest-consequence enums are affirmed and every profile is attributed. Everything above remains an operator assertion the system accepts.**

---

## 2. Priority 2 — the `commitGate` truth table

`blockKind` and `blockCount` replace a sentence the caller could only print. The full table, each row a passing test:

| rejects | unmapped cols | unmapped values | can_commit | declaration | busy | → `blockKind` | `blockCount` | message |
|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | `nothing` | 0 | Nothing to commit. |
| 1 | 0 | 0 | false | — | false | `rejects` | 1 | 1 error must be fixed… |
| 1 | 1 | 0 | false | — | false | **`rejects`** | 1 | rejects win — the more actionable fix |
| 0 | 1 | 0 | false | — | false | `unmapped-columns` | 1 | 1 column has no decision yet… |
| 0 | 2 | 0 | false | — | false | `unmapped-columns` | 2 | 2 columns have no decision yet… |
| 0 | 0 | 3 (2 cols) | false | — | false | `unmapped-values` | **3** | counted across columns |
| 0 | 0 | 0 | **false** | — | false | `rejects` | 0 | *"cannot be committed yet. See the details above."* |
| 0 | 0 | 0 | true | missing | false | `declaration` | 0 | Confirm the period above… |
| 0 | 0 | 0 | true | ok | true | `busy` | 0 | *(null)* |
| 0 | 0 | 0 | true | ok | false | **`null`** | 0 | *(enabled)* |
| `mapping: null` | | | true | ok | false | `null` | 0 | a canonical export never sees any of this |

Row 7 is the one worth reading twice. A server-side blocker this client does not model gets a deliberately vague message — **the defect being fixed was a confident wrong one**, and replacing it with a differently confident wrong one would be no better. The assertion is `expect(gate.blockedBecause).not.toContain('0')`.

`MappingPanel` renders the rest: outstanding work always open, the 22 correct renames collapsed behind a disclosure, `header_changed` warning that *"Nothing was re-mapped automatically"*. Each unmapped header is a button that opens the screen focused on that column.

---

## 3. Priority 3 — the screen, and the CLI that must not slip behind it

### 3.1 The CLI (ruling 1)

Authored with no browser, start to finish:

```
$ mapping_cli.py suggest --table employees --file export.csv --out decisions.yml
  22 proposed, 2 need a decision: ['ملاحظات', 'Column14']
  affirmation required for: ['end_of_service_type', 'status']
```

The file it writes carries the contract-derived matches with their rung, comments the two it cannot decide, and leaves the affirmation **empty** with the consequence above it:

```yaml
columns:
  "الرقم الوظيفي": employee_id   # label_exact (0.95)
  "الجنسيه": nationality         # label_normalised (0.85)
  # "ملاحظات":  # no suggestion; map it or move it to `ignored`
...
# AFFIRMATION - deliberately empty. Nothing here is pre-filled.
#   end_of_service_type: End-of-service type decides whether a leaver is owed money…
confirmations: {}
```

The operator fills in the two, adds `values` and `derive`, and saves:

```
ARM 1 - values present, confirmations still empty
  REFUSED: … nobody has affirmed them.
    status (no confirmed_by): 'موقوف' -> 'Inactive', 'نشط' -> 'Active'
      Status decides who is counted as employed: headcount, Saudization…
  exit=2, nothing written

ARM 2 - the operator restates the pairs; the same command
  affirming status: Status decides who is counted as employed…
     'موقوف' -> 'Inactive'
     'نشط' -> 'Active'
  saved version 1 of employees
    22 mapped, 2 ignored, 0 undecided, 1 derived
    attributed to operator@synthetic.local
```

**`--by` supplies the attribution only.** A separate test asserts the CLI never invents an affirmation: with `confirmations: {}` and a value mapping present, it exits 2 regardless of `--by`. A tool that signed on the operator's behalf would be recording nothing.

Evidence captured by construction on this path, read back off disk:

```
evidence rows : 24 of 24 headers
matched_by    : {label_exact: 21, label_normalised: 1, human: 2}
PII 'X1' kept : False        vocabulary 'نشط' kept : True
name column   : {kind: redacted, dtype: string, cardinality: 3,
                 length_range: [2,2], pattern: 'A9'}
```

### 3.2 The screen, walked through its own calls

```
1. an Arabic export, no profile
   can_commit: False | mapping applied: False

2. GET /uploads/{id}/columns          <- what the screen renders
   source columns  : 24 | canonical targets: 23
     الجنسيه      samples Saudi, سعودي     -> nationality (label_normalised, 0.85)
     حالة الموظف  samples موقوف, نشط       -> status      (label_exact, 0.95)
     ملاحظات      samples note             -> NOTHING - needs a human
   consequence     : End-of-service type decides whether a leaver is owed money…

3. POST /mapping/employees, value mapping NOT affirmed
   status: 400
     refusing this mapping: the value mapping(s) below rewrite a client's own…
       status (no confirmed_by): 'موقوف' -> 'Inactive', 'نشط' -> 'Active'

4. the operator ticks the box; the same request
   status: 200 | version 1, mapped 22, ignored 2, undecided 0
   created_by     : admin@synthetic.local   <- from the session, not the body
   evidence rows  : 24 of 24
   matched_by     : {label_exact: 21, label_normalised: 1, human: 2}
   PII 'X1' kept  : False | vocabulary kept: True

5. the screen re-previews
   applied: True v1 | 22 renamed / 2 ignored | derived ['is_saudi'] | unmapped none
   can_commit: True

6. commit
   status 200 | pipeline success in 25.0s
   data/raw : employee_id,employee_name,nationality,company,department,pro…
   -> canonical: True
   employees: 3 rows | [('Inactive',), ('Active',)]
```

Step 2 is the PII boundary in practice: `سعودي` and `نشط` are on screen because a header alone will not settle those columns, and step 4 shows neither `X1` nor any name reaching the profile. A structural test asserts the `save_mapping` handler contains no reference to `samples` at all — a save cannot carry values back even by accident.

### 3.3 The ladder

One test per rung, each asserting the `matched_by` as well as the target:

| Rung | Input | → | `matched_by` |
|---|---|---|---|
| 1 | `employee_id` | `employee_id` | `canonical` (1.0) |
| 2 | `الجنسية` | `nationality` | `label_exact` (0.95) |
| 3 | `الجنسيه`, `" الجنسية "` | `nationality` | `label_normalised` (0.85) |
| 4 | `الاسم الكامل` | `employee_name` | `alias` (0.7) |
| 5 | `ملاحظات` | — | `[]`, not a guess |

`config/mapping_aliases.yml` seeds rung 4: 63 targets, 209 spellings, scoped **per table** — `الحالة` is `status` on employees, `request_status` on hr_requests and `case_status` on employee_relations, and a global table would have to pick one and be wrong twice. Two tests pin it: the scoping, and that every alias target exists on its contract.

### 3.4 Evidence by construction (ruling 2)

`build_version(table, frame, decisions, created_by)` is the single constructor. It runs the ladder itself, so `matched_by`, `confidence` and the **rejected** candidates are computed rather than supplied — a caller that has to remember to attach provenance is the failure this replaces.

```python
def test_build_version_records_what_the_human_did_NOT_take():
    # human chose employment_type; the ladder had proposed status
    assert evidence["matched_by"] == "human"
    assert [r["canonical"] for r in evidence["rejected"]] == ["status"]
```

`save_version` now requires evidence covering every header the version references, and says how to get it (`build_version`, or the CLI). With ruling 1 in place the operator contract changes shape rather than vanishing.

---

## 4. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — **identical**; dbt 158/158, 11/11, reconciliation PASSED |
| pytest | **294 passed** (251 + 43 new) |
| vitest | **94 passed** (62 + 32 new) |
| `tsc -b` (the real one — see below) | 0 errors |
| `npm run build` | passes |
| flake8 (CI blocking selection) | 0 |
| flake8 (full, changed files) | no new findings — `data.py` reports the same 10 pre-existing as `main` |

Demo byte-identity is structural, not lucky: mapping is upload-time only, the demo pipeline never stages an upload, and `test_nothing_downstream_knows_profiles_exist` holds the line. It was run anyway, per guardrail.

### 4.1 CORRECTION — `tsc --noEmit` was checking nothing

The Docker gate failed this PR on `src/components/widgets/MappingScreen.tsx(106,18): error TS6133: 'setValues' is declared but its value is never read.` Gate 1 had passed, and so had my own `npx tsc --noEmit`.

**Both were vacuous.** `frontend/tsconfig.json` is a solution file — `"files": []` plus two project references — so bare `tsc --noEmit` resolves **zero input files** and exits 0 whatever the code says. Measured directly:

```
$ npx tsc --noEmit --listFilesOnly | wc -l
0
```

`noUnusedLocals` and `"include": ["src"]` live in `tsconfig.app.json`, which only `tsc -b` reads. So the only real typecheck in CI has been `tsc -b` inside `npm run build` in **Gate 3**, three gates and ninety seconds later than it should fire.

This invalidates the "tsc --noEmit: 0 errors" line in **every prior cycle report of mine that carried it**, including [`mapping-profiles-report.md`](mapping-profiles-report.md) §7 and [`upload-ui-report.md`](upload-ui-report.md). Those cycles were green on the Docker gate, so the code was in fact typechecked — but not by the check I cited, and I should not have cited it.

**And it was not only a reporting error.** The claim was put forward as evidence cycle after cycle and **accepted at review each time**. Nobody asked what `tsc --noEmit` actually covered, including me — the line looked like verification, so it passed for verification on both sides of the review. A check nobody has interrogated is not evidence; it is a habit. The lesson is not "cite `tsc -b` instead", it is that a verification line earns its place only once someone has confirmed it can fail. `--listFilesOnly` would have answered it in one command at any point in the last six cycles.

**Gate 1 now runs `npx tsc -b`.** The error surfaces in 30 seconds instead of 100, and the comment in the workflow records why.

### 4.2 What the unused variable actually was

Not a stray. `setValues` had no caller because **the value-mapping UI did not exist**: the screen rendered an affirmation for a `values` map nothing could populate, so a client could never map `معلق` to anything and the affirmation block was unreachable. Deleting the variable would have compiled and shipped a screen missing half its purpose.

Fixed properly:

- the workspace route returns `distinct_values` — **every** distinct value, but only where a candidate target declares `allowed_values`. Five samples cannot show a client a word that first appears on row 900, and the same predicate that governs the PII rule at the write governs what is returned here. A name column gets `distinct_values: []` and keeps its five recognition samples. Pinned by test.
- the screen renders a row per value that is not already canonical, each with the canonical options. Choosing a meaning **clears any existing affirmation for that column** — a changed pair is a new assertion, which is the same rule the backend enforces at save and at load.
- the save button blocks while any gated value has no meaning, so the screen cannot produce a profile the preview would immediately reject.

**One test was loosened and the loosening was paid for.** `test_nothing_downstream_reads_staging` scans `scripts/` for the string `data/staging`, and `mapping_cli.py` names it in its usage text because staging is where an operator's file actually is. Rather than change the docstring to dodge a text scan, the exemption is explicit and a companion test asserts no pipeline step imports the CLI — the only condition under which the exemption is safe. The exemption is to the letter of the scan; the rule it protects is untouched.

---

## 5. Open

1. **§1.4 stands in full.** Eleven EXCEPTION enums, plausible mis-mapped headers, and attribution-as-record are all still open, by decision.
2. **The value-mapping step has no component test.** Its rule (`valuesNeedingMapping`) is tested as a pure function and the screen wiring is not — the same gap as item 3 below, and the one that let the missing UI reach CI.
3. **The screen has no component test.** `MappingPanel` has eight; `MappingScreen` has none — its rules were extracted into `lib/mapping.ts` and tested as pure functions (pre-selection, ordering, progress, unaffirmed pairs), and the routes it calls are tested through the API. What is untested is the wiring between them. That is the thinnest part of this cycle.
4. **`derive` is not editable from the screen.** The save request carries `derive: {}`; only the CLI can set one. One rule exists (`nationality_is_saudi`), so this is small — but a client whose export lacks `is_saudi` still needs an operator.
5. **The alias table does not grow.** It needs mappings from more than one client; single-tenant accumulation would relearn one client's habits and call it knowledge.
6. **TD-007 (RTL)** is now sharper: the mapping screen is the densest Arabic surface in the product and its chrome is English.
7. **TD-009** is sharper too: `lib/mapping.ts` is another hand-written mirror of Pydantic models with nothing enforcing the match.
8. **`mart_wps_status`** still missing; `GET /api/compliance/wps` still 500s.

---

**Not merged. Awaiting review.**
