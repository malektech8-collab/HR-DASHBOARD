# -*- coding: utf-8 -*-
"""The demo figures and the dbt counts, asserted instead of quoted.

WHAT THIS REPLACES.

    Every cycle report this project has produced quotes a gate line:

        19 / 446175.0 / 50.0 / 667 / 15, dbt 158/158, 11/11, PASSED

    Measured in the org-dimensions cycle: NOTHING asserted any of it. The five
    demo figures were recomputed by hand each cycle and compared by eye. The
    dbt counts were read off stdout - a DELETED model reported 157/157 and was
    green. The pipeline going red on a broken model was real; the numbers were
    a habit that looked like a gate.

    So the last cycle's own byte-identity claim rested on a hand-run script.
    This is that claim, enforced.

WHY THE FIGURES ARE PINNED AS LITERALS.

    They are the demo's fingerprint. The point is that they CANNOT drift
    without someone deciding they should: changing one means editing this file,
    which is a reviewable act. A test that recomputed them from the same source
    the dashboard uses would agree with any drift and catch nothing - the
    tautology this project has now shipped twice.

WHEN THE DEMO LEGITIMATELY CHANGES, update the constants here in the same
commit that changes it, and say why in the message. That is the whole
mechanism, and it is deliberately annoying.

CI builds the warehouse (Run Data Ingestion & Build Analytical views) before
running pytest, so these run there. Locally they skip with a message rather
than failing someone who has not built one.
"""
import json
import os
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

# Overridable so the gate itself can be tamper-tested: a probe points this at
# a doctored copy and confirms each assertion goes red. A gate nobody has
# watched fail is the thing this whole cycle exists to stop shipping.
# SELF-SUFFICIENT AS OF THE TEST-ISOLATION CYCLE.
#
# This gate used to pass only because `test_data.py` sorts BEFORE
# `test_demo_gate.py` and rebuilt the warehouse in demo mode as a side effect.
# Nothing declared that dependency and nothing enforced it: -k filtering, a
# file rename, or parallelisation already broke it, and it broke silently
# because the guards below SKIPPED rather than failed.
#
# Measured against a real client load with that side effect absent:
#     SKIPPED [5] warehouse is anchored at 2026-08, not the demo's 2026-06
# Five pinned figures unasserted, and the gate reporting success.
#
# It now reads the isolated root that conftest.py builds, so it asserts the
# demo fingerprint because it BUILT the demo - not because of run order.
# HR_WAREHOUSE_PATH still wins, which is what the tamper probe points at a
# doctored copy.
WAREHOUSE = os.environ.get(
    "HR_WAREHOUSE_PATH",
    os.path.join(os.environ.get("HRDASH_DATA_ROOT", _ROOT),
                 "warehouse", "hr_analytics.duckdb"))
MANIFEST = os.path.join(_ROOT, "dbt_analytics", "target", "manifest.json")

# The demo's fingerprint. Six cycles of regressions have been caught by
# comparing against these by hand; from here the comparison is automatic.
ACTIVE_HEADCOUNT = 19
PAYROLL_COST = 446175.0
SAUDIZATION_PCT = 50.0
EXCEPTION_SOURCES = 667
DATA_QUALITY_ROWS = 15
REPORT_MONTH = "2026-06"

# dbt counts. 158 for the life of the project until the org-dimensions cycle
# added stg_locations, base_row_project and mart_unmatched_locations.
DBT_MODELS = 161
DBT_DATA_TESTS = 11


@pytest.fixture(scope="module")
def warehouse():
    """FAILS rather than skips. conftest builds this warehouse, so anything
    missing here is a broken build, not an environment the gate should excuse
    itself from. A skipped test is green, which is how this gate spent a cycle
    asserting nothing."""
    assert os.path.exists(WAREHOUSE), (
        "no warehouse at {} - conftest.py builds the isolated root before any "
        "test runs, so its absence is a build failure, not a reason to skip"
        .format(WAREHOUSE))
    conn = duckdb.connect(WAREHOUSE, read_only=True)
    built = conn.execute("SELECT COUNT(*) FROM information_schema.tables "
                         "WHERE table_name = 'mart_exec_kpis'").fetchone()[0]
    if not built:
        conn.close()
        raise AssertionError("warehouse present but dbt never built it")
    yield conn
    conn.close()


def _demo_only(conn):
    """The warehouse under test MUST be the demo one.

    This was two skips. Both were reachable only because the gate read whatever
    warehouse happened to be at the repo root - a client's, if one was loaded.
    It now reads the root conftest built, so a non-demo warehouse here means
    the isolation broke, and the gate must say so instead of standing down.
    """
    month = conn.execute("SELECT report_month FROM mart_exec_kpis").fetchone()[0]
    assert month == REPORT_MONTH, (
        "the isolated warehouse is anchored at {}, not the demo's {} - the "
        "gate is pointed at something that is not the demo build"
        .format(month, REPORT_MONTH))


def test_active_headcount(warehouse):
    _demo_only(warehouse)
    assert warehouse.execute(
        "SELECT active_headcount FROM mart_exec_kpis").fetchone()[0] \
        == ACTIVE_HEADCOUNT


def test_payroll_cost(warehouse):
    _demo_only(warehouse)
    assert warehouse.execute(
        "SELECT payroll_cost FROM mart_exec_kpis").fetchone()[0] \
        == pytest.approx(PAYROLL_COST, abs=0.01)


def test_saudization_pct(warehouse):
    _demo_only(warehouse)
    assert warehouse.execute(
        "SELECT saudization_pct FROM mart_saudization_summary "
        "WHERE period = ?", [REPORT_MONTH]).fetchone()[0] \
        == pytest.approx(SAUDIZATION_PCT, abs=0.001)


def test_exception_sources(warehouse):
    _demo_only(warehouse)
    assert warehouse.execute(
        "SELECT COUNT(*) FROM base_command_center_exception_sources"
    ).fetchone()[0] == EXCEPTION_SOURCES


def test_data_quality_rows(warehouse):
    _demo_only(warehouse)
    assert warehouse.execute(
        "SELECT COUNT(*) FROM data_quality").fetchone()[0] == DATA_QUALITY_ROWS


# --------------------------------------------------------------------------
# (c) the dbt counts stop being numbers read off stdout
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest():
    assert os.path.exists(MANIFEST), (
        "no dbt manifest at {} - conftest builds the isolated root, which runs "
        "dbt, so this is a build failure rather than a skip".format(MANIFEST))
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def _by_type(manifest, resource_type):
    return [k for k, v in manifest["nodes"].items()
            if v["resource_type"] == resource_type]


def test_the_dbt_model_count_is_what_we_say_it_is(manifest):
    """A DELETED model used to report 157/157 and stay green.

    dbt exits non-zero when a model FAILS, which is a real gate. It says
    nothing about a model that stopped existing.
    """
    models = _by_type(manifest, "model")
    assert len(models) == DBT_MODELS, sorted(
        m.split(".")[-1] for m in models)[:20]


def test_the_dbt_data_test_count_is_what_we_say_it_is(manifest):
    tests = _by_type(manifest, "test")
    assert len(tests) == DBT_DATA_TESTS, sorted(
        t.split(".")[-1] for t in tests)


def test_the_manifest_matches_the_files_on_disk(manifest):
    """Two independent counts of the same thing.

    The manifest is dbt's view; the filesystem is ours. If they disagree, a
    model exists that dbt is not building - which is exactly the state a count
    read off stdout cannot distinguish from a healthy one.
    """
    on_disk = set()
    for dirpath, _dirs, files in os.walk(
            os.path.join(_ROOT, "dbt_analytics", "models")):
        for name in files:
            if name.endswith(".sql"):
                on_disk.add(name[:-4])
    in_manifest = {k.split(".")[-1] for k in _by_type(manifest, "model")}
    assert on_disk == in_manifest, {
        "only on disk": sorted(on_disk - in_manifest),
        "only in manifest": sorted(in_manifest - on_disk),
    }
