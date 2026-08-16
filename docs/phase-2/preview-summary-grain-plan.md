# The preview summary describes the wrong file — Plan

**Status:** PLAN ONLY. Ruling 4 of the nationality/vocabulary cycle: *"a real UX defect — it reads as failure and an operator would stop. Plan the fix; do not build it this cycle."*
**Found:** during the first real employees preview, 2026-08-16. **Branch when built:** TBD.

---

## 1. What was seen

A preview of a real 105-column export against a saved profile returned, in one response:

```
columns present     : 105
columns missing     : [all 23 canonical columns]
columns unexpected  : 105

mapping applied     : True | version 1
renamed / ignored   : 18 / 87
REJECTs: 3          (none of them required-columns)
```

Every line is true. They are true of **two different files**. The column summary describes the client's export as uploaded; the violations describe the mapped file the validator actually read.

An operator reading top to bottom sees *"none of the 23 columns the contract needs are here"* and stops. The mapping worked.

## 2. Root cause — one variable, read twice

In [data.py:529](../../backend/app/api/data.py#L529):

```python
frame = pl.read_csv(path, ...)
present = list(frame.columns)          # the CLIENT's headers
```

Mapping then runs and writes a separate file:

```python
mapped, mapping_report = mapping_module.apply_profile(frame, table, profile)
validated_path = staging.mapped_path(upload_id)
result = validate_schema.validate_csv(validated_path, table)   # reads MAPPED
```

and the response is built from the stale name ([data.py:594-596](../../backend/app/api/data.py#L594-L596)):

```python
columns_present=present,
columns_missing=[c for c in contracted if c not in present],
columns_unexpected=[c for c in present if c not in contracted],
```

`present` is never rebound. This is not a mapping bug — mapping is correct — it is a **grain** bug: three fields answer a question about the post-mapping frame using the pre-mapping one.

## 3. The same root cause has a second, live consequence

Twenty lines above the summary, `present` is also used to pick the suggested coverage window:

```python
column = {"attendance": "attendance_date"}.get(table)
if column and column in present:
```

For a **mapped attendance upload**, `attendance_date` is not among the client's headers, so the branch never runs and the client is offered **no suggested coverage window at all** — silently, with no message. Attendance is the one table where `coverage_required` is True, so this is the case that needed it most.

Not seen in the wild yet: the real load in flight is employees. It is on the same line of reasoning as §2 and is listed here so the fix covers both rather than being repeated in a month.

## 4. What the fix must NOT do

**Do not just point the three fields at the mapped frame.** The client's own headers are the thing that lets the DQ page speak to a client in their own vocabulary — `back_map` exists for precisely that, and a preview that only ever names canonical columns would undo it.

**Do not drop the pre-mapping view.** *"105 headers arrived, 18 were recognised, 87 were ignored"* is a real and useful statement. The defect is that it is unlabelled, not that it is wrong.

## 5. Proposed shape

Report both grains, each named, rather than one grain wearing the other's label.

| field | grain | when mapping applied | when no profile |
|---|---|---|---|
| `columns_present` | source | client's headers (unchanged) | client's headers |
| `columns_missing` | **canonical** | computed from the MAPPED frame | unchanged |
| `columns_unexpected` | **source** | headers with no decision — i.e. `mapping.unmapped` | unchanged |
| `columns_ignored` *(new)* | source | headers the operator deliberately dropped | `[]` |

Two consequences worth stating in advance:

- With a complete profile, `columns_missing` becomes the short, meaningful list it was always supposed to be — the canonical columns genuinely absent after mapping and shape completion — and `columns_unexpected` becomes **empty**, because a header with no decision already blocks the upload via `mapping_out.unmapped`. The 87 deliberately-ignored headers move to their own field where "ignored" is what they are called.
- **With no profile, every number is exactly what it is today.** That is the compatibility line the fix must hold, and the tamper test that proves it.

The coverage-window lookup in §3 moves to the mapped frame, which is where `attendance_date` lives by definition.

## 6. Where the truth is decided

`apply_profile` already returns everything needed — `renamed`, `ignored`, `unmapped`, `derived`. The fix is to *use* it in the summary rather than recompute from a stale local. No new mapping logic, and no change to the validator.

## 7. Test obligations (SP-001 — both halves)

1. A mapped upload reports `columns_missing` computed post-mapping — **and** an unmapped upload reports exactly what it reports today (the tamper).
2. `columns_ignored` carries the deliberately-dropped headers, and they no longer appear under `columns_unexpected`.
3. A header with no decision still appears under `columns_unexpected` **and** still blocks the commit — the fix must not turn "undecided" into "ignored", which would drop a column silently and is the failure the whole mapping mechanism exists to prevent.
4. A mapped **attendance** upload receives a suggested coverage window (§3) — and an unmapped one still receives the same window it does today.
5. The client's own headers remain reachable for every violation via `back_map`.

## 8. Cost and priority

Small: one endpoint, one response model field, five tests. No contract change, no dbt change, no migration.

**Priority: below the P1 in [nationality-and-vocabularies-report.md](nationality-and-vocabularies-report.md) §2 and above cosmetic work.** It does not corrupt data and it does not block a commit — it causes a *human* to stop when they should proceed, which is a failure of the product's central claim to tell a client plainly what is wrong with their file.

---

**Not built. Awaiting a ruling.**
