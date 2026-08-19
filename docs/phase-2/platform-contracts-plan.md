# Steps 4 and 5 — the four platform contracts and the sample split — Plan

**Status:** PLAN ONLY. **Branch:** `phase-2/platform-contracts-plan` off `main` @ `c965555` · **Date:** 2026-08-19
**Follows:** steps 1–3 of the compliance split. The largest remaining piece, and the one carrying the demo byte-identity risk the sequencing exists for.

Per SP-003 this plan carries magnitudes and vocabulary only.

---

## 1. Two step-2 leftovers, found while measuring — and they must go first

Measuring the registry surfaced two entries that became **wrong** when `iqama_expiry` moved onto employees. Both are **over-suppression**: a figure withheld for a dependency that no longer exists.

| model | refs it actually reads | registry says |
|---|---|---|
| `mart_workforce_iqama_expiry` | **`base_active_workforce` only** | `[compliance]` |
| `mart_workforce_kpis` | joins `stg_compliance` and **reads nothing from it** | `iqama_expiring_30: [employees, compliance]` |

`mart_workforce_iqama_expiry` has **no compliance reference at all** — step 2 removed its join — yet a client without a compliance file has the whole mart suppressed. `mart_workforce_kpis` keeps a **dead LEFT JOIN** to `stg_compliance` reading no column from it, which also keeps a false dependency alive in the registry.

**This is the mirror of every defect this phase has chased.** Those were figures *served* when they should have been withheld; these are figures *withheld* when they can be served. The same registry, the opposite error, and equally invisible in demo — demo provides every domain, so nothing suppresses.

**They should be fixed before the split**, not during it: they are small, independently verifiable, and re-pointing 27 registry entries while two of them are already wrong would bake the error into four new domains.

## 2. The four contracts

`employee_id` and `period` are required in each. Everything else optional, so a client whose Qiwa export lists only contract status can still load it.

| contract | columns | what a real export from that portal plausibly carries |
|---|---|---|
| **`compliance_gosi`** | `gosi_status`, `gosi_salary`, `occupation_code` | GOSI's contributor list is the most complete of the four: per-employee registration status, the registered wage, and the registered occupation. **The most likely to arrive intact.** |
| **`compliance_qiwa`** | `qiwa_status`, `contract_authenticated`, `work_permit_expiry` | Qiwa exports contract and establishment data. Contract authentication is a Qiwa function. Work-permit expiry travels with it. |
| **`compliance_wps`** | `mudad_status` | A WPS/Mudad file is a **payment-file compliance result**, often a status per payroll run rather than a per-employee attribute. Thinnest of the four, and the most likely to arrive in a shape that needs mapping. |
| **`compliance_health`** | `health_insurance_status` | Comes from the insurer or the CCHI portal, commonly as a spreadsheet with policy numbers. **Expect PDPL-sensitive identifiers alongside** — the ignore-with-reason mechanism handles them, as it did for employees. |

**Removed from the family entirely**: `occupation_match_status` — a derived comparison (§5), not a column any portal exports.

### 2.1 `work_permit_expiry` — the principle, formalised on the Qiwa contract

Ruled, and it goes in the contract itself rather than only in a plan:

> **The period test decides where a column BELONGS. Availability decides where it can COME FROM. When they disagree, availability wins and the disagreement is recorded.**

`work_permit_expiry` fails the period test exactly as `iqama_expiry` did — a permit's expiry changes when the permit is renewed, not when the month turns. By the test it is an employee attribute and belongs on `employees`.

**It stays in the Qiwa contract anyway**, because no HRIS reliably carries it and it arrives with the Qiwa export. This client's employees file has no work-permit column at all, which is the evidence.

The note on the column will say so in those terms, so the next borderline column meets the rule where it applies rather than in a document nobody opens. **The disagreement is recorded, not resolved** — if a client's HRIS does carry it, that is the moment to move it, and the note is what tells the next reader the question was already asked.

## 3. Per-platform provenance, and what a GOSI-only client sees

**27 registry entries name `compliance` today.** Each must be re-pointed at the platform (or platforms) it actually depends on. That re-pointing is the substance of the work, and §7 argues it is where the risk lives.

A **GOSI-only** client — GOSI export, employees, nothing else — would see:

| | |
|---|---|
| **served** | `gosi_missing_count`, GOSI status breakdowns, the GOSI-versus-payroll salary comparison **if payroll is also loaded** (step 3's rule) |
| **served, and this is the point** | `iqamas_expired` / `iqamas_expiring_30` — these need **employees only** once §1 is fixed, and a client sees them without any compliance file at all |
| **withheld, with a named reason** | `work_permits_expired` / `work_permits_expiring_30` — *"Not yet provided: Qiwa"* |
| **withheld, with a named reason** | `wps_exception_count` — *"Not yet provided: WPS"* |
| **withheld** | health-insurance figures |

**Today that same client gets none of it.** A missing compliance file darkens all eleven metrics, including the iqama figures that need no platform export whatsoever. That is the argument for the split in one sentence, and §1 is half of it.

Four new domain labels are needed in both languages — `locations` was missed the same way, and its message read *"Not yet provided: locations."* untranslated until it was caught.

## 4. Demo byte-identity — the measured risk

One sample file becomes four while the fingerprint holds: `19 / 446175.0 / 50.0 / 667 / 15`.

**The exposure is precisely 109 rows.** Measured on the demo build:

```
exception_sources by source_mart (667 total)
   mart_attendance_exceptions   430
   mart_compliance_exceptions   109   <-- 16% of the pinned figure
   ...
```

The 15 data-quality rows come from `validate_data` and contain **no** compliance issue types, so that half of the fingerprint is not exposed.

**Why the split can be byte-identical.** `base_compliance_current` LEFT JOINs one `stg_compliance` on `(employee_id, period)`. Four LEFT JOINs on the same key produce the same row set **provided each file has at most one row per (employee_id, period)** — which the sample does and the contracts should enforce. The demo sample splits four ways with the same four employees and the same period in each.

That is a property worth asserting rather than assuming: **a duplicate row in any one platform file would fan out every compliance row for that employee**, which is the same hazard step 3 guarded with `GROUP BY employee_id` on the payroll join.

## 5. The GOSI-versus-iqama occupation comparison

Ruled: the divergence is what surfaces in a Qiwa audit and is worth more than either column alone. The split must preserve the ability to compare them.

After the split the two facts live in **different places, deliberately**:

| fact | home | why |
|---|---|---|
| `iqama_occupation` | **employees** | fails the period test — changes when the iqama is reissued |
| `occupation_code` (GOSI-registered) | **`compliance_gosi`** | period-grained; GOSI re-registers it |

`base_compliance_current` already carries `e.iqama_occupation` and would carry `gosi.occupation_code`, so **the comparison is a single expression in one view** — the seam again, and no cross-domain mechanism.

**Three states, and they are different findings:**

1. **Both present, equal** — nothing to report.
2. **Both present, different** — the audit finding. The occupation GOSI has registered is not the occupation on the iqama, which is what an inspector compares.
3. **One absent** — **withheld**, gated on both, exactly as the GOSI-versus-payroll comparison now is. A client with an iqama occupation and no GOSI export must not be told the two agree.

`occupation_match_status` — the column that used to carry the *answer* — leaves the contracts entirely. It was the client being asked to perform our comparison.

## 6. The measured surface

| touchpoint | today | after |
|---|---|---|
| contracts | 1 | **4** |
| dbt sources | 1 | 4 |
| staging models | `stg_compliance` | 4 |
| models reading compliance columns | 12 | **2 change** (the seam) |
| registry entries naming `compliance` | **27** | re-pointed |
| domain labels (EN + AR) | 1 | 4 |
| ingest domain blocks | 1 | 4 |
| demo sample files | 1 | 4 |
| `has_*_source_sql` vars | **already exist** for all four | unchanged |

The vars are the head start: `has_gosi_source_sql`, `has_wps_source_sql`, `has_qiwa_source_sql` and `has_health_insurance_source_sql` all exist and all resolve from provenance as of step 1. They currently ask `provides_column("compliance", …)` and would ask whether the *domain* was declared.

## 7. One step or more — recommendation

**Not one step. Two, split along a single question: does demo byte-identity prove it?**

| | step 4 — the plumbing | step 5 — the semantics |
|---|---|---|
| **what** | 4 contracts, 4 sources, 4 staging models, ingest, sample split, the seam | 27 registry entries re-pointed, 4 domain labels, per-platform suppression |
| **proved by** | **demo byte-identity.** If 109 stays 109 and the fingerprint holds, the plumbing is right | **not provable by demo** — demo provides every domain, so nothing suppresses |
| **failure mode** | a crash, or a moved count — loud | a figure withheld for the wrong reason, or served when it should not be — silent |

That is the whole argument. **Step 4's correctness is mechanically checkable; step 5's is not**, and mixing them means a demo-identical build would also "prove" a registry mapping that nothing tested. Step 5 needs its own tests — one per platform, asserting a client with that platform and no other gets its figures and a *named* reason for the rest.

**And §1 goes before both**, as step 3.5: two stale entries, small, and re-pointing 27 entries while two are already wrong would carry the error into four domains.

## 8. Test obligations (SP-001 — both halves)

1. Demo byte-identity, and specifically `mart_compliance_exceptions` still contributing **109**.
2. A duplicate row in one platform file does **not** multiply compliance rows — the fan-out hazard §4 names.
3. Per platform: a client with that platform only sees its figures **and a named reason** for the others — and a client with all four sees exactly what they see today (the tamper).
4. `iqamas_expired` / `iqamas_expiring_30` are served with **no compliance file at all** (§1).
5. Every new domain has a bilingual label, and no label is the key echoed back — the test added when `locations` was missed.
6. The occupation comparison is withheld when either side is absent (§5).

## 9. Risk

The largest cycle of the phase, on its highest-stakes domain. Two things reduce it: the **seam** confines model changes to two files, and the **step 4 / step 5 split** puts everything demo can prove in one place and everything it cannot in another.

**What remains is that step 5 has no mechanical check.** Twenty-seven mappings from a metric to the platform it depends on are twenty-seven judgements, each wrong in a way that produces a plausible page. §1 is the proof that this is not hypothetical: two of them are wrong *right now*, and were introduced by a step that passed every gate.

---

**Not built. Awaiting a ruling — in particular on §7's two-step split and on §1 going first.**

---

## Where things landed (added after the split shipped)

`data/contracts/compliance_schema.yml` no longer exists — a reader searching
that filename finds nothing. The four replacing it are
`compliance_gosi_schema.yml`, `compliance_qiwa_schema.yml`,
`compliance_wps_schema.yml` and `compliance_health_schema.yml`.

**The two tombstones travelled with their columns**, so each sits where a
reader looking for that column would land:

| tombstone | now on | because |
|---|---|---|
| `iqama_expiry MOVED to the employees contract` | **Qiwa** | it sat beside `work_permit_expiry`, the other expiry a platform export carries |
| `payroll_basic_salary REMOVED` | **GOSI** | it existed to be compared against `gosi_salary` |

