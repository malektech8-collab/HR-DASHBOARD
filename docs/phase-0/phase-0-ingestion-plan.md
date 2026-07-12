# Phase 0 — Real-Data Ingestion (PLAN ONLY)

**Branch:** `phase-0/real-data-ingestion` (off `main` @ `a5998c69`). **Nothing implemented — this doc is the only change on the branch.**
**Highest-blast-radius change in Phase 0:** it lets `scripts/ingest_raw.py` load real HR data from `data/raw/` instead of only `data/sample/`, for local single-user use per the AGENTS.md carve-out.

**Prime directive (guardrail):** with `data_mode='demo'` and no `data/raw/` contents, the pipeline must behave **exactly** as today — byte-identical CI. Every design choice below defaults to the current behavior.

---

## 0. Verified current state (facts this plan is built on)

| Fact | Verified | Detail |
|---|---|---|
| `ingest_raw.py` reads only sample | ✅ | `files{}` map (lines 24–47) hardcodes `data/sample/{table}_sample.csv`; nothing reads `data/raw/`. |
| `.uploaded` freeze mechanism | ✅ | Written at [data.py:192-194](../../backend/app/api/data.py) on upload; read via monkeypatched `os.path.exists` in [ingest_raw.py:6-16](../../scripts/ingest_raw.py) (skips sample re-ingest) and monkeypatched `open` in [generate_sample_data.py:15-26](../../scripts/generate_sample_data.py) (skips sample regeneration). Freezes a table **indefinitely** until the marker file is manually deleted. |
| Stray markers present | ✅ | `data/silver/{payroll,emp_live,test}.parquet.uploaded` exist (host + container). `employees` marker was cleared in an earlier cycle. `emp_live`/`test` are orphan test tables (no dbt source references them). |
| `.gitignore` covers data tiers | ✅ | `data/raw/*`, `data/bronze/*`, `data/silver/*`, `data/gold/*` (lines 1–4). `git check-ignore -v` confirms a real drop at any tier is ignored. |
| `data/contracts/*.yml` enforced by code | ❌ **NOT** | `grep -rn contracts scripts/ backend/app` → no functional reference (only an unrelated `unit="contracts"` UI label). The contracts are **declarative-only**; there is no schema-enforcement code path today. Item 4 must build one. |
| REAL-SOURCEABLE set vs contracts | ⚠️ **mismatch** | Named real-sourceable: `employees, payroll, attendance, compliance, employee_relations`. Contract files present: `employees, payroll, attendance, compliance, hr_requests`. Overlap = 4. **`employee_relations` is named but has no contract; `hr_requests` has a contract but was not named.** See §Decision-1. |

---

## Decision-1 (needs chief-architect ruling): which tables are the real-sourceable set?

The named set and the contract set diverge on the 5th/6th table. Validation (item 4) requires a contract per real-sourceable table, so this must be resolved before implementation. Options:

- **(A, recommended)** Real-sourceable = the tables that have a formal contract **and** are named: `employees, payroll, attendance, compliance` (4 tables, fully covered). Treat `employee_relations` and `hr_requests` as **raw-eligible only once a contract is authored for them** — until then they stay sample-only. Safest; no un-validated real load.
- **(B)** Author a missing `employee_relations_schema.yml` contract in this cycle so the named 5-set is fully real-sourceable; leave `hr_requests` sample-only (not in the named set).
- **(C)** Real-sourceable = union of named + contracted (6 tables), authoring the one missing contract. Broadest.

The rest of this plan is written to work for whichever set is chosen; it refers to that set as `REAL_SOURCEABLE`.

---

## 1. Prefer `data/raw/{table}.csv`, fall back to sample — for `REAL_SOURCEABLE` only

**File:** `scripts/ingest_raw.py`.

**Change (design):**
- Replace the hardcoded `files{}` values with a **resolver** applied only to `REAL_SOURCEABLE` tables:
  ```
  def resolve_source(table, is_real_sourceable, data_mode):
      raw = f"data/raw/{table}.csv"
      sample = f"data/sample/{table}_sample.csv"
      if data_mode == "real" and is_real_sourceable and original_exists(raw):
          return raw, "raw"
      return sample, "sample"
  ```
  - **Synthetic-only tables always resolve to sample**, regardless of `data_mode` — they have no real feed and no contract.
  - `data/raw/{table}.csv` uses the **plain** table name (no `_sample` suffix), matching the schema-template filenames the upload UI already downloads.
- The per-table ingest bodies (type casting → bronze → silver, e.g. lines 50–67 for employees) stay **unchanged** — a real CSV and a sample CSV for the same table share the same schema/casting, so only the *source path* differs. Add a one-line `print(f"Ingested {table} from {tier} source")` for observability.
- **Bronze semantics:** bronze parquet is written from whichever source was chosen (raw or sample), preserving the current "bronze = raw-as-loaded" meaning.

**Guardrail compliance:** on `demo` (or `real` with no `data/raw/{table}.csv`), `resolve_source` returns the exact sample path in use today → byte-identical output. The `data/raw` branch is only reachable when `data_mode='real'` **and** a real file is physically present.

**Risk:** Medium-High — this is the single most central file in ingestion. Mitigation: the resolver is additive and gated; the fallback path is the literal current path. Cover with the byte-identity check in §6.

---

## 2. `.uploaded` freeze: different behavior for raw-drop vs upload-API

**Problem:** the current marker means "a human uploaded this table via the API; never overwrite it from sample again." That protection makes sense for the **upload-API** path, but a **raw-drop refresh** (drop a fresh CSV in `data/raw/`, re-run pipeline) should pick up the new file **every time** without anyone hand-deleting a marker (this is exactly the trap that silently froze `employees` earlier).

**Recommendation (cleanest): the raw-drop path bypasses the marker check entirely.**
- The marker's monkeypatch in `ingest_raw.py` keys on `path.startswith("data/sample/")`. When the resolver returns a **`data/raw/` path**, that prefix check does not match, so the marker logic is naturally skipped — **raw ingest already ignores markers by construction.** The design in §1 should make this explicit/intentional (comment + a guard), not incidental.
- Rationale: raw is the operator's deliberately-placed source of truth for `real` mode; re-running should always reflect the current file. There is no "accidental overwrite of a manual upload" risk because raw *is* the manual input.
- **Do not** write `.uploaded` markers on raw ingest. Markers remain an upload-API-only concept.

**Secondary cleanup (recommend, low-risk):** the upload-API marker mechanism itself is fragile (freezes forever, no UI to clear, already stranded 3 stray markers). Options to include or defer:
- Leave upload-API behavior exactly as-is this cycle (minimize blast radius) — **recommended for this cycle**; only ensure raw ingest is marker-immune.
- Follow-up cycle: give markers a TTL or a clear-marker endpoint, and purge the 3 stray markers (`payroll`, `emp_live`, `test`). Flagged, not done here.

**Risk:** Low for the raw path (marker-immune by prefix). The stray `payroll` marker matters **today**: with the current sample-only pipeline, `payroll` sample re-ingest is still being skipped — worth purging as pipeline hygiene (call out in §Decision-2).

## Decision-2 (ruling): purge the 3 stray markers now, or leave them?
`data/silver/{payroll,emp_live,test}.parquet.uploaded` are local, gitignored runtime artifacts. Recommend the implementation cycle **deletes them** (they are stale test residue and `payroll` is actively suppressing sample re-ingest). This is local-state cleanup, not a code change, and does not affect CI.

---

## 3. Interaction with `data_mode`

- **`data_mode` is the master gate.** `real` is the *only* mode in which `data/raw/` is ever consulted. `demo` must never read `data/raw/` even if a file is physically present (protects CI and demos from a stray local file).
- `ingest_raw.py` currently receives no mode; **plumb `data_mode` in** the same way the rest of the pipeline already does — read `os.getenv("DATA_MODE", "demo")` (the `.env` is already loaded at the top of `build_warehouse.py` via `load_dotenv`; `refresh_all.py` → `ingest()` runs in the same process, so the env is present). Pass it into `ingest()` (arg with a `demo` default) rather than reading env deep inside, for testability.
- **Consistency with dbt:** `build_warehouse.py` already injects `data_mode` into dbt `--vars` from the same `DATA_MODE` env. So one env var drives ingest **and** dbt **and** the backend — no new source of truth.
- **`real` with an empty `data/raw/`:** resolver falls back to sample for every table → behaves like demo for data, but `data_mode='real'` still (correctly) suppresses the fabricated trend rows in the marts. This is a valid "real mode, no data yet" state, not an error. (Optionally: print a clear warning per table that fell back to sample under `real`.)

**Risk:** Low. The gate is a single `if data_mode == 'real'`.

---

## 4. Validation against `data/contracts/*.yml` — reject, never guess

**New component (does not exist today):** a schema-validation step that runs **before** a real CSV is accepted into bronze/silver.

**Design:**
- New helper (e.g. `scripts/validate_schema.py` or a function in `ingest_raw.py`) that, for a `data/raw/{table}.csv` about to be ingested, loads `data/contracts/{table}_schema.yml` and checks the CSV **header + types** against it:
  - **Required columns present** (contract `required: true`) — missing → reject.
  - **No unexpected columns** — a column not in the contract → reject (prevents silently ingesting a mis-exported file). (Could be a warning instead of hard-reject — see Decision-3.)
  - **Type conformance** — each column parses as its declared `type` (DATE/DECIMAL/BOOLEAN/VARCHAR/INTEGER); unparseable → reject with the offending column + row count.
  - **`allowed_values`** where the contract specifies them (e.g. employees `status`) — violations → reject.
- **Hard-fail, whole-table, with a clear error.** On any violation: do **not** write bronze/silver for that table, raise a descriptive error naming the file, the failing column(s), and the rule. **No partial load** (a partially-loaded real table produces silently-wrong KPIs — worse than a clean stop).
- **No auto-coercion / no column-mapping guesses.** If the header doesn't match the contract, the operator fixes the CSV (or the contract) — the pipeline never renames/reorders/infers. This is explicit in the guardrails.
- **Fail-closed for the run:** recommend the whole `refresh_all` aborts if any `REAL_SOURCEABLE` raw file fails validation, rather than falling back to sample for that one table (a silent raw→sample downgrade mid-load would mix real and synthetic — confusing and unsafe). Surface the error; let the operator decide.

**A table with no contract cannot be raw-loaded** — ties back to Decision-1. If `employee_relations` is to be real-sourceable, its contract must exist first.

**Guardrail compliance:** validation only runs on the `data/raw/` path, which is only reachable in `real` mode. `demo`/CI never invokes it → byte-identical.

## Decision-3 (ruling): unexpected-column handling — hard-reject vs warn?
Recommend **hard-reject** (safest; an unexpected column usually means a wrong/renamed export). If operators find real exports routinely carry extra benign columns, downgrade to "warn + ignore extras" in a follow-up. Chief-architect to rule.

**Risk:** Medium — new code, but fully isolated to the real path; zero effect on demo.

---

## 5. No real data can be committed — confirmation

- **`.gitignore` proven** (verified): `data/raw/*`, `data/bronze/*`, `data/silver/*`, `data/gold/*` all ignored; `git check-ignore -v` confirms `data/raw/employees.csv`, and each downstream tier, are ignored.
- **This change writes real data only to gitignored tiers:** ingest writes bronze/silver under `data/{bronze,silver}/`; dbt/validate write `data/gold/` and `warehouse/*.duckdb` (also gitignored). The resolver **reads** `data/raw/` (operator-placed) and never writes there. No real data is written anywhere outside the gitignored tiers.
- **No new commit surface:** the plan adds code (`ingest_raw.py`, a validator) and reads/writes only gitignored data dirs. It does not add any tracked file under a data path.
- **Residual watch-items (call out, don't change here):** `data/real_*/` stays `.gitkeep`-only (simulation zone, untouched by this cycle); ensure the implementation never routes real data into `data/real_*` (those are the governance-simulation dirs, not the ingest path). The ingest path is strictly `data/raw/` → `data/bronze/silver/gold/`.

---

## Proposed implementation order (for the execute cycle — not now)
1. Resolve **Decision-1/2/3** with the chief architect.
2. Plumb `data_mode` into `ingest()` (arg, default `demo`).
3. Add the raw/sample resolver for `REAL_SOURCEABLE`, marker-immune on the raw path.
4. Add the contract-validation helper; wire it as a hard gate on the raw path; fail-closed on the run.
5. (If ruled) author `employee_relations_schema.yml`; purge the 3 stray markers.
6. Prove byte-identical `demo` CI (build_warehouse + dbt 157/11 + pytest 8p/2f) and a `real`-mode dry run with a **synthetic** CSV placed in `data/raw/` (never real data) to exercise resolver + validation + reject paths.

## Guardrails restated
Plan only — no files touched beyond this doc. No real data accessed, requested, or generated. `demo` + empty `data/raw/` = byte-identical to today.

---

**Branch:** `phase-0/real-data-ingestion` · **Plan file:** `docs/phase-0/phase-0-ingestion-plan.md`

STOP — awaiting chief-architect review (esp. Decisions 1–3).
