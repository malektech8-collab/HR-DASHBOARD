# Onboarding UI (PLAN ONLY)

**Branch:** `phase-2/upload-ui` off `main` @ `aa51f84` · **Date:** 2026-08-12
**Status:** plan only. Nothing implemented.
**Closes:** TD-005 · **Implements:** `PRODUCT-ARCHITECTURE.md` §4 · **Prior:** [`p0-2-upload-validation-report.md`](p0-2-upload-validation-report.md)

The pipeline exists and nobody can reach it. This is the last gap before real client data can go through the system end to end.

---

## 0. What I found before planning

**(a) The frontend already has an auth client — in the wrong place.** `api.ts` sends no `Authorization` header on any call. But `hooks/useGovernance.ts` has a complete one: `fetchWithAuth` reads `localStorage.auth_token`, sets the Bearer header, and clears the token on 401; `useLoginMutation` posts to `/api/governance/token` and stores the result.

This matters more than it looks. **P0-2 put auth on six routes, and `api.ts` cannot call any of them** — every upload request would 401 today. The temptation is to add a header inside the new upload module. That would be a second auth client, and the last four cycles have all been about what a second implementation costs. **The plan is to lift `fetchWithAuth` into a shared module and route both governance and `api.ts` through it.**

**(b) There is no login screen, only a widget.** `GovernanceWidget` has three "mock login" buttons (admin / exec / analyst) that call the same endpoint. That is a governance-demo affordance, not an authentication flow, and it is the only way to obtain a token today. An upload UI needs a real one — see §8, which is the one place this plan asks for a ruling rather than proposing.

**(c) Routing is a `useState` switch.** `App.tsx` holds `currentPage` and renders from a switch; `SidebarNavigation` holds a `menuItems` array. Adding a page is two small edits, not a router change. Good news for scope.

**(d) Two data-fetching styles coexist.** Pages use `useState` + `useEffect`; the governance widget uses TanStack Query, which is already a dependency. The upload flow is stateful and multi-step, so the plan uses TanStack Query — and says so rather than adding a third style by accident.

---

## 1. The flow, and where each endpoint attaches

One page, `Data Onboarding`, with a step rail. Each step maps to exactly one call — no step invents an endpoint.

| # | Step | Endpoint | Notes |
|---|---|---|---|
| 1 | **Pick a domain** | `GET /api/data/templates` | returns name, bilingual label, description, per contract. The picker IS the contracted-domain list, so an uncontracted domain cannot be chosen |
| 2 | **Download the template** | `GET /api/data/templates?name=` | header-only CSV today; the bilingual Excel generator is §4's deliverable and is **not** in this cycle (§9) |
| 3 | **Fill** | — | outside the product |
| 4 | **Upload** | `POST /api/data/uploads?table=` | drag-and-drop; the domain comes from step 1, never from the filename |
| 5 | **See validation results** | `GET /api/data/uploads/{id}` | REJECT vs EXCEPTION (§3); read-only and repeatable, so "re-check" is a button |
| 6 | **Preview** | same response | row count, columns present/missing/unexpected, detected period |
| 7 | **Declare coverage** | same response supplies the *suggestion* | required for date-grained domains and for `employees` history (§4) |
| 8 | **Commit** | `POST /api/data/uploads/{id}/commit` | runs the pipeline; a REJECT-blocked upload never gets here |
| — | Abandon | `DELETE /api/data/uploads/{id}` | reachable from every step after 4 |

Steps 5 and 6 are one request and one screen. Separating them in the UI would imply a second validation pass that does not exist.

**The loop that matters is 4 → 5 → fix → 4.** A first real upload will fail, probably several times. The flow is designed around returning to step 4 with the errors still on screen, not around the happy path.

---

## 2. Error presentation — designed for acting, not reading

The validator emits bilingual, row-numbered, cell-level violations capped at 100 (`MAX_RENDERED_VIOLATIONS`). A flat list of 100 messages is technically complete and practically useless: the user's next action is to open their spreadsheet and change cells.

**Three views of the same violations, defaulting to the one that maps to that action:**

**(a) By column — the default.** Violations grouped by `column`, each with a count, the rule, one example message, and the affected row numbers.

```
تاريخ الانضمام / Joining Date          43 rows    expected YYYY-MM-DD
   rows 47, 48, 51, 52, 55 … (+38)     e.g. row 47: found '0025-01-26'
```

This is the shape of the fix: a user opens one column and fixes it, they do not walk 43 unrelated rows. It also collapses the commonest real case — one bad export column producing hundreds of violations — into one line.

**(b) By row.** For the opposite case: a handful of broken records rather than a broken column.

**(c) Download the error report — the important one.** A CSV the user opens **next to their file**:

```
row,column,column_ar,rule,severity,value,message_en,message_ar
47,joining_date,تاريخ الانضمام,date_range,REJECT,0025-01-26,"Row 47, Joining Date: date '0025-01-26' is outside…","الصف 47…"
```

Rationale: the fix happens in Excel, not in a browser tab. A downloadable report is the only artefact that survives the context switch, and it is the only way to hand the problem to whoever owns the source system.

> **The cap needs a decision the UI cannot make on its own.** The validator stops rendering at 100 violations. In the browser that is fine. In a downloadable report meant to be worked through, "here are 100 of your problems, there may be more" sends the user round the loop repeatedly. **Recommend the report carry the total count and an explicit truncation line**, and that raising the cap for the download path be considered separately — it is a validator change, not a UI one, so it is flagged rather than assumed (§9).

**Language.** Each violation already carries `message_en` and `message_ar`. The UI shows both in the report and follows the app locale on screen. Per the constraint, this is schema-derived labels and validator messages only — **it does not make the app RTL**, and §7 says where that stops being tenable.

---

## 3. REJECT vs EXCEPTION — visually distinct, because they mean opposite things

The distinction is not severity. It is **what happens next**, and the UI must say so in those terms:

| | REJECT | EXCEPTION |
|---|---|---|
| Meaning | the file is wrong | the *data* has a problem the business already has |
| Effect | **blocks commit** | loads, and appears on the Data Quality page |
| Who fixes it | whoever produced the export | HR, in the source system, over time |
| Colour | `critical` | `warning` |
| Verb | **"Fix and re-upload"** | **"Upload anyway — these will appear in Data Quality"** |

Two separate panels, never one list sorted by severity. Sorting implies a spectrum; these are different kinds of thing.

The commit button is disabled while `can_commit` is false, and its disabled state names the count: *"3 errors must be fixed before this can be committed."* When only exceptions remain, the button is enabled and **its label changes** to carry the consequence: *"Commit — 12 data-quality exceptions will be recorded."* A user who does not read the panels still cannot commit a rejected file, and still cannot commit exceptions without being told.

---

## 4. The declaration — suggested, confirmed, never applied silently

`GET /api/data/uploads/{id}` already returns `coverage_required`, `history_required`, and `suggested_coverage_start` / `_end` from the file's date range.

The UI renders the suggestion **into an editable field that starts filled**, with the commit button disabled until the user has actively confirmed — a checkbox, *"I confirm this file covers 1–14 August 2026"*, not merely a pre-filled input they can scroll past.

That distinction is Category F ruling 3 rendered honestly. A pre-filled field a human confirms is a declaration; a pre-filled field a human never looks at is inference wearing a costume. The API enforces the requirement regardless (`400` naming the field), so the UI cannot weaken it — but the UI is where the human either understands what they are asserting or does not.

For `employees`, `history_since` gets the same treatment, with the reason stated in one line: *"Historical months before this date will show as unavailable rather than estimated."* That sentence is why the field exists; without it the field is a form to be dismissed.

---

## 5. Onboarding state — the screen that makes partial onboarding legible

A second tab on the same page, and arguably the more valuable half. Source: `domain_provenance`, which `build_warehouse` already writes with `declared`, `row_count`, `provided`, `coverage_start/end`, `history_since`.

**This needs one new endpoint** — `GET /api/data/onboarding-status` — because nothing currently exposes that table. It is a read of an existing table, not a new computation, and it must be registered in `metric_provenance.yml` or the default-deny coverage test will fail, which is the guardrail doing its job.

| Domain | State | What it shows |
|---|---|---|
| Employees | ✅ provided | 20 rows · history since 2024-01-15 |
| Attendance | ⚠️ partial | 120 rows · **covers 6 of 27 working days** (1–7 Aug) |
| Payroll | ✅ provided | 59 rows · period 2026-08 |
| Compliance | ⬜ not provided | *Upload* → jumps to step 1 with the domain preselected |
| Recruitment | 🔒 not available | no contract yet — cannot be uploaded, and says why |

**Reusing the existing components, per the constraint:**
- `NotProvided` for a domain with no data — the same component the dashboard uses, so a user sees the same words in both places
- `CoverageNote` for the partial row — literally the same `CoverageItem` the API already returns

That reuse is the point: the onboarding screen should explain the dashboard's blanks using the dashboard's own vocabulary. Two components saying "not provided" in two ways would be the third parallel implementation this project keeps having to remove.

The fifth row is worth its own note. `recruitment` and `talent` have no contract, are never `provided` in real mode, and *cannot be onboarded at all* — the screen must say that plainly rather than showing them as merely missing, or a client will keep trying to upload them.

---

## 6. `uploadFile()` — the rewrite (TD-005)

Deleted and replaced by four functions in a new `lib/uploads.ts`, all going through the shared authenticated client:

```ts
stageUpload(table, file)          -> StagedUpload
previewUpload(uploadId)           -> UploadPreview
commitUpload(uploadId, declaration) -> RefreshReport
discardUpload(uploadId)           -> void
listUploads()                     -> StagedUpload[]
```

Types mirror the Pydantic models exactly. `TemplateInfo` already exists and needs no change.

**And the shared client.** `fetchWithAuth` moves from `hooks/useGovernance.ts` to `lib/http.ts`; `useGovernance` and `api.ts` both import it. One place that knows about the token, one place that handles a 401. A test asserts no `fetch(` outside `lib/http.ts` — the structural form, and the same technique that caught the silver writes in P0-2.

---

## 7. Arabic scope

Per the constraint: **schema-derived labels and validator messages only.** Column names come from `name_ar`, violations from `message_ar`, domain labels from the contract's bilingual text. The chrome — navigation, buttons, headings — stays English, and the layout stays LTR.

**Where the design pushes on that, honestly:** the error report and the violation list are the densest Arabic in the product, and mixed Arabic/English in a LTR table renders acceptably but not well — column alignment and punctuation both suffer. It is legible and it is not good. This does not force RTL *in this cycle*, and the error report being a downloadable CSV takes the worst of it out of the browser. But **the onboarding screen is where a real Arabic-first HR user meets the product**, and it is the strongest argument yet for the RTL cycle. Recommend scheduling it after this lands with real screens to look at, rather than pre-emptively.

---

## 8. The one ruling this plan needs: how does a user log in?

Every endpoint in §1 requires `get_current_user`. Today the only way to obtain a token is three "mock login" buttons inside `GovernanceWidget`.

Three options, and I do not think this is mine to choose:

1. **Reuse the mock-login buttons** — zero work, and the upload page becomes reachable only via a governance widget on another page. Coherent for a demo, incoherent for a client.
2. **A real login screen** gating the app, using the endpoints that already exist. The honest shape, but it is an app-wide change (an unauthenticated state, a redirect, a logout) landing inside an onboarding cycle — the same bundling objection I raised in P0-2 and which was correctly overruled *there* because the fix was one line per route. Here it is not.
3. **A login prompt inside the onboarding page only.** The upload page asks for credentials when it needs them, everything else stays open. Smallest change that makes the flow usable by someone who is not us, and it is honest about the fact that only these routes are protected.

**Recommend 3 for this cycle**, with 2 as its own small cycle once TD-006 (real password hashing) is addressed — building a real login screen on top of plaintext comparison against a dict literal invites treating it as finished.

---

## 9. Explicitly out of scope

1. **The bilingual Excel template generator** (`PRODUCT-ARCHITECTURE` §4 step 1) — instructions sheet, dropdowns, example rows. Step 2 serves the existing header-only CSV. This is a real gap for a non-technical user and deserves its own cycle; a CSV with 23 bare headers is not "a formatted template".
2. **Mapping profiles** (§4) — a client whose export has their own column names still cannot onboard. The hard-reject on unexpected columns stands, and the UI's job is to make that legible (the "unexpected columns" panel), not to reconcile it.
3. **Raising the validator cap for downloads** (§2) — validator change, flagged.
4. **Batch upload** — one domain at a time, as the endpoints are.
5. **RTL chrome** (§7).
6. **A background job for commit** — commit is synchronous with a 900s timeout; the UI shows a progress state and the pipeline's own output on failure.

---

## 10. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 1 | `lib/http.ts` shared client; `useGovernance` migrated | yes — fixes the "api.ts cannot call an authenticated route" problem on its own |
| 2 | `lib/uploads.ts`; delete `uploadFile()` (**closes TD-005**) | yes |
| 3 | `GET /api/data/onboarding-status` + registry entry | yes — backend only |
| 4 | The onboarding-state tab (§5), reusing `NotProvided` / `CoverageNote` | **yes, and it is useful before the upload flow exists** — it explains the dashboard's blanks today |
| 5 | The upload flow (§1–4) | the cycle's substance |
| 6 | Login (§8, pending ruling) | gates 5 being usable |

Step 4 before step 5 is deliberate: the screen that explains partial onboarding has value the moment it exists, and it exercises the provenance endpoint before the upload flow depends on it.

---

## 11. Tests

| Test | Pins |
|---|---|
| one HTTP client | no `fetch(` outside `lib/http.ts` |
| `uploadFile` is gone | TD-005, and that nothing still points at the removed endpoint |
| a REJECT disables commit | the button's disabled state and its count |
| an EXCEPTION does not | and the button's label carries the consequence |
| the two are rendered in separate regions | not one severity-sorted list |
| coverage requires active confirmation | the checkbox, not just the pre-filled field |
| the error report contains a row for every violation | and the truncation line when capped |
| onboarding state renders `NotProvided` / `CoverageNote` | reuse, not parallel components |
| an uncontracted domain cannot be selected | the picker is the contract list |
| demo | the new page loads with no upload in progress and changes nothing |

---

## 12. Risks

1. **The first real upload will fail, and this UI is the only thing standing between that and a lost client.** Everything in §2 is subordinate to that: the by-column default, the downloadable report, the fix-and-retry loop that keeps errors on screen. If a decision has to be made in implementation, make it in favour of the retry loop.
2. **Commit runs a full pipeline synchronously.** The UI will show a spinner for minutes on a real dataset. A progress state that says *what* is running ("validating… ingesting… rebuilding 158 models…") is worth more than a percentage that would be invented.
3. **The onboarding-state screen makes gaps visible for the first time.** A client mid-onboarding will see mostly grey. That is the truth and the whole point — but the copy has to read as *progress through a checklist*, not as *a broken product*. This is the cycle's largest non-technical risk and the reason §5 reuses the dashboard's vocabulary rather than inventing a starker one.

---

**Prepared for chief-architect review. No implementation performed.**
