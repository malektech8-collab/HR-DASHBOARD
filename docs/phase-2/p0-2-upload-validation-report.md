# P0-2 — Upload Validation (Execution Report)

**Branch:** `phase-2/p0-2-upload` off `main` @ `e9210b2` · **Date:** 2026-08-11
**Status:** executed, committed, pushed, PR open. **Not merged.**
**Plan:** [`p0-2-upload-validation-plan.md`](p0-2-upload-validation-plan.md) (approved, five answers accepted)

Every safeguard built since cycle 1b-i protected `data/raw/` + `build_warehouse`. `POST /api/data/upload` wrote to `data/silver/` and protected none of them. There is now one ingest path.

---

## 1. Proof (a) — a mismatched filename can no longer target another table

```
  2. a mismatched filename
     filename         : payroll.csv
     target table     : employees   <- from the request
```

`table` is a required parameter checked against `data/contracts/`. It was `os.path.splitext(filename)[0]`, so `payroll.csv` renamed `employees.csv` replaced the employee master, and `employees (3).csv` created a table called `employees (3)`. Four tests cover it: the target comes from the request, a table is required, it must be contracted, and a filename with punctuation creates nothing.

`.parquet` is refused with the precondition in the message, so it reads as *not yet*:

> Parquet uploads are not accepted yet. Contract validation reads CSV rows and reports the row and column of each violation; accepting parquet requires the same rules running against a dataframe, which is planned but not built.

---

## 2. Proof (b) — unvalidated data cannot reach silver by any path

End to end, real mode, an employees file whose `joining_date` is `1820-01-15`:

```
  1. a file the contract rejects
     staged as        : 41e1dca7 | silver: EMPTY
     rejects          : 3
     first reject     : Row 2, Joining Date: date '1820-01-15' is outside the
                        plausible range (1940-01-01 to 2028-…)
     can_commit       : False
     commit status    : 400
     silver after     : EMPTY
```

The 1b-i DATE-range rule now fires on the UI path, because the preview runs **`validate_schema.validate_csv` — the same function ingest runs**, not an equivalent one.

Structurally, a test walks the whole API with `ast` and fails if any route writes to, or even *resolves*, `data/silver`. Only `scripts/ingest_raw.py` may put a file there.

> That test failed on its first run — on its own prose. It scanned raw text, and the docstring *"Nothing here writes silver"* sits near a `shutil.copy2` that targets `data/raw`. Rewritten to parse the AST and inspect call targets. Worth recording: a structural guard that matches comments is a guard that will be silenced by someone editing a comment.

---

## 3. Proof (c) — the 17-table divergence is gone

```
[p0-2] tables typed by the single ingest path: 21
```

`compile_csv_to_parquet` is **deleted**, not fixed. Three tests hold the line:

- `compile_csv_to_parquet` no longer exists, and `derive_column` is not referenced anywhere in the API
- the API contains **no** `str.to_date`, `cast(pl.Float64`, `cast(pl.Int64`, `cast(pl.Boolean` or `write_parquet` — there is nothing left that knows a column's type, so there is nothing left to diverge
- `ingest_raw` still types **21** tables including `hr_requests`, so consolidating did not quietly drop a table from the path that survived

The second is the one that matters. The old defence was a comment saying the two paths "must behave identically"; the new one is that only one of them can express a type.

---

## 4. The flow, working

```
  3. commit without the declaration
     status : 400
     detail : 'employees' feeds point-in-time history: history_since is required…

  4. commit claiming history the file cannot support
     status   : 400
     detail   : Pipeline rejected the upload and it was rolled back.
     data/raw : ['.gitkeep']          <- restored
     registry : MISSING               <- restored

  5. commit with a supported declaration
     status           : 200
     pipeline         : success in 24.6 s
     data/raw         : ['.gitkeep', 'employees.csv']
     registry         : declared: [employees] | history: employees: since 2024-01-15
     employees rows   : 3
     is_saudi derived : [(True,)]
     provenance       : ('employees', True, 2024-01-15)
```

Arm 4 is Category F's history guard firing through the API: the file's earliest record is 2024-01-15 and the declaration claimed 2020-01-01. The rollback restored both `data/raw` and the registry. Arm 5 shows the declaration reaching `domain_provenance`, and `is_saudi` derived — by `ingest_raw`, not by a copy of it.

**Coverage is suggested, never applied.** The preview returns `suggested_coverage_start` / `_end` from the file's date range, and the commit still refuses without an explicit declaration — ruling 3 of Category F: a suggestion a human confirms is a declaration; an inferred value applied silently is not. Tested.

---

## 5. Two defects the end-to-end run exposed that the unit tests did not

**(a) Rollback did not undo a first-ever declaration.** It restored a *previous* registry but left a *new* one behind, so a failed first commit left a declaration with no data. The declared-domain guard would then abort every later run with "declared but EMPTY" — loud, but a mess the operator has to clean by hand after a commit that was supposed to have rolled back. `_restore()` now restores both to "not existing" as well as to their previous contents.

**(b) A `None` stdout turned a successful pipeline into a 500.** `RefreshReport` requires `str`; a `None` failed validation *after* the pipeline had already run and written silver, and the handler then rolled back data that had landed. `or ""` at the boundary.

Both are the same shape: an error path that fires after the work is done.

**What rollback still does not do**, stated plainly: it restores `data/raw` and the registry, not `data/silver`. After arm 4, silver held the partially-built state of a rejected commit. That is survivable only because of step 2b — with `build_warehouse` aborted, `domain_provenance` does not exist, and in real mode `provided_domains` then returns the empty set, so **every figure is suppressed rather than served from a rolled-back upload.** Default-deny catching a failure three cycles later is the design working, but it is a backstop, not a rollback.

---

## 6. The `.uploaded` marker is gone

Writer and both readers. It existed so sample regeneration would not clobber a manual upload into silver; nothing uploads into silver now, and `refresh_all` no longer calls `create_sample_data()` at all in real mode — which was itself unconditional and is fixed here.

It is the one mechanism in this codebase with a known incident: a stale marker froze employees ingest and zeroed four Attendance widgets while every check reported green. A test asserts no code path writes one.

---

## 7. Authentication

Folded into step 1 as its own commit, per ruling. `POST /api/data/upload`… and every new endpoint requires `get_current_user` **from the start** — six routes, parametrised in a test that fails if any is open.

The synthetic-JWT layer and `MOCK_USER_DB`'s shared secret are untouched. **Logged for Phase 3 hardening:** review the synthetic-JWT layer and `MOCK_USER_DB` — passwords are compared in plaintext against a dict literal.

---

## 8. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 158/158, 11/11, PASSED |
| Demo API | unchanged; `/api/data/uploads` is 401 as intended |
| Rejected file reaches silver | **no** — `silver after: EMPTY` |
| Filename decides the table | **no** — `payroll.csv → employees`, from the request |
| Tables typed by the API | **0** (was 5, against ingest's 21) |
| Tables typed by ingest | 21, `hr_requests` included |
| Routes requiring auth | 6/6 |
| `.uploaded` written anywhere | **no** |
| `tsc -b` | 0 errors |
| pytest | **205 passed** (183 + 22 new) |

---

## 9. Open

1. **No UI.** Steps 1–4 of the sequencing are done; step 5 (the frontend flow) is not, and `uploadFile()` in `api.ts` still points at the removed `POST /api/data/upload`. It was already dead — no page called it — but it is now dead *and* wrong, and should be rewritten with the UI.
2. **Commit is synchronous**, with the timeout raised 180s → 900s. A real dataset may still exceed it; a background job with a status endpoint is the answer when it does.
3. **Batch upload.** One file per commit. Five files is the realistic case and changes the rollback story.
4. **Excel.** A client's answer to "CSV only" will be "I have an .xlsx". Follows the Phase 1 template work.
5. **Phase 3 hardening:** the synthetic-JWT layer (§7).

---

**Not merged. Awaiting review.**
