# Frontend Test Foundation (PLAN ONLY)

**Branch:** `phase-2/frontend-tests` off `main` @ `e8a06a5` · **Date:** 2026-08-12
**Status:** plan only. Nothing implemented.
**Precedes:** TD-007 (RTL), by ruling — RTL touches every page and is far safer with component tests underneath.

Vitest runs in Gate 2 and collects **one file, three tests**. The harness is not missing; it is nearly empty.

---

## 0. Measured state

| | |
|---|---|
| CI | `npx vitest run src/` — Gate 2, `.github/workflows/ci-cd-pipeline.yml` line 82 |
| collected | **1 file, 3 tests** — all `GovernanceWidget` |
| config | `frontend/vitest.config.ts` — jsdom, globals, `src/setupTests.ts` |
| available | `@testing-library/react`, `@testing-library/jest-dom` |
| **not** available | `@testing-library/user-event`, `msw` |
| react-query | `QueryClientProvider` is mounted in `main.tsx`, so any react-query component needs a wrapper in tests |
| Playwright | `playwright.config.ts` and `e2e/governance.spec.ts` exist — and **e2e does not run in CI at all** (0 references in the workflow) |

The last row is worth its own note: there is already an E2E harness nobody runs. Any recommendation to "add E2E" has to reckon with the one we have first.

---

## 1. The uncomfortable finding, stated first

**The P0-2 widget breakage would not have been caught by any of the component tests in this plan.**

The architect asked me to state plainly what would have caught it. Working backwards from the actual defect:

- P0-2 deleted the **route** `/api/data/upload`. It did not touch `uploadFile()`, which kept its literal string.
- TypeScript was satisfied — the symbol existed and its types were fine.
- A component test of the Data Quality widget, mocking `useUploadMutation`, would have **passed**. The mock does not know the route is gone.

The defect was a **contract mismatch between two repositories' worth of code that never meet at compile time**. Component tests, by construction, mock exactly the boundary where it lived.

So item 4 needs a different kind of test, and §5 is it. Items 1–3 are worth doing on their own merits — they cover different defects — but they are not the answer to this one, and presenting them as such would be the reassuring answer rather than the true one.

---

## 2. Priority 1 — the onboarding step machine

The flow a client touches, and the one a source scan cannot check.

**The refactor to flag, not do.** `DataOnboarding.tsx` holds **thirteen** pieces of state and the two rules I most want to test are inline expressions inside the component body:

```tsx
const declarationReady = !preview
  || ((!preview.coverage_required || Boolean(declaration.coverage_start && declaration.coverage_end))
      && (!preview.history_required || Boolean(declaration.history_since))
      && confirmed);

disabled={!preview.can_commit || !declarationReady || busy !== null}
```

These are pure functions of `(preview, declaration, confirmed, busy)`. Extracting them into `lib/uploadFlow.ts` would let the gate be tested **exhaustively as a truth table** — sixteen combinations in milliseconds — instead of driving the DOM once per case. That is cheaper, more precise, and it makes the rule a named thing a reader can find.

**Recommend the extraction; flagging rather than doing it, per the guardrail.** If it is declined, the tests below still work through the DOM; they are just slower and cover fewer combinations.

`ScopedLogin` is also defined inside `DataOnboarding.tsx` and not exported, so it cannot be unit-tested directly. Same flag, smaller stakes.

### Tests

| Test | Defect it prevents |
|---|---|
| REJECT present → commit **disabled**, and the message names the count | a rejected file reaching commit |
| EXCEPTION present, no REJECT → commit **enabled**, and the label reads *"… N data-quality exceptions will be recorded"* | exceptions silently blocking, or committing without telling the user |
| both panels render in **separate regions** (`reject-panel`, `exception-panel`) | the two collapsing into one severity-sorted list, which loses the distinction |
| coverage required, fields pre-filled, **checkbox unticked** → commit disabled | the declaration degrading into a pre-filled field nobody reads — Category F ruling 3 |
| ticking the checkbox enables commit; **editing a date unticks it** | a confirmation that survives a change it no longer describes |
| history required for `employees` → same gate | amended ruling 2 |
| grouped-by-column rendering: 43 violations in one column render as **one row with a count**, not 43 rows | the error list becoming unusable at real scale — the whole reason for the default view |
| switching to by-row shows the individual violations | that the toggle is real |
| the error report contains a row per violation, plus the truncation line when capped | ruling 5 |
| discard clears the preview and returns to the upload step | a stale preview surviving a discard |

The grouped-rendering test should use ~50 synthetic violations. Three would pass a broken implementation.

---

## 3. Priority 2 — suppression rendering

The server-side ruling is *a suppressed payload is `null`, never `[]`*. **These tests assert the client honours the distinction rather than collapsing it.** A component that renders `data ?? []` turns a suppression into "no events", which is exactly the claim the ruling exists to prevent — and it would pass a typecheck and look fine on demo data.

| Test | Defect it prevents |
|---|---|
| `NotProvided` renders the missing domain labels and the withheld-figure count | a suppression rendering as an empty panel with no explanation |
| `CoverageNote` renders `covered / expected` and the declared window | the coverage note losing its numbers |
| `CoverageNote` with an **empty** items array renders **nothing** | the noise rule leaking a blank banner onto every page |
| `KpiCard` with `value: null` renders an em dash **and** its `unmeasurableReason` | an unmeasurable metric rendering as a bug-looking blank |
| `KpiCard` with `value: 0` renders **0**, not the em dash | the opposite error: a real zero being hidden |
| a page given `container: null` renders `NotProvided`, and given `[]` does **not** | the null/`[]` distinction collapsing at the last step |

The last one is the highest-value test in this section and the only one that checks the ruling end to end on the client. It needs one page — `Workforce` is the smallest.

---

## 4. Priority 3 — `lib/http.ts`

Small, and it is now the single point every request passes through.

| Test | Defect it prevents |
|---|---|
| a token in storage → `Authorization: Bearer …` on the request | the regression that made six routes unreachable |
| no token → no header, request still made | breaking the unauthenticated dashboard |
| 401 → token cleared **and** `ApiError.isUnauthorized` is true | a stale token failing silently forever |
| 403 → token **not** cleared, `isUnauthorized` still true | logging a user out for a permissions problem |
| a JSON `{detail: …}` body surfaces as `ApiError.detail` | error text arriving as `[object Object]` |
| `postForm` sets **no** `Content-Type` | a hand-set content type breaking the multipart boundary — a real and confusing upload failure |

**Mocking approach here is different from everywhere else:** `http.ts` *is* the fetch wrapper, so the test stubs `globalThis.fetch` directly. Mocking a module inside the module under test would test nothing.

---

## 5. Priority 4 — the contract test that would actually have caught P0-2

**A path-contract check between the frontend source and the backend's OpenAPI schema.** Every `/api/...` literal in `frontend/src` must correspond to a route the backend serves.

Prototyped against the current tree:

```
frontend literal paths : 81
backend openapi paths  : 85
unmatched              : none
```

And simulating the P0-2 state — frontend keeps `/api/data/upload`, backend route removed:

```
/api/data/upload           -> FLAGGED
```

**A design detail worth recording, because my first version of the rule silently passed the exact defect it exists to catch.** Template literals like `` `/api/data/uploads/${id}` `` scan as `/api/data/uploads/`, which has no exact match, so the rule needs a template allowance. The obvious one is "a literal matches if some backend path starts with it" — and under that rule `/api/data/upload` matches `/api/data/uploads` and passes. Verified:

```
naive prefix rule   : /api/data/upload -> []          (passes; wrong)
segment-aware rule  : /api/data/upload -> FLAGGED     (correct)
```

The correct rule matches a trailing-slash literal only where the **next path segment is a parameter** (`{upload_id}`), never on raw string prefix.

**Where it lives:** pytest, with the FastAPI app imported — the backend is the side that owns the schema, and this needs both halves in one process. It is a source scan of the frontend, so it belongs beside `test_frontend_structure.py`.

**What it does not cover:** request/response *shapes*. A backend renaming `can_commit` would still break the client silently. That is a bigger piece — generating TypeScript types from the OpenAPI schema — and is named in §8 rather than smuggled in here.

---

## 6. Utilities and mocking

**Follow the established pattern: `vi.mock` at the module boundary.** `GovernanceWidget.test.tsx` already does this, `lib/uploads.ts` is a clean seam, and the alternative (msw) would introduce a second mocking philosophy for no gain at this size. Recommend **not** adding msw.

Three small utilities in `src/test/`:

- **`renderWithQuery(ui)`** — wraps in a fresh `QueryClientProvider` with `retry: false` and a per-test client. Required because the app's provider lives in `main.tsx`, which tests do not mount; a shared client would leak cache between tests.
- **`builders.ts`** — `aPreview({...})`, `aViolation({...})`, `anOnboardingStatus({...})`. The `UploadPreview` shape has fourteen fields and a test that spells all of them out obscures the one that matters.
- **`fetchStub()`** — for `http.ts` only.

**One dependency to add: `@testing-library/user-event`.** The onboarding flow is a form — typing dates, ticking a checkbox, clicking through steps — and `fireEvent` does not reproduce the event sequences a browser fires. It is the difference between testing the flow and testing that handlers exist.

---

## 7. Not by coverage percentage

Per the guardrail, no target. The ordering above is by consequence:

1. **breaks a client's data** — the commit gate, the declaration gate
2. **hides a suppression** — null vs `[]`, the em dash, the coverage note
3. **silently kills a feature** — the path contract, the Authorization header

A percentage would rank a chart's tooltip formatter equal to the commit gate. The dashboards' rendering is deliberately near the bottom of this list, and that is a choice, not an omission.

---

## 8. Out of scope, named

1. **Generated TypeScript types from the OpenAPI schema.** The real fix for frontend/backend drift; the path contract in §5 catches removed routes but not renamed fields. Its own cycle.
2. **The unused Playwright harness.** `e2e/governance.spec.ts` exists and CI never runs it. Either wire it in or delete it — a test suite nobody runs is worse than none, because it reads as coverage. Recommend a decision, not necessarily work.
3. **Dashboard page rendering tests** beyond the one null/`[]` case in §3.
4. **The `DataOnboarding` extraction** (§2) — flagged for a ruling, not done here.
5. **Visual/RTL testing** — TD-007's business, and part of why this lands first.

---

## 9. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 1 | `src/test/` utilities + `user-event` | yes |
| 2 | **§5 path contract** (pytest) | yes — smallest, and the only one targeting a defect that has actually happened |
| 3 | §4 `lib/http.ts` | yes |
| 4 | §3 suppression rendering | yes |
| 5 | §2 the step machine | the bulk; benefits from the §2 extraction if it is ruled in |

Step 2 before the component tests is deliberate: it is an afternoon, and it closes the class of defect that shipped.

---

## 10. Risks

1. **Tests that assert the implementation rather than the behaviour.** The structural tests in `test_frontend_structure.py` already assert on source strings; that is defensible for "there is exactly one X", and a bad habit if it spreads into component tests. These should assert what a user sees — the disabled button, the counted message — not that a prop is passed.
2. **The step-machine tests are the ones most likely to be deleted** when the UI is restyled, because they are the most coupled to markup. `data-testid` on the panels and the commit button, already present, is what keeps them survivable.
3. **This plan will not have caught the next P0-2.** §5 catches removed routes. Renamed response fields, changed semantics, and a backend that starts returning `[]` where it used to return `null` all still pass. §8's generated types are the honest answer and they are not in this cycle.

---

**Prepared for chief-architect review. No implementation performed.**
