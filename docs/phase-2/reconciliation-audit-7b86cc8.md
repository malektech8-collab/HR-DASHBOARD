# Reconciliation audit of `7b86cc8` — what else went with WPS

**Commissioned:** after `mart_wps_status` was diagnosed as lost in the dbt migration, together with the assertion that guarded it.
**Question asked:** *enumerate everything else `7b86cc8` removed from the reconciliation suite and report which assertions have no surviving equivalent.*
**Status:** report only. Nothing fixed, nothing restored. **Date:** 2026-08-11.

---

## 1. The headline

```
reconciliation assertions BEFORE 7b86cc8 : 74
reconciliation assertions AFTER  7b86cc8 : 11
reconciliation assertions TODAY          : 11   (unchanged since)

removed : 63
```

**All 63 removed assertions have no surviving equivalent.** Not a weakened one — none.

The 11 survivors are the Command Center integration block, which `7b86cc8` left untouched. The suite did not shrink proportionally across modules; one block survived intact and every other block was deleted whole.

| Block | Assertions | Survives |
|---|---:|---|
| Command Center integration | 11 | **yes — all 11** |
| Warehouse (workforce distributions, contract expiry) | 2 | no |
| Payroll | 7 | no |
| Attendance | 8 | no |
| Compliance | 9 | no |
| Employee Relations & SLA | 11 | no |
| Recruitment & Workforce Planning | 13 | no |
| Talent & Succession | 13 | no |

The dbt test suite did not absorb them. It is **11 tests, all `not_null` or `unique`**, on 5 marts (`dbt_analytics/models/marts/schema.yml`); there is no `tests/` directory and no singular test. A `not_null` test passes on a fabricated zero, so the surviving dbt layer cannot detect the failure class P0-3 exists to close.

---

## 2. Only one guarded object actually disappeared

The deleted suite referenced **62 distinct `mart_`/`base_` objects**. Checked against today's warehouse:

```
still present in today's warehouse : 61
MISSING today                      :  1
   - mart_wps_status
```

So WPS is not the tip of an iceberg of lost marts — it is the **only** object casualty of the migration, and this audit is what establishes that rather than assuming it.

The iceberg is the other thing. 61 objects that still exist lost their guard anyway.

---

## 3. What the deleted assertions actually checked — and what they never did

This matters more than the count, and it cuts against restoring them verbatim.

**None of the 74 ever compared a KPI to the uploaded source rows.** Every one of them compares a mart to another mart, or a mart to a `base_` model:

```python
# deleted, payroll #1
total_payroll_cost_kpi = "SELECT total_payroll_cost FROM mart_payroll_kpis"
sum_gross_pay          = "SELECT SUM(gross_pay) FROM base_payroll_current"

# surviving, Command Center #2
kpi_pay = "SELECT payroll_cost      FROM mart_command_center_overview"
ref_pay = "SELECT total_payroll_cost FROM mart_payroll_kpis"
```

Both sides of every check sit **downstream of the same filters**. That gives the suite real power over one failure class and none at all over another:

- **Caught:** a breakdown that stops summing to its total, a KPI that drifts from its own base model, a distribution that loses rows to a broken join. This is where the 63 were load-bearing, and it is exactly the class the WPS check belonged to (`SUM(headcount) FROM mart_wps_status` vs active headcount).
- **Never caught, and still not caught:** anything wrong with the *shared upstream*. If a period filter selects the wrong month, the KPI and its recomputation both go to zero together and every assertion passes.

This cycle produced that second case on purpose. With the new ingest check disabled, an operator period of `2026-08` against a payroll file covering `2026-06`:

```
Declared-domain guard passed. Row counts: {... 'payroll': 3}
dbt run 157/157 · dbt test 11/11
Command Center integration reconciliation checks PASSED.

silver payroll rows       : 3
report_month              : 2026-08
base_payroll_current rows : 0
total_payroll_cost        : 0.0
```

Everything green, payroll cost zero, three valid payroll rows in silver. The 11 surviving assertions agree with each other perfectly, because they are comparing a copy to its original. Had the deleted payroll #1 still been present it would have thrown here too — but on a `TypeError` from `SUM` over zero rows, not on its own message.

---

## 4. The pattern the architect predicted

> *"The reconciliation assertion and its subject were deleted in the same commit, so nothing failed. That pattern will not be unique to WPS."*

Confirmed, with a correction to its shape. The pattern is not *N assertions each losing their subject*. It is one commit removing **4,300 lines** in which the views and the checks on those views lived side by side; porting the views to dbt moved 61 of 62 objects and **zero of 63 checks**. The checks were not evaluated and rejected — there is no trace of a decision about them. They were in the deleted region.

`mart_wps_status` is the single case where the subject was also missed, which is why it is the only one that produces a visible 500 rather than silent absence of coverage.

---

## 5. The full list

All 63, in original order, with the block they came from.

### Warehouse (2)
1. Distribution `{cat}` sum ≠ Active Headcount *(looped over several distributions)*
2. Contract Expiry sum ≠ Active Headcount

### Payroll (7)
3. Total Payroll Cost KPI ≠ SUM(gross_pay)
4. Reconciled gross components ≠ gross pay
5. Reconciled net payroll ≠ gross − deductions
6. Project Payroll sum ≠ Total Payroll Cost
7. Department Payroll sum ≠ Total Payroll Cost
8. Employees Paid KPI ≠ distinct paid employees
9. Exception Count KPI ≠ actual exceptions

### Attendance (8)
10. Expected workdays ≠ calendar rows
11. Absence Days KPI ≠ calculated
12. Late minutes KPI ≠ calculated
13. Calculated net late minutes logic check
14. Missing Punch KPI ≠ exceptions
15. Overtime Hours KPI ≠ calculated
16. Overtime Cost KPI ≠ calculated
17. Exception Count KPI ≠ calculated exceptions

### Compliance (9)
18. Saudi + Non-Saudi + Missing Nationality ≠ Active Headcount
19. Saudization % KPI ≠ expected
20. Project headcount sum ≠ Active Headcount
21. Department headcount sum ≠ Active Headcount
22. Iqama expiry buckets sum ≠ Non-Saudi Headcount
23. Work permit expiry buckets sum ≠ Non-Saudi Headcount
24. GOSI distribution sum ≠ Active Headcount
25. **WPS distribution sum ≠ Active Headcount** ← the one whose subject also vanished
26. Compliance Exception Count KPI ≠ exceptions table count

### Employee Relations & SLA (11)
27. Open cases KPI ≠ calculated
28. Closed cases KPI ≠ calculated
29. New cases KPI ≠ calculated
30. Case type distribution sum ≠ total ER population
31. Case status distribution sum ≠ total ER population
32. Project cases sum ≠ total ER population
33. Department cases sum ≠ total ER population
34. ER SLA Compliance KPI ≠ expected
35. Overdue cases KPI ≠ calculated
36. ER Exception Count KPI ≠ calculated exceptions
37. Aging buckets sum ≠ Open Cases KPI

### Recruitment & Workforce Planning (13)
38. Open Requisitions KPI ≠ calculated
39. Approved Vacancies KPI ≠ calculated
40. Candidates KPI ≠ calculated
41. Interviews KPI ≠ calculated
42. Offers KPI ≠ calculated
43. Offer Acceptance KPI ≠ expected
44. Hires KPI ≠ calculated
45. Time to Fill KPI ≠ calculated
46. Overdue Requisitions KPI ≠ calculated
47. Workforce Plan Fulfillment KPI ≠ expected
48. Project requisitions sum ≠ total requisitions
49. Department requisitions sum ≠ total requisitions
50. Exception Count KPI ≠ calculated exceptions

### Talent & Succession (13)
51. Employees Reviewed KPI ≠ calculated
52. Review Completion % KPI ≠ expected
53. Avg Performance Rating KPI ≠ calculated
54. Performance distribution sum ≠ reviewed employees
55. High Performers KPI ≠ calculated
56. Low Performers KPI ≠ calculated
57. Goal Completion % KPI ≠ expected
58. Training Completion % KPI ≠ expected
59. Average Training Hours KPI ≠ expected
60. Critical Roles Covered % KPI ≠ expected
61. Ready Successors KPI ≠ calculated
62. Project reviewed sum ≠ total reviewed
63. Talent Exception Count KPI ≠ calculated

---

## 6. What I would put to the architect

Report only, so these are options rather than actions.

1. **Restoration is cheap and mostly mechanical.** 61 of 62 subjects still exist and the assertions are pure SQL comparisons. As dbt singular tests (`dbt_analytics/tests/*.sql`) they would run inside `dbt test` and fail the pipeline the way they used to, with no Python in `build_warehouse.py`.
2. **Additivity checks must become domain-aware before they are restored.** "Breakdown sums to total" is false by design once P0-3 step 2b suppresses a payload: a null breakdown beside a real total is correct, and a restored assertion would fail every partial onboarding. Restoring them ahead of 2b would make the suite fire constantly and then be switched off — which is how suites die.
3. **The real gap is the one the suite never covered:** no check compares a KPI to the uploaded rows. The wrong-period scenario in §3 is caught this cycle at ingest, but only for that specific interaction. A general "KPI vs source" layer is a different and more valuable piece of work than restoring the 63.
4. **Sequencing suggestion:** WPS hotfix (restore the model + its one assertion) → step 2b/3/4 → restore the additivity suite as dbt singular tests, domain-aware, once suppression semantics are settled.

---

## 7. How this was established

```
git show 7b86cc8^:scripts/build_warehouse.py   # 4,410 lines
git show 7b86cc8:scripts/build_warehouse.py    #   257 lines
```

Assertions counted by matching `raise ValueError(...)` in each revision and today's file; subjects extracted from the `FROM`/`JOIN` clauses of the deleted region and checked against `information_schema.tables` in a freshly built demo warehouse. Both revisions are byte-for-byte from git; nothing was reconstructed by hand.
