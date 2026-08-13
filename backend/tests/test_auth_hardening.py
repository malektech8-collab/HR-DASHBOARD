# -*- coding: utf-8 -*-
"""The credential layer: secret, hashing, store, bootstrap.

SEVERITY ORDER, as ruled. The committed secret outranks the plaintext
passwords: `SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD` was identical in every
deployment, so forging a SYSTEM_ADMIN token needed repository access, not
server access, and the result worked at every customer install. Plaintext
passwords at least required reaching the machine.

Per SP-001, every check here is watched failing: each protection has a test
that tampers its input and asserts the refusal.
"""
import os
import sys

import jwt
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.config import settings  # noqa: E402
from app.core import bootstrap, security, users  # noqa: E402
from app.core.security import Role  # noqa: E402

OLD_COMMITTED_SECRET = "SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD"
STRONG = "x" * 64


@pytest.fixture
def store(tmp_path, monkeypatch):
    """An empty user store, isolated from the deployment's own."""
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.db"))
    security._reset_for_tests()
    bootstrap._reset_for_tests()
    users.initialise()
    yield
    security._reset_for_tests()
    bootstrap._reset_for_tests()


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setattr(settings, "DATA_MODE", "real")
    yield


# --------------------------------------------------------------------------
# (b) a token minted with the old committed secret is rejected
# --------------------------------------------------------------------------

def test_a_token_signed_with_the_old_committed_secret_is_REJECTED(store):
    """The proof the ruling asks for.

    Anyone with the repository could mint this. It must be worthless.
    """
    forged = jwt.encode(
        {"sub": "admin@synthetic.local", "iss": security.ISSUER,
         "aud": security.AUDIENCE, "exp": 9999999999, "iat": 1,
         "jti": "forged"},
        OLD_COMMITTED_SECRET, algorithm="HS256")
    assert security.decode_access_token(forged) is None


def test_the_old_secret_cannot_be_configured_in_real_mode(real_mode,
                                                          monkeypatch):
    """Restoring it - by copy/paste, a rolled-back file, an old runbook -
    must fail loudly rather than silently working."""
    monkeypatch.setattr(settings, "JWT_SECRET", OLD_COMMITTED_SECRET)
    with pytest.raises(security.SecretNotConfigured) as excinfo:
        security.get_secret()
    assert "placeholder" in str(excinfo.value)


def test_real_mode_refuses_to_run_without_a_secret(real_mode, monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", None)
    with pytest.raises(security.SecretNotConfigured) as excinfo:
        security.get_secret()
    assert "token_urlsafe" in str(excinfo.value), "say how to generate one"


def test_real_mode_refuses_a_short_secret(real_mode, monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "tooshort")
    with pytest.raises(security.SecretNotConfigured):
        security.get_secret()


def test_demo_generates_a_secret_per_process(monkeypatch):
    """Demo works with no setup, and its tokens do not survive a restart -
    so there is no demo secret that could become a production one."""
    monkeypatch.setattr(settings, "DATA_MODE", "demo")
    monkeypatch.setattr(settings, "JWT_SECRET", None)
    security._reset_for_tests()
    first = security.get_secret()
    assert len(first) >= security.MIN_SECRET_LENGTH
    assert first == security.get_secret(), "stable within a process"
    security._reset_for_tests()
    assert security.get_secret() != first, "and different after a restart"


def test_the_old_secret_survives_ONLY_as_a_denylist_entry():
    """Structural, and both halves matter.

    The string must not be ASSIGNED to anything - but it must still appear in
    FORBIDDEN_SECRETS, so restoring it fails loudly instead of silently
    working. A test that simply banned the string would delete its own guard,
    and would also flag the module docstring that explains what was replaced.

    Parsed, not grepped. A line-based scan cannot tell an assignment from prose
    quoting one, and security.py's docstring quotes the old constant verbatim
    on purpose. (The same mistake a text scan made of dbt refs last cycle.)
    """
    import ast

    offenders = []
    for dirpath, _dirs, files in os.walk(os.path.join(_ROOT, "backend", "app")):
        if "__pycache__" in dirpath:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = ([node.target] if isinstance(node, ast.AnnAssign)
                           else node.targets)
                names = {t.id for t in targets if isinstance(t, ast.Name)}
                if "FORBIDDEN_SECRETS" in names:
                    continue          # the denylist is the legitimate use
                for child in ast.walk(node):
                    if (isinstance(child, ast.Constant)
                            and child.value == OLD_COMMITTED_SECRET):
                        offenders.append("{}:{}".format(
                            os.path.relpath(path, _ROOT), child.lineno))
    assert not offenders, offenders
    assert OLD_COMMITTED_SECRET in security.FORBIDDEN_SECRETS,         "the guard against restoring it must itself survive"


def test_the_denylist_guard_would_catch_a_restored_constant():
    """The tamper for the test above (SP-001), without editing the module.

    Proves the AST walk finds an assignment - so the check above passing means
    there is none, rather than meaning the walk never looks.
    """
    import ast

    restored = 'SECRET_KEY = "{}"'.format(OLD_COMMITTED_SECRET)
    tree = ast.parse(restored)
    found = [c.lineno for node in ast.walk(tree)
             if isinstance(node, ast.Assign)
             for c in ast.walk(node)
             if isinstance(c, ast.Constant) and c.value == OLD_COMMITTED_SECRET]
    assert found == [1]


def test_MOCK_USER_DB_no_longer_exists():
    assert not hasattr(security, "MOCK_USER_DB")


# --------------------------------------------------------------------------
# token hygiene - iss / aud / jti, and the two RETAINED decisions
# --------------------------------------------------------------------------

def test_a_token_carries_issuer_audience_and_an_id(store):
    payload = security.decode_access_token(
        security.create_access_token({"sub": "a@b.c"}))
    assert payload["iss"] == security.ISSUER
    assert payload["aud"] == security.AUDIENCE
    assert payload["jti"] and payload["iat"]


def test_a_token_for_another_audience_is_rejected(store):
    other = jwt.encode(
        {"sub": "a@b.c", "iss": security.ISSUER, "aud": "someone-elses-api",
         "exp": 9999999999, "iat": 1},
        security.get_secret(), algorithm="HS256")
    assert security.decode_access_token(other) is None


def test_RETAINED_the_role_is_not_in_the_token(store):
    """Deliberately kept, and stated so a later rewrite does not lose it.

    Only `sub` identifies the user. The role is read from the store on every
    request, so deactivation takes effect on the NEXT REQUEST rather than the
    next login. Rewrites lose this constantly to save a lookup.
    """
    payload = security.decode_access_token(
        security.create_access_token({"sub": "a@b.c"}))
    assert "role" not in payload


def test_RETAINED_the_algorithm_list_is_pinned():
    """The defence against `alg: none` and RS->HS confusion.

    It must never become a list read from configuration.
    """
    source = open(os.path.join(_ROOT, "backend", "app", "core", "security.py"),
                  encoding="utf-8").read()
    assert "algorithms=[ALGORITHM]" in source


def test_an_unsigned_token_is_rejected(store):
    unsigned = jwt.encode({"sub": "a@b.c"}, key="", algorithm="none")
    assert security.decode_access_token(unsigned) is None


def test_logout_revokes_that_token(store):
    token = security.create_access_token({"sub": "a@b.c"})
    assert security.decode_access_token(token) is not None
    assert security.revoke(token) is True
    assert security.decode_access_token(token) is None, "there was no logout"


# --------------------------------------------------------------------------
# hashing and the store
# --------------------------------------------------------------------------

def _store_bytes() -> bytes:
    """Everything SQLite has written, including the write-ahead log.

    WAL mode means a just-inserted row lives in `<db>-wal`, not the main file.
    Reading only the main file made an earlier version of this test pass for
    the wrong reason - it found no plaintext because it found no row at all.
    """
    path = os.environ["AUTH_DB_PATH"]
    blob = b""
    for candidate in (path, path + "-wal", path + "-journal"):
        if os.path.exists(candidate):
            with open(candidate, "rb") as handle:
                blob += handle.read()
    return blob


def test_a_password_is_never_stored_in_plaintext(store):
    users.create("a@b.c", "correct-horse-battery", Role.HR_ANALYST)
    blob = _store_bytes()
    assert b"$argon2" in blob, "the hash must actually be there"
    assert b"correct-horse-battery" not in blob


def test_authentication_accepts_the_right_password(store):
    users.create("a@b.c", "correct-horse-battery", Role.HR_ANALYST)
    user = users.authenticate("a@b.c", "correct-horse-battery")
    assert user and user["role"] == Role.HR_ANALYST


@pytest.mark.parametrize("password", ["wrong", "", "correct-horse-batter"])
def test_authentication_rejects_a_wrong_password(store, password):
    users.create("a@b.c", "correct-horse-battery", Role.HR_ANALYST)
    assert users.authenticate("a@b.c", password) is None


def test_an_unknown_user_and_a_wrong_password_look_the_same(store):
    """No account enumeration: one outcome for both."""
    users.create("a@b.c", "correct-horse-battery", Role.HR_ANALYST)
    assert users.authenticate("nobody@b.c", "anything") is None
    assert users.authenticate("a@b.c", "anything") is None


def test_a_deactivated_user_cannot_authenticate(store):
    users.create("a@b.c", "correct-horse-battery", Role.HR_ANALYST)
    users.deactivate("a@b.c")
    assert users.authenticate("a@b.c", "correct-horse-battery") is None


def test_the_account_locks_after_repeated_failures(store):
    users.create("a@b.c", "correct-horse-battery", Role.HR_ANALYST)
    for _ in range(users.MAX_FAILED_ATTEMPTS):
        users.authenticate("a@b.c", "wrong")
    assert users.authenticate("a@b.c", "correct-horse-battery") is None, \
        "the right password must not open a locked account"


def test_a_short_password_is_refused(store):
    with pytest.raises(users.UserStoreError):
        users.create("a@b.c", "short", Role.HR_ANALYST)


def test_the_column_is_named_for_what_it_holds():
    """`hashed_password` held "adminpassword". A name that asserts a property
    the code does not have is what a reviewer skims past."""
    source = open(os.path.join(_ROOT, "backend", "app", "core", "users.py"),
                  encoding="utf-8").read()
    assert "password_hash" in source
    assert "hashed_password TEXT" not in source


# --------------------------------------------------------------------------
# (c) bootstrap - no hardcoded credential ever exists
# --------------------------------------------------------------------------

def test_a_fresh_deployment_has_no_users(store, real_mode):
    assert users.count() == 0
    assert users.seed_demo_users() == 0, "real mode must never seed"


def test_the_bootstrap_token_creates_the_first_admin(store, real_mode):
    token = bootstrap.issue_if_needed()
    assert token and len(token) > 40
    assert bootstrap.consume(token) is True
    users.create("first@client.example", "a-real-password-1", Role.SYSTEM_ADMIN)
    assert users.count() == 1


def test_the_bootstrap_token_is_single_use(store, real_mode):
    token = bootstrap.issue_if_needed()
    assert bootstrap.consume(token) is True
    assert bootstrap.consume(token) is False


def test_no_bootstrap_token_is_issued_once_a_user_exists(store, real_mode):
    users.create("first@client.example", "a-real-password-1", Role.SYSTEM_ADMIN)
    assert bootstrap.issue_if_needed() is None


def test_a_wrong_bootstrap_token_is_rejected(store, real_mode):
    bootstrap.issue_if_needed()
    assert bootstrap.consume("not-the-token") is False


def test_the_bootstrap_token_is_not_written_to_disk(store, real_mode, tmp_path):
    token = bootstrap.issue_if_needed()
    for dirpath, _dirs, files in os.walk(str(tmp_path)):
        for name in files:
            with open(os.path.join(dirpath, name), "rb") as handle:
                assert token.encode() not in handle.read(), name


# --------------------------------------------------------------------------
# (d) demo still works, and the demo path cannot reach real mode
# --------------------------------------------------------------------------

def test_demo_seeds_three_accounts_hashed(store, monkeypatch):
    monkeypatch.setattr(settings, "DATA_MODE", "demo")
    assert users.seed_demo_users() == 3
    email, password = users.demo_credentials(Role.SYSTEM_ADMIN)
    assert users.authenticate(email, password)
    assert password.encode() not in _store_bytes(), "hashed, not stored"


def test_demo_seeding_is_UNREACHABLE_in_real_mode(store, real_mode):
    """The property that makes demo passwords in the repository acceptable.

    Not "they are weak but fine" - they cannot exist on a real deployment.
    Tampered rather than asserted: set real mode, seed, assert nothing.
    """
    assert users.seed_demo_users() == 0
    assert users.count() == 0
    with pytest.raises(users.UserStoreError):
        users.demo_credentials()


def test_demo_seeding_is_idempotent(store, monkeypatch):
    monkeypatch.setattr(settings, "DATA_MODE", "demo")
    assert users.seed_demo_users() == 3
    assert users.seed_demo_users() == 0
