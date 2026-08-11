# Coverage Surface — making partial coverage visible (PLAN ONLY)

**Branch:** `phase-2/coverage-surface` off `main` @ `98342a0` (Category F merged) · **Date:** 2026-08-11
**Status:** plan only when written; **executed 2026-08-11** — see [`coverage-surface-report.md`](coverage-surface-report.md).
**Closes:** [`p0-3-category-f-report.md`](p0-3-category-f-report.md) open item 1.

Category F made the numbers honest. It did not make them **explicable**. A client who uploads the first week of August now sees a thin month, correctly, and has nothing telling them why.

---

## 1. What is missing, precisely

Category F already computes everything needed and stores none of it where a reader can reach it:

| Fact | Where it lives now | Reachable by the API? |
|---|---|---|
| the declared window | `domain_provenance.coverage_start/_end` | yes, unused |
| covered vs unreported **working days** | `base_expected_attendance.coverage_status` | only as raw rows |
| which marts are affected | `metric_provenance.yml` — **21 marts** name `attendance` | yes, unused for this |

So the work is a surface, not a computation.

Three things a client currently cannot distinguish, all of which render identically:

1. `absence_days = 0` because nobody was absent.
2. `absence_days = 0` because only six days were reported and nobody was absent in them.
3. `attendance_compliance_pct = —` because **no** day was reported — the em dash Category F §7 introduced, which today carries no explanation at all.

---

## 2. This is NOT a suppression, and must not reuse that channel

The tempting shortcut is a fourth reason code in step 2b's `suppressed` block. It would be wrong.

> `suppressed` means **withheld** — the figure is absent and named. Partial coverage means the figure is **present and qualified**.

Putting a served number in a list of withheld figures would either make a real number look withheld or teach the reader that "withheld" does not mean withheld. So: a **sibling block of its own**, `coverage`, alongside `suppressed`, with its own shape, its own component and its own rendering rule.

```jsonc
{
  "kpis": [ … ],                  // real figures
  "suppressed": [ … ],            // withheld, step 2b
  "coverage": [                   // present but qualified, this step
    {
      "domain": "attendance",
      "domain_label_en": "Attendance",
      "domain_label_ar": "الحضور",
      "declared_start": "2026-08-01",
      "declared_end":   "2026-08-07",
      "covered_days":   6,
      "expected_days":  27,
      "coverage_pct":   22.2,
      "message_en": "Covers 6 of 27 working days (1–7 Aug).",
      "message_ar": "يغطي ٦ من ٢٧ يوم عمل (١–٧ أغسطس)."
    }
  ]
}
```

**Definitions, because "reported" is ambiguous and will be misread otherwise.** `covered_days` counts **working days inside the declared window**, not days that happen to have rows. A day inside the window with no row is a real absence (Category F's central inversion), so counting rows here would double-count the very thing the design worked to separate. The note says how much of the period the client *vouched for*, and that is the actionable fact.

---

## 3. Where the numbers come from

A new mart, `mart_attendance_coverage` — one row:

```sql
SELECT
    '{{ var('report_month') }}'                      AS report_month,
    DATE '{{ var('attendance_coverage_start') }}'    AS declared_start,
    DATE '{{ var('attendance_coverage_end') }}'      AS declared_end,
    COUNT(DISTINCT CASE WHEN coverage_status = 'covered'
                        THEN calendar_date END)      AS covered_days,
    COUNT(DISTINCT calendar_date)                    AS expected_days
FROM {{ ref('base_expected_attendance') }}
```

`DISTINCT calendar_date` because the base model is one row per employee per day; the note is about days, not rows.

A mart rather than an API-side query for three reasons: it is cacheable, it is the same shape as everything else the API reads, and — the deciding one — **the default-deny coverage test forces it to be registered.** `test_every_api_served_mart_is_mapped` will fail until `mart_attendance_coverage` appears in `metric_provenance.yml` with `domains: [attendance]`. A new surface that quietly bypasses provenance is exactly what step 2b exists to prevent.

*Registry note:* the entry must be `mode: payload`, `domains: [attendance]`. That means it self-suppresses when attendance is not provided — correct: with no attendance at all, step 2b's `suppressed` block is already saying so, and a coverage note beside it would be noise.

---

## 4. Which figures carry the note

Derived from the registry, not hand-listed: **any mart whose provenance includes a domain with partial coverage**. Today that is `attendance`, and **21 marts** name it. The mapping already exists; this step reads it in the other direction.

`Provenance` gains two methods, mirroring the ones 2b established:

```python
prov.coverage(domain)        # the declared window and day counts, or None
prov.note_coverage(mart)     # record a CoverageItem if any of the mart's
                             # domains is partially covered
```

`@suppressible` attaches the coverage block on the way out exactly as it attaches `suppressed`, so a handler cannot forget it — the same reasoning as 2b.

**The rule for emitting a note: only when `covered_days < expected_days`.** Full coverage is the normal case, and "27 of 27 working days" on every card is noise that trains people to stop reading notes. This also keeps demo byte-identical: demo's coverage is the whole reporting period, so the block is always empty.

---

## 5. Rendering

Three placements, deliberately different weights:

**(a) Page banner** — one line at the top of any page whose data is partially covered:
> ⓘ Attendance covers **6 of 27 working days** (1–7 Aug 2026). Figures below are measured over those days only.

**(b) Caption under a chart or KPI strip** — small, permanent, attached to the affected figures rather than the page, so a screenshot of one chart carries its own qualification. This matters: charts get pasted into decks and emails without their page.

**(c) The em dash gets its reason.** `KpiCard` currently renders `—` with nothing else when a metric is unmeasurable. It should show the coverage note in its place — "no days reported yet" is the answer to the question the em dash raises.

A new `CoverageNote` component, distinct from `NotProvided` in weight and colour: `NotProvided` replaces content and says *nothing is here yet*; `CoverageNote` sits beside content and says *this is real, over less than you might assume*. Conflating them visually would undo §2's distinction at the last step.

---

## 6. Scope

| | Change |
|---|---|
| dbt | 1 new model, `mart_attendance_coverage` |
| registry | 1 entry, `mode: payload`, `domains: [attendance]` |
| API | `CoverageItem` schema; `Provenance.coverage()` / `note_coverage()`; `coverage: List[CoverageItem] = []` on the **72** response models that already carry `suppressed`, by the same mechanical sweep 2b used |
| frontend | `CoverageItem` type; `CoverageNote` component; banner on 9 pages; `KpiCard` em-dash reason |
| tests | below |

The 72-model sweep is the bulk of the diff and the least interesting part of it; it is mechanical and the script from 2b applies almost unchanged.

---

## 7. Tests

| Test | Pins |
|---|---|
| partial coverage emits a note | 6 of 27, with the declared window in the message |
| **full coverage emits nothing** | the noise rule, and what keeps demo identical |
| the note is not a suppression | `coverage` and `suppressed` are separate keys; a partially-covered figure is still **served** |
| attendance absent | `suppressed` fires, `coverage` stays empty — one explanation, not two |
| `covered_days` counts declared days, not days with rows | the §2 definition; a gap inside the window is an absence, not missing coverage |
| the new mart is registered | already enforced by `test_every_api_served_mart_is_mapped`; the test exists, the entry does not |
| demo | `coverage` empty on all 78 endpoints |

---

## 8. Risks

1. **Note fatigue.** Three placements is already the maximum defensible. If the banner and the caption both fire on every chart, readers will filter them out and the em-dash case — the one that most needs an explanation — goes with them. The `covered < expected` rule is what keeps this survivable; it should not be softened into "always show coverage".
2. **The 72-model sweep touching every response again.** Mechanical, but it is the second such sweep in three cycles.

> ### DECISION — the meta envelope, and its trigger
>
> **Ruled 2026-08-11. Do not build an envelope now.** Two fields with different
> semantics are not yet evidence of a shared shape, and an envelope changes the
> API contract for every consumer — in a cycle already touching 72 response
> models and the frontend.
>
> **Named trigger: the THIRD cross-cutting response field adopts a shared
> `meta` envelope.** `suppressed` (step 2b) and `coverage` (this step) are the
> first two. A third must not be added as a third parallel list by default;
> reaching for one is the signal that the envelope is now owed, and the work
> is to introduce `meta` and migrate all three together.
>
> Recorded here rather than in a commit message because a commit message is
> not where a future contributor looks before adding a field.
3. **Arabic numerals in the message.** The example above uses Arabic-Indic digits (٦, ٢٧). The rest of the product renders Western digits in Arabic text.
   > **SETTLED at execution:** Western digits inside Arabic text, everywhere. Matches every bilingual message step 2b and Category F already ship, and a test asserts no Arabic-Indic digit appears in a coverage message.

---

## 9. Open questions

1. **Does the coverage note belong on the exception tables too?** A client seeing 3 attendance exceptions over 6 covered days should know the denominator. I think yes, but it makes the note near-universal on the Attendance page, which is risk 1.
2. **Should `coverage_pct` be shown as a number at all**, or only the day counts? A percentage invites comparison between clients and periods that the underlying declaration does not support. Recommend day counts in the text, percentage in the payload only.
3. **Coverage for period-grained domains.** Payroll and compliance have no window, and the 2a.5 membership gate already proves the period is present. Should the block carry a trivially-full entry for them, for uniformity? Recommend no — an entry that is always full is the noise of risk 1 in a different place.

---

**Prepared for chief-architect review. No implementation performed.**
