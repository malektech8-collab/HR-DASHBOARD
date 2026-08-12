# Onboarding UI (Execution Report)

**Branch:** `phase-2/upload-ui` off `main` @ `aa51f84` · **Date:** 2026-08-12
**Status:** executed, committed, pushed, PR open. **Not merged.**
**Plan:** [`upload-ui-plan.md`](upload-ui-plan.md) (approved, six rulings) · **Closes:** TD-005

The pipeline existed and nobody could reach it. A file now goes upload → validate → preview → declare → commit through the UI.

---

## 1. The proof

The exact sequence the page performs, against a real backend in real mode.

### Before sign-in

```
GET  /api/data/onboarding-status -> 401
POST /api/data/uploads           -> 401
```

### REJECT — the file is wrong, commit is blocked

A file named `Book1 (final).csv`, with two corrupted date serials and one bad enum:

```
staged     : a2f28197 | filename: Book1 (final).csv -> table: employees
rows       : 3
REJECTS    : 3      EXCEPTIONS: 0      can_commit: False

  row 2    joining_date   Row 2, Joining Date: date '0025-01-26' is outside the plausible range…
  row 3    joining_date   Row 3, Joining Date: date '0025-02-11' is outside the plausible range…
  row —    status         Employment Status: value(s) ['Actif'] are not allowed. Allowed values:…

Arabic     : الصف 2، تاريخ الانضمام: التاريخ '0025-01-26' خارج النطاق المعقول (1940…

grouped BY COLUMN (what the page shows first):
  joining_date   2 rows  [2, 3]
  status         1 row

commit     : 400 | silver: []
```

The corrupted date serial is the exact case `PRODUCT-ARCHITECTURE` §4 names as a real-world issue, and the filename is the kind a client actually sends. Neither the name nor the extension decided anything.

### EXCEPTION — the file loads, the problems surface on Data Quality

```
REJECTS: 0   <- commit is allowed
can_commit: True    history_required: True
button label: "Commit"      (with exceptions: "Commit — N data-quality exceptions will be recorded")
commit: 200 in 26.9s
```

### The checklist afterwards

```
data_mode: real | period: 2026-08
   Attendance           not provided       0 rows
   Compliance           not provided       0 rows
   Employee Relations   not provided       0 rows
   Employees            provided           3 rows  history since 2024-01-15
   HR Requests          not provided       0 rows
   Payroll              not provided       0 rows
   Recruitment          NOT AVAILABLE     32 rows
   Talent               NOT AVAILABLE     55 rows
```

The last two rows are the point of the screen. They have no contract, so they cannot be onboarded at all — different from "not uploaded yet", and a client shown "missing" for a domain they cannot provide will keep trying.

### The declaration

```
coverage_required : True
SUGGESTED         : 2026-08-03 -> 2026-08-04
commit WITHOUT it : 400 | 'attendance' is date-grained: coverage_start and coverage_end are required…
```

Suggested from the file, required at commit, and the UI additionally demands an active confirmation — a checkbox, not a pre-filled field the user can scroll past.

---

## 2. One HTTP client

`api.ts` had **77 fetch sites and not one Authorization header**, while `hooks/useGovernance.ts` held a complete auth client. `fetchWithAuth` moved to `lib/http.ts`; both callers route through it; 75 GET sites were rewritten mechanically and the two POSTs by hand.

A structural test bans `fetch(` outside `lib/http.ts`. It is a **Python** test scanning TypeScript, deliberately: CI runs `pytest backend/tests` and a typecheck, and nothing else — a vitest suite would not run, and **a guard that does not run in CI is decoration**. It also strips comments first, because the equivalent guard in P0-2 failed on its own prose.

`ApiError` carries the status, so a page branches on `isUnauthorized` rather than string-matching a message.

---

## 3. Two corrections to what I reported in P0-2

**`uploadFile()` was NOT unreachable.** I wrote in the P0-2 report that nothing called it. `useDataManagement.useUploadMutation` wired it into a **Data Quality page upload widget** which:

- offered a hardcoded five-table list rather than the contracted domains
- **renamed the file client-side** to `{target}.{ext}` — a workaround for the filename-derived table that P0-2 removed
- told the user the CSV would be *"routed directly to the Silver layer"*, which was the defect

So P0-2 did not merely remove a dead endpoint; it broke a live widget, and the breakage was invisible because the frontend has no CI test job. The widget is now a link to Data Onboarding. TD-005's entry carries the correction.

**A server path was leaking into client-facing errors.** Five violation messages embedded `csv_path`. Before the UI those only reached an operator's console; now they render in a browser and go into a downloadable report — and after P0-2 the path is `data/staging/<uuid>/data.csv`, which leaks our filesystem layout and tells the reader nothing about their own file. Found by reading the rig's output rather than by a test:

```
before: [employees] D:\workspace\repos\HR-DASHBOARD\data\staging\9a845aa6-802f…: column 'status' has value(s) ['Actif']…
after : Employment Status: value(s) ['Actif'] are not allowed. Allowed values: […]
```

All five fixed, and the message now uses the bilingual label rather than the raw column name, matching the other rules.

---

## 4. Error presentation

**By column, by default** — the shape of the fix. A user opens one column in their spreadsheet; they do not walk 43 unrelated rows. It also collapses the commonest real case (one bad export column, hundreds of violations) into a single line. A by-row view is one click away.

**A downloadable CSV error report**, because the fix happens in Excel and a browser tab does not survive the context switch. It carries `severity, row, column, rule, message_en, message_ar` — and per ruling 5, the true totals plus an explicit truncation line when the validator's 100-violation cap is hit:

> `NOTE: the validator reports at most 100 violations per severity. N are listed here and there may be more. Fix these and re-upload to see the next batch.`

**Raising the cap was not done.** It is a validator change and it stays out of scope.

---

## 5. REJECT vs EXCEPTION

Two regions, never one severity-sorted list — they differ in *what happens next*, not in how bad they are.

| | REJECT | EXCEPTION |
|---|---|---|
| copy | "must be fixed before this can be committed" | "do not block the upload… will appear on the Data Quality page" |
| colour | `critical` | `warning` |
| commit | disabled, with the count | enabled, and the **label** carries the consequence |

---

## 6. What was built

| | |
|---|---|
| `lib/http.ts` | the one client: token, 401 handling, `ApiError` |
| `lib/uploads.ts` | stage / preview / commit / discard / list, the onboarding read, the error report, `groupByColumn` |
| `pages/DataOnboarding.tsx` | two tabs — Progress and Upload — plus the scoped login |
| `components/widgets/OnboardingStatusTable.tsx` | reuses `NotProvided` and `CoverageNote` |
| `components/widgets/ViolationPanels.tsx` | the two panels, both views, the report download |
| `GET /api/data/onboarding-status` | a read of `domain_provenance`; registered in the provenance registry |

**The registry guardrail fired, as designed.** `domain_provenance` is not a `mart_`/`base_` object, so the coverage test could not see the API reads it. I **widened** `API_REF` to include it — that strengthens the rule ("an API-served object must be mapped") by removing a naming assumption — and added the entry to the source-free pin with its justification: the onboarding checklist *reports* provenance rather than carrying a client measure, and suppressing it would hide the screen that explains the suppression.

One backend fix from the rig: `get_onboarding_status` resolved `conn` before `current_user`, so with no warehouse an unauthenticated request 500'd instead of 401'ing. Authentication is now decided before the database is opened.

---

## 7. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 158/158, 11/11, PASSED |
| `fetch(` outside `lib/http.ts` | **0** |
| `uploadFile` / `/api/data/upload` anywhere in `frontend/src` | **0** — TD-005 closed |
| REJECT blocks commit, end to end | 400, `silver: []` |
| EXCEPTION commits | 200 in 26.9s |
| Coverage required and suggested | 400 without it; `2026-08-03 → 2026-08-04` suggested |
| Server paths in violation messages | **0** (was 5) |
| `tsc -b` / `npm run build` | 0 errors / passes |
| pytest | **222 passed** (205 + 17 new) |

---

## 8. Open

1. **TD-007 — RTL/i18n**, scheduled next per ruling. The violation list is the densest Arabic in the product and mixed Arabic/English in an LTR table is legible but not good.
2. **TD-008 — the template is 23 bare headers**, not the formatted bilingual Excel `PRODUCT-ARCHITECTURE` §4 specifies. The UI makes the gap sharper: the flow says "download the template, fill it", and the template does not carry enough to fill it correctly. Dropdown validation on enum columns would have prevented the `Actif` rejection in §1.
3. **No frontend test job in CI.** The structural guards run in pytest, which is why they run at all. That is a workaround; the P0-2 widget breakage would have been caught by a real frontend test suite. Worth its own small cycle.
4. **Commit is synchronous** (900s timeout) with a progress message but no per-stage detail.
5. **Mapping profiles** (§4) — a client whose export has their own column names still cannot onboard; the UI surfaces "unexpected columns" but cannot reconcile them.

---

**Not merged. Awaiting review.**
