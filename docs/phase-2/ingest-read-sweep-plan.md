# The remaining unguarded reads in `ingest_raw.py` — Plan

**Status:** PLAN ONLY (A2). **Branch:** `phase-2/ingest-read-sweep` off `main` @ `028856e` · **Date:** 2026-08-17
**Blocks:** every domain after `employees`.

---

## 1. The measured surface

`scripts/ingest_raw.py`: **47 unguarded `pl.read_csv` calls, 2 guarded** — the employees pair fixed when the first real commit was rejected.

**Everywhere else in the codebase is already guarded.** `backend/app/api/data.py` (3), `scripts/mapping_cli.py` (1), `scripts/validate_schema.py` (1) — all pass `infer_schema_length=0`. The only other hits are in `scratch/`, which is on no pipeline path and is excluded from pytest by `norecursedirs`.

So this is one file, and the answer to *"does the same defect shape exist in any other reader?"* is **no for CSV** — with two qualifications in §5.

## 2. The part that is worse than a crash

Three of the 47 are not domain loaders. They are period probes — `_periods_in_csv`, and the coverage check — and each is wrapped in:

```python
try:
    frame = pl.read_csv(path, columns=[column])
except Exception:
    return None
```

**A dtype-inference `ComputeError` there is swallowed and returned as "no periods found".** Demonstrated on a file whose column holds whole numbers then a decimal:

```
direct read of the AMOUNT column:   raises: ComputeError
_periods_in_csv on the same column: returns: None
=> a ComputeError here is indistinguishable from 'column absent'.
```

That matters because these feed `check_period_coverage` and `check_payroll_period_matches_report_month` — the guard whose own error message says the alternative is *"every employee absent on every working day"*. A swallowed read error **disables that guard silently**.

The 44 domain loaders fail loudly and roll back, which is the safe direction. **These three fail quietly, and they should be fixed first even though they are the smallest part of the work.**

## 3. Why this is not 47 keyword additions

The employees fix was two reads **and one cast**. Reading as text meant `is_saudi` arrived as `"true"`/`"false"`, and `Utf8 → Boolean` is not a supported cast — the demo pipeline broke immediately.

Measured cast profile per domain block:

| tier | domains | why |
|---|---|---|
| **A — will break identically** | `attendance`, `hr_requests`, `compliance`, `employee_relations`, `succession_plans` | each casts to `pl.Boolean`, exactly what failed for employees |
| **B — numeric casts, expected safe** | `payroll`, `offers`, `workforce_plan`, `vacancy_requests`, `performance_reviews`, `competency_assessments`, `training_catalog`, `talent_reviews`, `career_paths` | `.cast(pl.Float64, strict=False)` from text is fine |
| **C — `str.to_date` only, or no casts** | `locations`, `recruitment_requisitions`, `candidates`, `interviews`, `onboarding`, `performance_goals`, `learning_enrollments`, `employee_skills` | `str.to_date` **requires** Utf8, so reading as text removes a latent fragility rather than adding one |

Tier C is the useful surprise: those domains are currently one oddly-shaped export away from breaking in the *opposite* direction — polars inferring `Date` and `str.to_date` failing on a non-string column. The sweep fixes that too.

**Estimate: 47 reads, ~5 boolean parses, 23 domains to verify.** The keyword is trivial; the verification is the work.

## 4. Can a structural test prevent a fifty-first? — yes, and it is prototyped

**AST, not regex.** Prototyped against the current tree:

```
./scripts/ingest_raw.py    47  lines [114, 189, 224, 497, 500] ...
TOTAL unguarded: 47
multi-line call handled? yes
```

It finds exactly the 47, nothing else in the repo, and correctly accepts a call whose keyword is on another line. A regex cannot do the last part, and this codebase writes multi-line reads.

Shape: walk every `ast.Call`, match `read_csv` by attribute or bare name, require an `infer_schema_length` keyword. Roughly twenty lines, in the idiom of `test_no_script_hardcodes_a_state_path` and `test_dbt_vars`.

**Two honest limits.** It cannot see a read built by `getattr`, and it checks that the keyword is *present*, not that it is `0`. Both are acceptable: neither pattern exists here, and pinning the value as well is one extra comparison. Per SP-001 the test needs its own tamper — a fixture with a deliberately unguarded read, asserted to be caught.

## 5. Where the same *shape* could still hide

CSV is the only inference-based reader on the pipeline path, but the shape is *"a reader that guesses types from a sample"*:

- **Parquet** — carries an embedded schema. Not vulnerable. This is why silver/bronze are safe and only the raw boundary matters.
- **DuckDB `read_csv_auto`** — has its own sampling sniffer and would have the identical failure. One occurrence, in `scratch/`, on no pipeline path. Worth a line in the structural test so it cannot arrive later.
- **The `.env` / YAML readers** — no inference.

The generalisable rule, and the one worth writing down: **every CSV boundary is a text boundary.** Types come from the contract, never from the first N rows.

## 6. Sequencing

1. **The three probes first** — smallest change, and the only ones that fail silently.
2. **Tier C, then B, then A** — cheapest and safest first, so the boolean work is done against an already-verified pipeline rather than alongside it.
3. **The structural test last**, once the count is zero, so it lands green rather than as a known-failing gate.

Each tier: demo rebuild + byte-identity, because ingest is the one path both modes share.

## 7. Test obligations (SP-001 — both halves)

1. A synthetic CSV of the failing shape — whole numbers then a decimal — loads for **every** domain, and the same file **fails** on `main` (the tamper; otherwise the fixture proves nothing).
2. Boolean columns in tier A round-trip: `"true"`/`"false"` → `True`/`False`, **and NULL stays NULL** — a missing value must never become `False`.
3. `_periods_in_csv` returns periods for the failing shape rather than `None`, and still returns `None` for a genuinely absent column — the two cases that are currently indistinguishable.
4. The structural test reports zero, and catches a deliberately unguarded read.
5. Demo byte-identity: `19 / 446175.0 / 50.0 / 667 / 15`.

## 8. Cost and risk

Moderate and mechanical: one file, 47 call sites, ~5 cast adjustments, one structural test. No contract change, no API change, no migration.

**The risk is not the reads, it is the casts.** A blanket find-and-replace would pass CI — demo supplies well-formed data for every domain — and then break on the first real file for a tier-A domain, which is exactly the failure mode this cycle exists to remove. That is why the plan is per-tier with a demo rebuild at each step rather than one commit.

---

**Not built. Awaiting a ruling.**
