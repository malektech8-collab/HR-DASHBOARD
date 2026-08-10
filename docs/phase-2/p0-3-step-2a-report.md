# P0-3 Step 2a — Registry Extended to the Full API Surface (Execution Report)

**Branch:** `phase-2/p0-3-step-2a` off `main` @ `4142c62` (step 1 merged) · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.**
**Plan:** [`p0-3-mart-fabrication-plan.md`](p0-3-mart-fabrication-plan.md) · **Prior:** [`p0-3-step-1-report.md`](p0-3-step-1-report.md)
**Scope:** step 2a only — registry, modes, tests, measurement. **No behaviour change; no application code touched.** Steps 2b–4 not started.

---

## 1. Step 1 merged

```
mergeCommit: 4142c62f9617ce0bc353de069a960e86ab21f36f
mergedAt:    2026-08-10T13:25:24Z
```

Pre-merge items landed first (`4d236e2`): every `domains: []` must carry a same-line reason, enforced by a raw-text parse and proven by removing the comment from `report_month` and watching it fail at line 75; both coverage tests print the count.

---

## 2. The extended registry

`config/metric_provenance.yml` v2 — **76 API-served marts**, up from 10.

```
[provenance] 76 API-served marts mapped (10 column / 66 payload),
             102 columns, 5 source-free
```

Coverage is derived from the **router source** (`FROM mart_…` / `FROM base_…` across `backend/app/api/`), not from a naming convention. The API is the surface that must never emit a fabricated number, so the API defines what must be covered.

### How domains were assigned

Hand-mapping ~70 marts would have been guesswork, so payload-mode domains are resolved from the **dbt ref graph**: every model's transitive refs terminate at `stg_<table>`, and each source table belongs to exactly one domain. Column-mode mappings stay hand-authored, because per-column reasoning is precisely what a dependency graph cannot infer.

---

## 3. Mode assignments

Declared explicitly per mart, never inferred. **18 of the 77 API objects are single-row on demo data**, but several only by accident — `mart_attendance_late_arrival` has one row because the sample contains one late arrival. Any runtime heuristic would misclassify them, which is why the ruling forbade inference.

**`mode: column` — 10 marts.** Reserved for a single row whose columns have *different* provenance:

`mart_exec_kpis`, `mart_workforce_kpis`, `mart_payroll_kpis`, `mart_attendance_kpis`, `mart_compliance_kpis`, `mart_er_kpis`, `mart_recruitment_kpis`, `mart_talent_kpis`, `mart_data_quality_summary`, `mart_command_center_overview`

A test enforces the reservation: a column-mode mart whose columns all share one domain set fails, because the distinction would otherwise stop meaning anything.

**`mode: payload` — 66 marts.** Everything else, including single-row breakdowns whose columns share one domain set. The rows themselves are fabricated when a domain is absent, so the payload goes as a unit.

### Non-obvious assignments, with reasoning

| Mart | Mode | Why |
|---|---|---|
| `mart_workforce_contract_expiry` | payload | single-row, but it is an aging *distribution* — the buckets are one artefact, and all columns share `[employees, payroll]`. Column mode would add nothing |
| `mart_attendance_late_arrival`, `mart_onboarding_status` | payload | single-row **on sample data only**; they emit a row per entity |
| `mart_command_center_filter_options` | payload, `domains: []` | dropdown values. Suppressing them would break navigation rather than protect a number |
| `base_command_center_report_context` | payload, `domains: []` | period metadata, no client measures |
| `mart_data_quality_exceptions` | payload, **`scope_to_provided: true`** | see §4 |
| `mart_payroll_reconciliation` | payload | single-row, but uniformly `[payroll]` |

---

## 4. Two findings that changed the mapping

### 4.1 The reporting anchor is derived from payroll — a hidden cross-domain dependency

**Eight models** derive their reporting anchor from `MAX(payroll_period)`:

```
base_command_center_data_freshness   mart_workforce_contract_expiry
base_payroll_current                 mart_workforce_exceptions
base_payroll_previous                mart_workforce_iqama_expiry
mart_payroll_exceptions              mart_workforce_kpis
```

With payroll absent the anchor is `NULL`, every date-window comparison collapses, and the count reads **0**:

```
demo anchor              : 2026-06-30
anchor over empty payroll: None
```

**This corrects my own step-1 registry.** At `declared: [employees]` the step-1 audit showed `mart_workforce_kpis` returning zero for `probation_count`, `contract_expiring_30` and `iqama_expiring_30` — metrics I had mapped as `[employees]`, on a **declared** domain. They read zero not because nobody is on probation but because the anchor was null. Under step-1's mapping, suppression would have passed those fabricated zeros through as real.

Corrected: `probation_count` and `contract_expiring_30` → `[employees, payroll]`; `iqama_expiring_30` → `[employees, compliance, payroll]`.

This is a *fabricated zero on a declared domain* — a fourth route, distinct from Categories A–D, and it would not have surfaced without mapping the full surface.

### 4.2 `mart_data_quality_exceptions` has no source domain in the graph

It derives from the gold DQ report rather than a source table, so the ref graph resolves nothing. Suppressing it outright would hide **the exceptions a client most needs during onboarding** — the rows telling them which uploaded records are wrong.

Treated by analogy with ruling 1: `domains: [employees, payroll, attendance, compliance]` with `scope_to_provided: true`, so rows are filtered to provided domains rather than the payload suppressed. **This extends ruling 1's exception to a fifth entry and to payload mode, so it needs confirmation.** The pinned test records it explicitly rather than letting it pass unnoticed.

---

## 5. Coverage proof

14 tests, all passing. The coverage guarantee holds in both directions:

- `test_every_api_served_mart_is_mapped` — an API-served mart with no entry fails, by name.
- `test_registry_has_no_entries_for_marts_the_api_does_not_serve` — stale entries fail too.
- `test_column_mode_marts_map_every_column` — all 102 columns of the 10 column-mode marts.
- `test_mode_shape_matches_mode` — column marts carry `columns`, payload marts carry `domains`; mixing would make suppression ambiguous.
- `test_column_mode_is_reserved_for_mixed_provenance` — stops column mode spreading to uniform marts.
- `test_empty_domain_lists_carry_a_reason` + `test_source_free_entries_are_pinned` — 5 source-free entries, each justified on its line.
- `test_scope_to_provided_is_limited_to_the_ruled_metrics` — now 5 entries, including the payload one from §4.2.

### A pre-existing defect surfaced by the enumeration

`GET /api/compliance/wps` executes `SELECT * FROM mart_wps_status`, and **that object does not exist in the warehouse** — not as a view, not as a table. The endpoint returns 500 unconditionally.

```
exists as view: 0 | as table: 0
```

Not introduced by this cycle and not fixed here (no application code in 2a). `test_api_references_that_do_not_exist` pins the known-missing set so the list cannot grow unnoticed, and the mart is excluded from coverage rather than mapped.

---

## 6. Pydantic re-measurement by surface

```
NON-OPTIONAL NUMERIC FIELDS : 180

by surface:                     by file:
  breakdown     126               payroll.py      32    compliance.py      18
  series         25               attendance.py   30    command_center.py  15
  kpi            19               talent.py       29    kpi.py              8
  other          10               er.py           21    workforce.py        6
                                  recruitment.py  21
```

**This is the number that settles the scope question.** KPI-only suppression would have covered **19 of 180 fields — about 11%.** The other 89% is breakdowns and series: exactly the surface that, per the ruling, inherits the fabricator rather than merely fabricating zeros.

*Reconciliation with step 1:* step 1 reported **182**; this reports **180**. The step-1 counter also matched `List[int]`/`List[float]` annotations, which are not scalar metric fields. Two fields, same surface, stricter definition — not a change in the code.

---

## 7. Design constraint encoded for 2b

The registry header states it, so 2b cannot lose it:

> **A suppressed payload returns `null`, NEVER `[]`.** An empty array renders as an empty chart, and an empty chart is a claim that the period had no events.

---

## 8. Verification

| Check | Result |
|---|---|
| API-served marts mapped | **76 / 76** (excluding the non-existent `mart_wps_status`) |
| Column-mode columns mapped | **102 / 102** |
| Modes declared explicitly | 10 column, 66 payload; none inferred |
| Source-free entries | 5, each with a same-line reason |
| Pydantic re-measurement | **180**, split 126 / 25 / 19 / 10 |
| pytest | **73 passed** (68 + 5 new) |
| Demo | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 157/157, 11/11, reconciliation PASSED |
| Behaviour change | **none** — `config/`, `backend/tests/`, `docs/` only |

---

## 9. Open for step 2b

1. **`mart_data_quality_exceptions` scoping** (§4.2) — confirm the extension of ruling 1 to payload mode.
2. **The anchor dependency** (§4.1) — suppression will now null `probation_count` whenever payroll is absent, which is correct but surprising: a workforce metric disappears because payroll is missing. The alternative is fixing the anchor to derive from something domain-neutral (`report_month` is already a dbt var). **Recommend fixing the anchor in step 3** — the dependency is incidental, not semantic.
3. **`GET /api/compliance/wps`** (§5) — a broken endpoint on `main`, unrelated to P0-3. Worth its own small fix.
4. `mart_command_center_filter_options` carries `domains: []` so navigation keeps working while its own data may be absent. Confirm that is the right call.

---

**Not merged. Awaiting review.**
