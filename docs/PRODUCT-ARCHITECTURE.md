# HR Analytics Command Center — Product Architecture

**Status:** foundational reference. Every future development cycle should point at this document.
**Repo state at time of writing:** `main` @ `2257d4a` — Phase 0 complete (working 3-gate CI, `data_mode` switch, single-source `report_month` resolver, real-data ingestion mechanism with contract validation).

---

## 1. What this product is

A deployable HR analytics platform for the KSA/GCC market, sold to HR professionals and HR departments. It ingests a client's HR data via standardised bilingual templates, validates it against explicit contracts, and produces governed analytics across workforce, Saudization/Nitaqat compliance, payroll, attendance, and employee relations — with data quality exceptions surfaced as a first-class feature rather than hidden.

**Primary differentiator:** it is built by a practitioner for the Saudi regulatory reality (Nitaqat bands, GOSI, Iqama expiry, Qiwa/Mudad/WPS), and it tells the client *which of their records are wrong* rather than silently averaging over bad data.

**Secondary differentiator:** it can run entirely inside the client's own infrastructure. In a market where HR data is highly sensitive and PDPL enforcement is active, "your data never leaves your premises" is a sales advantage, not just an architecture choice.

---

## 2. Deployment model — single-tenant-per-deployment

**Decision: one isolated stack per client. Not shared multi-tenancy.**

Each client gets their own container stack (backend + frontend + warehouse), deployed to one of two targets:

| Mode | Where it runs | Data controller | Data processor | Notes |
|---|---|---|---|---|
| **Client-hosted** | Client's own servers/VPC | Client | Client | Vendor never touches the data. Simplest compliance posture. Premium option for conservative sectors. |
| **Vendor-hosted** | Certified KSA-region infrastructure | Client | Vendor (you) | Requires DPA per client, KSA data residency, documented security controls. Each tenant physically isolated. |

### Why this over multi-tenancy

- The current stack is *already* nearly ideal for it: docker-compose, embedded DuckDB, no external service dependencies. This was an accident of the local-first design but it is a genuine asset.
- DuckDB is an embedded analytical database, not a shared transactional store. Forcing it into multi-tenancy is a rewrite of the data layer.
- Isolation is physical, not logical — the strongest possible answer to "how do you guarantee my data isn't mixed with another company's."
- Per-deployment overhead only becomes painful at high customer counts. At 5–20 mid-size clients, one stack each is cheaper to build *and* cheaper to defend in an audit.

**Revisit trigger:** if the customer base moves toward many small clients (50+), re-evaluate a shared control plane with per-tenant warehouses. Not before.

### What this requires building

- Reproducible deployment packaging (compose stack, environment templates, versioned images).
- Per-deployment configuration: client identity/branding, entity size and sector (drives Nitaqat bands), locale default, enabled modules.
- Real authentication and user management (the current `MOCK_USER_DB` with a shared JWT secret is a prototype, not a product).
- An upgrade path — clients must be able to move to a new version without losing configuration or mapping profiles.

---

## 3. Data governance and PDPL posture

**This is not a compliance appendix. It is a product constraint that shapes the architecture.**

- Saudi PDPL is actively enforced. Processing another company's employee records (national IDs, GOSI numbers, payroll) is high-sensitivity processing.
- **Client-hosted:** the client is both controller and processor; the vendor is a software supplier. Materially lower exposure.
- **Vendor-hosted:** the vendor is a processor. Requires a Data Processing Agreement per client, KSA-region hosting, documented security controls, breach procedures, and a defined retention/deletion policy. A DPO may be required depending on scale.
- **Cross-border transfer is the sharp edge.** Any personal data leaving KSA — *including a call to an LLM API hosted abroad* — is a regulated transfer requiring approved safeguards. See §5.
- Engage a Saudi privacy specialist before onboarding the first paying client. This document is an engineering position, not legal advice.

### Governance features that are also product features

- Audit log of who uploaded what, when, and what changed.
- Explicit retention and deletion controls (a client must be able to demand erasure).
- Role-based access — an HR analyst should not necessarily see individual salaries.
- Data lineage: every figure traceable to its source file and ingestion run.

---

## 4. Canonical bilingual schema and the template flow

**This is the onboarding path, and onboarding friction is what kills HR SaaS deals.**

The existing `data/contracts/*.yml` files become the single source of truth for a **bilingual canonical schema**. Each column carries:

```
- name: joining_date          # canonical key, used everywhere internally
  name_en: Joining Date
  name_ar: تاريخ الانضمام
  type: DATE
  required: true
  description_en: Date the employee started employment
  description_ar: تاريخ بدء الموظف للعمل
  example: "2024-03-15"
  allowed_values: [...]       # where applicable
```

One definition generates all of: the downloadable template, the validator rules, the UI labels, and the error messages.

### The user-facing flow

1. **Download template** — a formatted Excel file per domain: correct headers, an instructions sheet in Arabic and English, dropdown validation on enum columns, and 2–3 example rows.
2. **Fill and upload** — drag-and-drop, one domain at a time.
3. **Validate** — contract validation runs *before* anything is committed. Errors are reported per-cell, in the user's language: *"Row 47, تاريخ الانضمام: expected YYYY-MM-DD, found `0025-01-26`."*
4. **Preview** — row counts, detected period, sample of parsed records, and a summary of what will change. Nothing is written until the user confirms.
5. **Commit** — ingest to bronze/silver, rebuild marts, refresh dashboard.

### Mapping profiles

Clients will not always use the template. Many will have an existing export (an HRIS extract, a payroll file) with their own column names — often Arabic, often inconsistent.

A **mapping profile** records how a client's raw columns map to canonical keys, including derivations (e.g. `is_saudi` derived from a nationality field) and value translations (status vocabularies). Saved per client, reused on every subsequent upload.

**These accumulated mapping profiles are the training ground for the AI column mapper in §5.** Build the manual version first; the automated version becomes far more tractable once real mappings exist to learn from and test against.

### Known real-world data issues the pipeline must handle explicitly

Encountered in actual exports — these are validation cases, not edge cases:

- Corrupted date serials (year `0025` instead of `2025`).
- Arabic column headers with inconsistent spacing and naming.
- Derived fields that do not exist in source data (`is_saudi`, project/location mapping).
- Mixed status vocabularies (Arabic and English values in the same column).
- Extra columns in real exports that the contract does not define.

Current policy is **hard-reject** on unexpected columns — correct default, because a surprise column usually means a wrong or renamed export. The mapping profile is the sanctioned way to reconcile a legitimately different file, not silent coercion.

---

## 5. AI module architecture

**Constraint first: AI must be optional, swappable, and non-load-bearing.**

- Client-hosted deployments will frequently forbid outbound API calls entirely.
- Calling an LLM hosted outside KSA with employee data is a cross-border personal data transfer under PDPL.
- Therefore: a provider-abstraction layer supporting a KSA-region endpoint, a client-provided endpoint, a self-hosted model, or **disabled**. With AI disabled, every core dashboard function must still work.
- AI output is **advisory**. It never writes to marts, never alters figures, never auto-commits data. It proposes; a human approves.

### Tier 1 — genuine differentiation, build these

1. **Column mapper agent.** Client uploads a raw export; the agent proposes a mapping to the canonical schema, flags required derivations, shows per-column confidence, and a human approves. Directly attacks the biggest onboarding barrier.
2. **Compliance advisor (Nitaqat what-if).** *"You are 2.1% below Green. Hiring 4 Saudi employees in these roles reaches it. Three Iqamas expiring next quarter would drop you to Yellow."* Combines Nitaqat band mathematics with the client's actual workforce composition — the capability nobody else is positioned to build as well.
3. **Exception triage.** The data quality layer already detects problems. The agent explains each in plain language, proposes the correction, and ranks by business impact.

### Tier 2 — expected by 2026, build after Tier 1

4. **Narrative generation** — executive commentary written from the marts.
5. **Natural-language query** over the analytical layer.
6. **Report builder** — user-defined report schemas, agent-assisted. (This is the "build your own report" capability; it depends on the canonical schema being solid first.)

---

## 6. Roadmap

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — Foundation** ✅ | Working CI, `data_mode` gating, single-source period resolver, ingestion mechanism with contract validation | Complete at `2257d4a` |
| **1 — Canonical schema + templates** | Bilingual schema definition, template generator, validate/preview/commit flow, localized errors | A non-technical HR user can download, fill, upload, and see their data |
| **2 — Client zero** | Run real data end-to-end through Phase 1. Mapping profile for a real Arabic-headed export. Fix what breaks | Real workforce, Saudization, and payroll figures rendering correctly — **and no metric rendering at all when its source data is absent** |
| **3 — Product hardening** | Real auth and user management, RBAC, audit logging, demo/real UI indicator, retention controls | Safe to put in front of a client |
| **4 — Deployment packaging** | Reproducible per-client stack, configuration, upgrade path, KSA hosting decision, DPA templates | A second deployment can be stood up without manual surgery |
| **5 — AI Tier 1** | Provider abstraction, column mapper, compliance advisor, exception triage | AI improves onboarding measurably; disabling it breaks nothing |
| **6 — AI Tier 2 + report builder** | Narrative, NL query, user-defined report schemas | — |

**Phase 2 exit criterion, expanded (2026-08-10).** "Rendering correctly" includes *not rendering*. A metric whose source domain the client has not provided must return null from the API and render as an empty state — never as a value manufactured from an empty table. Measured before this was enforced, a client who had uploaded only their employee master was shown `absence_days = 494` (every employee absent every workday), `gosi_missing_count = 19` (a false regulatory finding), and `sla_compliance_pct = 100.0` over zero cases. Suppression belongs at the API layer, because CSV export, report generation and the local Power BI profile consume the same endpoints as the React app.

**Sequencing rationale:** Phase 2 (real data, by hand) must precede Phase 5 (AI mapping). An inference engine cannot be built or tested without ground truth, and the manual mapping work produces exactly that ground truth.

---

## 7. Known open items carried from Phase 0

| Item | Impact |
|---|---|
| `/api/meta/app-config` has no frontend consumer | **A user cannot tell demo data from real data in the UI.** Cheap to fix, high consequence if a client sees sample numbers and believes them. Address in Phase 1 or 3. |
| Only 4 of 21 tables are real-sourceable (5 contracts exist) | Recruitment, talent, succession, learning have no real feed. Must be gated or clearly labelled, never shown as real. |
| TD-001 open — three closure clauses unmet | Tracked debug scripts with module-level side effects (network calls, read-write DB access at import). Contained by `pytest.ini` scoping; no CI exposure. |
| Local `.venv` shim broken after repo relocation | `build_warehouse.py` cannot invoke `dbt.exe` locally; also a genuine code bug — the fallback checks file existence rather than runnability. |
| No real data has yet run through the ingestion mechanism | Phase 0 landed the mechanism, not the outcome. |

---

## 8. Principles carried forward from Phase 0

These held throughout the foundation work and should not be relaxed as scope grows:

- **Plan before execute.** Every cycle produces a reviewed plan before code is written.
- **Verify against a reproduced failure**, not an assertion. Prove the bug, then prove the fix.
- **Never show a fabricated number as real.** The `data_mode` gate exists for this reason.
- **Clean-environment verification.** Local runs with warm state hide real defects; CI on an empty runner is the honest test.
- **Do not close an item until its stated criterion is met.** Partial fixes get recorded as partial.
