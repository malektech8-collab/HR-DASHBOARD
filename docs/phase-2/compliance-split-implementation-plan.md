# Splitting compliance by platform — Implementation Plan

**Status:** PLAN ONLY. **Branch:** `phase-2/compliance-split` off `main` @ `4ff1891` · **Date:** 2026-08-17
**Follows:** [`compliance-load-plan.md`](compliance-load-plan.md), approved with five rulings.

Four new contracts, a provenance change, and the highest regulatory-value domain in the product. Planned before building because the surface is wider than any cycle so far.

---

## 1. The measured surface

| touchpoint | today | after |
|---|---|---|
| contracts | 1 (`compliance`) | **4** + one employees change |
| dbt sources | 1 | **4** |
| **models referencing compliance** | **12** | see §2 |
| ingest domain blocks | 1 | 4 |
| provenance registry domains | 1 | 4 |
| domain labels (EN + AR) | 1 | 4 |
| demo sample files | 1 | 4 |

Column reach across models: `iqama_expiry` **7**, `gosi_status` **6**, `mudad_status` **5**, `gosi_salary` **4**, `work_permit_expiry` **4**, `payroll_basic_salary` **4**, `qiwa_status` **3**, `health_insurance_status` **3**, `contract_authenticated` **3**, `occupation_code` **2**.

## 2. The seam — and this codebase has already used it

**`base_compliance_current` is the only place the compliance columns are assembled.** Eleven of the twelve models read *it*, not `stg_compliance`.

So the four staging models are joined **there**, and the downstream eleven need no edit. That is not a convenience — it is the technique `stg_employees` already used for `project`, in its own words:

> *"Resolving here means the 33 downstream models that name `project` keep working unchanged and are correct by construction — the alternative was editing all of them and hoping none was missed."*

**Same reasoning, same seam, and it is the single decision that makes this cycle tractable.**

`base_government_platform_records` also reads `stg_compliance` directly and is the one model that must change with it.

## 3. The four contracts

| contract | columns | period-grained? |
|---|---|---|
| `compliance_gosi` | `employee_id`, `period`, `gosi_status`, `gosi_salary`, `occupation_code` | yes |
| `compliance_qiwa` | `employee_id`, `period`, `qiwa_status`, `contract_authenticated`, `work_permit_expiry` | yes |
| `compliance_wps` | `employee_id`, `period`, `mudad_status` | yes |
| `compliance_health` | `employee_id`, `period`, `health_insurance_status` | yes |

**Moved out entirely:**

- `iqama_expiry` → **employees, optional** (ruling 4: it does not change with the reporting period; it changes when the iqama is renewed).
- `payroll_basic_salary` → **removed** (ruling 2: we have payroll).
- `occupation_match_status` → **derived**, and see §6.

`employee_id` + `period` are required in each; everything else optional, so a client with a Qiwa export listing only contract status can load it.

### 3.1 Applying ruling 4's test to each column

The test — *does the value change with the reporting period?* — is worth applying explicitly, because it is the rule future contracts will be judged by:

| column | changes with period? | home |
|---|---|---|
| `gosi_salary` | **yes** — it is re-registered as pay changes | GOSI contract |
| `gosi_status` | yes — registered this month, lapsed next | GOSI contract |
| `qiwa_status`, `mudad_status`, `health_insurance_status` | yes | their contracts |
| `contract_authenticated` | yes — a contract is authenticated at a point in time | Qiwa contract |
| `work_permit_expiry` | **no** — an attribute of the permit | Qiwa contract *(see below)* |
| `iqama_expiry` | **no** | **employees** |

`work_permit_expiry` is the awkward one: by the test it is an attribute, like `iqama_expiry`. It stays in the Qiwa contract because **it arrives with the Qiwa export** and no HRIS reliably carries it — where `iqama_expiry` demonstrably sits on the employees master. **The test decides where a column belongs; availability decides where it can actually come from, and when they disagree the disagreement is worth stating rather than resolving silently.**

## 4. Provenance and the config defect (ruling 3)

`has_gosi_source_sql` and `has_wps_source_sql` resolve from `config/business_rules.yml`:

```yaml
compliance_rules:
  has_gosi_source_for_period: true
  has_wps_source_for_period: true
```

**A repo literal deciding a client fact, defaulting True** — SP-009's shape, one cycle after recording it. Every deployment gets `TRUE` unless someone edits a file nothing prompts them to open.

**Fix regardless of the split**: resolve both from provenance, exactly as `has_cost_center_source_sql` does, and **delete the config keys** so the old path cannot silently win. Two more vars join them — `has_qiwa_source_sql`, `has_health_source_sql` — with the same resolution.

Per SP-009 this needs its expiry test: **a `has_*_source_sql` var that is not resolved from provenance in `build_warehouse` fails.** That test is the general form and would have caught these two.

## 5. Demo byte-identity is the hard constraint

`generate_sample_data` writes one `compliance_sample.csv`. It must become four, and **the demo fingerprint must not move**: `19 / 446175.0 / 50.0 / 667 / 15`.

`667` is the exception-source count and `15` the data-quality row count — both reachable from compliance exceptions. Splitting one sample into four rewrites which rows exist in which file while the *joined* result must be identical.

**This is the highest-risk part of the cycle** and the sequencing in §7 exists for it: the split lands with all four domains provided in demo, so every gate is TRUE and the joined shape is unchanged. A demo where one platform is absent is a *later* test, not part of the migration.

## 6. Ruling 5 — does the same-file assumption generalise?

**Checked. It generalises only partly, and the split changes the answer.**

This client's employees export carries both the job title and the job title as recorded on the iqama, so their comparison is same-file. But that is a fact about **their HRIS**, not about KSA HR systems generally: platforms that integrate with MOI commonly store the iqama profession, while a client whose occupation is maintained only in GOSI would have it in a GOSI export.

**Applying ruling 4's own test resolves it.** The occupation recorded on the iqama does *not* change with the reporting period — it changes when the iqama is reissued. **So it is an employee attribute, and by ruling 4 it belongs on the employees contract**, as `iqama_occupation`, optional.

If that is accepted, then:

- `occupation_match_status` compares `job_title` against `iqama_occupation` — **both on employees, for every client.**
- **RI does not need a cross-domain mechanism for it.** It becomes an ordinary same-file derivation, of the species already built.
- The GOSI-registered occupation stays `occupation_code` in the GOSI contract as a *separate* fact, because a GOSI occupation and an iqama occupation genuinely can differ — and where they do, that is itself a compliance finding worth surfacing.

**Recommendation: add `iqama_occupation` to employees as optional, and reduce `occupation_match_status` to a same-file derivation.** RI keeps its cross-domain design for the orphan-key problem, which genuinely needs it — but it should not be built to serve this column.

## 7. Sequence

Each step demo-rebuilt and byte-identity checked; each is independently revertable.

1. **The provenance fix alone** (§4), with its SP-009 expiry test. No shape change, and it is a live defect today.
2. **`iqama_expiry` → employees, optional** (ruling 4). Touches 7 models — the widest single move — and is worth doing on its own so a demo drift is unambiguous.
3. **`payroll_basic_salary` removed** (ruling 2), with the GOSI-versus-payroll comparison rebuilt across domains and withheld when payroll is absent.
4. **The four contracts and four staging models**, joined at the seam (§2). `base_compliance_current` changes; the eleven downstream do not.
5. **Ingest, sample data, provenance registry, labels.**
6. **`iqama_occupation` and the same-file derivation** (§6) — only if ruling 5's recommendation is accepted.
7. **Per-platform suppression tests**: a GOSI-only client gets GOSI figures and a *named* reason for the rest.

## 8. Test obligations (SP-001 — both halves)

1. A client with one platform gets that platform's figures **and a named reason** for the others — and a client with all four gets exactly what they get today (the tamper).
2. `has_*_source_sql` resolves from provenance; the config path is **gone**, not merely superseded.
3. The SP-009 expiry test: any `has_*_source_sql` not resolved from provenance fails.
4. No compliance figure is served for an absent platform — the `manager_id` lesson, per platform.
5. `iqama_expiry` on employees produces the same `iqama_expiring_30` it does today.
6. The GOSI-versus-payroll comparison withholds when payroll is absent rather than reporting agreement.
7. Demo byte-identity at every step.

## 9. Cost and risk

**The largest cycle in the phase so far**: four contracts, twelve models in reach, ingest, sample data, provenance, labels, and a migration that must not move the demo fingerprint.

Two things reduce it: the **seam** (§2) confines the model changes to two files, and the **sequencing** (§7) puts a live defect fix first and the risky sample split late, behind three independently verifiable steps.

**The risk that remains is regulatory.** A wrong Saudization or GOSI figure is not a cosmetic defect — it is a Nitaqat band, and that is hiring permits, visa quotas and government-contract eligibility. Every fabricated-favourable shape this phase has removed costs more here than anywhere else, which is the argument for doing this as five reviewable steps rather than one large change.

---

**Not built. Awaiting a ruling — in particular on §6, which changes what the referential-integrity cycle needs to build.**
