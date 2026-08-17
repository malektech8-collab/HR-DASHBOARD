"""Phase 2 P0 steps 1-2: the declared-domain registry and the guard.

All four guard states from the plan §0.2 are covered, because the two abort
arms are the whole reason the mechanism exists — without them, scoping would
rest on inference and a broken ingest would look identical to a domain that
simply has not been uploaded.

Synthetic only. Nothing here touches data/sample, data/raw, or client data.
"""
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402
import onboarding as onb  # noqa: E402

CONTRACTED = None  # resolved per-test against the real contracts directory


@pytest.fixture(autouse=True)
def _at_root(monkeypatch):
    monkeypatch.chdir(_ROOT)
    global CONTRACTED
    CONTRACTED = set(cs.available_tables())


def _registry(tmp_path, monkeypatch, body):
    root = tmp_path / "root"
    p = root / "data" / "onboarding" / "declared_domains.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    # Redirect the STATE ROOT rather than patching a private constant.
    # registry_path() resolves through scripts/paths.py now, so this
    # exercises the mechanism that actually ships instead of a bypass.
    monkeypatch.setenv("HRDASH_DATA_ROOT", str(root))
    return p


# --------------------------------------------------------------------------
# the four guard states (§0.2)
# --------------------------------------------------------------------------

def test_state_1_declared_and_populated_is_fine():
    assert onb.assert_declared_matches_populated(
        {"employees": 1420, "payroll": 1418}, declared={"employees", "payroll"})


def test_state_2_declared_but_empty_aborts():
    """The masking case. A declared domain with no rows is a load failure, not
    an absence — the signal that must never be scoped away."""
    with pytest.raises(onb.OnboardingError) as exc:
        onb.assert_declared_matches_populated(
            {"employees": 1420, "payroll": 0}, declared={"employees", "payroll"})
    msg = str(exc.value)
    assert "declared but EMPTY" in msg
    assert "payroll" in msg
    assert "load failure" in msg


def test_state_3_undeclared_and_empty_is_fine():
    assert onb.assert_declared_matches_populated(
        {"employees": 1420, "payroll": 0}, declared={"employees"})


def test_state_4_undeclared_but_populated_aborts():
    """A stale registry, or data reaching a table by an unintended path."""
    with pytest.raises(onb.OnboardingError) as exc:
        onb.assert_declared_matches_populated(
            {"employees": 1420, "payroll": 55}, declared={"employees"})
    msg = str(exc.value)
    assert "populated but NOT declared" in msg
    assert "payroll" in msg


def test_both_arms_reported_together():
    """One run should surface every problem, not the first one."""
    with pytest.raises(onb.OnboardingError) as exc:
        onb.assert_declared_matches_populated(
            {"employees": 0, "payroll": 55}, declared={"employees"})
    msg = str(exc.value)
    assert "declared but EMPTY" in msg and "populated but NOT declared" in msg


# --------------------------------------------------------------------------
# registry loading
# --------------------------------------------------------------------------

def test_absent_registry_declares_nothing(tmp_path, monkeypatch):
    # An empty root: the registry file simply is not there.
    monkeypatch.setenv("HRDASH_DATA_ROOT", str(tmp_path / "empty"))
    assert onb.load_declared() == set()


def test_registry_round_trips(tmp_path, monkeypatch):
    _registry(tmp_path, monkeypatch,
              "version: 1\ndeclared:\n  - employees\n  - payroll\n")
    assert onb.load_declared() == {"employees", "payroll"}


def test_unknown_domain_is_a_hard_error(tmp_path, monkeypatch):
    """A typo must not silently declare nothing — that reintroduces the exact
    ambiguity the registry removes."""
    _registry(tmp_path, monkeypatch, "declared:\n  - employees\n  - payrol\n")
    with pytest.raises(onb.OnboardingError) as exc:
        onb.load_declared()
    assert "payrol" in str(exc.value) and "no contract" in str(exc.value)


def test_declare_adds_and_is_idempotent(tmp_path, monkeypatch):
    _registry(tmp_path, monkeypatch, "version: 1\ndeclared: []\n")
    assert onb.declare("employees", declared_by="op@client") == {"employees"}
    assert onb.declare("employees") == {"employees"}
    assert onb.declare("payroll") == {"employees", "payroll"}
    assert onb.load_declared() == {"employees", "payroll"}


def test_declare_rejects_an_uncontracted_domain(tmp_path, monkeypatch):
    _registry(tmp_path, monkeypatch, "declared: []\n")
    with pytest.raises(onb.OnboardingError):
        onb.declare("recruitment_requisitions")


# --------------------------------------------------------------------------
# empty tables for undeclared domains
# --------------------------------------------------------------------------

def test_empty_table_is_typed_and_zero_row(tmp_path):
    import polars as pl
    path = onb.write_empty_table("payroll", silver_dir=str(tmp_path))
    df = pl.read_parquet(path)
    assert df.height == 0
    assert list(df.columns) == cs.column_names("payroll")
    assert df.schema["basic_salary"] == pl.Float64
    assert df.schema["payroll_period"] == pl.Utf8


def test_empty_table_overwrites_previous_rows(tmp_path):
    """A previous run's rows must never survive as this client's data."""
    import polars as pl
    p = tmp_path / "payroll.parquet"
    pl.DataFrame({"payroll_period": ["2026-06"]}).write_parquet(str(p))
    assert pl.read_parquet(str(p)).height == 1
    onb.write_empty_table("payroll", silver_dir=str(tmp_path))
    assert pl.read_parquet(str(p)).height == 0


# --------------------------------------------------------------------------
# the undeclared sentinel is an invariant, not a convention
# --------------------------------------------------------------------------

def test_undeclared_sentinel_directory_must_not_exist():
    """Control flow carried by a filesystem convention is the .uploaded pattern.

    Undeclared domains are skipped because their `files` entry points at a
    directory that cannot exist. If that directory were ever created, every
    undeclared domain would silently ingest whatever it contained — the same
    class of failure as the .uploaded marker that froze employees ingest and
    zeroed four Attendance widgets.
    """
    import ingest_raw
    assert not os.path.exists(ingest_raw.UNDECLARED_SENTINEL_DIR), (
        "{} exists on disk. Undeclared domains would ingest from it instead of "
        "being skipped.".format(ingest_raw.UNDECLARED_SENTINEL_DIR))


def test_undeclared_sentinel_is_a_named_constant():
    """Not an inline literal, so it cannot drift between the two use sites."""
    import ingest_raw
    # Resolved through the state root now, so assert the SHAPE rather than a
    # literal - the point of the constant is that it has one definition, and
    # that is what still needs pinning.
    assert ingest_raw.UNDECLARED_SENTINEL_DIR.replace("\\", "/").endswith(
        "data/raw/__undeclared__")
    src = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
               encoding="utf-8").read()
    assert src.count('_p.raw("__undeclared__")') == 1,         "the sentinel path should appear once, as the constant definition"
