# Organisational Dimensions — Execution Report

**Branch:** `phase-2/org-dimensions` off `main` @ `e88db9a` · **Date:** 2026-08-13
**Plan:** [`org-dimensions-plan.md`](org-dimensions-plan.md) (approved, three corrections adopted) · **Status:** PR open, **not merged**

---

## 0. Step 0 — the blocking question, answered before anything was built

`locations` is the first contracted table with no `employee_id`. If the guard machinery assumed employee grain, the cycle's shape changed.

**17/17 clean, re-run 18/18 after cycle B merged.** Probed with a throwaway contract in a temp directory; nothing in the repo was touched.

```
canonical_schema  discovered, columns load, bilingual labels resolve
validate_schema   clean file passes; duplicate PRIMARY KEY rejects on `location`,
                  not employee_id; missing required column rejects
empty_frame_schema  typed empty frame builds on a VARCHAR key
declared/populated  declared+populated passes; declared+EMPTY still aborts
                  naming locations; neither DATE_GRAINED nor HISTORY_DECLARING
mapping           ladder: الموقع -> location (label_exact),
                  المشروع -> project (label_exact); no REJECT enums;
                  value_profile redacts a non-vocabulary column
hand edits        ingest_raw file map (1 entry), build_warehouse path map
                  (1 entry). validate_data is per-table, not a generic loop.
```

**Note (a), recorded where someone generalising would look.** The last line is *why* there was no assumption to break, and it is a constraint that happens to hold rather than one that is enforced. A grain note now sits at the top of `scripts/validate_data.py`:

> The moment this becomes `for table in contracted_tables()`, that stops being true and `locations` (and any future reference dimension) starts being fed to checks that assume a per-employee grain. The guard machinery in `scripts/onboarding.py` IS grain-agnostic and was verified as such; this module is not, and only escapes the question by not asking it.

---

## 1. What shipped

**`project` was renamed, not extracted.** The employees contract already published that `project` meant the site — `work_unit`'s own description said *"the location (the `project` column) is the physical site"*. So no employee's site assignment moved. What is new is the grouping *above* the site, which now lives in `locations` and nowhere else.

**Facts keep their own location** (correction 1, adopted). All four contracts — employees, payroll, attendance, hr_requests — carry `location`. A test pins that none of them carries `project`, and that only `locations` does.

**All seven by-project marts moved** (correction 2, adopted), including the three reading uncontracted domains, so the day `talent` and `recruitment` get contracts is a no-op.

**Department is orthogonal and `work_unit`'s description is corrected in place** (correction 3, adopted), with the original quoted inside the replacement so the correction stays checkable. A test asserts the wrong text is still there beside the right one.

### The seam

`base_row_project` answers one question — *what project is this row in?* — and is the only place it is answered. Resolution happens at the **staging boundary**, so all 33 downstream models that name `project` are correct by construction rather than by 33 edits and a hope.

This is what keeps matrix assignment additive: it becomes a second branch in one model, and the marts do not move again. Repeating the join in seven marts is what would have precluded it.

`LEFT JOIN`, deliberately: a row whose site is absent from the reference file **keeps its row and its measures** and gets `project = NULL`. It counts in every total, is excluded from the project breakdown, and `mart_unmatched_locations` names the sites to add. Dropping the row would silently change a headcount — a worse failure than the one being fixed.

---

## 2. A real defect, found on the first run

The demo payroll fixture had EMP011's site column set to **`CC-HR`** — a *cost centre* — contradicting the same employee's `PROJ-ALPHA` in the employees fixture.

```
base_payroll_current, before the fixture was corrected:
    ('EMP011', 'CC-HR', None, 'PROJ-ALPHA')
                ^site   ^project resolved: NOTHING

mart_unmatched_locations:
    ('CC-HR', 'payroll', 'Missing Location')
```

The old schema treated whatever string sat in that column **as the project**. So `mart_payroll_by_project` has been reporting a project called `CC-HR` that never existed, and nothing could notice, because there was nothing to check the value against.

This surfaced as `payroll|Missing Project` going 2 → 3 in the exception breakdown — a delta I chased to its row rather than accepting. The fixture is corrected to the employee's real site; the mechanism that caught it is covered by test. **This is the defect class the cycle exists to remove, demonstrating itself on the first run.**

---

## 3. Demo byte-identity — NOT structural this cycle

Stated plainly, per ruling: **this cycle changes the pipeline.** Unlike the mapping cycles, byte-identity here is not a property of the design; it holds only because the migration was built to make it hold.

**The §5.1 invariant:** for every fact row, `locations[row.location].project` equals the value that row's `project` column held before.

The demo satisfies it by an **identity mapping** — each site maps to a project of the same name — so every `GROUP BY` key downstream is unchanged.

```
GATE: (19, 446175.0, 50.0, 667, 15)   BYTE-IDENTICAL: True
dbt 161/161 · dbt test 11/11 · reconciliation PASSED

Exception breakdown, diffed row-by-row against a baseline captured from a
stashed working tree:
  data-quality|Missing Location   0 -> 1
  data-quality|Missing Project    1 -> 0
  totals: 667 -> 667
```

The single delta is one label, `Missing Project` → `Missing Location` — the rename reaching the place it should. Every other one of the 100+ issue-type buckets is unchanged.

**The cost of the identity mapping, stated rather than hidden:** the demo does **not** exercise a real rollup. That is why §4 exists.

---

## 4. The real-hierarchy fixture

`backend/tests/test_org_dimensions.py` — 15 tests on a fixture warehouse built with the models' own SQL shapes: 4 sites, 2 projects, one site belonging to no project, one site used in the data but absent from the reference file.

| | |
|---|---|
| `several_sites_roll_up_into_one_project` | RUH-P1 (2) + RUH-P2 (1) → `Riyadh Tower` 3 |
| `a_site_with_no_project_has_no_project` | `HQ` → `NULL`, not a bucket called `Unassigned` |
| `an_unmatched_site_keeps_its_row_and_its_measures` | 6 rows in, 6 rows out |
| `the_unmatched_site_is_reportable_by_name` | `YANBU-9` |
| `project_totals_exclude_the_unmatched_but_headcount_does_not` | headcount 6, in-project 4 |
| `a_department_spans_projects_and_stays_one_department` | Safety at 3 sites, 2 projects → **1** department |

The last one is the adopted correction as an executable claim: under the nested reading the contract asserted until this cycle, that would have been three departments.

---

## 5. The client-facing warning

Effective-dated locations are out of scope, which means **re-assigning a site re-groups months already reported**. Per ruling, that travels with the template, not only the plan:

> **IMPORTANT** — this file records the CURRENT assignment of each site, and it has **no history**. If a site moves to a different project, re-uploading this file re-groups EVERY period, including months already reported. A figure you published last month can change. If you need a site's history preserved, tell us before you re-assign it — effective-dated locations are not yet supported and there is no way to recover the previous grouping afterwards.

Bilingual, on the contract; served through `describe()` and `GET /api/data/templates`; rendered in the onboarding UI beside the template download, in a warning box rather than as body text. Pinned by test in both locales.

---

## 6. Note (b) — which quoted gate lines can actually go red

Applying the §4.1 lesson to the figures this project has forwarded every cycle. One probe each, every tamper reverted.

| Quoted line | Verdict |
|---|---|
| `dbt 158/158` | **Half real.** A model that cannot compile → dbt exit 2, and `refresh_all` calls it with `check=True`, so the pipeline aborts. **The count is asserted by nothing** — a deleted model would report 157/157 and be green. |
| `dbt test 11/11` | **Half real.** A `not_null` test on a nullable column → dbt exit 1. The count is again unasserted. |
| `reconciliation PASSED` | **8 of its 11 checks are tautologies.** See below. |
| `667 exceptions` | **Habit.** Nothing in the repo or CI asserts it. |
| `19 / 446175.0 / 50.0 / 15` | **Habit.** The one grep hit is `test_suppression.py` using `446175.0` as a literal *input*, not a pin. |

### The reconciliation finding

I tampered `mart_workforce_kpis.active_headcount` with `+ 1` and the pipeline stayed **green**. The tamper provably applied (asserted in the probe). The reason:

```python
# scripts/build_warehouse.py
418:  cc_active_headcount = SELECT active_headcount FROM mart_workforce_kpis   # WRITE
431:  INSERT INTO command_center_overview_data VALUES (cc_active_headcount, ...)
...
439:  kpi_hc = SELECT active_headcount FROM mart_command_center_overview       # read back
440:  ref_hc = SELECT active_headcount FROM mart_workforce_kpis                # same source
441:  if kpi_hc != ref_hc: raise ValueError(...)
```

**The overview table is populated FROM the marts the checks then compare it against, fifteen lines earlier, in the same connection.** Checks 1–8 compare a value with the source it was copied from. They cannot fail. Checks 9–11 (registry / freshness / navigation = 9 rows) assert constants against independent tables and are real.

So "Command Center integration reconciliation checks PASSED" means *three* things were verified, not eleven. It has been quoted as a gate in every cycle report including mine.

**Not fixed here** — no tooling built, per instruction. Recommended as its own small cycle: the checks want independent recomputation (count from `base_active_workforce` rather than re-reading `mart_workforce_kpis`), and the five demo figures want a single pytest that queries the warehouse CI already builds. That test is ~15 lines and would have made this cycle's byte-identity claim enforced rather than hand-computed.

---

## 7. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — **identical**, diffed per issue-type against a stashed-tree baseline |
| dbt | **161/161** models (158 + `stg_locations`, `base_row_project`, `mart_unmatched_locations`), 11/11 tests |
| pytest | **309 passed** (294 + 15 new) |
| vitest | 94 passed |
| `tsc -b` / `npm run build` | 0 errors / passes |
| flake8 | CI selection 0; every changed file reports the same count as `main` |

---

## 8. Open

1. **The `'Unassigned'` / `'Missing Project'` sentinels are still in the marts.** `mart_unmatched_locations` is built and reports the sites by name, but the seven marts still `COALESCE` a NULL project into a bucket. Removing them changes what a client sees on a screen they already use — the plan flagged this as a product change, not a refactor — and it would move demo mart payloads. **Deliberately not done; it needs the copy owner.**
2. **Effective-dated locations (SCD Type 2).** Out of scope, warned about in §5, same shape as matrix assignment; they should be done together.
3. **The reconciliation tautology** (§6) — diagnosed, not fixed.
4. **The five demo figures are still unasserted** (§6). This cycle's own byte-identity claim rests on a hand-run script.
5. **`work_unit` still has no consumer**, as recorded in its corrected description. `end_of_service_type` likewise — Article 80 exposure is a Phase 2 selling point that nothing computes.
6. **`mart_wps_status`** still missing; `GET /api/compliance/wps` still 500s.

---

**Not merged. Awaiting review.**
