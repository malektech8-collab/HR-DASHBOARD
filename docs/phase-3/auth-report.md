# Phase 3 — Real Authentication (Execution Report)

**Branch:** `phase-3/auth` off `main` @ `6f1962c` · **Date:** 2026-08-13
**Plan:** [`auth-plan.md`](auth-plan.md) (approved, route coverage folded in as step 0) · **Status:** PR open, **not merged**
**Closes:** TD-006

---

## 1. (a) No route serves employee data unauthenticated

The step-0 finding, before and after. Same requests, no token:

| | before | after |
|---|---|---|
| `/api/payroll/summary` | **200** | 401 |
| `/api/workforce/summary` | **200** | 401 |
| `/api/workforce/exceptions` | **200** | 401 |
| `/api/compliance/summary` | **200** | 401 |
| `/api/meta/refresh-status` | **200** | 401 |
| `employee_name` in the body | **`Fahad Al-Otaibi`** | absent |
| still public | — | `/health` 200, `/api/meta/app-config` 200, `/api/meta/schema` 200 |

83 routes existed and `get_current_user` appeared in **one file**. P0-2 had authenticated the six that write; the seventy-seven that read were open.

**The dependency goes on the router, not the route.** Per-route means the next route added is unprotected until someone remembers; per-router means it is protected by default and an exemption has to be *written down*. `test_route_coverage.py` enumerates every route and asserts each is either authenticated or in `PUBLIC_ROUTES` **with a reason** — five entries, each justified in the file.

**`/api/meta/refresh-status` is protected rather than exempted.** It carries no employee data, but it tells an anonymous caller that a warehouse exists and when it was last built, and the UI only shows it after login. Protected-by-default means the exemption needs the argument, not the protection.

---

## 2. (b) A token minted with the old committed secret is rejected

```
a token signed with SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD
   /api/workforce/exceptions       -> 401
   real mode configured with it    -> REFUSED: JWT_SECRET is a known placeholder value.
   real mode with NO secret        -> REFUSED, names the fix
```

**Why this outranked the passwords, as ruled.** Plaintext passwords require an attacker to reach the server. A forged token required only the *source* — which staff, contractors and anyone the repo ever touched already had — and because nothing in the token said which deployment it was for, one forged `SYSTEM_ADMIN` token worked at **every customer install**.

`JWT_SECRET` now comes from the environment with no default:

- **real mode** refuses to start without one, refuses a known placeholder, refuses anything under 32 characters;
- **demo mode** generates a random secret **per process**, so demo needs no setup, its tokens die with the process, and there is no demo value that could be promoted to production by accident.

The old constant survives in exactly one place — the denylist — so restoring it by copy/paste, a rolled-back file or an old runbook **fails loudly instead of silently working**. A test asserts both halves: no assignment anywhere, and the denylist entry still present.

Tokens gained `iss`, `aud`, `iat`, `nbf` and `jti`. `iss`/`aud` make a token from one deployment useless at another even if secrets ever coincide. `jti` is what makes **logout** possible — before, a token handed to the wrong person was valid for its full lifetime and nothing could stop it.

### Two decisions retained, deliberately

Stated here so a later rewrite does not lose them, and pinned by test:

1. **The algorithm list stays pinned** — `algorithms=[ALGORITHM]`. It is the defence against `alg: none` and RS→HS confusion, and must never become a list read from configuration.
2. **The role stays out of the token.** Only `sub` identifies the user; the role is read from the store on every request, so deactivating a user takes effect on their **next request** rather than their next login. Rewrites lose this constantly to save a lookup — the lookup is one indexed read from a local file.

---

## 3. (c) A fresh deployment bootstraps with no hardcoded credential

```
a FRESH deployment, real mode, zero users
   users after startup             -> 0
   demo seeding in real mode       -> 0 created
   an authenticated route          -> 503   (not 401)
   one-time token issued           -> 64 chars, in memory only
   POST /bootstrap wrong token     -> 401
   POST /bootstrap correct token   -> 200 {'email': 'operator@client.example',
                                           'role': 'SYSTEM_ADMIN'}
   the same token, again           -> 409
   the new admin logs in           -> 200
   'a-real-password-1' in source   -> False
```

Two paths, both with the property the dict literal could not meet — **no credential exists in a file, an image, an environment variable or the repository at any moment**:

- `python -m app.cli create-admin --email you@example.com` prompts via `getpass`, so the password is never in argv, shell history or `ps`;
- for vendor-hosted, a single-use token printed to the container log: memory only, 60-minute expiry, destroyed the moment an account exists.

**The 503 is the design, not an accident.** A deployment with zero users is not refusing an unauthorised caller — it has not been set up. A `401` invites guessing and describes the door; `503` says the deployment is uninitialised, which is true and makes it obviously broken rather than quietly open.

---

## 4. (d) Demo still works

```
login as admin@synthetic.local    -> token issued
/api/workforce/exceptions         -> 200, 25 exception(s)
password stored in plaintext      -> False | argon2 hash present: True
```

The three demo accounts are seeded **hashed**, in demo mode only. What makes demo passwords in the repository acceptable is not that they are weak-but-fine — it is that `seed_demo_users()` **cannot run in real mode**, which is tampered rather than asserted: set real mode, seed, assert nothing appears.

Demo byte-identity holds: `19 / 446175.0 / 50.0 / 667 / 15`, dbt 161/161, 11/11, reconciliation `PASSED (12 independent checks)`.

---

## 5. The store, and why not the warehouse

**SQLite at `data/auth/auth.db`**, gitignored alongside the other deployment state.

The obvious place is the warehouse, and it is wrong for two verified reasons:

1. The API opens DuckDB **read-only**; a write path would need a second writable connection, reintroducing the concurrency question read-only was chosen to avoid.
2. `build_warehouse.py` runs `DROP TABLE IF EXISTS` **per table**. A `users` table there would survive until the next data refresh and then vanish — a deployment losing every account on a routine load.

`PRODUCT-ARCHITECTURE` §2 states it directly: *"DuckDB is an embedded analytical database, not a shared transactional store."* Postgres would forfeit §2's "no external service dependencies" for three rows.

Column is `password_hash`, not `hashed_password` — the old name held `"adminpassword"`, and a name asserting a property the code lacks is what a reviewer skims past. argon2id with `check_needs_rehash` on login, lockout after 5 failures, and one outcome for "no such user" / "wrong password" / "locked" so accounts cannot be enumerated.

---

## 6. Roles — the mechanism landed; here is the list the policy needs

`RoleChecker` survived the rewrite and now reads the role from the store. **The policy did not land**, by ruling: who may see an individual salary is a product and legal decision per client under PDPL data minimisation, and this cycle has no real client.

What the next cycle starts from:

| Endpoint group | Why it needs a decision |
|---|---|
| **`/api/data/uploads/{id}/columns`** | **The sharpest entry.** Its entire purpose is returning the client's own raw values, and today any authenticated user reaches it — including `EXECUTIVE`, which has no business mapping a file. Created by my own mapping cycle |
| `/api/payroll/*` | 10 salary references; individual gross/net per employee |
| `/api/workforce/exceptions`, `/api/payroll/exceptions`, `/api/compliance/exceptions` | per-employee rows with `employee_id` and `employee_name` |
| `/api/compliance/*` | GOSI status, Iqama and work-permit expiry — regulatory identifiers |
| `/api/data/uploads/{id}` (preview) | violation messages quote the client's own offending values |
| `/api/data/uploads*`, `/api/data/mapping/*`, refresh | mutating; a case for admin-or-analyst rather than anyone |

---

## 7. Two defects in my own tests, recorded

Per SP-001, the point is that a check is watched failing. Two of mine passed for the wrong reason first:

1. **The plaintext check read only the main SQLite file.** WAL mode puts a just-inserted row in `<db>-wal`, so it found no plaintext because it found **no row at all**. It now asserts the argon2 hash *is* present before asserting the password is not — a check that cannot pass on an empty file.
2. **The "old secret appears nowhere" check flagged `security.py`'s own docstring**, which quotes the constant to explain what was replaced. Rewritten to walk the **AST**: a text scan cannot tell an assignment from prose quoting one. The same lesson as the dbt-ref detector two cycles ago, arrived at the same way — by the naive version being wrong first.

---

## 8. Verification

| Check | Result |
|---|---|
| Anonymous access to employee data | **closed** — 5 routes measured before and after |
| Forged token with the old committed secret | **401** |
| Fresh deployment bootstrap | admin created, no credential ever at rest |
| Demo | login works, 25 exceptions read, password hashed |
| Demo byte-identity | `19 / 446175.0 / 50.0 / 667 / 15`, dbt 161/161, 11/11, reconciliation PASSED |
| pytest | **404 passed** (358 + 46 new) |
| vitest | 94 passed |
| `tsc -b` / `npm run build` | 0 errors / passes |
| flake8 | CI blocking selection 0 |

---

## 9. Open

1. **Role policy** (§6) — mechanism only this cycle.
2. **Revocation is in-process.** A restart clears the list; short expiry is the actual control. Honest for one container per deployment, and it should not be mistaken for a distributed session store.
3. **A forgotten admin password is unrecoverable** except via the CLI on the box — no SMTP in this stack. Documented, not solved.
4. **No refresh token.** Expiry is 12 hours, which removes the mid-task logout the 30-minute setting caused, but a session still ends abruptly.
5. **argon2 memory cost** is the library default (64 MiB per verification). Not measured under concurrent login on a small container.
6. **`DataOnboarding` still has its own `ScopedLogin`** inside the app-level gate — now redundant, harmless, and worth removing next time that file is open.
7. TD-004 (rollback), GAP-001 (no gate reads text), the mapping sentinels and §1.4's residual all remain open, unchanged.

---

**Not merged. Awaiting review.**
