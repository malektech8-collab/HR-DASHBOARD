# Frontend Test Foundation (Execution Report)

**Branch:** `phase-2/frontend-tests` off `main` @ `e8a06a5` · **Date:** 2026-08-12
**Status:** executed, committed, pushed, PR open. **Not merged.**
**Plan:** [`frontend-tests-plan.md`](frontend-tests-plan.md) (approved, five rulings) · **Precedes:** TD-007 (RTL)

```
before : 1 test file,  3 tests
after  : 5 test files, 58 tests   + 5 backend contract tests
```

---

## 1. The truth table

`declarationReady` and the disabled-commit condition were inline expressions inside a 400-line component. Extracted to `lib/uploadFlow.ts` by ruling — they either **block a valid commit** or **admit bad data**, and rules with those failure modes should not be verified by driving a form.

`isDeclarationReady`, all fifteen combinations:

| requirement | dates supplied | confirmed | ready |
|---|---|---|---|
| nothing | — | no | ✅ |
| nothing | — | yes | ✅ |
| coverage | none | no | ❌ |
| coverage | none | yes | ❌ |
| coverage | both | **no** | ❌ |
| coverage | both | yes | ✅ |
| coverage | start only | yes | ❌ |
| coverage | end only | yes | ❌ |
| history | none | yes | ❌ |
| history | date | **no** | ❌ |
| history | date | yes | ✅ |
| both | coverage only | yes | ❌ |
| both | history only | yes | ❌ |
| both | all | **no** | ❌ |
| both | all | yes | ✅ |

The three bold rows are Category F ruling 3 as an assertion: **the page fills those dates from the file, so "the dates are present" says nothing about whether a human agreed with them.** Filling is not confirming.

`commitGate`, eleven cases. The ones that matter:

| case | enabled | what the user sees |
|---|---|---|
| 2 rejects | ❌ | *"2 errors must be fixed before this can be committed."* |
| 1 reject | ❌ | *"1 error…"* — singular |
| 3 exceptions, no reject | ✅ | *"Commit — 3 data-quality exceptions will be recorded"* |
| 1 exception | ✅ | *"…1 data-quality exception…"* — singular |
| **reject + exception** | ❌ | label still warns, button still blocks |
| dates filled, unconfirmed | ❌ | *"Confirm the period above to continue."* |
| commit in flight | ❌ | no message — nothing is wrong |

---

## 2. The path contract flags a simulated P0-2

```
[contract] frontend literals: 81 | backend routes: 85     -> clean
test_the_rule_flags_a_simulated_p0_2                      -> PASSED
test_the_naive_prefix_rule_would_have_missed_it           -> PASSED
```

Per ruling 4, the naive-rule failure is recorded in the test's docstring, because it is the reason the rule has its shape:

```
naive prefix rule   : /api/data/upload -> []          (passes; WRONG)
segment-aware rule  : /api/data/upload -> FLAGGED     (correct)
```

`/api/data/upload` is a string prefix of `/api/data/uploads`, so a `startswith` template allowance waves the defect through. The rule matches a trailing-slash literal **only where the next path segment is a parameter**. A dedicated test asserts the naive rule *would* have passed it, so nobody simplifies it back.

**Scanning excludes `*.test.ts`** — my own `http.test.ts` names `/api/x` as a 404 fixture, and the check failed on it first time round. A contract test that fails on its own fixtures gets deleted.

---

## 3. A null suppression renders as NotProvided, not empty

```
a page given null renders NotProvided
  ✓ a suppressed KPI strip is not an empty page      -> not-provided, "needs Employees"
  ✓ a suppressed trend series suppresses the page

a page given [] does NOT render NotProvided
  ✓ an empty-but-present series renders as the page
  ✓ a fully populated page renders its KPIs

the coverage note is a sibling, not a suppression
  ✓ a partially covered page still renders its data, with the note
```

**The `[]` half is what makes the `null` half meaningful.** If a page treated them alike, the first two tests would still pass and the distinction would be gone. That is the quiet failure: `data ?? []` typechecks, looks right on demo data where nothing is ever suppressed, and renders an empty chart in production — a claim that the period had no events.

The component-level tests hold the same line: `CoverageNote` with an empty list renders **nothing** (the noise rule), `KpiCard` with `null` renders an em dash **and its reason**, and `KpiCard` with `0` renders **0** — the opposite error, hiding a measured zero behind the dash used for "unknown".

---

## 4. `lib/http.ts` — 12 tests, `globalThis.fetch` stubbed

Per ruling 2. Mocking a module inside the module under test would test nothing.

The Authorization header attaches when a token exists and is absent when it does not (the dashboard stays readable). **401 clears the token; 403 does not** — a permissions problem is not a session problem, and logging a user out for one sends them round a login loop that cannot help. Both are `isUnauthorized`, so a page branches on status rather than string-matching. `postForm` sets **no** `Content-Type`, because a hand-set one breaks the multipart boundary and produces an upload failure whose message points nowhere useful.

---

## 5. Three things the work surfaced

**(a) A structural test broke on the extraction — the risk I named, materialising.** `test_the_commit_button_is_gated_on…` asserted the inline expression `disabled={!preview.can_commit || !declarationReady…}` and failed the moment the logic moved. It was asserting an *implementation*. Rewritten to hold the only thing a source scan is the right tool for — that the page has not grown a **second copy** of the rule — with the behaviour left to the truth table. The plan predicted this class of problem; it is worth recording that it arrived immediately.

**(b) jsdom has no `ResizeObserver`, and recharts requires one.** Rendering *any* page that draws a chart threw. A stub in `setupTests.ts` fixes it in three lines — and it is a large part of why no page had a test: the first person to try would have hit an error with no obvious connection to their code.

**(c) The Playwright harness is deleted**, per ruling 3 — `e2e/governance.spec.ts`, `playwright.config.ts`, and the `@playwright/test` dependency, so `package.json` and the lockfile stay in sync. If E2E is wanted later it arrives with a CI job, deliberately.

---

## 6. What was built

| | |
|---|---|
| `lib/uploadFlow.ts` | `isDeclarationReady`, `commitGate` — pure, named, tested exhaustively |
| `lib/uploadFlow.test.ts` | 26 tests, the truth table |
| `lib/http.test.ts` | 12 tests, fetch stubbed |
| `components/ui/suppression.test.tsx` | 12 tests — `NotProvided`, `CoverageNote`, `KpiCard` |
| `pages/Workforce.test.tsx` | 5 tests — null vs `[]` at the page level |
| `test/builders.ts` | `aPreview`, `aViolation`, `aSuppression`, `aCoverageItem`, `aDomainStatus` |
| `backend/tests/test_path_contract.py` | 5 tests, segment-aware |

`ScopedLogin` is exported for testability, per ruling 1. **`renderWithQuery` was not built** — nothing in this cycle's scope uses react-query (`DataOnboarding` and the pages use `useState`/`useEffect`), and a helper with no callers is the kind of unused scaffolding this repo has been deleting. It is a five-line addition when the first react-query component needs a test.

---

## 7. Verification

| Check | Result |
|---|---|
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 158/158, 11/11, PASSED |
| vitest | **58 passed** (5 files) — was 3 in 1 |
| pytest | **227 passed** (222 + 5 contract) |
| `tsc -b` / `npm run build` | 0 errors / passes |
| Path contract | 81 literals, 85 routes, clean; flags a simulated P0-2 |
| Playwright harness | deleted, lockfile in sync |

---

## 8. Open

1. **TD-009 — generated OpenAPI TypeScript types**, recorded with an explicit statement of what the path contract does *not* catch: a renamed response field (the backend renaming `can_commit` leaves the path valid, every test green, and the button reads `undefined` — falsy, so it disables forever), a changed type, changed semantics (`[]` where `null` used to be), and a new required request field.
2. **TD-007 — RTL/i18n** is now unblocked, which was the point of the sequencing.
3. **`DataOnboarding` still holds eleven pieces of state** after the extraction. The remaining ones are genuinely UI state (which tab, which file, busy) rather than rules, so this is a readability note, not a correctness one.
4. **The other nine pages have no tests.** Workforce was chosen as the smallest with both shapes; the null/`[]` guarantee is asserted once, not nine times. Whether that generalises is a judgement — the pages were generated from one pattern, and the `NotProvided` guard is mechanically identical across them.

---

**Not merged. Awaiting review.**
