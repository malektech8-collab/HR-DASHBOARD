# Mapping Profiles — Cycle A (Execution Report)

**Branch:** `phase-2/mapping-profiles` off `main` @ `bc2d7c5` · **Date:** 2026-08-12
**Status:** executed, committed, pushed, PR open. **Not merged.**
**Plan:** [`mapping-profiles-plan.md`](mapping-profiles-plan.md) (approved, six rulings) · **Cycle B** (the mapping screen) is separate

An Arabic HR export now goes through stage → preview → declare → commit. Before this it hard-rejected on Rule 2 with no sanctioned way forward.

---

## 1. Proof (a) — a violation names the client's column and row

The fixture is a real export *shape*: **24 headers** — every contract column under its Arabic label from `name_ar`, plus a free-text `ملاحظات` and an empty `Column14` — with deliberate messiness (a trailing space, `الجنسيه` with ta-marbuta→ha, and a `0025-02-11` corrupted date serial).

**Without a profile**, the file behaves as it does on main:

```
mapping applied : False
can_commit      : False
first reject    : required-columns | [employees] missing required column(s) …
```

**With a profile:**

```
mapping applied : True | version 1
renamed         : 22 columns
ignored         : ['ملاحظات', 'Column14']
derived         : ['is_saudi']
unmapped        : none
rejects         : 1
   canonical : joining_date   row 3
   CLIENT'S  : تاريخ الانضمام  <- what they actually wrote
   message   : Row 3, Joining Date: date '0025-02-11' is outside the plausible ra…
```

The validator stays **canonical-only** — it reported `joining_date` and knows nothing about mapping. The translation happens at the edge, in `_violation_out(v, back_map)`, and `source_column` is one field on `ViolationOut`.

Row 3 is the client's own row: mapping renames and derives, never filters, reorders or deduplicates. A test asserts row count *and* row identity, because a row number that silently shifts would point every violation at the wrong record.

**The error report leads with their header.** Columns are now `severity, row, your_column, canonical_column, rule, message_en, message_ar`, and the by-column grouping groups by the client's header — they scan by the name they wrote.

---

## 2. Proof (b) — the PII rule holds under test

What the profile actually persisted, read back off disk:

```
vocabulary kept : True    ("نشط" — the status values)
names kept      : False
name column     : {'kind': 'redacted', 'dtype': 'string', 'cardinality': 3,
                   'length_range': [2, 2], 'pattern': 'A9'}
```

Enforced at the write by `mapping.assert_no_pii`, which **refuses** the save and leaves nothing on disk. Three tests: verbatim values survive for a vocabulary column, are absent for a name column, and a profile that tries to smuggle names in is rejected.

**`PRODUCT-ARCHITECTURE` §4 is corrected in place**, with the original wording recorded beside it. §4 said to record *"verbatim source headers, sample values, derivations…"* without qualification. Sample values from an HR export are client PII, and a mapping profile is by design the longest-lived object in the system — accumulated, reused, eventually fed to a model.

The correction is not a reduction in training signal, which is why it is a correction and not a compromise: for a **vocabulary** column the values *are* the signal and are vocabulary, not people; for a **name or salary** column the header is the signal and the values add nothing the shape does not already carry.

---

## 3. Proof (c) — the mapped file revalidates through the unchanged ingest path

```
5. commit a CLEAN export
   rejects         : 0 | can_commit: True
   status          : 200
   pipeline        : success in 27.3s
   data/raw header : employee_id,employee_name,nationality,company,department,…
   -> canonical    : True   <- ingest_raw revalidated it unchanged
   employees rows  : 3
   is_saudi        : [(False, 1), (True, 2)]
   status          : [('Inactive',), ('Active',)]
```

`data/raw/employees.csv` contains **no non-ASCII byte** — it is fully canonical, and `ingest_raw` validated it a second time without knowing a profile exists. `is_saudi` was derived from `الجنسيه` through the existing registry, and `نشط`/`موقوف` became `Active`/`Inactive`.

A structural test asserts `ingest_raw`, `build_warehouse` and `validate_data` never import `mapping`. **Profiles are upload-time only**, which is what keeps P0-2's single ingest path intact.

---

## 4. Value mapping and the REJECT enums

```
unmapped_values : {'status': ['معلق', 'منتهي']}
options offered : ['Active', 'Inactive', 'Terminated', 'On Leave']
can_commit      : False   <- a task, not a dead end
```

Per ruling 4, an unmapped value in a REJECT enum arrives as a **mapping task with the canonical options listed** — not a bare rejection sending the client back to Excel to rename a word the product could learn once. `reject_enum_columns()` derives the list from `on_violation`, so it stays right if a contract changes.

Matching runs after normalisation, so `نشط ` and `نشط` need one entry, and `الجنسيه` matches the canonical `الجنسية`. `_normalise` was **promoted to `scripts/text.py`** and is now shared by nationality derivation, header matching and value matching — one implementation, three callers.

Attribution is on the version (`created_by`, `created_at`), and versions are **append-only**: without that history nobody could say which mapping produced last month's numbers.

---

## 5. No eval

A profile names a rule; `derivations.resolve()` raises on anything not in `REGISTRY`. On top of that, `load_profile` **walks the parsed YAML and refuses anything expression-shaped** — `lambda`, `__`, `eval`, `import`, `os.`, `sys.` — rather than trusting that nobody will try. Four parametrised tests, one per payload.

> A small illustration that landed during the work: my first evidence format used the sentinel `"__ignored__"`, and the module's own dunder guard rejected it. Replaced with an explicit `decision: mapped | ignored | undecided`, which is better modelling anyway — a magic string is not a data model.

---

## 6. Cycle B's inputs are settled

Recorded in the plan §5, per ruling: the suggestion ladder (canonical key → `name_ar`/`name_en` → normalised → alias table → human), with `matched_by` and `confidence` captured on every rung. **The manual UI is the data collection** — every human decision, including the rejected candidates, becomes labelled training data for §5's AI mapper.

Evidence round-trips through save/load with `rejected` intact, tested. That is the part that cannot be reconstructed later, which is why it was built before value mapping per ruling 5.

---

## 7. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 158/158, 11/11, PASSED |
| Violation names the client's column | `تاريخ الانضمام`, row 3 |
| PII rule | vocabulary kept, names redacted, write refused on violation |
| `data/raw` after commit | canonical, no non-ASCII; pipeline 200 in 27.3s |
| Nothing downstream imports `mapping` | asserted |
| pytest | **251 passed** (227 + 24 new) |
| vitest | **62 passed** (58 + 4 new: the error report and by-column view under a mapping profile) |
| `tsc -b` / `npm run build` | 0 errors / passes |

---

## 8. Open

1. **Cycle B — the mapping screen.** 24 headers here; a real export is nearer 37. The suggestion ladder is designed and the format supports it.
2. **A profile can only be written by hand or by a script.** There is no API to create one — deliberate for cycle A, and it is what "a technical operator completes the first real load" means in practice.
3. **`source_fingerprint` is computed and surfaced as `header_changed`, but nothing acts on it.** The preview reports it; deciding what to *do* when an export's headers change belongs with the screen that can ask.
4. **One profile per table, single-tenant**, as the rest of the system is.
5. **TD-008 (the bare-headers template) is now sharper**, not softer: a client who cannot fill the template is exactly the client who needs a mapping profile, and both cycles are still open.

---

**Not merged. Awaiting review.**
