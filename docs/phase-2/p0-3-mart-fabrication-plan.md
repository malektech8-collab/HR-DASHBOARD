# P0-3 — Mart-Layer Fabrication (PLAN ONLY)

**Status:** proposed. Nothing implemented. This document is the only file added on `phase-2/p0-3-mart-fabrication`.
**Branch:** `phase-2/p0-3-mart-fabrication` off `main` @ `de8efc7` (P0 steps 1–2 merged) · **Date:** 2026-08-10
**Related:** [`p0-onboarding-safety-plan.md`](p0-onboarding-safety-plan.md) · [`p0-step-1-2-report.md`](p0-step-1-2-report.md) §(d)

---

## 0. Why this is a third defect, not a variant of the first two

P0-1 stopped fabricated **rows** entering silver. P0-2 will stop unvalidated rows entering at all. P0-3 is downstream of both: silver is *correctly empty*, and the **mart layer manufactures values from that emptiness**.

The declared-domain guard structurally cannot catch it. The guard compares declarations against **silver row counts**, and at `declared: [employees]` silver is exactly right — `payroll` and `attendance` have zero rows, as declared. Every check passes, and the dashboard still shows invented numbers. Nothing in the current architecture inspects what the marts do with an empty input.

Reference case, verified:

```sql
-- base_expected_attendance.sql
FROM calendar_dates c
CROSS JOIN base_employees_deduplicated e     -- every active employee × every workday
...
LEFT JOIN base_attendance_current att
...
CASE WHEN att.employee_id IS NULL THEN 1.0   -- no attendance row => a full day absent
     ELSE COALESCE(att.absence_days, 0.0) END AS absence_days
```

With attendance empty, every expected workday becomes an absence. `mart_attendance_kpis` then reports `absence_days = 494.0` and `attendance_compliance_pct = 0.0`.

---

## (c) The audit — all marts of this shape

Measured, not inferred: the pipeline was run at `declared: [employees]` with the other five contracted domains empty, and every KPI mart dumped. 134 mart models, 48 using `COALESCE`.

### Category A — non-zero fabricated **measures** (worst)

A real quantity, invented from absence.

| Mart | Value at `declared: [employees]` | Mechanism |
|---|---|---|
| `mart_attendance_kpis.absence_days` | **494.0** | `base_expected_attendance` cross join + `CASE … IS NULL THEN 1.0` |

This is the only place a numeric *measure* is manufactured from a non-existent row. Everything else in the audit is a count, a rate, or a zero.

### Category B — fabricated **exception counts**

Worse than they look: each one tells the client *their data is wrong*, when the truth is *they have not uploaded it*. Exception rows by module at `declared: [employees]`:

```
attendance       494        <- one per employee per workday
compliance       135
talent            28        <- Category E, sample-sourced
workforce         26        <- legitimate (employees IS declared)
recruitment       25        <- Category E, sample-sourced
payroll           19        <- one per employee with no payroll record
data-quality      15
             total 742      (demo shows 667)
```

The client sees **more** exceptions than the demo dataset, essentially all invented. Specific counters:

| Mart | Column | Value | Reads as |
|---|---|---|---|
| `mart_attendance_kpis` | `attendance_exception_count` | 494 | 494 attendance problems |
| `mart_compliance_kpis` | `compliance_exception_count` | 135 | 135 compliance breaches |
| `mart_compliance_kpis` | `gosi_missing_count` | 19 | 19 staff not registered with GOSI |
| `mart_compliance_kpis` | `wps_exception_count` | 19 | 19 WPS violations |
| `mart_payroll_kpis` | `payroll_exception_count` | 19 | 19 employees with payroll problems |
| `mart_command_center_overview` | `total_active_exceptions` | 742 | — |

`gosi_missing_count = 19` is the sharpest example. It is regulatory in flavour, and a client could act on it.

### Category C — fabricated **favourable** metrics

| Mart | Column | Value | Problem |
|---|---|---|---|
| `mart_er_kpis` | `sla_compliance_pct` | **100.0** | 100% SLA compliance computed over zero cases |

Dangerous precisely because it reassures. A wrong bad number invites a question; a wrong good number does not.

### Category D — fabricated zeros

| Mart | Columns | Value |
|---|---|---|
| `mart_exec_kpis` | `payroll_cost` | 0.0 |
| `mart_payroll_kpis` | `total_payroll_cost`, `employees_paid` | 0.0 / 0 |
| `mart_attendance_kpis` | `attendance_compliance_pct` | 0.0 |
| `mart_er_kpis` | open/closed case counts | 0 |

`COALESCE(SUM(...), 0)` and `COUNT(*)` over empty tables. A zero is a claim: *"your payroll cost this month was zero."*

### Category E — sample-sourced, out of P0-3 scope

`mart_recruitment_kpis` (11 non-zero metrics) and `mart_talent_kpis` (11 non-zero metrics) are fully populated from sample data, because those 15 domains have no contract and always load sample. That is the §1.3 boundary already ruled on (ruling 2 → provenance `not_provided`), listed here only so the audit is complete.

### Shapes that look similar but are NOT fabrication

Checked and cleared, so the fix does not over-reach:

- **Label `CASE`s** — `'Unknown Employee'`, `'Not Eligible'`, `'missing_date'` in `base_attendance_current`, `base_case_sla_clock`, `base_document_expiry`, `base_er_case_parties`, `base_er_cases_current`, `base_government_platform_records`. These classify a row that exists; they do not invent one.
- **Scalar cross joins** — `mart_compliance_kpis`, `mart_er_kpis`, `mart_recruitment_kpis`, `mart_command_center_data_freshness` cross-join single-row aggregates to assemble one KPI row. Not row-multiplying.
- **Missing-value counters** — `base_saudization_population`, `mart_workforce_contract_expiry`, `mart_workforce_iqama_expiry` count nulls *within* present rows. Legitimate data quality.
- **`base_document_expiry` cross join** — joins to a single-row anchor date, not a calendar.

**The only structural fabricator is `base_expected_attendance`.** Everything else in categories B–D is `COALESCE`/`COUNT` over an empty input — pervasive, but uniform and therefore addressable in one place.

---

## (a) Suppression at the API layer

Per ruling: the API must return `null`, and the frontend renders an empty state **because the value is null**, not because it independently knows the provenance.

The reasoning is worth restating because it drives the design: `/api/*` is consumed by the React app, CSV export, report generation, and the `feature/local-powerbi-workspace` profile. A React empty state protects **one consumer in four**. A CSV export of `absence_days = 494` is indistinguishable from a real one, and it outlives the session it was generated in.

**Proposed:** a suppression layer in the response path, between the mart query and serialisation.

```python
# backend/app/api/_provenance.py  (sketch)
def suppress(payload: dict, metric_domains: dict, provided: set) -> dict:
    """Null out any metric whose source domain is not provided."""
    return {k: (None if metric_domains.get(k) and metric_domains[k] not in provided else v)
            for k, v in payload.items()}
```

Three properties this needs:

1. **Default-deny.** A metric with no declared source domain should be suppressed, not passed through. An unmapped metric is an unreviewed one, and the failure mode of default-allow is exactly the silent fabrication we are removing.
2. **Applied once, centrally** — a FastAPI dependency or response middleware, not per-endpoint. Ten routers each remembering to call it is nine chances to forget.
3. **Pydantic models must permit `null`.** Many response schemas declare non-optional `float`/`int`. Making them `Optional` is a broad but mechanical change, and it is the part most likely to be underestimated in effort.

Suppressed metrics should also be *reported*, not merely blanked — a sibling block naming which metrics were suppressed and why, so a consumer can distinguish "null because not provided" from "null because the query failed".

---

## (b) Metric → source-domain mapping

Per ruling: **metric-level**, not page-level or mart-level. `mart_exec_kpis` proves the need — one row carrying `active_headcount` (employees) and `payroll_cost` (payroll). At `declared: [employees]` that row must return a real headcount **and** a null payroll cost.

Proposed shape — a single declarative registry, not annotations scattered across routers:

```yaml
# config/metric_provenance.yml
mart_exec_kpis:
  active_headcount:   [employees]
  payroll_cost:       [payroll]
  turnover_rate:      [employees]
  data_quality_score: [employees, payroll, attendance, compliance]   # multi-source
mart_attendance_kpis:
  absence_days:              [attendance]
  attendance_compliance_pct: [attendance, employees]
```

Design points:

- **A metric may have several source domains.** `attendance_compliance_pct` needs attendance *and* employees (the denominator is the expected-workday calendar). Suppress if **any** required domain is absent — a partially-sourced metric is not a real one.
- **`data_quality_score` is the awkward case.** It aggregates checks across every domain, so under an "any absent ⇒ suppress" rule it is null until onboarding completes. That is defensible, but it removes the one number a client most wants during onboarding. Alternative: scope the score to provided domains and label it as such. **Needs a ruling** — it is a product decision, not a technical one.
- **Coverage must be enforced, not hoped for.** A test asserting every column of every KPI mart appears in the registry; a new metric without an entry fails CI. Combined with default-deny, an unmapped metric is invisible rather than fabricated.
- The existing `config/metrics_dictionary.yml` is the obvious neighbour and may be the right home — worth checking for overlap before adding a second registry, given how much of this cycle has been about removing duplicate lists.

---

## (d) Where §4's three provenance states change

The states themselves stand — `client`, `not_provided`, `demo` — but (b) moves where they are *applied*.

| §4 as written | Revised |
|---|---|
| Provenance is a **domain**-level attribute exposed by `/api/meta/app-config` | Still true, and still the source of truth |
| The frontend uses it to decide what to render | **No.** The frontend renders an empty state because the value is `null`. Provenance drives *suppression* in the API |
| Per-domain provenance is enough for the UI | **Not enough.** A single response row can mix provenances, so suppression must be per-metric even though provenance is per-domain |

So `/api/meta/app-config` keeps exposing the three states — useful for banners, export headers and "you have not uploaded X yet" prompts — but it is no longer the mechanism that prevents a fabricated number reaching a consumer. That mechanism is metric-level suppression.

One addition: the `demo` state now needs to apply to **whole modules** as well as domains, for the 15 uncontracted tables (ruling 2). A module-level state is the cleanest way to gate Recruitment and Talent without inventing a metric mapping for domains that have no contract.

---

## (e) Revised ordering — recommendation

**Recommend: P0-3 moves ahead of steps 3–5, and step 6 merges into it.**

Reasoning:

1. **P0-3 is the only remaining route to a fabricated number reaching a client.** P0-1 closed the ingest route. Steps 3–5 (format rule, staging, `.uploaded`) are all *correctness and safety of the upload path* — real work, but none of them stops a wrong number being displayed today. A deployment with steps 1–2 merged and P0-3 outstanding will still show `absence_days = 494`.
2. **Step 6 is not separable from P0-3.** Step 6 was "per-domain provenance + empty states". Under ruling (a) the empty state is a consequence of a null API value, so step 6's frontend work *is* the consumer half of P0-3. Keeping them apart would mean building the empty state twice.
3. **Steps 3–5 are prerequisites for onboarding, not for safety.** Without them a client cannot self-serve an upload — they need an operator to place files in `data/raw/`. That is friction, not danger, and Client Zero is operator-assisted by definition.
4. **One exception: the format rule (step 3) should come first anyway.** It is a handful of lines, and `payroll_period = "June 2026"` currently breaks the *build* with an unattributed `Conversion Error`. Cheap, unrelated to P0-3, and it removes a crash.

Proposed order:

| # | Item | Was |
|---|---|---|
| 1 | Format rule (`payroll_period`, `compliance.period`) | step 3 |
| 2 | **P0-3**: metric registry + API suppression + empty states + module gating | new + step 6 |
| 3 | Staging, validate, preview, commit-to-`raw`, block uploads in demo | step 4 |
| 4 | Retire `.uploaded` | step 5 |

Phase 2's exit criterion is *real workforce, Saudization and payroll figures rendering correctly*. "Correctly" has to include *not rendering at all when the data is absent*, which makes P0-3 part of the exit criterion rather than a follow-up to it.

---

## Open questions

1. **`data_quality_score` under partial onboarding** — suppress until complete, or scope to provided domains and label? Product decision.
2. **Registry home** — new `config/metric_provenance.yml`, or extend `config/metrics_dictionary.yml`?
3. **Category A specifically** — suppression hides `absence_days = 494` from the API, but `base_expected_attendance` still computes it, and it still inflates `total_active_exceptions` and the DQ score. Should the model itself be gated on attendance being provided, or is API suppression sufficient? **Recommend fixing the model too** — a wrong number that exists is one refactor away from being displayed again.
4. **Exception rows (Category B)** — should `mart_*_exceptions` stop emitting rows for absent domains entirely? They are not "metrics" and may bypass a metric-level suppression layer.
5. **`Optional` on response models** — confirm the scale of the Pydantic change before committing to an estimate.

---

**Prepared for chief-architect review. No implementation performed.**
