# Test isolation — Execution Report

**Branch:** `phase-2/test-isolation` off `main` @ `90f38f0` · **Date:** 2026-08-17
**Plan:** [`test-isolation-plan.md`](test-isolation-plan.md) (approved as written) · **Status:** PR open, **not merged**

Per SP-003 this report carries magnitudes and vocabulary only.

---

## 1. `HRDASH_DATA_ROOT`, and the distinction that made it work

[`scripts/paths.py`](../../scripts/paths.py) is the single resolver. Order: the env override, then the container layout, then the repo default. Unset, every path resolves exactly where it did before — that is the compatibility line, and a test pins it.

The load-bearing decision is **STATE versus SOURCE**:

| | follows the root | |
|---|---|---|
| **STATE** | yes | raw, bronze, silver, gold, sample, staging, mapping profiles, onboarding registry, warehouse |
| **SOURCE** | **no** | `data/contracts`, `config/` |

Contracts are repository content the pipeline only reads. A suite pointed at a temp root must still validate against the **real** contracts — moving them would mean the suite checks a copy of its own fixtures instead of the thing that ships. The rule is *isolate writes, not reads*.

## 2. Two things the plan did not foresee

**The dbt profile.** `dbt_analytics/profiles.yml` hard-coded `../warehouse/hr_analytics.duckdb`. The first isolated run therefore had `build_warehouse` open the redirected warehouse while **dbt built models into the operator's** — and the run then failed on a missing table. Fixed by `env_var('HRDASH_WAREHOUSE_PATH', <the previous literal>)`, exported by `build_warehouse` for both the `run` and `test` invocations. The default is unchanged, so every existing deployment resolves as before.

**Silver was read from the cwd.** `build_warehouse` composed its parquet paths as `f"{data_prefix}data/silver/…"`, cwd-relative when `DATA_PREFIX` was unset. The second isolated run wrote its own silver correctly and then loaded the **operator's** — producing a warehouse holding a client's rows under a demo label. That is worse than not isolating at all, because it looks like it worked; the demo gate caught it immediately by asserting the client's headcount against the demo's. `DATA_PREFIX` now defaults to the state root.

Both were only visible under an override, which is why they were not in the plan.

## 3. `test_demo_gate` is self-sufficient (ruling 2)

It read whatever warehouse sat at the repo root, and passed only because `test_data.py` sorts before `test_demo_gate.py` and rebuilt the warehouse in demo mode as a side effect. **Nothing declared that dependency and nothing enforced it.** It was already a live hazard before this cycle: `-k` filtering, a file rename, or parallelisation each break it.

It now reads the root `conftest.py` builds, so it asserts the demo fingerprint because it **built** the demo.

**Every skip became a failure.** Four guards — missing warehouse, un-built warehouse, real mode, wrong anchor month — stood the gate down silently. A skipped test is green. `pytest.skip` no longer appears in the file.

## 4. Proofs

### (a) A full suite run leaves operator-owned state untouched

```
snapshotting operator-owned state...
  62 file(s) under 8 protected path(s)
549 passed in 60.28s
pytest exited 0
PASSED - 62 file(s) byte-identical; the suite wrote nothing outside its own root.
```

Directories are walked rather than listed, so a **created** file fails as loudly as a changed one.

The client's loaded state, before and after the entire cycle: **identical** — same row count, same data-quality row count, same recorded absent columns, same declared history. It needed no rebuild, which is the point.

### (b) The gate fails on a wrong fingerprint, regardless of run order

| | result |
|---|---|
| run **alone**, nothing before it | `8 passed` — 0 skipped |
| pointed at a **non-demo** warehouse | **`5 failed`** — the scenario that previously reported `SKIPPED [5]` |
| a pinned figure tampered | **`1 failed`** — `assert 19 == 20` |

The middle row is the regression this ruling exists for: same input, previously green by skipping, now red.

### (c) The CI step catches a deliberate regression

```
  wrote a deliberate regression: data\onboarding\__isolation_probe__.yml
DETECTED: data\onboarding\__isolation_probe__.yml
the checker fails when the suite writes here. Good.
```

Run as its own CI step. Per SP-001 a guard nobody has watched fail is not a guard — and a comparison that cannot detect a change is green forever.

## 5. The CI step, and why it is a step (ruling 3)

Two invocations in the Test Suite gate: `check_test_isolation.py` (runs the suite, compares, forwards pytest's exit code) and `--verify-detects`.

Recorded as **GAP-003** beside GAP-002:

> CI can verify the **mechanism** — that paths resolve through the state root, that a redirected run writes only inside it, that no module hard-codes a state path. CI **cannot** verify the **guarantee** from inside the suite, because *"a full run leaves operator state untouched"* is a statement **about** that run: the writes it must observe happen in sibling tests, in arbitrary order, and some in subprocesses. It needs a second invocation, which is a job step, not a test.
>
> CI's bytes are synthetic, but the property is about **paths**, not data — so an operator-only failure becomes CI-visible.

## 6. Tests changed, and why that is the honest direction

Seven fixtures monkeypatched private constants (`mapping.PROFILE_DIR`, `onboarding.REGISTRY_PATH`, and their container twins). Those constants are no longer what the resolvers read, so the patches silently stopped working. They now `monkeypatch.setenv("HRDASH_DATA_ROOT", …)` — **exercising the mechanism that ships instead of a bypass around it.**

One test asserted a path literal (`UNDECLARED_SENTINEL_DIR == "data/raw/__undeclared__"`). It now asserts the shape and the single definition, which is what the constant was for.

`test_no_script_hardcodes_a_state_path` is the enforcement a per-artefact fix could never have: an artefact stays isolated because it is **under the root**, not because someone remembered it.

## 7. A leak the shared root exposed

The built root is reused between runs for speed. A mapping profile written by `test_mapping_api` therefore **survived into `test_upload_flow`** and made its preview un-committable — cross-test contamination that a per-test `tmp_path` would not have had. `conftest` now clears `data/mapping` and `data/staging` at session start, and the profile tests write to their own roots.

Stated rather than buried: a shared root buys speed and costs isolation between tests, and both halves needed handling.

## 8. `conftest` also pins the report month

Two `test_contract_exceptions` tests failed on the operator's machine and nowhere else, because the repo `.env` carries `REPORT_MONTH` for the real load and `report_period` reads that **file** — so unsetting the variable was not enough. Now pinned to the demo month. That is GAP-002's benign form, closed.

## 9. Verification

| Check | Result |
|---|---|
| pytest | **549 passed** (536 + 13 new) |
| Isolation check | `PASSED - 62 file(s) byte-identical` |
| Isolation check, tampered | detects the regression |
| dbt | 161/161 models, 11/11 tests |
| Reconciliation | `PASSED (12 independent checks)` |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15` — now asserted from the suite's **own** demo build |
| flake8 (CI gate) | 0 |
| Client state | unchanged before → after |

## 10. Open

1. **`docs/PILOT-ROADMAP.md` (ruling 4) was not committed — it does not exist.** Not on disk, not in git history, not gitignored; and `PRODUCT-ARCHITECTURE.md` is tracked and clean with no pending changes. Authoring a pilot roadmap means writing scope, sequencing and client commitments that are the chief architect's to state, so it is raised rather than invented.
2. **The root is reused between runs.** Staleness is an mtime comparison against `scripts/`, `dbt_analytics/models/` and `data/contracts/`; `HRDASH_REBUILD_TEST_ROOT=1` forces a rebuild. A change outside those three paths that alters demo output would not trigger one.
3. **First-run cost.** Building the isolated root takes about ninety seconds once per machine, then it is reused. CI pays it every run.

---

**Not merged. Awaiting review.**
