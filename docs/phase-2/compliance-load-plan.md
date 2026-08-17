# Compliance on real data, and the deferred shape question — Plan

**Status:** PLAN ONLY (A5). **Branch:** `phase-2/compliance-load` off `main` @ `4ff1891` · **Date:** 2026-08-17
**Answers:** the shape question deferred from the contract audit. Per SP-003 this plan carries magnitudes and vocabulary only.

The highest regulatory-value domain in the product, and the one whose contract least resembles anything a client can produce.

---

## 1. The finding that reframes the question

**Most of what compliance needs is already on the employees export we loaded — and we ignored it as PII.**

Read from the client's header line only (no row read), their employees file carries columns for:

| compliance fact | present on the employees export |
|---|---|
| iqama expiry | **yes** — an iqama expiry date column |
| GOSI registration status | **yes** — a "registered in social insurance" column |
| GOSI salary | **yes** — a "value registered with social insurance" column |
| health-insurance status | **yes** — a Council of Cooperative Health Insurance column |
| occupation as recorded on the iqama | **yes** — a "job title on the iqama" column |
| Qiwa status | no |
| work permit | no |

So the question is **not** "does the client have a compliance file". For the facts that matter most, they have the data and it is not in a compliance file at all — it is a facet of their HRIS master, which we already hold.

### 1.1 And it changes an assumption the referential-integrity cycle is built on

`occupation_match_status` was moved to that cycle because its comparison — the platform occupation against the actual job title — was believed to cross a domain boundary.

**For this client it does not.** Their employees export carries *both* the job title and the job title as recorded on the iqama. **The comparison is same-file.** That should be checked before the RI cycle designs a cross-domain mechanism to serve it.

## 2. What the contract asks for, and where each column actually comes from

Compliance is **8 of 13 required**, and its columns come from **five external sources plus one of our own domains**:

| column | actual source |
|---|---|
| `gosi_status`, `gosi_salary` | **GOSI** |
| `qiwa_status`, `contract_authenticated`, `work_permit_expiry` | **Qiwa** (MHRSD) |
| `mudad_status` | **Mudad** (WPS) |
| `health_insurance_status` | **CCHI** / the insurer |
| `iqama_expiry` | **MOI / Absher** — and in practice the HRIS |
| `occupation_code` | GOSI or the iqama |
| `occupation_match_status` | **derived** — a comparison |
| `payroll_basic_salary` | **our own payroll domain** |
| `employee_id`, `period` | keys |

**No client has a single file containing these.** They are five portals with five logins, and a client using Qiwa but not Mudad cannot produce a row that satisfies both.

### 2.1 `payroll_basic_salary` should not be in this contract at all

It exists so `gosi_salary` can be compared against payroll — a GOSI-versus-payroll salary mismatch is a real and valuable compliance finding. But **we already have payroll as a domain**. Asking the client to copy payroll figures into a compliance file is the same species as the derived columns: *asking the client to assemble a comparison we are better placed to make*, and rejecting their file when they cannot.

It should be **removed**, and the comparison made across the two domains we hold.

## 3. The codebase already believes the sources are separable

`mart_compliance_exceptions` gates two of its arms:

```sql
WHERE gosi_status  IS NULL AND {{ var('has_gosi_source_sql') }}
WHERE mudad_status IS NULL AND {{ var('has_wps_source_sql') }}
```

**This is the shape question already half-answered in code.** But both vars resolve from `config/business_rules.yml`:

```yaml
compliance_rules:
  has_gosi_source_for_period: true
  has_wps_source_for_period: true
```

**A hand-edited repository literal deciding a fact about a client.** It is the class `test_dbt_vars` exists for — a repository choosing a client's window — and escapes that test only because the values are booleans rather than date-shaped. Every client gets `true` unless an operator remembers to edit a config file, which nothing prompts them to do.

That is a defect independent of the shape decision and should be fixed either way: these must resolve from what the client actually provided, exactly as `has_cost_center_source_sql` does.

## 4. Recommendation — split by platform

**Recommended: replace the single `compliance` contract with one optional contract per platform** — `compliance_gosi`, `compliance_qiwa`, `compliance_wps`, `compliance_health` — each with its own provenance entry, each independently declarable.

### Why

1. **It matches how the data is obtainable.** One portal, one export, one contract. A client with GOSI and no Mudad declares GOSI and gets GOSI figures. Today they get a rejected file or a file padded with invented columns.
2. **The codebase already models it this way** and does so with a hand-edited flag (§3). Splitting makes the existing belief honest and automatic: provision comes from what arrived, not from a config someone forgot.
3. **Per-platform provenance means per-platform suppression.** A missing Mudad export suppresses WPS figures and nothing else. Today a missing *anything* means no compliance domain at all — all eleven metrics dark, including the iqama expiry figures that need no platform export whatsoever.
4. **It is the only shape that survives partial adoption**, which is the normal state. Nitaqat, WPS and GOSI compliance are separate regulatory regimes with separate deadlines; clients adopt them at different times.

### The cost, stated

More domains means more declarations, more provenance entries, and a longer onboarding checklist. **That cost is real and I think it is the right trade**: the alternative is a single contract that no client can satisfy, which converts every partial adopter into a rejected upload and a support conversation.

### What I considered and rejected

- **Keep one contract, relax everything.** Cheapest, and it hides the problem. A file with two of thirteen columns would load and produce a compliance page that is almost entirely withheld, with no way to say *which platform* is missing — because provision is domain-grain and there would still be one domain.
- **Move everything onto `employees`.** Tempting given §1, and wrong: compliance is **period-grained** (`period` is required, and GOSI salary changes month to month) while employees is a snapshot. Folding them in would lose the history that makes a GOSI-versus-payroll comparison meaningful over time.

### 4.1 Where §1 fits

The split does not by itself get this client their iqama and GOSI figures, because those columns are on their *employees* export. Two options, and this needs a ruling:

- **(a)** Let the employees contract carry the HRIS-resident compliance facts as **optional columns** — honest for a snapshot fact like iqama expiry, less so for GOSI salary.
- **(b)** Let one uploaded file feed **more than one table** via a mapping profile — a real mechanism change, and the more general answer.

**(a) for `iqama_expiry` and `health_insurance_status`, which are genuinely employee attributes**; **(b) considered separately**, because it is a mapping-layer capability rather than a compliance question.

## 5. What the operator must do

1. **Ask which platforms the client actually uses.** Not which they should — which they log into. That answer determines which contracts to expect and is worth more than any file inspection.
2. **Check the employees export first** (§1). For this client, iqama expiry, GOSI status and salary, and health-insurance status are already in hand and were ignored as PII. Some of the highest-value compliance figures may need no new file at all.
3. **Per-platform, one file each.** Do not ask for a merged file; a client producing one by hand introduces transcription errors into regulatory figures.
4. **`period` is required and compliance is a period source.** As with payroll, an operator-set `REPORT_MONTH` absent from the file will be caught at ingest.
5. **Expect PDPL sensitivity.** Iqama numbers, GOSI numbers and health-insurance identifiers are personal data. The mapping profile should ignore identifiers and map only statuses and expiry dates — the ignore-with-reason mechanism already exists and the employees load used it for exactly these columns.

## 6. What changes on screen

**11 metrics un-suppress** with compliance alone: `mart_compliance_kpis` in full (GOSI missing count, iqamas expired and expiring, work permits expired and expiring, WPS exception count, compliance exception count), `mart_document_expiry`, `mart_gosi_status`, `mart_workforce_iqama_expiry`, and `mart_workforce_kpis.iqama_expiring_30`.

Under the split, these divide by platform — which is the point: a GOSI-only client would get the GOSI figures and a stated reason for the rest, rather than a blank page.

## 7. Test obligations, when built

1. A client with one platform gets that platform's figures and **a named reason** for the others.
2. `has_gosi_source_sql` and `has_wps_source_sql` resolve **from what the client provided**, not from the repo config (§3) — with the config path removed, so it cannot silently win.
3. The GOSI-versus-payroll comparison works across domains without `payroll_basic_salary` (§2.1), and withholds when payroll is absent.
4. Demo byte-identity.
5. A test that no compliance figure is served for a platform whose export is absent — the `manager_id` lesson, per platform this time.

## 8. Risk

**The regulatory stakes make the usual failure modes worse.** A withheld Saudization figure is an inconvenience; a *wrong* one is a Nitaqat band, which is hiring permits, visa quotas and government-contract eligibility. Every fabricated-favourable shape this phase has removed — the zero that reads as compliant, the sentinel that reads as a category — is more expensive here than anywhere else in the product.

**The single largest risk is not technical**: it is asking a client for five portal exports and receiving one hand-merged spreadsheet, assembled by someone under time pressure, which we then treat as authoritative for regulatory reporting.

---

**Not built. Awaiting a ruling — on the shape (§4), and separately on §4.1.**
