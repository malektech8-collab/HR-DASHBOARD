# Contract audit — what is required that a real export will not carry

**Date:** 2026-08-17 · **Cycle:** payroll relaxations (A3) · **Status:** audit only, no contract changed here except payroll

Commissioned because payroll was **13 of 13 required with zero optional**, which suggested the contract had been written from the sample rather than from what real exports carry. The employees load found the same thing the expensive way: three relaxations, discovered one rejected upload at a time.

---

## 1. Where the six contracts stand

| contract | columns | required | optional | |
|---|---|---|---|---|
| `employees` | 23 | 14 | 9 | after three relaxations |
| `payroll` | 13 | **8** | **5** | this cycle |
| `attendance` | 15 | **13** | 2 | **worst remaining** |
| `compliance` | 13 | **11** | 2 | |
| `hr_requests` | 11 | **9** | 2 | |
| `employee_relations` | 14 | 8 | 6 | healthiest |

## 2. The systemic finding

**Four contracts mark DERIVED columns as required.** These are outputs of the analytics, not inputs a source system produces:

| column | contract | what it actually is |
|---|---|---|
| `net_late_minutes` | attendance | `late_minutes − excused_late_minutes` |
| `missing_punch_count` | attendance | a count computed from the punch record |
| `sla_breached` | hr_requests | `created_at + sla_hours` versus `closed_at` |
| `occupation_match_status` | compliance | the comparison of `occupation_code` against the GOSI record |

The employees contract already has the mechanism for exactly this — `derived_from` / `derivation`, resolved from a registry by name, which is how `is_saudi` is produced from `nationality`. **None of these four use it.** Each asks the client to send us an answer we are better placed to compute, and rejects their file when they cannot.

This is the single highest-value change in the audit: it is not a relaxation, it is a correction of what the column *is*.

## 3. Attendance — 13 of 15, and the inversion

**`actual_check_in` and `actual_check_out` are OPTIONAL. `scheduled_start` and `scheduled_end` are REQUIRED.** That is backwards. A biometric terminal certainly produces the actual punches; the *schedule* requires a rostering system the client may not have, and many run fixed hours with no roster export at all.

Plausibly absent from a real attendance export:

| column | why |
|---|---|
| `shift_name`, `scheduled_start`, `scheduled_end` | need a rostering system |
| `excused_late_minutes` | an adjudicated figure — a supervisor decision, rarely exported |
| `net_late_minutes` | derived (§2) |
| `missing_punch_count` | derived (§2) |
| `absence_days` | usually computed from punches, not supplied |
| `overtime_approved` | an approval-workflow flag |
| `location` | as on payroll — often costed to the employee, not the row |

That is potentially **eight of thirteen**. Attendance is also the only `DATE_GRAINED` domain, so it already carries the heaviest operator burden — a declared coverage window — and it is the domain that must load for payroll reconciliation to work at all.

**Recommendation: audit attendance properly before the client is asked for a file, not after their first upload is rejected.**

## 4. Compliance — 11 of 13

| column | why it may be absent |
|---|---|
| `payroll_basic_salary` | duplicates payroll *inside* the compliance file; a GOSI export will not carry it |
| `occupation_match_status` | derived (§2) |
| `qiwa_status`, `mudad_status`, `health_insurance_status` | three separate government platforms — a client may use some and not others |
| `contract_authenticated` | a Qiwa attestation flag |
| `gosi_salary` | present in a GOSI export; absent from a Qiwa-only one |

And the same inversion as attendance: **`iqama_expiry` is optional** while three platform statuses are required, though iqama expiry is the most universally available compliance fact and the one feeding `iqama_expiring_30`.

The deeper point: `compliance` is modelled as **one file from one system**, but the columns come from **at least three government platforms plus payroll**. A client is unlikely to have a single export containing all of them. That is a shape question, not a relaxation question — and the `has_gosi_source_sql` / `has_wps_source_sql` vars already hint at the answer.

## 5. HR requests — 9 of 11

| column | why it may be absent |
|---|---|
| `sla_breached` | derived (§2) |
| `sla_hours` | a policy figure, usually in a policy document rather than on the ticket |
| `owner` | unassigned tickets are normal |
| `location` | as elsewhere |

## 6. Employee relations — 8 of 14

The healthiest contract, and worth noting *why*: six columns are already optional, including `closed_date`, `escalation_reason` and `description`. Someone wrote this one thinking about partial data.

Remaining questions are narrow: `owner_id` (unassigned cases) and `escalated` (an approval-workflow flag, same shape as `overtime_approved`).

## 7. Recommended order

1. **Convert the four derived columns to `derivation` entries** (§2). **RULED NEXT, as its own cycle, 2026-08-17** — it outranks further relaxation. Requiring them asks the client to compute our metrics before uploading. It is a correction of what the column IS; dropping four required columns is a consequence, not the goal. **The two inversions (§3, §4) land in the same cycle** — they are the same species: a contract asking for the derived or the scheduled while treating the observed as optional.
2. **Attendance**, before the client is asked for a file. It is next in the load order, it gates payroll reconciliation, and it is the worst of the four.
3. **Compliance's shape** — one file or several. **DEFERRED to A5, ruled 2026-08-17.** The reasoning, recorded because a deferral without one becomes a thing nobody remembers deciding: it decides which columns belong together at all, so it is a bigger question than a contract edit — and **it cannot be answered without a real compliance export, which we do not have.** Relaxing individual compliance columns before answering it would be guessing at the shape one column at a time, which is how payroll reached 13-of-13.
4. **hr_requests and employee_relations** — narrow, and can follow the pattern once set.

## 8. What this audit does not do

It reads contracts against **general knowledge of what KSA HR systems export**, not against this client's actual files. Only the employees export has been seen. Every row above is a *plausibility* judgement and should be confirmed against a real header line before any contract is changed — which is exactly the check that turned payroll from a guess into the five relaxations in this cycle.

---

**Audit only. Each recommendation is a ruling.**
