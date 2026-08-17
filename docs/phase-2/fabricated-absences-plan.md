# A fabricated absence figure inside the marts — Plan

**Status:** PLAN ONLY. Ruling 5 of the first-real-load cycle: *"the API suppresses it, so it is not client-facing — but the number sits in the mart and a new consumer would read it as real. Plan only, do not build."*
**Found:** during post-commit inspection of the first real load, 2026-08-16.

---

## 1. What is in the mart

The client provided **employees only**. `attendance` was never declared and holds zero rows. `mart_attendance_trend` nonetheless carries a five-figure `absence_days` for the report month, alongside `attendance_compliance_pct = 0.0`.

The magnitude is close to **active headcount × working days in the month**. It is not a partial or stale figure; it is the whole workforce marked absent for the whole month.

## 2. Why it is not client-facing today

`/api/attendance/summary` returns `kpis: null` and names every withheld key in its `suppressed` block, bilingually. The provenance layer suppresses on the `attendance` domain, which was never provided, so no attendance figure reaches a screen. **This is a latent defect, not a live one** — and it is worth stating that the suppression layer did exactly its job.

## 3. Root cause — a calendar that outlives its source

`base_expected_attendance` builds the denominator by construction:

```sql
FROM calendar_dates c
CROSS JOIN {{ ref('base_employees_deduplicated') }} e
WHERE e.status = 'Active' AND ...
```

Every active employee crossed with every working day. `mart_attendance_kpis` then derives absence from expected-minus-actual. With an empty attendance table, **every expected row becomes an absence**, and the figure is arithmetically correct given a denominator that should never have been built.

The coverage machinery exists for exactly this: `attendance_coverage_start/end` make a missing row mean *"absent"* rather than *"not sent yet"*. **The gate is applied to the window, not to the existence of the source.** A client with no attendance file has no window either, so nothing narrowed the cross join.

## 4. Why this is worth fixing despite being suppressed

Three reasons, in order of weight:

1. **Defence is single-layered.** The only thing between this number and a client is the API registry. Add one consumer of `mart_attendance_trend` that forgets a `prov` call and the figure ships. Every other absence surface has the same shape.
2. **It is exactly the fabrication class the phase already ruled against** — `COALESCE(project, 'Unassigned')`, `missing_cost_center_count = 0`, the sentinel bucket named *Missing Cost Center*. The ruling was that the number must not exist, not that it must not be rendered.
3. **It costs compute on a table that should be empty.** A cross join over headcount × days is the largest thing this pipeline builds for a domain the client did not send.

## 5. Proposed shape

Gate at the **source**, matching the `has_cost_center_source_sql` / `has_manager_id_source_sql` precedent now established:

| model | change |
|---|---|
| `base_expected_attendance` | `WHERE {{ var('has_attendance_source_sql') }}` — the cross join produces no rows without a source |
| `build_warehouse.py` | resolve the var from `onboarding.load_declared()`, as `has_locations_source_sql` now does |
| `dbt_project.yml` | default `"TRUE"`, so every existing deployment is unchanged |

Everything downstream then reads zero expected days and produces NULL or empty rather than a fabricated total — no per-mart edits, because the fabrication has exactly one origin.

**Demo must stay byte-identical.** Demo provides attendance, so the var is TRUE and nothing changes. That is the check that this is a gate and not a behaviour change.

## 6. Test obligations (SP-001 — both halves)

1. With attendance undeclared, `base_expected_attendance` is empty **and** `mart_attendance_trend.absence_days` is not a positive number.
2. With attendance declared, the expected calendar is built exactly as it is today — the tamper, without which a gate that always suppressed would pass (1).
3. The demo gate's five pinned figures are unchanged.
4. A test asserting the var is resolved per client in `build_warehouse.py`, not left to the `dbt_project.yml` default — the class `test_dbt_vars` already polices.

## 7. Cost and priority

Small: one model, one var, one resolver line, four tests. No contract change, no API change, no migration.

**Priority: below anything client-facing.** It is invisible today and the suppression layer is doing its job. It should be done before the first client who provides attendance *partially*, because that is when the window gate and the source gate start to interact — and that interaction is the one this plan does not attempt to specify.

---

**Not built. Awaiting a ruling.**
