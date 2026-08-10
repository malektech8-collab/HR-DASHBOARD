# P0-3 Step 1 — Metric Provenance Registry (Execution Report)

**Branch:** `phase-2/p0-3-mart-fabrication` off `main` @ `de8efc7` · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.**
**Plan:** [`p0-3-mart-fabrication-plan.md`](p0-3-mart-fabrication-plan.md)
**Scope:** step 1 only — registry and tests. **No behaviour change.** Steps 2–4 not started.

---

## 1. Rulings applied

| # | Ruling | Applied |
|---|---|---|
| 1 | `data_quality_score` → scope, don't suppress | `scope_to_provided: true` on all three copies. A test pins the set so the exception cannot spread silently. The dbt rescoping is step 4. |
| 2 | New `config/metric_provenance.yml` + consistency check | Created. Consistency test asserts no metric declares source domains in both files. |
| 3 | Fix the model too, second, not naively | Step 3. Not started. The trap is recorded in the plan. |
| 4 | Gate exception rows **and** cover the counts | Both halves mapped: `*_exception_count` columns carry provenance; dbt gating is step 3. |
| 5 | **Measure** the Pydantic change | Measured — **182 fields**, see §5. |
| — | Add the exit criterion to `PRODUCT-ARCHITECTURE.md` | Done, §6. |

---

## 2. The registry

`config/metric_provenance.yml` — **102 columns across 10 KPI marts**, every one mapped.

```
mart_attendance_kpis          10      mart_er_kpis                  11
mart_command_center_overview  12      mart_exec_kpis                 9
mart_compliance_kpis          11      mart_payroll_kpis             10
mart_data_quality_summary      7      mart_recruitment_kpis         11
mart_talent_kpis              11      mart_workforce_kpis           10
```

Domains are split into **contracted** (six, gated by the declared-domain registry) and **uncontracted** (`recruitment`, `talent` — the 15 tables with no contract, gated at module level per ruling 2 of the P0 plan). The contracted half is asserted equal to `data/contracts/` so the two cannot drift.

### Mappings worth calling out

**Cross-domain columns — the reason this is per-column, not per-mart:**

| Column | Domains | Why |
|---|---|---|
| `mart_exec_kpis.active_headcount` / `.payroll_cost` | `[employees]` / `[payroll]` | one row, two provenances — the case that rules out mart-level mapping |
| `mart_workforce_kpis.iqama_expiring_30` | `[employees, compliance]` | **LEFT JOINs `stg_compliance`** — verified at `mart_workforce_kpis.sql:18`. A workforce metric that silently depends on the compliance feed, exactly as `DECISIONS.md` #5 describes |
| `mart_attendance_kpis.attendance_compliance_pct` | `[attendance, employees]` | the denominator is the expected-workday calendar, which is employees × dates |
| `mart_attendance_kpis.overtime_cost` | `[attendance, payroll]` | reconciles attendance OT hours against *paid* OT cost |
| `mart_compliance_kpis.saudi_headcount` | `[employees]` | on a compliance mart, but sourced from employees — mapping by mart would have got this wrong in the opposite direction |

**Multi-source means all-required.** A partially-sourced metric is not a real one, so any absent domain suppresses.

**`domains: []`** marks the four genuinely source-free columns — `report_month`, `modules_healthy`, `last_data_refresh`, `latest_source_business_date`. A test pins that exact set, because each one bypasses suppression by design.

---

## 3. CI test proof — add a column, watch it fail

`backend/tests/test_metric_provenance.py`, 8 tests. Coverage is read **from the built warehouse**, not parsed from SQL, so it cannot drift from what the API actually queries.

An unmapped column was added to a KPI mart and the warehouse rebuilt:

```
added: unmapped_probe_metric   ->  mart_workforce_kpis
warehouse rebuilt (exit=0)

E  AssertionError: unmapped KPI mart column(s) — add them to
   config/metric_provenance.yml with their source domains:
E      mart_workforce_kpis.unmapped_probe_metric
1 failed, 7 passed
```

Probe reverted, warehouse rebuilt, **8 passed**. The failure names the exact column, which is the intended workflow: a new metric fails CI at the moment it is added, rather than appearing as a blank on a dashboard weeks later.

The other seven tests: no stale entries for columns that no longer exist; every referenced domain is declared; the source-free set is exactly those four; `scope_to_provided` is exactly the four ruled metrics; registry shape; contracted domains equal the contracts directory; and the dictionary consistency check.

---

## 4. Consistency with `metrics_dictionary.yml`

The two files have different key spaces — `metrics_dictionary.yml` is keyed by global business metric name for a curated subset; this one by mart → column for every KPI column.

The check asserts that no name appearing in both declares source domains in `metrics_dictionary.yml`. It carries none today, so the test currently guards the invariant rather than resolving a conflict: **it fails the day someone adds a `domains:` or `source_domain:` key there instead of here.** Provenance has one home.

---

## 5. Pydantic measurement (ruling 5)

Static analysis of every `BaseModel` in `backend/app/schemas/`:

```
response model classes scanned            : 128
NON-OPTIONAL NUMERIC FIELDS TO CHANGE     : 182
schema files affected                     : 9 of 10

payroll.py       32     er.py            21     command_center.py  15
attendance.py    30     recruitment.py   21     kpi.py              8
talent.py        29     compliance.py    18     workforce.py        8
```

### The number reveals a scoping question for step 2

**182 non-optional numeric fields, but the registry covers 102 KPI columns.** The gap is not slack — it is a different surface.

The registry covers KPI marts. The 182 include `AttendanceTrendItem`, `AttendanceByProjectItem`, `AttendanceByDepartmentItem` and their equivalents across every domain: the **trend and breakdown endpoints**. Those marts fabricate exactly as the KPI marts do — a by-project attendance breakdown over an empty attendance table returns a row per project with zeros, and a trend returns a series of them.

So step 2 needs a decision that step 1 has now made concrete:

- **(a) Extend the registry to every mart the API serves**, not just KPI marts. Complete, and larger — the coverage test would need to enumerate every mart behind an endpoint rather than the 10 KPI ones.
- **(b) Suppress at KPI level first**, accepting that trend and breakdown endpoints still return fabricated zeros in the interim.

**Recommend (a).** A client reading `absence_days = 0` on a per-project breakdown is misled the same way as on the KPI card, and (b) leaves the CSV export — the consumer that motivated API-layer suppression — still exporting fabricated series. But it roughly doubles step 2, and that is the architect's call, not mine to assume.

This is the value of "measure, don't estimate": the estimate would have been "make the KPI fields Optional", and the measurement says the real surface is 1.8× that and spans a category of endpoint the plan had not named.

---

## 6. `PRODUCT-ARCHITECTURE.md`

Phase 2's exit criterion now reads *"Real workforce, Saudization, and payroll figures rendering correctly — **and no metric rendering at all when its source data is absent**"*, with a dated paragraph recording the measured `494` / `19` / `100.0` evidence and why suppression belongs at the API layer.

---

## 7. Verification

| Check | Result |
|---|---|
| Registry coverage | **102 / 102** KPI mart columns mapped |
| Coverage test fails on an unmapped column | **proven** — added, failed by name, reverted, green |
| Consistency check | passes; guards the invariant |
| Contracted domains == `data/contracts/` | asserted |
| Pydantic measurement | **182** fields, 128 models, 9 files |
| pytest | **67 passed** (59 + 8 new) |
| Demo | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 157/157, 11/11, reconciliation PASSED |
| Behaviour change | **none** — no application code touched |

Nothing outside `config/`, `backend/tests/` and `docs/` was modified. No client data; the probe used a literal `999`.

---

## 8. Open for step 2

1. **Registry scope** (§5) — every mart the API serves, or KPI marts first? Recommend the former.
2. `total_active_exceptions` carries `scope_to_provided: true` rather than a plain domain list, because summing exception rows across modules makes it meaningless to suppress outright but wrong to leave whole. Worth confirming that is the right treatment.
3. Ruling 3's trap applies to more than attendance: any ungrouped aggregate returns one row of defaults when gated to zero rows. Step 3 should sweep for that shape rather than fixing `base_expected_attendance` alone.

---

**Not merged. Awaiting review.**
