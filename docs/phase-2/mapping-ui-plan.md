# Mapping Cycle B — closing ruling 4, then the screen (PLAN ONLY)

**Branch:** `phase-2/mapping-ui` off `main` @ `b705194` · **Date:** 2026-08-12
**Follows:** [`mapping-profiles-plan.md`](mapping-profiles-plan.md) / [`mapping-profiles-report.md`](mapping-profiles-report.md) (cycle A, merged in #26)
**Status:** PLAN ONLY. Nothing implemented.

Cycle A shipped the mechanism and left two gaps, both self-reported and both accepted. This cycle closes them **before** building the screen: one is the only route by which a wrong number currently reaches a client, and the other makes the product unusable at exactly the moment a mapping is needed.

The priority order below is the build order. If the cycle is cut, it is cut from the bottom.

---

## 1. Priority 1 — close the ruling-4 gap

### 1.1 What is actually open

Ruling 4 of cycle A asked for *"attribution + explicit confirmation for the 3 REJECT enums"*. Cycle A delivered the **task-surfacing** half — an unmapped value in a REJECT enum blocks the commit and arrives with the canonical options listed — and left the **assertion** half unbuilt. Verified on `main`:

```
saved WITHOUT created_by: {'values': {'status': {'معلق': 'Active'}}, 'version': 1,
                           'created_at': '2026-08-12T13:57:47'}
-> attribution enforced: False
```

`معلق` means *suspended*. Mapped to `Active`, that employee is counted in headcount, in Saudization, and in payroll exposure. The translation is invisible downstream **by design** — `data/raw` is canonical and `ingest_raw` revalidates it without knowing profiles exist — so nothing after the upload can question it. There is no record of who asserted it.

The three columns, read from the contracts rather than transcribed:

| Table | Column | Canonical options |
|---|---|---|
| `employees` | `status` | Active, Inactive, Terminated, On Leave |
| `employees` | `end_of_service_type` | Resignation, Article 74/75/77/80/81, Probation |
| `employee_relations` | `case_type` | Disciplinary, Grievance, Labor Case |

These are the three where `on_violation` is absent, so the default REJECT applies. `end_of_service_type` is the one with real teeth: Article 80 is dismissal for cause and carries no end-of-service award, so a value mapping that turns a client's word into `Article 80` decides whether a leaver is owed money.

### 1.2 (a) Attribution, enforced at the write

`save_version` gains a required-field check: a version without a non-empty `created_by` is refused. `created_at` is already auto-stamped and stays that way — a timestamp nobody can forge is worth more than one someone types.

Deliberately **not** derived from the JWT inside `mapping.py`: `scripts/` must stay importable without the backend, which is what lets the pipeline, the tests and a console session all use it. The API layer passes `current_user["email"]` in; the module refuses if it arrives empty. Same seam `staging.py` already uses.

### 1.3 (b) Confirmation, enforced at both ends

**Keyed by the pair, not the column.** Confirming `status` once and then adding `منتهي → Active` next month must not inherit the old affirmation. The stored shape:

```yaml
values:
  status: {"نشط": Active, "موقوف": Inactive}
confirmations:
  status:
    confirmed_by: operator@client.example
    confirmed_at: 2026-08-12T14:02:11
    pairs: {"نشط": Active, "موقوف": Inactive}   # must match `values` exactly
```

New `mapping.assert_value_mappings_confirmed(table, version)`:

- for every canonical column in `values` that is in `reject_enum_columns(table)`, every pair must appear identically under `confirmations[column].pairs`;
- `confirmed_by` must be non-empty;
- a pair present in `confirmations` but absent from `values` is fine (a withdrawn mapping); the reverse is not.

**Called from `save_version` AND from `load_profile`.** Save-side alone would leave the hand-written YAML path open, and hand-written YAML is precisely today's operator path — the one that produced this gap. Load-side enforcement means an unconfirmed profile cannot be *applied* even if it reached the disk some other way.

Failure is loud and bilingual and names the specific pairs, because the operator's next action is to confirm those exact pairs.

**Fail-closed consequence, accepted:** a cycle-A profile with a REJECT-enum value mapping and no `confirmations` block stops working on upgrade. `data/mapping/` is gitignored deployment state, so there is nothing in the repo to migrate, and the failure direction is the right one. The error message will say what to add.

**This is the same shape as the coverage declaration, and deliberately not the same lifetime.** Coverage is confirmed *per upload*, because what a file covers changes every month. A value mapping is confirmed *per profile version*, because the meaning of `معلق` does not change monthly and re-asking would train the operator to click through it. Adding or changing a pair mints a new version, which needs its own affirmation. A suggestion still does not count: `assert_value_mappings_confirmed` cannot be satisfied by anything the machine writes, only by a `confirmed_by` the API takes from the session.

### 1.4 (c) What remains unguarded after this — stated plainly

Closing 1.2 and 1.3 does **not** make value mapping safe. It makes one class of it attributable and affirmed. What is still an operator assertion, accepted without challenge:

1. **The 11 EXCEPTION-severity enum columns.** `compliance.qiwa_status`, `gosi_status`, `mudad_status`, `occupation_match_status`, `health_insurance_status`; `employee_relations.case_status`, `priority`; `employees.employment_type`, `contract_type`; `hr_requests.request_status`; `payroll.payroll_status`. A profile may map any client word to any of these and it will load, appear on the dashboard, and be recorded as fact. `payroll_status` mapping a client's *held* to `Paid` misstates what a client has actually disbursed. **No confirmation is proposed for these in this cycle** — the ruling named three, and extending the gate to fourteen columns would make the affirmation a formality, which is worse than not having one.

2. **A plausible mis-mapped header.** Mapping `القسم` (department) to `project` instead of `department` passes every rule: both are free-text VARCHAR, both required, no format constraint distinguishes them. Every departmental figure is then silently wrong. The suggestion ladder in §3 reduces the odds; nothing detects it.

3. **A derivation pointed at the wrong source.** `derive: {is_saudi: {rule: nationality_is_saudi, from: <wrong column>}}` raises `DerivationError` on unrecognised values, so a random column usually fails loudly — but a second nationality-shaped column would not.

4. **Attribution is a string the operator supplies.** After 1.2 it must be present and the API will fill it from the session, but a console caller can still write anything. It is a record, not an authentication.

The honest summary: after this cycle, **the three highest-consequence enums are affirmed and every profile is attributed; everything else in a profile remains an operator assertion the system trusts.** That is a defensible position for an operator-assisted first load. It is not a defensible position for unattended self-service, and the difference should be recorded before anyone proposes the latter.

---

## 2. Priority 2 — the `commitGate` dead end

### 2.1 The defect

Cycle A's step a3 widened `can_commit` to also block on unmapped headers and unmapped REJECT-enum values. `commitGate` was not told, and still assumes `!can_commit` implies rejects:

```ts
if (!preview.can_commit) {
  const n = preview.rejects.length;
  return { enabled: false, blockedBecause: `${n} errors must be fixed…` };
}
```

With a clean file and an incomplete profile: **"0 errors must be fixed before this can be committed."** Meanwhile `MappingOut` — which carries `unmapped`, `unmapped_values`, `reject_enum_options`, `ignored`, `renamed`, `header_changed` — is returned by the preview and **no frontend code reads it**. Grepped: zero references outside the type declaration in `uploads.ts`.

It fails closed, so nothing wrong is committed. It is simply a dead end.

### 2.2 The fix

`commitGate` derives the reason from all three blockers rather than assuming one, and returns enough for the page to act on:

```ts
export type BlockKind = 'rejects' | 'unmapped-columns' | 'unmapped-values'
                      | 'declaration' | 'nothing' | 'busy';
// CommitGate gains: blockKind, and the counts for the mapping cases
```

Truth-table tested as a pure function, the same as the existing two rules — the reason it was extracted in the first place. Cases that must be named: clean + unmapped headers; clean + unmapped values; rejects + unmapped (rejects win, they are the more actionable fix); mapping complete + declaration missing.

A new `MappingPanel` renders `MappingOut` in the review step, beside `ViolationPanels`:

- **what the profile did** — N renamed, N ignored (with the recorded reason), N derived — collapsed by default, because on a working profile this is noise;
- **what still needs a decision** — unmapped headers, and unmapped REJECT-enum values with their canonical options — expanded, and the only part shown when the profile is complete and silent;
- **`header_changed`** — surfaced as a warning with the mismatch spelled out, never auto-remapped. A client who added a column should be told, not have it silently ignored by a profile written before it existed. Cycle A computed this and nothing acted on it; this is where it starts mattering.

Each unmapped item links into the mapping screen (§3) with that column pre-selected. Without the screen, the panel is an accurate dead end instead of a misleading one — which is why §2 is worth shipping even if §3 slips.

---

## 3. Priority 3 — the mapping screen

### 3.1 Where it sits

The `Step` machine becomes `'pick' | 'upload' | 'map' | 'review' | 'done'`. `map` is entered when the preview reports unmapped headers or unmapped REJECT-enum values, and is reachable from the review step's `MappingPanel` at any time. It is skipped entirely when the profile is complete — a client whose export already matches never sees it.

### 3.2 The suggestion ladder

Settled input from cycle A's plan §5, implemented as `mapping.suggest(table, headers)` returning ranked candidates per source header:

| Rung | Match | `matched_by` | `confidence` |
|---|---|---|---|
| 1 | exact canonical key | `canonical` | 1.0 |
| 2 | exact `name_ar` or `name_en` | `label_exact` | 0.95 |
| 3 | normalised match on either (`scripts/text.py`) | `label_normalised` | 0.85 |
| 4 | alias table | `alias` | 0.7 |
| 5 | nothing | `human` | null |

Rung 3 is where the real value is: `الجنسيه` → `الجنسية` and a trailing space both dissolve, using the same `normalise` that already backs value matching and nationality derivation.

**The alias table is a new checked-in `config/mapping_aliases.yml`** — `الرقم الوظيفي` / `رقم الموظف` / `الرقم` → `employee_id` and so on — seeded by hand, bilingual, reviewed like code. It does **not** auto-grow from accumulated profiles this cycle: growing it needs mappings from more than one client, and single-tenant accumulation would just relearn one client's habits. The evidence captured here is what makes that growth possible later.

**Pre-selection rule, and the distinction it rests on.** Rungs 1–3 arrive pre-selected; rung 4 arrives suggested but unselected; rung 5 is blank. A *header* mapping that is wrong usually fails validation loudly, and pre-selecting saves 20 of 24 decisions on a well-formed export. A *value* mapping into a REJECT enum that is wrong is silent — which is why §1.3 requires a tick for those and this does not. `matched_by` records the rung for every column, so a later audit can tell which decisions the machine proposed.

### 3.3 Sample values — the boundary from cycle A

A header alone often will not settle a mapping, so the screen shows sample values beside each source column. The boundary drawn in cycle A holds without exception:

> Showing a client their own values, in their own session, is fine — it is their file. **Persisting** them is not, for any column whose canonical target does not declare `allowed_values`.

Mechanically:

- a new `GET /api/data/uploads/{upload_id}/columns` returns per-source-column samples **read from the staged file at request time**. A separate route rather than a widening of the preview response, so the one place client values deliberately cross the API is explicit and reviewable;
- the response is never written anywhere — not to the profile, not to the manifest, not to a log;
- `mapping.assert_no_pii` already refuses the write and is unchanged. The new test asserts the round trip: values visible on the samples endpoint, absent from the profile saved from that same screen.

### 3.4 Writing the profile — evidence by construction

Today evidence exists only if someone remembers to call `build_evidence()` and then `save_version()`. A hand-written YAML with `columns` and `values` loads perfectly and captures nothing. Since the screen *is* the data collection, that must stop being a matter of discipline.

**New `mapping.build_version(table, frame, decisions, created_by)` — the single constructor.** It takes the human's decisions (per header: `chosen` / `ignored` + reason / `undecided`, plus the candidates they were shown and did not pick) and returns a complete version: `columns`, `ignored`, `values`, `derive`, `confirmations`, `source_fingerprint`, `created_by`, and `evidence` covering **every** source header with `matched_by`, `confidence`, `chosen`, `decision`, `rejected` and a PII-safe `value_profile`.

**`save_version` then requires evidence** covering every header the version references. Combined with 1.2 and 1.3, the effect is that a version can only realistically be produced by `build_version`, which needs the frame, which means evidence cannot be forgotten.

The cost, stated rather than buried: **this breaks the cycle-A hand-authored path.** An operator can no longer write a profile in a text editor and have it save; they stage the file first and go through the screen or the API. That is a real reduction in operator freedom, and it is the recommendation anyway — the hand-authored path is the one that produced both gaps this cycle exists to close, and cycle B is precisely the cycle that supplies the replacement. `load_profile` deliberately does **not** require evidence, so a profile written before this change still applies; only writing a new one is gated.

> **Flagging for the architect:** if hand-authored profiles must stay writable for an operator working without a browser, the fallback is a small `scripts/` CLI taking a YAML of decisions plus the staged CSV and calling `build_version` — same guarantees, no UI. Cheap to add, but it is a decision about the operator contract rather than an implementation detail, so it is not in the sequencing below.

### 3.5 Screen design

Fixed in cycle A's plan and unchanged: **unmapped first** (never a 37-row list with the 3 that matter in the middle); sample values beside each source column; progress as *"14 of 37 mapped, 3 need attention"*, not a percentage.

Added here: the value-mapping step for REJECT enums renders the canonical options as radio buttons with the affirmation checkbox beneath, worded with the consequence rather than as ceremony — *"I confirm 'معلق' means Terminated for this client."* Arabic scope stays as it has been: schema-derived labels (`name_ar`) and validator messages. Chrome stays English; that is TD-007 and it is deliberately not started here.

---

## 4. Testing

| Area | What is pinned |
|---|---|
| Attribution | `save_version` without `created_by` raises; with it, succeeds and records the value |
| Confirmation | unconfirmed REJECT-enum mapping refused at **save** *and* at **load**; a confirmed one applies; adding a pair invalidates the prior affirmation; an EXCEPTION-enum mapping needs none — pinning 1.4 item 1 as a decision rather than an oversight |
| Ladder | one test per rung, incl. `الجنسيه` matching `الجنسية` at rung 3 and the alias table at rung 4; `matched_by`/`confidence` present on every result |
| Evidence | `build_version` produces evidence for every header including undecided ones; `save_version` refuses a version whose evidence misses a header; `rejected` candidates survive the round trip |
| PII | samples visible via the columns endpoint, **absent** from the profile saved from the same decisions; `assert_no_pii` still refuses a smuggled value |
| `commitGate` | truth table over rejects × unmapped headers × unmapped values × declaration; specifically that clean-file-plus-unmapped never renders "0 errors" |
| `MappingPanel` | renders unmapped headers and unmapped values with options; `header_changed` warns and does not remap |
| Path contract | the two new routes exist — `test_path_contract.py` covers this once the frontend names them |
| Demo | byte-identical: `19 / 446175.0 / 50.0 / 667 / 15`, dbt 158/158, 11/11, reconciliation PASSED |

**Demo byte-identity is structural here, not lucky.** Mapping is upload-time only, nothing under `data/raw` or downstream imports `mapping`, and the demo pipeline never stages an upload. The existing `test_nothing_downstream_knows_profiles_exist` keeps it that way. The gate is still run.

---

## 5. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 1 | `created_by` required in `save_version` | yes — closes half of ruling 4 on its own |
| 2 | `confirmations` + `assert_value_mappings_confirmed`, at save and load | yes — closes the other half |
| 3 | `commitGate` block kinds + `MappingPanel` | yes — turns a dead end into an accurate one, with or without the screen |
| 4 | `suggest()` + `config/mapping_aliases.yml` | yes — testable as a pure function before any UI |
| 5 | `build_version`, evidence required at save | yes, and it is the step that makes 6 honest |
| 6 | `GET /uploads/{id}/columns` + the mapping screen + `POST` the profile | the substance |

Steps 1 and 2 are the ones the ruling names. If the cycle is cut, cut from step 6 upward — noting that cutting 6 while keeping 5 leaves **no** way to write a profile, so 5 and 6 are cut together or the CLI fallback in §3.4 lands.

---

## 6. Risks

1. **The affirmation becomes a reflex.** Three columns is few enough that a tick means something; the moment it is asked for everything, it stops being read. This is why 1.4 item 1 recommends *not* extending it to the EXCEPTION enums, and why the wording carries the consequence rather than the mechanism.
2. **Step 5 removes an operator capability before step 6 restores it.** A sequencing risk, not a design one — they must land in the same release, or the CLI fallback must.
3. **Sample values cross the API.** They already cross it inside violation messages, which quote offending values, so this is not a new class of exposure — but it is a new *route* whose entire purpose is to return client data, and it should be reviewed as such rather than as another read endpoint.
4. **The alias table encodes one team's guesses about Arabic HR vocabulary.** Seeded by hand, it will be wrong somewhere. Rung 4 is therefore suggested-not-preselected, and a rejected alias suggestion is recorded — which is how the table gets better rather than staying wrong.
5. **A plausible mis-mapped header stays undetectable** (1.4 item 2). The ladder makes it less likely; nothing makes it visible. Worth stating in the client-facing copy that the mapping is their assertion.

---

## 7. Out of scope

- **TD-007 (RTL)** — the chrome stays English. The mapping screen will be the densest Arabic surface yet built, which strengthens the case for TD-007 next and is not a reason to start it inside this cycle.
- **TD-008 (bilingual Excel template)** — orthogonal. Mapping is the escape hatch that makes TD-008 non-blocking.
- **Auto-growing the alias table from accumulated profiles** — needs more than one tenant.
- **The AI column mapper** (`PRODUCT-ARCHITECTURE` §5) — this cycle produces its training substrate; it does not consume it.
- **Multi-tenancy.** One profile per table, single-tenant, as the rest of the system is.
- **`mart_wps_status`** — still missing, `GET /api/compliance/wps` still 500s. Its own hotfix.

---

**PLAN ONLY. Nothing implemented. Stopping for review.**
