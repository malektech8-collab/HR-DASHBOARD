# P0-3 Step 2b — Suppression (Execution Report)

**Branch:** `phase-2/p0-3-step-2b` off `main` @ `faf6555` · **Date:** 2026-08-11
**Status:** executed, committed, pushed. **Not merged.**
**Prior:** [`p0-3-step-2a5-report.md`](p0-3-step-2a5-report.md) (merged `7dc423b`) · **Plan:** [`p0-3-mart-fabrication-plan.md`](p0-3-mart-fabrication-plan.md)

Step 2a mapped every mart to its source domains. **Step 2b makes the mapping do something:** a figure whose domain the client has not provided is no longer served.

---

## 1. Category F rulings recorded first

Committed separately (`5505304`) so the step after 2b starts from settled semantics: trend depth is three points with nulls; `headcount_months` is derivation rather than fabrication **on condition that periods before the client's earliest data emit `NULL`, not `0`** — zero asserts "nobody worked here", null says "we don't know"; and partial-period coverage is **declared** per upload, never inferred from `MIN`/`MAX(attendance_date)`.

`base_expected_attendance` is carved out of that step and recorded as a **Phase 2 blocker** — fabricated absences feed Article 80 dismissal grounds and payroll deduction, so they are a harm vector rather than a chart defect.

---

## 2. The substrate — one question, answered where the pipeline already answered it

The suppression layer has to know *"was this domain provided?"* on every request, and it has to get the same answer the pipeline got. It cannot read `data/onboarding/declared_domains.yml` — different image, different volume — and re-deriving provided-ness from row counts at request time would be exactly the inference this design has refused twice.

So `build_warehouse.py` writes it into the warehouse the API already reads:

```
domain_provenance(domain, kind, declared, row_count, provided)

('employees',   'contracted',   True,  21, True)     demo
('recruitment', 'uncontracted', False, 32, True)
```

In real mode a contracted domain is provided **iff it was declared** — never iff it has rows. The declared-domain guard has already made those agree or aborted, which is precisely what lets a zero be attributed to "not uploaded yet" instead of to a load that silently dropped every row.

**The 16 uncontracted tables are never provided in real mode.** They have no contract, so they always load from `data/sample`. That is the module gating: `recruitment` and `talent` gate off as a consequence of the substrate, not as a special case — **26 marts** suppress through the ordinary rule.

*Correction to the plan: it says 15 uncontracted tables. Counted from the registry, which covers every silver table without a contract, it is **16** (recruitment 7 + talent 9). A test pins the count.*

---

## 3. The dependency — `backend/app/api/_provenance.py`

One rule: **a mart may be served only if every domain it depends on was provided.** Three call-site methods, and every `False` also records *why*:

```python
prov.payload(mart)         # may the rows be served at all?
prov.column(mart, column)  # may this one column be served?
prov.rows(mart, loader)    # the rows, or None
```

Four properties that are easy to get wrong one endpoint at a time, so they live here:

**A suppressed mart is never queried.** `rows()` takes a callable. The fabricated rows are not produced and discarded — they are not produced. Anything that merely filters a result keeps the fabricator one refactor away from emitting it.

**KPI cards are factories, not values.** `prov.kpis(mart, [(column, factory)])` builds only the cards it may serve, so `round(rate * 100, 2)` and `value > 0` never run against a NULL or fabricated figure.

**Default-deny.** An unmapped mart or column is suppressed, with reason `not_mapped`.

**`@suppressible(ResponseModel, mart)`** gates a payload endpoint before the handler runs and attaches the sibling block on the way out, so a handler cannot forget it. The marts are declared per route rather than sniffed from the SQL — inference is what fails silently when someone adds a second mart to a handler.

---

## 4. The sibling block

A null with nothing beside it is indistinguishable from a bug, and a client who cannot tell those apart will ask for the number to be "fixed" — which is how a fabricated number gets restored. So every response carries:

```json
{"key": "absence_days", "mart": "mart_attendance_kpis",
 "missing_domains": ["attendance"], "reason": "not_provided",
 "message_en": "Not yet provided: Attendance.",
 "message_ar": "لم يتم تقديم البيانات بعد: الحضور."}
```

**72 of 78** endpoints carry the block. The six that do not are the meta endpoints and `/api/data/*`, which serve no mart.

---

## 5. `null`, never `[]` — including a violation this cycle's own rig caught

The measurement held exactly: **77 containers + 33 scalars = 110**, across 9 schema files, matching 2a.5's prediction to the field.

**Plus five the sweep missed.** `WorkforceDistributionResponse` carries five `CategoryDistribution` fields — five charts from one payload-mode mart — which are a nested model rather than `List[...]`, so neither the 2a.5 counter nor the 2b sweep saw them. They suppress together. **115, not 110.**

**And a genuine ruling violation.** The first implementation returned `kpis: []` when every card on a strip was suppressed:

```
before: /api/attendance/summary -> kpis: []      <- "this module has no KPIs"
after : /api/attendance/summary -> kpis: null    <- "not yet provided: Attendance"
```

Found by the real-mode rig in §7, not by review. `[]` on a KPI strip makes the same claim an empty chart makes. A *partial* strip is still a list — the missing cards are named in the block — but an all-suppressed strip is `None`. Pinned by `test_a_fully_suppressed_kpi_strip_is_none_not_an_empty_list`.

---

## 6. Frontend

`types.ts`: **75 array fields** became `T[] | null` and 72 response interfaces gained `suppressed?`. That is deliberate — the compiler is what forces every call site to decide what to draw instead of a number. It produced **131 errors**, which is the honest size of the problem.

`NotProvided.tsx` renders what goes in a chart's place: which domain is missing, that it is missing rather than empty, and the withheld figures by name. Nine pages bind their nullable containers to locals and guard, so nothing below can draw a zero.

**Scope I chose, stated plainly:** the guard is **page-level**, not per-section. When any domain a page needs is absent, the whole page renders the notice rather than a mosaic of half-drawn charts. During onboarding a module is usually missing all at once, so this is the better reading — but it is coarser than per-section suppression, and a page mixing a provided and an unprovided domain will hide charts it could have drawn. Per-section refinement is follow-up work; it is a UX improvement, not a correctness gap, because nothing fabricated renders either way.

`tsc -b`: **0 errors.** `npm run build`: passes. `ExceptionTable` now accepts `null` — an empty table would tell a client their data is clean.

---

## 7. The proof — real mode, `declared: [employees]`, all 78 endpoints

```
still computed in the warehouse : absence_days=513.0, exceptions=765

served by /api/attendance/summary : kpis = null
   - absence_days               Not yet provided: Attendance.
   - attendance_compliance_pct  Not yet provided: Attendance.
   - attendance_exception_count Not yet provided: Attendance, Payroll.

served by /api/workforce/summary  : 9 KPI cards, 1 suppression
   + active_headcount     19      + saudization_rate      52.63
   + saudi_headcount      10      + probation_count        0
   + non_saudi_headcount   9      + contract_expiring_30   0
   + missing_manager_count 2      + missing_project_count  1
   + missing_cost_center_count 1
   - iqama_expiring_30            Not yet provided: Compliance.
```

**The 513 is still computed and no longer served.** That is the whole step in one line — and note the mart-layer fabricator is untouched, which is why `base_expected_attendance` is a separate Phase 2 blocker rather than something 2b closed.

| | count |
|---|---|
| served in full | 16 |
| withheld, with the reason named | 59 |
| empty list where null is required | **0** (was 5) |

`/api/workforce/summary` is the case worth reading twice: nine real figures from real employee data, one suppressed because it needs compliance, and the reader is told which. That is the product working during onboarding rather than waiting for it to finish.

**Two things the rig flags that are not suppression:**

- `/api/command-center/filter-options` returns `locations: []` — the sample has no locations. This mart is `domains: []` (navigation metadata, never suppressed), so the empty list is a real property of the data, not a suppressed payload.
- `/api/compliance/wps` still returns **500**. Deliberate: `mart_wps_status` does not exist, so default-deny would have turned the 500 into a tidy null payload and quietly repaired the symptom of a defect that has an open hotfix. It keeps failing loudly.

---

## 8. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 157/157, 11/11, PASSED |
| Demo API byte-identity | **78/78 endpoints identical** ignoring `suppressed` + timestamps; only `/openapi.json` differs |
| Suppressions in demo | **0** — everything is provided, so nothing withholds |
| Optional response fields | **115** (77 + 5 containers, 33 scalars) |
| Endpoints carrying the sibling block | 72 |
| Marts the layer can decide on | 76 |
| Uncontracted marts gated in real mode | 26 |
| `tsc -b` / `npm run build` | 0 errors / passes |
| pytest | **144 passed** (122 + 22 new) |

---

## 9. Open

1. **`base_expected_attendance`** — Phase 2 blocker (§1). Suppression hides the 513 from the API; the model still computes it, and it still inflates `total_active_exceptions` and the DQ score.
2. **Step 3** — dbt model gating; **step 4** — `data_quality_score` rescoping and the `scope_to_provided` filter, which 2b deliberately passes through.
3. **Per-section frontend suppression** (§6).
4. **`mart_wps_status`** — still its own hotfix, still failing loudly on purpose.

---

**Not merged. Awaiting review.**
