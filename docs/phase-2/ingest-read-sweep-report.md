# The ingest read sweep — Execution Report

**Branch:** `phase-2/ingest-read-sweep` off `main` @ `028856e` · **Date:** 2026-08-17
**Plan:** [`ingest-read-sweep-plan.md`](ingest-read-sweep-plan.md) (approved with the architect's reordering) · **Status:** PR open, **not merged**

Per SP-003 this report carries magnitudes and vocabulary only.

---

## 1. (d) The guarded count

| file | guarded | unguarded |
|---|---|---|
| `scripts/ingest_raw.py` | **47** | 0 |
| `backend/app/api/data.py` | 3 | 0 |
| `scripts/mapping_cli.py` | 1 | 0 |
| `scripts/validate_schema.py` | 1 | 0 |
| **total on pipeline paths** | **52** | **0** |

## 2. (a) The three swallowed probes — ruling 1

They were two defects at once, and the second was the dangerous one. Unguarded, so a later row could raise `ComputeError`; and wrapped in `except Exception: return None`, so that error was **indistinguishable from "column absent"**. A caller reading `None` concludes there are no periods and the gate stands down — the gate whose own message warns the alternative is *every employee absent on every working day*.

`_read_probe_column()` now reads as text and catches **only** `ColumnNotFoundError`. Everything else propagates: a probe that cannot read a file has not discovered the file is empty.

**Proof, tampering with the exact class that used to be swallowed:**

```
TAMPER - the exact class that used to be swallowed:
   propagates ComputeError: could not parse `1584.91` as dtype `i64`
   <-- the run stops instead of reporting 'no periods'. Correct.

   and the OTHER two probes, same tamper:
      check_payroll_period_matches_report_month  propagates ComputeError
      check_rows_within_declared_coverage        propagates ComputeError
```

And the behaviour that must **not** change — a genuinely absent column still returns `None` rather than raising, so the existing "nothing to compare here" path is intact. Both halves, per SP-001.

## 3. (b) Per-domain casts — ruling 2

Every domain rebuilt from a full demo run: **161/161 models, 11/11 tests, reconciliation PASSED**.

**Six boolean columns, all genuinely `Boolean` and none collapsed to null:**

| domain | column | dtype | non-null |
|---|---|---|---|
| employees | `is_saudi` | Boolean | 21 |
| attendance | `overtime_approved` | Boolean | 76 |
| hr_requests | `sla_breached` | Boolean | 4 |
| compliance | `contract_authenticated` | Boolean | 4 |
| employee_relations | `escalated` | Boolean | 11 |
| succession_plans | `is_critical` | Boolean | 6 |

**Across all 23 domains: no numeric or date column is wholly null.** That is the check that matters — a cast that silently produced nulls would leave the build green and the data empty.

`_bool_col()` is one shared helper rather than six copies, and **NULL stays NULL**: an absent `sla_breached` is not a met SLA, and an absent `is_critical` is not a non-critical role.

### 3.1 A correction to my own plan

The plan said a blanket replace *"would pass CI — demo supplies well-formed data for every domain — and break on the first real file"*. **For the boolean casts that is wrong, and I measured it while writing the helper's docstring:**

```
naive .cast(pl.Boolean, strict=False) on TEXT:
   raises InvalidOperationError
```

`Utf8 → Boolean` raises; `strict=False` does not change it. Demo supplies all six columns, so a blanket replace would have **broken the demo build immediately** — the safe direction. The boolean half was never the silent half.

### 3.2 The premise was wrong in a way the outcome concealed

Worth stating plainly, because the shape of this mistake is the dangerous kind.

**The plan's argument was:** the boolean casts are the risk, because a blanket replace passes CI and breaks later on real data.

**The premise was false.** `Utf8 → Boolean` raises immediately, and demo supplies all six boolean columns — so a blanket replace would have broken the demo build **loudly, in CI, on the first run**. The boolean casts were never able to reach a client.

**The conclusion was still right.** Sequencing the three probes first was correct — but for a reason the plan did not give. They were not the *smallest* silent defect among several; they were **the only genuinely silent defect in the file**. Everything else fails loudly and rolls back.

**Why this is recorded rather than quietly amended.** The outcome concealed the error: the work was ordered correctly, every gate went green, and nothing in the result would have prompted anyone to re-examine the reasoning. A wrong premise that produces a right answer is not self-correcting — it survives, and it gets reused. Next time it may carry the decision rather than accompany it.

The concrete residue: **"a blanket change would pass CI and break on real data" was assumed, not measured.** It was measurable in one line, and the one line disagreed. Recorded as [SP-005](../TECHNICAL_DEBT_REGISTER.md#sp-005--a-correct-conclusion-from-a-wrong-premise-is-still-a-defect).

## 4. (c) The structural test — ruling 3

AST, not regex. Both regression shapes caught, each naming file and line:

```
a deliberate 51st, hidden among 47 correct reads:
   scripts/ingest_raw.py:554: no infer_schema_length
   2 failed, 13 passed

a duckdb sniffer on a pipeline path:
   read_csv_auto samples rows to infer types...
   scripts/build_warehouse.py:114
```

`read_csv_auto` is in scope because it carries the identical sampling sniffer and would reintroduce the defect by another route. The count is pinned as well as the rule, so a read **disappearing** is noticed too — a domain that stops being ingested is its own defect.

**Both limits are in the test's docstring**, per ruling: it cannot see a read built by `getattr`, and it checks the keyword is *present* rather than that it is `0` — though a non-zero **literal** is caught, since `infer_schema_length=10000` is the fix people reach for first and only moves the row at which the guess goes wrong.

Six tampers, including the one that matters most: an unguarded read hidden **among guarded siblings**, because the fifty-first arrives beside fifty correct ones rather than alone.

## 5. `str.to_date` — ruling 4

**31 `str.to_date` sites.** That method requires a `Utf8` column, so before this change every one of them depended on polars *happening* to infer text. A file that inferred `Date` — entirely possible for a well-formed date column — would have broken them from the other direction.

Reading as text makes that guarantee explicit. **Those 31 sites removed a latent fragility rather than acquiring one**, and the same is true of the eight domains whose only typing is `str.to_date`.

## 6. Verification

| Check | Result |
|---|---|
| pytest | **564 passed** (549 + 15 new) |
| Isolation check | `PASSED - 62 file(s) byte-identical` |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` |
| flake8 (CI gate) | 0 |
| Unguarded reads on pipeline paths | **0** |

**Client load, before → after:** row count, data-quality rows, absent columns and declared history all unchanged, and `data/raw/employees.csv` byte-identical by md5. The demo rebuilds ran into an isolated root, so the client's warehouse was never touched — the first cycle in which that was true by construction rather than by remembering.

## 7. Open

1. **`getattr`-built readers are invisible to the test** (§4). Nothing does this today.
2. **`scratch/` is not scanned** — one unguarded read and one `read_csv_auto` live there. On no pipeline path and excluded from pytest, so left alone deliberately rather than missed.
3. **The pinned count of 47** must be updated in the same commit that adds or removes a domain. That is the intended friction.

---

**Not merged. Awaiting review.**
