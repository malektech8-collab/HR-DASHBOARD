# The suite writes to operator-owned state — Plan

**Status:** PLAN ONLY. Unpredicted item #1 of the first-real-load report, ruled highest-priority remaining.
**Branch:** `phase-2/test-isolation` off `main` @ `90f38f0` · **Date:** 2026-08-17

---

## 1. Measured, not inferred

An mtime-watching pytest plugin was run over the whole suite against a live client load. **Four tests of 536 write to operator-owned state:**

| test | writes |
|---|---|
| `test_data.py::test_refresh_trigger` | registry, warehouse, 7× silver, gold, bronze — and deletes `contract_exceptions.parquet` |
| `test_contract_exceptions.py::test_transport_file_is_cleared_at_the_start_of_every_run` | registry, silver, bronze |
| `test_contract_exceptions.py::test_demo_mode_produces_no_transport_file` | registry, silver, bronze |
| `test_contract_exceptions.py::test_validate_merges_contract_exceptions_into_gold` | gold |

A full run mutates **11 artefacts and deletes 1**. Three further tests (`test_upload_flow`) *fail* — they do not write, they are shadowed by a live profile in `data/mapping/` that overrides their fixtures.

The concentration is the good news: this is four tests and one shared mechanism, not a diffuse property of the suite.

## 2. What is actually damaged

Not the warehouse — that rebuilds from `data/raw` in about ninety seconds. **The registry.**

`test_refresh_trigger` runs the demo pipeline, which rewrites `absent_columns` with the *demo's* set while leaving the client's `declared`, `history_since` and `declared_by` untouched. The file is then internally inconsistent: a real client's declaration carrying demo's column provision. `provides_column("employees", "cost_center")` flips to `True`, and the next real run silently re-fires every suppressed check.

Measured on this repo: that is **2,170 warnings** returning to a Data Quality page that should hold 372. The suppression mechanism built over two cycles is one `pytest` away from being disabled, and nothing anywhere says it happened.

## 3. Why it is invisible to CI by construction

CI has no mapping profile, no client load, and no declared registry. Every artefact the suite clobbers is one CI created moments earlier from sample data, so clobbering it is indistinguishable from correct behaviour. **The defect can only ever bite on the machine where real data lives** — GAP-002's family exactly.

It also taxes every cycle: `pytest` cannot be run without destroying loaded state, which is the condition under which people stop running tests. That is the second-order cost and it is larger than the first.

## 4. Options

### (a) `tmp_path` fixtures with monkeypatched module paths

Per-test temp directories; patch `onboarding.REGISTRY_PATH`, `mapping.PROFILE_DIR`, the `ingest_raw` constants.

**Fails on the test that matters most.** `test_refresh_trigger` POSTs `/api/data/refresh`, and `_run_pipeline()` launches `refresh_all.py` as a **subprocess**. A monkeypatch lives in the pytest process and cannot cross that boundary. The single worst offender is precisely the one this approach cannot reach.

It also isolates only what someone remembered to isolate — the failure mode is silent and identical to the current bug.

### (c) A separate test warehouse

Point `DATABASE_PATH` / `HR_WAREHOUSE_PATH` at a temp file.

**Covers one artefact class of four.** The warehouse is the cheap, reproducible one; the registry — the damaging one — is untouched, as are profiles, silver, gold and bronze. It solves the visible symptom and leaves the actual harm.

### (b) An env-scoped data root — **recommended**

One variable, `HRDASH_DATA_ROOT`, consulted as the **highest-priority branch** by every path resolver. The suite sets it once, session-scoped, to a temp directory seeded with the sample data.

Why this one:

1. **It crosses the process boundary.** An env var is inherited by `refresh_all.py`, by dbt, by anything the API spawns. This is decisive and is what disqualifies (a).
2. **It matches the shape already there.** Every resolver is already a two-branch function — container path, else repo-relative. This adds a third branch at the top. `registry_path()`, `profile_dir()`, `get_raw_dir()`, `get_silver_dir()` all take it identically, and `DATABASE_PATH` / `HR_WAREHOUSE_PATH` already work this way, which is the precedent.
3. **One mechanism, so nothing is forgotten.** With (a), each artefact is isolated by someone remembering it. With one root, an artefact is isolated because it is under the root — and a *source-level* test can assert that no module writes to a hard-coded repo-relative path, which is the enforcement (a) cannot have.
4. **It costs the operator nothing.** Unset, every path resolves exactly as today. Demo output is unchanged by construction, because nothing about the demo pipeline changes.

**The rule is: isolate WRITES, not reads.** A test that reads the built warehouse is doing its job. Only writes need redirecting.

## 5. The interaction this plan exists to surface

**`test_demo_gate` currently depends on `test_data` running first, and only alphabetical filename ordering guarantees it.**

`test_data.py` sorts before `test_demo_gate.py`. `test_refresh_trigger` rebuilds the warehouse in demo mode, re-anchoring it to 2026-06, and the demo gate's `_demo_only()` guard then passes. Measured against the live client load with that side effect absent:

```
SKIPPED [5] warehouse is anchored at 2026-08, not the demo's 2026-06
3 passed, 5 skipped
```

So isolating writes **silently turns the demo fingerprint into a no-op on any operator machine** — the five pinned figures stop being asserted, and the gate reports success while checking nothing. That is a worse failure than the one being fixed, and it would arrive quietly.

The fix is not to exempt the gate. It is to make it **self-sufficient**: build a demo warehouse inside the isolated root and point `HR_WAREHOUSE_PATH` at it, so the gate asserts the demo fingerprint because it built the demo, not because an unrelated test happened to run first. The existing env override means this needs no change to the gate's assertions.

This dependency is a live test-ordering hazard today, independent of isolation. Anything that reorders the suite — `-p no:randomly` removed, a file renamed, `-k` filtering, parallelisation — already breaks it.

## 6. The three shadowed tests

`test_upload_flow` fails when a real profile exists because `mapping.load_profile(table)` reads `data/mapping/` and the client's profile overrides the fixtures' expectations. Under (b) the profile directory moves under the root, so the fixtures see an empty one and the tests pass — no change to the tests themselves.

## 7. Can CI verify this? — partly, and the split is the point

**CI can verify the mechanism.** Three things, all runnable on a machine with no real data:

- *Structural*: no module writes to a hard-coded repo-relative data path; every resolver consults the root. A source-level test in the idiom of `test_dbt_vars` and `test_path_contract`.
- *Functional*: set the root to `tmp_path`, run `ingest_raw.ingest(data_mode="demo")`, assert the temp registry was written **and** the repo-root registry was not touched. This proves the redirect works, including the subprocess path if exercised through `/api/data/refresh`.
- *Regression*: seed a sentinel registry with distinctive content, run the four named tests, assert byte-identical.

**CI cannot verify the guarantee from inside the suite.** "A full suite run leaves operator state untouched" is a statement *about* a suite run, so no test within that run can make it. It needs a second invocation.

**That is a CI job step, not a test**, and it should be added:

```
snapshot data/ + warehouse/  ->  pytest backend/tests  ->  assert unchanged
```

CI's state is synthetic, but the *property* — "the suite does not write here" — is identical whether the bytes are a client's or a sample's. So this converts an operator-only property into a CI-visible one, which is precisely what GAP-002 says this family lacks. It is the most valuable single item in this plan.

**What still cannot be proven in CI**: that a real client's *specific* load survives — real data never exists there. But that is a statement about data, and the sentinel makes it a statement about paths, which is the part that can actually be wrong.

## 8. Test obligations (SP-001 — both halves)

1. With the root set, a demo ingest writes the temp registry **and** leaves the repo registry byte-identical — and with the root unset, it writes the repo registry exactly as today (the tamper; isolation that never releases is not isolation).
2. `test_refresh_trigger` writes nothing outside the root — the subprocess case, and the one (a) cannot satisfy.
3. The demo gate asserts all five figures with a real-mode warehouse present at the repo root, i.e. it no longer skips (§5).
4. The three `test_upload_flow` tests pass with a profile present at the repo root.
5. A source-level test that every data-path resolver consults the root.
6. Demo byte-identity: `19 / 446175.0 / 50.0 / 667 / 15`.

## 9. Cost

Moderate, and concentrated: one env var, five resolver functions, one session fixture, one CI step, six tests. No contract change, no dbt change, no API behaviour change, no migration. The risk is not in the mechanism but in §5 — the demo gate must be made self-sufficient **in the same change**, or this plan trades a loud problem for a silent one.

---

**Not built. Awaiting a ruling.**
