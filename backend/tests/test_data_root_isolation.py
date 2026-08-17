# -*- coding: utf-8 -*-
"""The MECHANISM half of GAP-003: paths resolve through the state root.

The GUARANTEE half - that a full suite run leaves operator state untouched -
cannot be asserted from inside the suite, because it is a statement about the
run these tests are part of. That lives in scripts/check_test_isolation.py and
runs as a CI job step beside pytest.

What IS assertable here: that every resolver consults HRDASH_DATA_ROOT, that
SOURCE deliberately does not follow it, and that a redirected write lands
inside the redirect and nowhere else.

Per SP-001 each assertion is paired with a tamper.
"""
import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import mapping        # noqa: E402
import onboarding     # noqa: E402
import paths          # noqa: E402
import staging        # noqa: E402


# --------------------------------------------------------------------------
# STATE follows the root
# --------------------------------------------------------------------------

@pytest.mark.parametrize("resolver", [
    lambda: onboarding.registry_path(),
    lambda: mapping.profile_dir(),
    lambda: staging.staging_root(),
    lambda: paths.silver(),
    lambda: paths.raw(),
    lambda: paths.gold(),
    lambda: paths.bronze(),
    lambda: paths.warehouse_path(),
])
def test_every_state_resolver_follows_the_root(resolver, monkeypatch, tmp_path):
    monkeypatch.setenv("HRDASH_DATA_ROOT", str(tmp_path))
    resolved = os.path.abspath(resolver())
    assert resolved.startswith(os.path.abspath(str(tmp_path))), resolved


def test_with_no_override_the_repo_layout_is_unchanged(monkeypatch):
    """The tamper, and the compatibility line. Unset, every path must resolve
    exactly where it did before this cycle - an operator who sets nothing sees
    no change at all."""
    monkeypatch.delenv("HRDASH_DATA_ROOT", raising=False)
    assert os.path.abspath(onboarding.registry_path()) == os.path.abspath(
        os.path.join(_ROOT, "data", "onboarding", "declared_domains.yml"))
    assert os.path.abspath(mapping.profile_dir()) == os.path.abspath(
        os.path.join(_ROOT, "data", "mapping"))
    assert os.path.abspath(paths.warehouse_path()) == os.path.abspath(
        os.path.join(_ROOT, "warehouse", "hr_analytics.duckdb"))


# --------------------------------------------------------------------------
# SOURCE does NOT follow the root
# --------------------------------------------------------------------------

def test_contracts_stay_in_the_repository(monkeypatch, tmp_path):
    """A test pointed at a temp root must still validate against the REAL
    contracts. Moving them would mean the suite checks a copy of its own
    fixtures instead of the thing that ships."""
    monkeypatch.setenv("HRDASH_DATA_ROOT", str(tmp_path))
    resolved = os.path.abspath(paths.contracts_dir())
    assert not resolved.startswith(os.path.abspath(str(tmp_path)))
    assert resolved.startswith(_ROOT)


# --------------------------------------------------------------------------
# a redirected WRITE lands inside the redirect
# --------------------------------------------------------------------------

def test_declaring_writes_into_the_redirect_only(monkeypatch, tmp_path):
    monkeypatch.setenv("HRDASH_DATA_ROOT", str(tmp_path))
    before = os.path.getmtime(
        os.path.join(_ROOT, "data", "onboarding", "declared_domains.yml")) \
        if os.path.exists(os.path.join(_ROOT, "data", "onboarding",
                                       "declared_domains.yml")) else None

    onboarding.declare("employees", declared_by="isolation-test@local",
                       history_since="2025-01-01")

    written = os.path.join(str(tmp_path), "data", "onboarding",
                           "declared_domains.yml")
    assert os.path.exists(written), "the declaration did not land in the root"

    repo_registry = os.path.join(_ROOT, "data", "onboarding",
                                 "declared_domains.yml")
    if before is not None:
        assert os.path.getmtime(repo_registry) == before, \
            "declaring under a redirect still touched the repository registry"


# --------------------------------------------------------------------------
# no module reaches around the resolver
# --------------------------------------------------------------------------

_STATE_LITERAL = re.compile(r'''["']data/(raw|bronze|silver|gold|sample|'''
                            r'''mapping|staging|onboarding)/''')

# paths.py defines the layout, so it is the one place these may appear.
_ALLOWED = {"paths.py"}


def test_no_script_hardcodes_a_state_path():
    """The enforcement a per-artefact fix could never have. An isolated
    artefact stays isolated because it is UNDER THE ROOT, not because someone
    remembered it - and this is what catches the next one that forgets."""
    offenders = []
    scripts_dir = os.path.join(_ROOT, "scripts")
    for name in sorted(os.listdir(scripts_dir)):
        if not name.endswith(".py") or name in _ALLOWED:
            continue
        with open(os.path.join(scripts_dir, name), encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if _STATE_LITERAL.search(line):
                    offenders.append("{}:{}: {}".format(
                        name, number, stripped[:70]))
    assert not offenders, (
        "state paths must resolve through scripts/paths.py:\n  "
        + "\n  ".join(offenders))


def test_that_rule_would_catch_a_regression():
    """The tamper. A pattern that matched nothing would pass the test above
    for the wrong reason."""
    assert _STATE_LITERAL.search('df.write_parquet("data/silver/x.parquet")')
    assert _STATE_LITERAL.search("open('data/onboarding/declared_domains.yml')")
    # And it must not fire on SOURCE, which legitimately stays in the repo.
    assert not _STATE_LITERAL.search('open("data/contracts/employees.yml")')
