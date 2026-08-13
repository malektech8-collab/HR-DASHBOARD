# Phase 3 — Real Authentication (PLAN ONLY)

**Branch:** `phase-3/auth` off `main` @ `6f1962c` · **Date:** 2026-08-13
**Status:** PLAN ONLY. Nothing implemented.
**Closes:** TD-006 · **Rationale adopted:** this layer was decorative before P0-2 and is load-bearing now.

The brief is right about the layer. It is wrong about the perimeter, and that has to come first because it changes what "safe" means at the end of this cycle.

---

## 0. BLOCKING FINDING — 77 of 83 routes have no authentication at all

TD-006 says the auth layer "is now the only thing between an anonymous request and a client's data". That is true for the six routes P0-2 protected. It is not true of the product.

Measured on `main` @ `6f1962c`, no token, no header:

```
/api/payroll/summary      -> 200
/api/workforce/summary    -> 200
/api/compliance/summary   -> 200
/api/payroll/exceptions   -> 200
/api/data/uploads         -> 401   <- the only kind that is protected
```

And the bodies are not aggregates:

```json
/api/workforce/exceptions -> 200
{"exceptions":[{"employee_id":"EMP003","employee_name":"Fahad Al-Otaibi",
  "issue_type":"Missing Manager", ...}]}
```

**Named individuals, to an anonymous caller.** `grep` confirms the shape: 83 routes across `backend/app/api/`, and `get_current_user` appears in exactly one file — `data.py`.

So the honest statement of the current posture is not "weak auth on the data". It is:

> **Strong-ish auth on the six routes that write, and no auth whatsoever on the seventy-seven that read** — including individual salaries (`payroll.py`, 10 salary references), GOSI status, Iqama expiry, and per-employee exception rows carrying names.

**This changes the cycle's exit criterion.** Replacing `MOCK_USER_DB` with argon2 and a real user store makes the lock on the back door real. It does nothing about the front door being open. A deployment could finish this cycle with textbook authentication and still serve a client's payroll to anyone who can reach the port.

**Recommendation: fold route coverage into this cycle**, as its own step, before the credential work. It is smaller than the credential work (one dependency, applied to a router list, plus a test that enumerates routes and asserts coverage) and it is the half that actually stops the exposure.

**Ruling requested.** The guardrail says "this is about making the existing layer real", which I read as excluding this. I think excluding it would ship a cycle whose report reads "authentication is now production-grade" while `/api/workforce/exceptions` still names employees to strangers — and that sentence would be true and misleading at once, which is the exact pattern SP-001 and the cycle-5a routing-around were about. If it is out of scope, it needs to be recorded as a named blocker in the same breath, not left implied.

---

## 1. What is WRONG with the JWT implementation, not merely missing

### 1.1 The signing secret is a committed constant — the most severe item

```python
SECRET_KEY = "SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD"
```

Every deployment of this product signs with the same key, and the key is in the repository.

**This is worse than the plaintext passwords.** Plaintext passwords require an attacker to reach the server and get a database read. A forged token requires only the source — which the vendor's own staff, any contractor, and anyone the repo is ever shared with already have. With five lines of `pyjwt`, anyone can mint a valid `SYSTEM_ADMIN` token for any deployment, and it will pass `decode_access_token` and `get_current_user`.

The comment says `DO_NOT_USE_IN_PROD`. Nothing enforces that, and there is no other value to fall back to.

### 1.2 The password comparison is plaintext and non-constant-time

```python
if not user or user["hashed_password"] != form_data.password:
```

`!=` on a `str` short-circuits at the first differing byte. The timing signal is small over HTTP and is the least of the problems here, but it is worth naming because the fix is free: the hash verifier is constant-time by construction.

### 1.3 The field name asserts a property the code does not have

`hashed_password` holds `"adminpassword"`. A name that lies is worse than no name: it is exactly the kind of thing a reviewer skims past because it looks correct. (Same family as `tsc --noEmit` reading like a typecheck — SP-001.)

### 1.4 The token carries no identity beyond `sub` and no lifecycle

Claims present: `sub`, `exp`. Absent: `iat`, `nbf`, `iss`, `aud`, `jti`.

- No `iss`/`aud` → a token minted for deployment A is valid at deployment B. With §1.1's shared secret this is not theoretical: **one token works everywhere.**
- No `jti` → no revocation list is possible, so **there is no logout**. A token handed to the wrong person is valid until it expires, and nothing can stop it.
- No `iat` → cannot invalidate all tokens issued before a password change.

### 1.5 Thirty-minute hard expiry with no refresh

`ACCESS_TOKEN_EXPIRE_MINUTES = 30`, and there is no refresh path. A user mapping a 37-column export is logged out mid-task and loses the screen's state. **The current design is simultaneously insecure and hostile**, which is worth stating because the fix must address both — a longer expiry alone trades one for the other.

### 1.6 Two things that are already right — keep them

- `jwt.decode(..., algorithms=[ALGORITHM])` pins the algorithm list. This is the correct defence against `alg: none` and RS→HS confusion. **Do not "improve" it into accepting a list from config.**
- **The role is not in the token.** `create_access_token(data={"sub": user["email"]})` carries only the subject; `get_current_user` looks the role up per request. That means a role change or a deactivation takes effect on the next request rather than on the next login. Many rewrites lose this by putting claims in the token for performance. **Preserve it explicitly** — with a per-request store lookup it costs one indexed SQLite read.

---

## 2. Password hashing and the user store

### 2.1 Hashing: argon2id

`argon2-cffi`, used directly. Not `passlib` — an extra abstraction layer over a decision we are making once, and its maintenance status is not something to depend on for the security-critical path.

Parameters at the library defaults (argon2id, 64 MiB, t=3, p=4), recorded in the plan so they are a decision rather than an accident, with a `needs_rehash` check on successful login so raising them later upgrades users transparently.

`bcrypt` is an acceptable alternative if `argon2-cffi`'s wheel causes trouble in the container; the interface below is written so the choice is one module.

### 2.2 Where the store lives — and why not the warehouse

Two facts settle this, both verified:

1. **The API opens DuckDB read-only.** `duckdb_client.py`: `duckdb.connect(database=..., read_only=True)`. A write path for user records would mean a second, writable connection to the analytics database — reintroducing exactly the concurrency question that read-only was chosen to avoid.
2. **The pipeline drops and rebuilds warehouse tables.** `build_warehouse.py` runs `DROP TABLE IF EXISTS {table_name}` per table. A `users` table there would survive exactly until the next refresh, then vanish — and the failure mode is a deployment that silently loses every account on a scheduled data load.

And `PRODUCT-ARCHITECTURE` §2 names it directly: *"DuckDB is an embedded analytical database, not a shared transactional store."* A user table is transactional.

**Recommendation: SQLite, at `data/auth/auth.db`.**

| | |
|---|---|
| Why SQLite | stdlib (`sqlite3`), no new service, transactional, single-writer — which matches one backend container per deployment exactly |
| Why not Postgres | §2 names "no external service dependencies" as a genuine asset of this stack. Adding one for three user rows would forfeit it, and the per-client deployment story gets materially harder |
| Why a separate file | it is deployment **state**, like `data/onboarding/` and `data/mapping/` — it survives pipeline rebuilds, is volume-mounted, and is gitignored |
| Backup story | one file, alongside the other deployment state, which is what the client-hosted operator already has to back up |

`data/auth/*` joins the gitignore block that already covers `data/onboarding/*`, `data/staging/*`, `data/mapping/*`, with the same comment: **deployment state, never repo content.**

### 2.3 Schema

```sql
CREATE TABLE users (
    id                  INTEGER PRIMARY KEY,
    email               TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash       TEXT NOT NULL,        -- argon2id, never anything else
    role                TEXT NOT NULL,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    password_changed_at TEXT NOT NULL,        -- for §1.4's iat check
    failed_attempts     INTEGER NOT NULL DEFAULT 0,
    locked_until        TEXT
);
CREATE TABLE auth_schema_version (version INTEGER NOT NULL);
```

`password_hash`, not `hashed_password` — the old name is retired along with the lie it told.

`failed_attempts` / `locked_until` give lockout after N failures. Worth having: three known email addresses and a network port is an inviting target, and the alternative is rate limiting, which needs infrastructure this stack does not have.

---

## 3. First-run bootstrap — the question the dict literal was avoiding

The requirement is exact: **a fresh deployment must reach a working admin account without a credential ever existing in a file, an image, an env var, or the repo.**

### 3.1 Primary: an interactive CLI

```
python -m app.cli create-admin --email operator@client.example
Password: ********        # prompted, never in argv, never in the environment
```

`getpass`, so it is absent from shell history and from `ps`. This is the client-hosted path, where an operator has a shell on the box.

### 3.2 Fallback: a one-time bootstrap token, for vendor-hosted

When the store has **zero users**, the backend generates a single-use token at startup and writes it to the container log — nowhere else:

```
================================================================
 THIS DEPLOYMENT HAS NO USERS. To create the first administrator:
   POST /api/auth/bootstrap   with token  <64 random chars>
 This token is single-use, expires in 60 minutes, and is destroyed
 the moment the first account exists. It is not stored on disk.
================================================================
```

Held in process memory only. Invalidated by first use, by expiry, or by any user existing. `docker compose logs` is the operator's channel, which they already have.

### 3.3 The invariant that makes both safe

**With zero users, every authenticated route returns `503`, not `401`.**

`401` invites guessing and tells an attacker the shape of the door. `503` with *"this deployment has not been initialised"* is the truth, and it makes an uninitialised deployment obviously broken rather than quietly open. A test asserts it.

**No default account is ever created in real mode.** Not a disabled one, not one with a random password. The store starts empty and the operator fills it.

---

## 4. Roles — mechanism now, policy next

`RoleChecker` already exists and is used on exactly **one** endpoint (`/api/governance/status`). Three roles are defined.

**Recommendation: the mechanism lands in this cycle; the policy does not.**

The mechanism has to land — the rewrite touches `get_current_user`, which `RoleChecker` wraps, and leaving it half-migrated is worse than either end state. It is also nearly free: the role moves from a dict lookup to a column read.

The **policy** — who may see an individual salary — is a product and legal decision per client under PDPL data minimisation, not an engineering one. Too tight and the product is useless to the analyst it was built for; too loose and it is a breach. That is an architect's call informed by a real client, and this cycle has no real client.

What this cycle owes the next one is **the list**, so it starts from facts:

| Endpoint group | Why it needs a role decision |
|---|---|
| `/api/payroll/*` | 10 salary references; individual gross/net per employee |
| `/api/workforce/exceptions`, `/api/payroll/exceptions`, `/api/compliance/exceptions` | per-employee rows with `employee_id` and `employee_name` |
| `/api/compliance/*` | GOSI status, Iqama and work-permit expiry — regulatory identifiers |
| `/api/data/uploads/{id}` (preview) | violation messages quote the client's own offending values |
| **`/api/data/uploads/{id}/columns`** | **returns sample values from the staged file by design.** The mapping cycle established that this is the one route whose *purpose* is to return client data. Today any authenticated user reaches it, including `EXECUTIVE` |
| `/api/data/uploads*`, `/api/data/mapping/*`, refresh | mutating; a case for `SYSTEM_ADMIN`-or-analyst rather than anyone |
| `/api/governance/*` | already gated — the only thing that is |

The samples endpoint is the sharpest of these and was created by my own cycle; it is correct that it exists, and it should not be reachable by a role that has no business mapping a file.

---

## 5. Migration — demo keeps working, plaintext does not survive

`MOCK_USER_DB` is imported by **9 test files across 25 call sites**, and the three accounts appear in demo flows and the runbook.

### 5.1 Demo seeds the same three accounts, hashed

On startup, **in demo mode only**, if the store is empty, seed the three accounts with the **same passwords** and argon2 hashes, and log that it happened. `DEMO_RUNBOOK` and any muscle memory keep working; nothing about the plaintext path survives.

### 5.2 Real mode refuses to seed

The seeding function checks `settings.DATA_MODE` and refuses in real mode — the same fail-closed shape as P0-1's ingest. **Enforced by test, not by a comment**, and the test tampers: set real mode, start with an empty store, assert no user exists and the route returns 503.

### 5.3 The tests stop reaching into a user database

Today: `MOCK_USER_DB[email]["hashed_password"]` — tests read the "database" to learn the password, which only works because it is plaintext. That idiom cannot survive hashing and should not.

Replace with one fixture:

```python
def demo_credentials(role=Role.SYSTEM_ADMIN) -> tuple[str, str]:
    """The demo account for `role`. Demo mode only; raises in real mode."""
```

A mechanical change across 9 files, and it removes the assumption that a password is readable.

### 5.4 Structural guards

- `MOCK_USER_DB` does not exist as a symbol anywhere.
- No password literal appears in `backend/app/` (the demo passwords live in one demo-only constants module, which the guard exempts by name and which is unreachable in real mode).
- The string `SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD` appears nowhere in the repo.

---

## 6. Secret management

### 6.1 Behaviour

`JWT_SECRET` from the environment, **no default**.

| Mode | Missing secret | Weak/known secret |
|---|---|---|
| **real** | **refuse to start**, with a message naming the variable and the command to generate one | same — a denylist containing the old constant and obvious placeholders |
| **demo** | generate a random secret **per process** | n/a |

Demo generating per process is deliberate: demo keeps working with no setup, and tokens do not survive a restart — which is correct for a demo and makes it impossible for a demo secret to become a production one by accident.

Refusing to start in real mode is the same fail-closed decision as `REPORT_MONTH`: the operator is told exactly what to set. A weak secret that boots is a deployment nobody revisits.

### 6.2 Generation and supply

```
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

- **Client-hosted** — operator generates it and puts it in `.env` (already gitignored) or their own secret manager; `docker-compose.yml` reads `${JWT_SECRET}` with no `:-` fallback, so a missing value fails loudly rather than defaulting.
- **Vendor-hosted** — generated per deployment at provisioning, stored in the vendor's secret manager, injected as an environment variable. Never baked into an image, never in the repo, different for every client — which is what makes §1.4's cross-deployment token forgery impossible rather than merely unlikely.

`.env.example` gains `JWT_SECRET=` with a comment saying it must be generated per deployment and never committed.

### 6.3 Rotation

Rotating invalidates every live token; users log in again. That is the whole design, and it is acceptable for a 3–20 user deployment. **Dual-key rotation with a grace window is explicitly not built** — it is the kind of thing that gets built, never exercised, and quietly breaks.

Rotation is documented as a runbook step, including *when*: staff departure, suspected exposure, and after any incident.

---

## 7. Sequencing

| | Step | Independently shippable |
|---|---|---|
| 0 | **Route coverage** — apply the dependency to the read routes, plus a test enumerating all 83 and asserting each is covered or explicitly public (`/health`, `/api/meta/*`, the token route) | **yes, and it is the step that stops the exposure** — pending the §0 ruling |
| 1 | `JWT_SECRET` from env; fail closed in real mode; per-process in demo; delete the constant | yes |
| 2 | SQLite store + argon2 + the `users` schema, behind the existing `get_current_user` interface | yes |
| 3 | Bootstrap: CLI, one-time token, and the zero-users `503` invariant | yes |
| 4 | Demo seeding (demo-only, hashed) + the test-fixture migration across 9 files | lands with 2 |
| 5 | Token hygiene: `iat`, `iss`, `aud`, `jti`; revocation list; logout; refresh | yes |
| 6 | Lockout after N failed attempts | yes |

**Step 0 first if it is in scope.** Strengthening a credential system while the data is served without credentials is work on the wrong half.

Step 5 is last because it is the only step that is a genuine improvement rather than a repair, and it is the one to cut if the cycle runs long — with the exception of **logout**, which is a user-visible absence, not a hardening nicety.

---

## 8. Risks

1. **Step 0 changes every frontend read path.** Pages that fetch without a token start getting 401s. `lib/http.ts` already clears the token and handles `isUnauthorized`, so the mechanism exists, but every page needs to be behind the login gate — which today only `DataOnboarding` is. **This is the real cost of step 0 and the reason it deserves its own ruling rather than being folded in silently.**
2. **A forgotten admin password is unrecoverable** by design — no email, no reset flow, no SMTP in this stack. Mitigated by the CLI being able to reset a password on the box. Documented, not solved.
3. **argon2's memory cost** is 64 MiB per verification by default. On a small container with concurrent logins this is real. Measure it before shipping; lower `m` deliberately if needed rather than discovering it under load.
4. **SQLite and DuckDB in the same volume** invite the assumption they are the same store. Separate directory (`data/auth/`), and the module is the only thing that opens it.
5. **The demo seed is a plaintext password in the repo**, just a hashed one at rest. That is intentional and acceptable **only** while real mode cannot reach it — which is why §5.2's test tampers rather than merely asserting.

---

## 9. Out of scope

- **SSO / enterprise identity (SAML, OIDC, Entra)** — per guardrail, a later product decision. Noting only that the `users` table and the `sub` claim are compatible with an external IdP later; nothing here forecloses it.
- **The role POLICY** (§4) — next cycle, with the endpoint list this one produces.
- **Password reset by email** — no SMTP in this stack; a product decision.
- **MFA** — worth its own conversation once roles exist.
- **Audit logging** — `PRODUCT-ARCHITECTURE` §3 lists it beside RBAC in Phase 3; it wants the user identity this cycle makes real, so it follows naturally and is not folded in here.
- **Rate limiting at the edge** — lockout (§7 step 6) covers the credential-stuffing case within the app; anything more belongs to the deployment.

---

**PLAN ONLY. Nothing implemented. Stopping for review — with the §0 ruling requested before step 0 is built.**
