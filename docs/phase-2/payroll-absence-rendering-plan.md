# Two absences rendered as values on the payroll path — Plan

**Status:** PLAN ONLY. Ruled during A3: *plan, do not build.* **Date:** 2026-08-17

Two defects of one shape, both on the payroll path, both invisible until payroll loads. Neither is caused by the relaxations in this cycle; both were there already and the relaxations brought them into view.

---

## Part A — `payroll_variance_pct` reads 0.0 with one period loaded

### What it does

```sql
WHEN COALESCE(prev.total_payroll_cost, 0.0) = 0.0 THEN 0.0
ELSE (curr.total_payroll_cost - prev.total_payroll_cost) / prev.total_payroll_cost
END AS payroll_variance_pct
```

`base_payroll_previous` selects the month before the report month. A client uploading a single payroll file has no previous month, so the branch fires and the KPI renders **0.0%** — *"payroll unchanged since last month"*.

### Why it is a lie rather than a placeholder

It is the exact shape already ruled on twice. `missing_cost_center_count = 0` read as *"nobody is missing a cost centre"*; this reads as *"payroll did not move"*. Both are **fabricated-favourable**: the reassuring answer, produced by absence, indistinguishable from the same figure honestly measured.

The distinction that matters: **0.0% variance is a real and meaningful business result.** A client whose payroll genuinely did not move sees 0.0%, and so does a client who has uploaded one file. Nothing on screen separates them.

### Proposed shape

NULL, not 0.0, when there is no previous period — and the suppression layer says why, exactly as `missing_cost_center_count` now does. The precedent is complete and needs no new mechanism: the mart withholds, `prov.value()` passes the NULL through, and the card renders with no figure and neutral status.

**Not** `has_..._source_sql` — this is not an absent column. The condition is *"no prior period in the data"*, which the mart can test directly (`prev` produced no rows), so the gate is local rather than a var.

### Test obligations

1. One period loaded → variance withheld, not `0.0`.
2. Two periods loaded → a real figure, including a genuine 0.0% when payroll truly did not move (the tamper — a fix that withheld both would destroy a legitimate result).
3. Demo, which carries two periods, is byte-identical.

---

## Part B — three `COALESCE(project, 'Missing Project')` sentinels

### Where they are

`base_payroll_current`, `base_payroll_previous`, and the sibling `COALESCE(department, 'Missing Department')` beside them:

```sql
COALESCE(e.project,    'Missing Project')    AS emp_project,
COALESCE(e.department, 'Missing Department') AS emp_department,
```

The `cost_center` sentinel that sat **on the very next line** was deleted in the `contract-required-relax` cycle, with a comment explaining why. These two were not, and the comment now sits directly above two live instances of what it describes.

### Why it matters more than it looks

`project` is resolved through the client's **locations file**. This client has not provided one, so **`project` is NULL for every employee**. The moment payroll loads, every payroll row buckets under a category literally named **"Missing Project"** — in `mart_payroll_by_project`, in every breakdown, on every chart that groups by project.

A client sees their entire payroll attributed to a category named after our data model's gap. The cost-centre cycle's own words: *a sentinel renders an absence as a value*.

`department` is the same mechanism with a smaller blast radius — this client does supply department — but it will fire for the first client who does not.

### Proposed shape

Delete both sentinels, keep the NULL, and let the existing machinery do the rest — precisely what was done for `cost_center`:

- `mart_payroll_by_project` is already registry-gated on `locations` (corrected in the withheld-counts cycle), so with no locations file the breakdown is **suppressed with a reason** rather than served under a fabricated heading.
- `mart_unmatched_locations` already reports the *different* problem — a site supplied by the client that is missing from their locations file — so the two cases stay separate.

### The interaction to check when building

Deleting a sentinel changes a `GROUP BY` key from a string to NULL. Every consumer grouping on `emp_project` or `emp_department` needs checking: SQL groups NULLs together, so the bucket does not disappear, it becomes unnamed. The honest rendering of an unnamed group is a suppression, not a blank label — and that is an API-layer question, not a mart one.

### Test obligations

1. With no locations file, no payroll row carries a project **value**; the project breakdown is suppressed with a reason rather than served.
2. With a locations file, the breakdown is exactly as it is today (the tamper).
3. A client who supplies `location` but whose site is missing from the locations file still appears in `mart_unmatched_locations` — the two absences stay distinguishable.
4. Demo byte-identity.

---

## Sequencing

**Part B before Part A**, and before any real payroll load. Part B is client-visible the moment payroll serves — a mislabelled breakdown on a chart. Part A is a single KPI card, wrong in a quieter way, and its fix has an exact precedent to copy.

Both are small. Neither should ride along with a client load in flight.

---

**Not built. Awaiting a ruling.**
