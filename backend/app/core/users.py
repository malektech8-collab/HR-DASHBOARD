# -*- coding: utf-8 -*-
"""The user store. SQLite, per deployment, argon2id.

WHY NOT THE WAREHOUSE, which is the obvious place and the wrong one.

    Two verified facts settle it:

    1. The API opens DuckDB READ-ONLY (app/db/duckdb_client.py). A write path
       for user records would need a second, writable connection to the
       analytics database - reintroducing exactly the concurrency question
       read-only was chosen to avoid.

    2. scripts/build_warehouse.py runs `DROP TABLE IF EXISTS {table}` per
       table. A `users` table there would survive until the next data refresh
       and then vanish, taking every account with it. The failure mode is a
       deployment that loses all its logins on a routine load.

    PRODUCT-ARCHITECTURE §2 says it directly: "DuckDB is an embedded analytical
    database, not a shared transactional store." A user table is transactional.

WHY NOT POSTGRES. §2 names "no external service dependencies" as a genuine
    asset of this stack, and the per-client deployment story depends on it.
    Forfeiting that for three rows would be a bad trade.

SO: SQLite, stdlib, one file at data/auth/auth.db, alongside the other
    deployment state (data/onboarding/, data/staging/, data/mapping/) and
    gitignored with them. Single writer, which matches one backend container
    per deployment exactly.

THE COLUMN IS `password_hash`, NOT `hashed_password`. The old name held
    "adminpassword". A name that asserts a property the code does not have is
    worse than no name: it is what a reviewer skims past because it reads
    correctly. Same family as `tsc --noEmit` looking like a typecheck.
"""
import datetime
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import settings
from app.core.security import Role

SCHEMA_VERSION = 1

# argon2id at the library defaults, named here so they are a decision rather
# than an accident. `check_needs_rehash` on successful login means raising them
# later upgrades users transparently instead of requiring a reset.
_hasher = PasswordHasher()

_LOCK = threading.Lock()

# Failed logins before the account locks, and for how long. Three known email
# addresses and an open port is an inviting target, and the alternative -
# rate limiting - needs infrastructure this stack does not have.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class UserStoreError(RuntimeError):
    pass


def store_path() -> str:
    configured = os.getenv("AUTH_DB_PATH")
    if configured:
        return configured
    container = "/app/data/auth/auth.db"
    if os.path.isdir(os.path.dirname(os.path.dirname(container))):
        return container
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "auth", "auth.db"))


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")


def _connect() -> sqlite3.Connection:
    path = store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialise() -> None:
    """Create the schema if absent. Safe to call on every startup."""
    with _LOCK, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                  INTEGER PRIMARY KEY,
                email               TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash       TEXT NOT NULL,
                role                TEXT NOT NULL,
                is_active           INTEGER NOT NULL DEFAULT 1,
                created_at          TEXT NOT NULL,
                password_changed_at TEXT NOT NULL,
                failed_attempts     INTEGER NOT NULL DEFAULT 0,
                locked_until        TEXT
            )
        """)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS auth_schema_version (version INTEGER)")
        row = conn.execute(
            "SELECT version FROM auth_schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO auth_schema_version VALUES (?)",
                         (SCHEMA_VERSION,))


def count() -> int:
    with _connect() as conn:
        try:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        except sqlite3.OperationalError:
            return 0


def is_initialised() -> bool:
    """Whether this deployment has any account at all.

    A deployment with none is not 'unauthorised', it is UNINITIALISED - see
    app/api/dependencies/auth.py for why that distinction is a 503 and not a
    401.
    """
    return count() > 0


def _row_to_user(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "email": row["email"],
        "role": Role(row["role"]),
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "password_changed_at": row["password_changed_at"],
    }


def get(email: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email,)).fetchone()
    return _row_to_user(row) if row else None


def listing() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY email").fetchall()
    return [_row_to_user(r) for r in rows]


def create(email: str, password: str, role: Role) -> Dict[str, Any]:
    """Add a user. The plaintext is hashed here and never stored or logged."""
    email = (email or "").strip()
    if not email or "@" not in email:
        raise UserStoreError("A user needs an email address.")
    if len(password or "") < 12:
        raise UserStoreError(
            "Password must be at least 12 characters. This is the only "
            "credential guarding a client's employee records.")
    initialise()
    stamp = _now()
    try:
        with _LOCK, _connect() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, role, is_active, "
                "created_at, password_changed_at) VALUES (?, ?, ?, 1, ?, ?)",
                (email, _hasher.hash(password), role.value, stamp, stamp))
    except sqlite3.IntegrityError:
        raise UserStoreError("A user with that email already exists.")
    return {"email": email, "role": role, "is_active": True,
            "created_at": stamp, "password_changed_at": stamp}


def set_password(email: str, password: str) -> None:
    if len(password or "") < 12:
        raise UserStoreError("Password must be at least 12 characters.")
    with _LOCK, _connect() as conn:
        changed = conn.execute(
            "UPDATE users SET password_hash = ?, password_changed_at = ?, "
            "failed_attempts = 0, locked_until = NULL WHERE email = ?",
            (_hasher.hash(password), _now(), email)).rowcount
    if not changed:
        raise UserStoreError("No such user.")


def deactivate(email: str) -> None:
    with _LOCK, _connect() as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE email = ?", (email,))


def authenticate(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify a credential. Returns the user, or None for ANY failure.

    One return value for "no such user", "wrong password" and "locked": the
    caller must not be able to enumerate accounts. The argon2 verify is
    constant-time, unlike the `!=` this replaced.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email or "",)).fetchone()
    if row is None:
        # Hash anyway, so a missing account and a wrong password take
        # comparable time.
        _hasher.hash("absent-user-timing-equaliser")
        return None
    if not row["is_active"]:
        return None
    if row["locked_until"] and row["locked_until"] > _now():
        return None

    try:
        _hasher.verify(row["password_hash"], password or "")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        _record_failure(row)
        return None

    if _hasher.check_needs_rehash(row["password_hash"]):
        set_password(email, password)
    with _LOCK, _connect() as conn:
        conn.execute("UPDATE users SET failed_attempts = 0, "
                     "locked_until = NULL WHERE id = ?", (row["id"],))
    return _row_to_user(row)


def _record_failure(row: sqlite3.Row) -> None:
    attempts = row["failed_attempts"] + 1
    locked = None
    if attempts >= MAX_FAILED_ATTEMPTS:
        locked = (datetime.datetime.now(datetime.timezone.utc)
                  + datetime.timedelta(minutes=LOCKOUT_MINUTES)
                  ).isoformat(timespec="seconds")
        attempts = 0
    with _LOCK, _connect() as conn:
        conn.execute("UPDATE users SET failed_attempts = ?, locked_until = ? "
                     "WHERE id = ?", (attempts, locked, row["id"]))


# --------------------------------------------------------------------------
# demo seeding - demo mode ONLY, and the restriction is the point
# --------------------------------------------------------------------------

# The demo accounts. These passwords are in the repository on purpose: they are
# the demo's, they open synthetic data, and DEMO_RUNBOOK documents them. What
# makes that acceptable is not that they are weak-but-fine - it is that
# seed_demo_users() CANNOT RUN IN REAL MODE, which is enforced by a test that
# sets real mode and asserts no account appears.
DEMO_USERS = (
    ("admin@synthetic.local", "demo-admin-password", Role.SYSTEM_ADMIN),
    ("hr@synthetic.local", "demo-hr-password", Role.HR_ANALYST),
    ("exec@synthetic.local", "demo-exec-password", Role.EXECUTIVE),
)


def seed_demo_users() -> int:
    """Create the three demo accounts, hashed. Returns how many were created.

    Refuses in real mode. No account is EVER created implicitly on a real
    deployment - the operator creates the first one, and there is no default
    to forget about.
    """
    if settings.DATA_MODE == "real":
        return 0
    initialise()
    if is_initialised():
        return 0
    created = 0
    for email, password, role in DEMO_USERS:
        try:
            create(email, password, role)
            created += 1
        except UserStoreError:
            pass
    if created:
        print("[auth] demo mode: seeded {} demo accounts (hashed). "
              "This path is unreachable in real mode.".format(created))
    return created


def demo_credentials(role: Role = Role.SYSTEM_ADMIN):
    """The demo account for a role, for tests and the runbook.

    Tests used to read MOCK_USER_DB['x']['hashed_password'] to learn the
    password - an idiom that only works because the password was in plaintext,
    and which cannot survive hashing. This is the replacement.
    """
    if settings.DATA_MODE == "real":
        raise UserStoreError("There are no demo credentials in real mode.")
    for email, password, user_role in DEMO_USERS:
        if user_role == role:
            return email, password
    raise UserStoreError("No demo account for role {}".format(role))
