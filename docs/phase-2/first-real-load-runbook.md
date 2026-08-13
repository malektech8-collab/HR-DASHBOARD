# First Real Load — Operator Runbook

**Scope: `employees` only.** One domain, one file, one pass.
**Platform:** Windows / PowerShell · **Repo:** `D:\workspace\repos\HR-DASHBOARD` · **Python:** the repo `.venv`

Every command below was run before it was written down. Where output is quoted, it is real output from a synthetic placeholder file — **no client data was used to write this document, and none should be pasted into it.**

> **The other five domains will show nothing, and that is correct.** Payroll, attendance, compliance, employee relations and HR requests have not been provided, so their figures are *withheld*, not computed. §6 shows exactly what that looks like. A dashboard that showed numbers for a domain you have not uploaded would be inventing them.

---

## 0. Before you touch a real file

Two things in this repo's `.env.example` were wrong until 2026-08-13. If your `.env` predates that, fix both or nothing will start.

```powershell
cd D:\workspace\repos\HR-DASHBOARD
Get-Content .env | Select-String -Pattern 'VITE_API_URL|DATABASE_PATH'
```

If either line appears **uncommented**, comment it out:

| Line | Why it breaks |
|---|---|
| `VITE_API_URL=...` | A frontend variable in the shared `.env`. The backend refused to start: `ValidationError: 1 validation error for Settings / vite_api_url  Extra inputs are not permitted`. Now tolerated, but a stale `.env` on an older build still fails. |
| `DATABASE_PATH=../warehouse/hr_analytics.duckdb` | Relative, and correct only from `backend\`. Run from the repo root — as the pipeline and uvicorn both are — it resolves **outside the repo**, and every endpoint fails with `duckdb.IOException: Cannot open file "...\repos\hr-dashboard\..\warehouse\hr_analytics.duckdb"`. Leave it unset; `config.py` computes the right absolute path itself. |

---

## 1. Preconditions

### 1.1 Create `.env`

```powershell
cd D:\workspace\repos\HR-DASHBOARD
Copy-Item .env.example .env
```

### 1.2 Generate the auth secret

```powershell
& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Verified output shape (86 characters — **yours will differ, and must**):

```
pSlI-tTEA-FxEdmI6MKUbW2_l6-w8w_nfwrKzymZlRHiehJD3DQno0-G4vBkPpTQoGO97wHlmbZaxQy4SYfHkg
```

Paste it into `.env` as `JWT_SECRET=`. **Generate a fresh one per deployment.** A shared secret means a token minted for one client's install works at another's.

### 1.3 The three variable names, quoted from the code

| Variable | Defined at | Value for this run |
|---|---|---|
| `JWT_SECRET` | `backend/app/config.py:45` — `JWT_SECRET: str \| None = None` | the string from 1.2 |
| `DATA_MODE` | `backend/app/config.py:15` — `DATA_MODE: str = "demo"` | `real` |
| `REPORT_MONTH` | `backend/app/config.py:21` — `REPORT_MONTH: str \| None = None` | `YYYY-MM`, or leave unset |

`DATA_MODE` is read by the pipeline from the same file — `scripts/build_warehouse.py:246`:

```python
    if os.getenv("DATA_MODE", "demo") == "real":
```

and `scripts/build_warehouse.py:11-12` loads the repo-root `.env` **before** any variable is read, so one file drives both.

`REPORT_MONTH` is resolved by `scripts/report_period.py:107`:

```python
    raw = os.getenv(SETTING_NAME, getattr(settings, SETTING_NAME, None) or "")
```

Leave it unset and real mode derives the period from your payroll close, then compliance — **and aborts if neither is present.** On an employees-only first pass there is no payroll file, so **set it explicitly**:

```
DATA_MODE=real
REPORT_MONTH=2026-06
JWT_SECRET=<the string from 1.2>
```

### 1.4 Verify git ignores everything that will hold client data — BEFORE the file arrives

```powershell
foreach ($p in @('.env','data\raw\employees.csv','data\auth\auth.db','data\mapping\employees.yml','data\staging\x\data.csv','data\onboarding\declared_domains.yml')) {
  $r = & git check-ignore -v $p 2>&1
  if ($LASTEXITCODE -eq 0) { Write-Output ("IGNORED      {0}" -f $p) } else { Write-Output ("NOT IGNORED  {0}  <-- STOP" -f $p) }
}
```

Verified output — all six must say `IGNORED`:

```
IGNORED      .env
IGNORED      data\raw\employees.csv
IGNORED      data\auth\auth.db
IGNORED      data\mapping\employees.yml
IGNORED      data\staging\x\data.csv
IGNORED      data\onboarding\declared_domains.yml
```

> **Check a file path, not a directory.** `git check-ignore data\staging` returns *not ignored* — the rule is `data/staging/*`, which covers the contents, not the folder. That is why the list above names a file inside it. Do not read that result as a failure.

**If any line says NOT IGNORED, stop and fix `.gitignore` before the client's file goes anywhere near this directory.**

---

## 2. Create the first administrator

No account exists on a fresh deployment, and none is created for you — that is deliberate. Until one exists, every authenticated route answers `503`, not `401`: the deployment is not set up, rather than refusing you.

```powershell
cd D:\workspace\repos\HR-DASHBOARD\backend
& ..\.venv\Scripts\python.exe -m app.cli list-users
```

Verified output on a fresh store:

```
No users. This deployment has not been initialised.
```

Then:

```powershell
& ..\.venv\Scripts\python.exe -m app.cli create-admin --email operator@client.example
```

You will be prompted twice. **The password is never echoed, never in your command line, and never in your PowerShell history.**

```
Password (min 12 chars):
Repeat:
Created operator@client.example as SYSTEM_ADMIN.
Store: D:\workspace\repos\HR-DASHBOARD\data\auth\auth.db
```

Confirm:

```powershell
& ..\.venv\Scripts\python.exe -m app.cli list-users
cd D:\workspace\repos\HR-DASHBOARD
```

```
  operator@client.example            SYSTEM_ADMIN   active
```

### What refusals look like (all verified)

```
Password must be at least 12 characters. This is the only credential guarding a client's employee records.
Passwords do not match. Nothing was created.
Unknown role 'ANALYST'. One of: SYSTEM_ADMIN, HR_ANALYST, EXECUTIVE
```

> **The prompt needs a real console.** `getpass` reads the terminal directly, so it **hangs** under `docker exec` without `-it`, in a CI step, or through a pipe. Use `docker exec -it`, or use the one-time bootstrap token below.

### 2.1 The token alternative (no interactive shell)

On a deployment with zero users the backend prints this to its log at startup:

```
====================================================================
 THIS DEPLOYMENT HAS NO USERS.

 Create the first administrator, either:
   python -m app.cli create-admin --email you@example.com
 or POST /api/governance/bootstrap with this one-time token:

   <64 characters>

 Single use. Expires in 60 minutes. Not stored on disk, and
 destroyed the moment the first account exists.
====================================================================
```

```powershell
$body = @{ token = '<paste the token>'; email = 'operator@client.example'; password = '<a strong password>' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/governance/bootstrap -ContentType 'application/json' -Body $body
```

Verified: wrong token → `401`. Correct token → `200 {"email": "...", "role": "SYSTEM_ADMIN"}`. The same token again → `409`.

---

## 3. Author the mapping profile

Your client's export will not use the canonical column names. The profile is how you record what their headers mean — once, reusably, with your name on it.

**Placeholder headers only in this document.** The shapes below come from `data/contracts/employees_schema.yml`'s own `name_ar` values. Substitute the client's actual headers when you run it; do not paste them back into this file.

### 3.1 Propose

```powershell
cd D:\workspace\repos\HR-DASHBOARD
& .\.venv\Scripts\python.exe scripts\mapping_cli.py suggest --table employees --file "C:\path\to\their-export.csv" --out decisions.yml
```

Verified output against a 24-header placeholder:

```
wrote decisions.yml
  22 proposed, 2 need a decision: ['ملاحظات', 'Column14']
  affirmation required for: ['end_of_service_type', 'status']
```

### 3.2 Edit `decisions.yml`

The file arrives with the contract-derived matches filled in and their confidence noted:

```yaml
columns:
  "الرقم الوظيفي": employee_id   # label_exact (0.95)
  "الجنسيه": nationality         # label_normalised (0.85)
  # "ملاحظات":  # no suggestion; map it or move it to `ignored`
  # "Column14":  # no suggestion; map it or move it to `ignored`
```

**Every source header needs a decision.** Map it, or ignore it with a reason. There is no default-drop, because a renamed export would then lose a column silently.

**When a header has no canonical home** — free-text notes, an internal code, an empty column — move it to `ignored` with a reason a colleague can read in six months:

```yaml
ignored:
  - header: "ملاحظات"
    reason: "Free-text notes; no canonical home."
  - header: "Column14"
    reason: "Empty in every row."
```

Then the value vocabulary and the derived column:

```yaml
values:
  status:
    "نشط": Active
    "موقوف": Inactive

derive:
  is_saudi: {rule: nationality_is_saudi, from: "الجنسية"}
```

### 3.3 The affirmation — and what happens if you skip it

```powershell
& .\.venv\Scripts\python.exe scripts\mapping_cli.py save --table employees --file "C:\path\to\their-export.csv" --decisions decisions.yml --by operator@client.example
```

With `confirmations: {}` still empty, this is the **verified** result — exit code 2, nothing written:

```
REFUSED: refusing this mapping: the value mapping(s) below rewrite a client's own
words into canonical ones, and nobody has affirmed them.
  status (no confirmed_by): 'موقوف' -> 'Inactive', 'نشط' -> 'Active'
    Status decides who is counted as employed: headcount, Saudization and payroll
    exposure all read it.
```

**This is not a bug.** Mapping `موقوف` to `Inactive` changes who counts as employed, and it is invisible afterwards. Restate the pairs — that duplication *is* the affirmation:

```yaml
confirmations:
  status:
    pairs:
      "نشط": Active
      "موقوف": Inactive
```

Run the same command again. Verified:

```
affirming status: Status decides who is counted as employed: headcount, Saudization
and payroll exposure all read it.
   'موقوف' -> 'Inactive'
   'نشط' -> 'Active'
saved version 1 of employees to data\mapping\employees.yml
  22 mapped, 2 ignored, 0 undecided, 1 derived
  attributed to operator@client.example
```

Confirm:

```powershell
& .\.venv\Scripts\python.exe scripts\mapping_cli.py show --table employees
```

```
employees profile, version 1 by operator@client.example at 2026-08-13T14:40:49
  22 mapped, 2 ignored, 1 value vocabularies, 1 derived
  affirmed status by operator@client.example at ...: {'نشط': 'Active', 'موقوف': 'Inactive'}
```

> **`end_of_service_type` also requires affirmation** if you map any values into it. Article 80 is dismissal for cause and carries **no** end-of-service award — that mapping decides whether a leaver is owed money.

---

## 4. Upload → preview → declare → commit

Start the stack, sign in at the browser, and go to **Data Onboarding**. The four steps below are what the screen does; the verified figures are from the placeholder file.

### Step 1 — stage

The file is stored, hashed, and **nothing else happens**. It is not in `data/silver`, so nothing serves it; not in `data/raw`, so no pipeline picks it up.

```
   status        : 200
   upload_id     : 86ae0528-d3be-4b1f-aacb-03e2188aa734
   sha256        : 97454888bc5803cb ...
```

### Step 2 — preview

```
   rows          : 2
   mapping       : applied=True v1 | 22 renamed, 2 ignored, derived ['is_saudi']
   unmapped      : none
   rejects       : 0
   exceptions    : 0
   can_commit    : True
   coverage req  : False | history req: True
```

### Step 2b — a NORMAL rejection

A bad joining date, deliberately introduced:

```
   rejects       : 1 | can_commit: False
   rule          : date-range row 2
   YOUR column   : تاريخ الانضمام
   message       : Row 2, Joining Date: date '0025-02-11' is outside the plausible range
```

**This is the system working.** Note it names **their** column, not ours, and their row number. Send them the error report from the screen, get a corrected file, re-upload. Discard the staged one:

```
   discarded     : the staged file is removed, nothing reached silver
```

### Step 3 — declare and commit

```
   status        : 200
   pipeline      : success in 31.1 s
```

Thirty seconds to a few minutes is normal — the whole warehouse rebuilds.

### Normal rejection vs real failure

| | Looks like | Do |
|---|---|---|
| **Normal** | `rejects: N`, `can_commit: false`, each with a rule, a row, and *their* column name | Send the error report. Fix the file. Re-upload. |
| **Normal** | `exceptions: N` — the file still commits | Nothing. They appear on Data Quality for HR to work through. |
| **Real failure** | HTTP `500`, a Python traceback, `detail: "..."` from an unhandled error | §7. |
| **Real failure** | commit returns non-200, or the pipeline reports anything but `success` | §7. Nothing was committed — rollback restores `data/raw`. |
| **Config, not data** | `503` with *"this deployment has not been initialised"* | §2. |
| **Config, not data** | `503` naming `JWT_SECRET` | §1.2. |

---

## 5. Coverage and `history_since`

`coverage_required: False` for employees — coverage is for date-grained domains, which is attendance. `history_required: **True**` is the one you must get right.

**`history_since` is the date before which this file has no information.** Usually the client's earliest joining date, or the date their HR system went live.

**Get it wrong and here is exactly what happens:**

- **Too recent** (you say 2025-01 when the file reaches back to 2020) — every trend month before it is withheld. You lose reporting you were entitled to. Recoverable: re-upload with the right date.
- **Too early** — *this is the dangerous one.* You say 2020 when the file only reaches 2024. The trend marts will treat 2020–2023 as **measured and empty** rather than unknown, and report headcounts, joiners and leavers for years the client never gave you. Those numbers look plausible and are fabricated. **This is the single mistake in this runbook that produces a wrong number instead of a missing one.**

If you are unsure, **choose the later date.** A withheld figure is a question; an invented one is an answer that is wrong.

---

## 6. What the dashboard shows afterwards — and why five domains are blank

Verified after a successful employees-only load:

```
   workforce (employees)  -> 200  kpis=9
        withheld: iqama_expiring_30 <- missing ['compliance']
        message : Not yet provided: Compliance.
   payroll                -> 200  kpis=None (withheld)
        withheld: allowances_cost <- missing ['payroll']
   attendance             -> 200  kpis=None (withheld)
        withheld: absence_days <- missing ['attendance']
   compliance             -> 200  kpis=4
        withheld: gosi_missing_count <- missing ['compliance']
   employee relations     -> 200  kpis=None (withheld)
        withheld: average_case_aging_days <- missing ['employee_relations']

   employees rows in warehouse: 2
   is_saudi derived           : [(False, 1), (True, 1)]
   status mapped              : [('Active',), ('Inactive',)]
```

Read this carefully, because it is the point of the whole product:

- **Workforce serves 9 KPIs** — it runs on employees, which you provided.
- **Payroll, attendance and employee relations return `kpis: null`** — not zero, not an empty list. Every figure is withheld and named, with the domain that would supply it.
- **Compliance serves 4 and withholds the rest.** Saudization is computable from employees alone; GOSI and Iqama status are not. Partial is the honest answer, and the API says which half is which.
- **`is_saudi` was derived** from their nationality column, and **`status` was mapped** from their vocabulary.

**Every `200` with `kpis: null` is correct behaviour.** If you see a number for payroll before a payroll file exists, that is a defect — report it.

---

## 7. When it breaks

### Where to look, in order

```powershell
# 1. the API's own answer - it usually names the problem
#    (the browser devtools Network tab shows the same thing)

# 2. the backend log
docker compose logs backend --tail 200

# 3. what is actually declared
Get-Content data\onboarding\declared_domains.yml

# 4. what the profile says
cd D:\workspace\repos\HR-DASHBOARD
& .\.venv\Scripts\python.exe scripts\mapping_cli.py show --table employees

# 5. the file's SHAPE - headers and row count only
& .\.venv\Scripts\python.exe -c "import polars as pl,sys; d=pl.read_csv(sys.argv[1]); print(d.height,'rows'); print(list(d.columns))" "C:\path\to\their-export.csv"
```

### What to capture in a bug report

- the HTTP status and the `detail` string
- the rule name, the row number, the **column name**
- the file's **shape**: row count, the list of headers, the mapping profile version
- what you expected versus what you saw
- the last 50 log lines

### What must NOT go in a bug report

- **No employee rows.** Not one, not "just an example", not redacted-by-hand.
- **No cell values** from a non-vocabulary column — names, national IDs, salaries, phone numbers, Iqama numbers.
- **No screenshots showing data.** Crop to the message.
- **No `.env`, no `JWT_SECRET`, no `data/auth/auth.db`.**
- **No copy of their export.** Ever. Not into a ticket, a chat, or this repository.

Vocabulary values are the exception and are safe: `نشط`, `موقوف`, `Active` are the client's *terms*, not their people — and they are usually the thing in question.

> If you cannot describe the problem without a row of client data, describe it as a shape and say so. Someone will ask a better question.

### Starting over

A failed commit rolls back `data/raw` and the declaration; nothing serves a rejected upload. To reset a first load completely, delete `data/raw\employees.csv`, `data\silver`, `data\onboarding\declared_domains.yml` and `warehouse\hr_analytics.duckdb`, then re-run from §4. **Keep `data\mapping\employees.yml`** — the profile is the work, and it is reusable.

---

## 8. Known, and not your fault

| | |
|---|---|
| `GET /api/compliance/wps` returns **500** | `mart_wps_status` was never built. Known, tracked, does not affect anything else. |
| Everything Arabic is right-to-left in a left-to-right layout | TD-007. Labels and validator messages are Arabic; the chrome is English. |
| The template is 23 bare headers | TD-008. The mapping profile in §3 is the way around it. |
| Project-level figures are empty | You did not supply a `locations` file — this pass is employees only. Correct, not broken. |

---

**Written 2026-08-13. Every command in it was executed against synthetic input before being written down.**
