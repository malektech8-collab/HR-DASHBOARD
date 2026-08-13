# -*- coding: utf-8 -*-
"""Two defects an operator meets before any client data is involved.

Both were found by executing the first-real-load runbook rather than writing
it, and both are the same shape: the system failed closed, and failed unhelpfully.

Per SP-001 each fix is paired with a test that demonstrates the FAILURE MODE -
not just that the fix works, but that the thing it prevents is real.
"""
import os
import shutil
import sys
import tempfile

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.config import Settings, settings  # noqa: E402
from app.core import security, users  # noqa: E402
from app.core.security import Role  # noqa: E402

NL = chr(10)
ENV_EXAMPLE = os.path.join(_ROOT, ".env.example")
FRONTEND_ENV_EXAMPLE = os.path.join(_ROOT, "frontend", ".env.example")


# --------------------------------------------------------------------------
# FIX 1 - the documented setup path must work
# --------------------------------------------------------------------------

def test_copying_the_committed_env_example_lets_the_backend_start(tmp_path):
    """THE DOCUMENTED ACTION, end to end.

    `Copy-Item .env.example .env` then start the backend. Before this fix that
    raised at import:

        ValidationError: 1 validation error for Settings
        vite_api_url  Extra inputs are not permitted

    VITE_API_URL is a FRONTEND variable, and Vite never read it here - it reads
    frontend/.env, because vite.config.ts sets no envDir. Its only observable
    effect was to stop the backend starting.
    """
    env = tmp_path / ".env"
    shutil.copy2(ENV_EXAMPLE, str(env))
    loaded = Settings(_env_file=str(env))
    assert loaded.DATA_MODE in ("demo", "real")


def test_the_backend_env_example_declares_no_frontend_variables():
    """The root .env.example is consumed by pydantic-settings. Every variable
    in it must be one the Settings model declares, or the documented copy
    breaks again the moment someone adds another."""
    import re

    declared = set(Settings.model_fields)
    offenders = []
    with open(ENV_EXAMPLE, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            match = re.match(r"^([A-Z][A-Z0-9_]*)=", line.strip())
            if match and match.group(1) not in declared:
                offenders.append("{}:{}".format(number, match.group(1)))
    assert not offenders, (
        "these are not declared on Settings, so copying .env.example to .env "
        "will raise at import: " + ", ".join(offenders))


def test_the_frontend_variable_lives_where_vite_reads_it():
    assert os.path.exists(FRONTEND_ENV_EXAMPLE), \
        "frontend/.env.example must exist - it is where VITE_API_URL belongs"
    with open(FRONTEND_ENV_EXAMPLE, encoding="utf-8") as handle:
        assert "VITE_API_URL" in handle.read()


def test_vite_still_has_no_envDir_override():
    """The premise of the fix, pinned.

    Moving VITE_API_URL to frontend/.env.example is correct only while Vite's
    envDir is the frontend directory. If someone sets `envDir: '..'` in
    vite.config.ts, the variable belongs back at the root - and the backend
    breaks again unless this is revisited together.
    """
    config = os.path.join(_ROOT, "frontend", "vite.config.ts")
    with open(config, encoding="utf-8") as handle:
        assert "envDir" not in handle.read()


def test_a_misplaced_variable_is_still_REFUSED(tmp_path):
    """What the strictness actually buys, and the reason the fix was not
    simply `extra = "ignore"`.

    A variable that belongs to another component - which is precisely what
    VITE_API_URL was - is refused rather than silently carried.
    """
    env = tmp_path / ".env"
    env.write_text("DATA_MODE=demo" + NL + "SOME_OTHER_TOOLS_SETTING=1" + NL,
                   encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        Settings(_env_file=str(env))
    assert "some_other_tools_setting" in str(excinfo.value).lower()


@pytest.mark.parametrize("typo,field", [
    ("DATA_MODEE=real", "DATA_MODE"),
    ("JWT_SECRETT=abc", "JWT_SECRET"),
])
def test_forbid_does_NOT_catch_a_typo_that_prefixes_a_real_field(
        tmp_path, typo, field):
    """A MEASURED LIMITATION, pinned so nobody trusts this for more.

    pydantic-settings matches an env name that starts with a field name
    against that field and discards the remainder, so these are accepted and
    ignored rather than refused. `extra = "forbid"` protects against MISPLACED
    variables, not MISSPELLED ones.

    I asserted the opposite while writing this fix, and it was wrong. What
    catches the second kind is real mode's own fail-closed check: an unset
    JWT_SECRET refuses to start, so a typo'd one is still caught - by a
    different mechanism, with a different message.
    """
    env = tmp_path / ".env"
    env.write_text("DATA_MODE=demo" + NL + typo + NL, encoding="utf-8")
    loaded = Settings(_env_file=str(env))          # no exception
    assert loaded.DATA_MODE == "demo", (
        "the typo is discarded, so the real field keeps its own value")


# --------------------------------------------------------------------------
# FIX 2 - a correct credential against a misconfigured deployment
# --------------------------------------------------------------------------

@pytest.fixture
def misconfigured_real_deployment(monkeypatch):
    """Real mode, a real user, and no JWT_SECRET."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("AUTH_DB_PATH", os.path.join(tmp, "auth.db"))
    security._reset_for_tests()
    monkeypatch.setattr(settings, "DATA_MODE", "demo")
    users.initialise()
    users.create("op@client.example", "a-strong-operator-password",
                 Role.SYSTEM_ADMIN)
    monkeypatch.setattr(settings, "DATA_MODE", "real")
    monkeypatch.setattr(settings, "JWT_SECRET", None)
    security._reset_for_tests()
    yield
    security._reset_for_tests()
    shutil.rmtree(tmp, ignore_errors=True)


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_login_with_a_correct_credential_says_what_is_missing(
        misconfigured_real_deployment):
    """THE FAILURE MODE: this returned a bare `500 Internal Server Error`.

    `create_access_token` raised SecretNotConfigured uncaught. The operator had
    typed the right password, and got the least informative response in the
    system at the one moment the most informative one existed - the data routes
    were already answering 503 with the variable name and the command to
    generate a value.
    """
    response = _client().post(
        "/api/governance/token",
        data={"username": "op@client.example",
              "password": "a-strong-operator-password"})

    assert response.status_code == 503, "not 500, and not 401"
    detail = response.json()["detail"]
    assert "JWT_SECRET" in detail
    assert "token_urlsafe" in detail, "say how to generate one"


def test_it_is_not_reported_as_a_credential_problem(
        misconfigured_real_deployment):
    """401 would send the operator to check the password they typed correctly.

    The deployment is misconfigured; that is not the caller's fault and must
    not be described as one.
    """
    response = _client().post(
        "/api/governance/token",
        data={"username": "op@client.example",
              "password": "a-strong-operator-password"})
    assert response.status_code != 401


def test_a_WRONG_credential_is_still_401_not_503(
        misconfigured_real_deployment):
    """The fix must not turn every failed login into "misconfigured".

    A wrong password is refused before the secret is ever needed, so it stays a
    401 - otherwise a misconfigured deployment would silently stop reporting
    bad credentials at all.
    """
    response = _client().post(
        "/api/governance/token",
        data={"username": "op@client.example", "password": "wrong"})
    assert response.status_code == 401


def test_the_data_routes_already_answered_this_way(
        misconfigured_real_deployment):
    """The behaviour login was inconsistent with, pinned so it stays the pair."""
    response = _client().get("/api/workforce/summary",
                             headers={"Authorization": "Bearer anything"})
    assert response.status_code == 503
    assert "JWT_SECRET" in response.json()["detail"]
