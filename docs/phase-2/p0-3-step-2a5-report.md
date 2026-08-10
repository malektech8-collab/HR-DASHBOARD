# P0-3 Step 2a.5 — Anchor Convergence (Execution Report)

**Branch:** `phase-2/p0-3-anchor-convergence` off `main` @ `959d9fb` (2a merged) · **Date:** 2026-08-10
**Status:** executed, committed, pushed. **Not merged.**
**Scope:** dbt models, registry and tests only. **No application code.** Step 2b not started.

---

## 1. Step 2a merged

```
mergeCommit: 959d9fb9fa1f3cc0be063b85914dacc87257fded
mergedAt:    2026-08-10T13:43:04Z
```

Green on all three gates (run 31393974559).

---

## 2. Convergence — 7 models, 9 sites, 1 deliberate exclusion

Every converged site now matches `base_document_expiry`'s existing idiom exactly:

```sql
last_day(CAST('{{ var('report_month') }}-01' AS DATE))
```

| Model | Site | Was |
|---|---|---|
| `base_payroll_current` | current-period filter | `= (SELECT MAX(payroll_period) …)` |
| `base_payroll_previous` | previous-period filter | `strftime(CAST(MAX(payroll_period)…) - 1 MONTH)` |
| `mart_payroll_exceptions` | anchor `month_start` / `month_end` | `CAST(MAX(payroll_period)…)` |
| `mart_payroll_exceptions` | current-period filter | `= (SELECT MAX(payroll_period) …)` |
| `mart_workforce_contract_expiry` | `anchor_date` | `last_day(CAST(MAX(payroll_period)…))` |
| `mart_workforce_exceptions` | `anchor_date` | same |
| `mart_workforce_exceptions` | current-period filter | `= (SELECT MAX(payroll_period) …)` |
| `mart_workforce_iqama_expiry` | `anchor_date` | same |
| `mart_workforce_kpis` | `anchor_date` | same |

### The eighth is not an anchor — excluded, with reasoning

`base_command_center_data_freshness` keeps its `MAX(payroll_period)`. There it is **the metric itself**: one of seven parallel per-module `max_source_date` measurements that tell the user how fresh each source is. Converging it would replace a measurement with a constant and destroy the feature.

The ruling said "all 8". Seven were anchors; the eighth was a measurement wearing the same syntax. A test pins the exemption, and a second test fails if `data_freshness` ever stops needing it — so the carve-out cannot quietly go stale.

### Why convergence is safe

`report_month` is itself derived as `MAX(payroll_period)`, falling back to `MAX(period)` from compliance, then `DEFAULT_REPORT_MONTH` (`scripts/build_warehouse.py`). So on demo the two idioms are the *same value by construction*, and when payroll is absent the var still resolves while the raw `MAX` goes `NULL`. That is exactly the divergence, and exactly why the fix is convergence on the existing var rather than a new mechanism.

---

## 3. Demo byte-identity — the gate

```
dbt run  -> Done. PASS=157 WARN=0 ERROR=0 SKIP=0 TOTAL=157
dbt test -> Done. PASS=11  WARN=0 ERROR=0 SKIP=0 TOTAL=11
Command Center integration reconciliation checks PASSED.

headline: (19, 446175.0, 50.0) | exceptions 667 | DQ 15
BYTE-IDENTICAL: True
```

Per-mart spot checks on the seven converged models — `payroll_kpis` (446175.0 / 20), `payroll_exceptions` 15 rows, `workforce_exceptions` 25 rows, `contract_expiry` / `iqama_expiry` 1 row each — all unchanged. `data_freshness` still reports `2026-06` for payroll, confirming the exclusion left the measurement intact.

---

## 4. The before/after proof — and a correction to my own step-2a evidence

**My step-2a framing overstated the evidence, and I need to say so plainly.**

I cited `probation_count = 0` at `declared: [employees]` as a fabricated zero. It is not, on that data: no sample employee joined within 90 days of 2026-06-30, so **0 is the correct answer either way**. The observation was coincidental and proved nothing.

```
anchor (report_month end) : 2026-06-30
probation window starts   : 2026-04-01
employees joining in window: NONE      (max joining_date in sample = 2025-04-01)
```

The *mechanism* is real — a `NULL` anchor makes every window comparison `NULL` — but demonstrating it requires data with a non-zero answer. Synthetic employees, two inside both windows, at `declared: [employees]` with payroll absent:

```
########## BEFORE — anchor from MAX(payroll_period) ##########
  payroll rows        : 0        (undeclared -> empty)
  anchor via MAX()    : None
  employees rows      : 3
  probation_count     : 0        <- WRONG
  contract_expiring_30: 0        <- WRONG

########## AFTER — anchor from var('report_month') ##########
  payroll rows        : 0        (still empty)
  employees rows      : 3
  probation_count     : 2        <- 2 employees joined within 90 days
  contract_expiring_30: 2        <- 2 contracts expiring within 30 days
```

`0 → 2` on a **declared** domain with payroll still absent. That is the finding demonstrated properly.

Incidentally the fixture's first version used a `2030-01-01` contract end and was rejected by the 1b-i DATE range rule (`outside 1940-01-01 to 2028-08-10`) — the validator doing its job on my own test data.

---

## 5. Registry reversions

The payroll terms those metrics briefly carried were artefacts of the old idiom, not real dependencies:

| Entry | 2a | 2a.5 | Reason |
|---|---|---|---|
| `mart_workforce_kpis.probation_count` | `[employees, payroll]` | **`[employees]`** | payroll term was the anchor |
| `mart_workforce_kpis.contract_expiring_30` | `[employees, payroll]` | **`[employees]`** | same |
| `mart_workforce_kpis.iqama_expiring_30` | `[employees, compliance, payroll]` | **`[employees, compliance]`** | payroll reverted; **compliance is real** — it LEFT JOINs `stg_compliance` for `iqama_expiry` |
| `mart_workforce_contract_expiry` (payload) | `[employees, payroll]` | **`[employees]`** | anchor |
| `mart_workforce_iqama_expiry` (payload) | `[compliance, employees, payroll]` | **`[compliance, employees]`** | anchor |

`mart_workforce_exceptions` keeps `[compliance, employees, payroll]`: it genuinely reads payroll rows to flag pay for inactive employees, so that dependency survives the convergence.

The registry header records the resolution and the data-freshness carve-out.

---

## 6. `mart_data_quality_exceptions` — filter requirement encoded

Per ruling, "scope" now explicitly means **filter**:

```yaml
    scope_to_provided: true
    scope_filter: source_table   # rows are filtered by this column
```

with the reasoning inline — unfiltered, this surface becomes the route the entire fabricated exception set takes to the client (attendance 494, compliance 135, payroll 19 at `declared: [employees]`, against a demo baseline of 667), on the screen they read most closely during onboarding. Implementation is step 4.

---

## 7. Mode-aware Pydantic count

```
previous flat count (2a)                     : 180

OPTIONAL CONTAINERS needed (payload mode)    :  77
OPTIONAL SCALARS needed (column mode)        :  33
                                               ---
TOTAL FIELDS TO MAKE OPTIONAL                : 110

scalars INSIDE item models (no change needed): 147
```

Containers by file: `command_center` 13, `talent` 13, `recruitment` 11, `er` 9, `attendance` 8, `compliance` 8, `payroll` 8, `workforce` 5, `kpi` 2.

**110, not 180.** The expectation was ~66 containers; the measurement is 77, plus 33 scalars that sit on column-mode responses (including scalars alongside a list, such as a total beside its breakdown — those still need `Optional`). 147 item-model scalars need no change at all, because under payload mode the container goes `null` and they never surface.

On the split question: **2b does not look like it needs splitting.** 110 mechanical annotation changes across 9 files, with the suppression dependency itself being the only real logic, is a single cycle.

---

## 8. `mart_wps_status` diagnosis — report only, not fixed

**Verdict: lost in the dbt migration.** Not deleted deliberately, not renamed at the API layer, never re-created.

Evidence:

- The API reference dates from the initial baseline (`70af5ae`) — `GET /api/compliance/wps` has always queried `mart_wps_status`.
- In the pre-dbt era the view was created in `scripts/build_warehouse.py` as raw SQL (`print("Created view 'mart_wps_status'")` at line 1807 of `7b86cc8^`).
- Commit **`7b86cc8`** — *"Integrate dbt-duckdb and decouple raw SQL out of FastAPI layer"* — removed 4,300 lines from `build_warehouse.py` and **did not port `mart_wps_status` to a dbt model**. No file matching `*wps*` has ever existed under `dbt_analytics/models/`.
- The same commit also removed the reconciliation assertion that would have caught it:
  ```
  - wps_dist_sum = conn.execute("SELECT SUM(headcount) FROM mart_wps_status")…
  -     raise ValueError("CRITICAL: WPS distribution sum … does not match Active Headcount")
  ```
  The guard and the thing it guarded were deleted together, so nothing failed.
- The data survives under a different name and shape: `base_government_status.sql` exposes `mudad_status AS wps_status`. The endpoint was never repointed.

So the endpoint has returned 500 on every call since `7b86cc8`. Per ruling this is a separate hotfix branch; the fix is most likely a small `mart_wps_status` model over `base_government_status`, restoring the deleted reconciliation assertion alongside it.

---

## 9. Verification

| Check | Result |
|---|---|
| Anchor sites converged | 9 across 7 models |
| `MAX(payroll_period)` remaining | 1, in `data_freshness`, exempt and tested |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 157/157, 11/11, PASSED |
| `declared:[employees]` proof | `probation_count` 0 → **2**, `contract_expiring_30` 0 → **2** |
| Registry reversions | 5 entries |
| DQ filter requirement | encoded (`scope_filter: source_table`) |
| Mode-aware Pydantic | **110** (77 containers + 33 scalars) |
| pytest | **76 passed** (73 + 3 new) |
| Application code touched | **none** |

Synthetic artefacts removed; demo rebuilt and re-verified.

---

## 10. Open

1. **`mart_wps_status`** — separate hotfix branch; diagnosis above. Restore the reconciliation assertion with the model.
2. **2b scope** — 110 fields; recommend a single cycle.
3. `mart_workforce_exceptions` retains a real payroll dependency (inactive-employee pay checks), so it will suppress when payroll is absent. Correct, but worth knowing it behaves differently from its sibling workforce marts.

---

**Not merged. Awaiting review.**
