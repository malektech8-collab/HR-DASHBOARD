"""P0-3 steps 1 and 2a: the metric provenance registry must stay complete.

No suppression behaviour exists yet — these cycles are the registry and the
tests that keep it correct. Coverage is the load-bearing one: under
default-deny an unmapped mart is suppressed, so a mart added without an entry
becomes invisible rather than fabricated. That is the safe failure direction,
but it is still a failure, and CI should say so when the mart is added rather
than when someone notices a blank dashboard.
"""
import io
import os
import re
import sys

import pytest
import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

PROVENANCE_PATH = os.path.join(_ROOT, "config", "metric_provenance.yml")
DICTIONARY_PATH = os.path.join(_ROOT, "config", "metrics_dictionary.yml")
WAREHOUSE = os.path.join(_ROOT, "warehouse", "hr_analytics.duckdb")
NEWLINE = chr(10)

API_REF = re.compile(r"FROM\s+(mart_[a-z0-9_]+|base_[a-z0-9_]+)")
API_DIRS = [
    os.path.join(_ROOT, "backend", "app", "api"),
    os.path.join(_ROOT, "backend", "app", "api", "endpoints"),
]

# Referenced by a router but absent from the warehouse. A pre-existing defect,
# not a provenance gap — see test_api_references_that_do_not_exist.
KNOWN_MISSING_FROM_WAREHOUSE = {"mart_wps_status"}


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@pytest.fixture(scope="module")
def registry():
    return _load(PROVENANCE_PATH)


@pytest.fixture(scope="module")
def known_domains(registry):
    d = registry["domains"]
    return set(d["contracted"]) | set(d["uncontracted"])


def _entry_domains(entry):
    if isinstance(entry, dict):
        return list(entry.get("domains") or [])
    return list(entry or [])


def _all_column_entries(registry):
    for mart, spec in registry["marts"].items():
        if spec.get("mode") != "column":
            continue
        for col, entry in (spec.get("columns") or {}).items():
            yield mart, col, entry


def _api_served_objects():
    """Every mart/base object the API queries, read from the router source.

    The API is the surface that must never emit a fabricated number, so it —
    not a naming convention — defines what the registry has to cover.
    """
    found = set()
    for d in API_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.endswith(".py"):
                text = io.open(os.path.join(d, fn), encoding="utf-8").read()
                found |= set(API_REF.findall(text))
    return found


def _warehouse_objects():
    import duckdb
    conn = duckdb.connect(WAREHOUSE, read_only=True)
    try:
        views = {r[0] for r in conn.execute(
            "SELECT view_name FROM duckdb_views()").fetchall()}
        tables = {r[0] for r in conn.execute(
            "SELECT table_name FROM duckdb_tables()").fetchall()}
        return views | tables
    finally:
        conn.close()


def _columns_of(name):
    import duckdb
    conn = duckdb.connect(WAREHOUSE, read_only=True)
    try:
        cur = conn.execute("SELECT * FROM {} LIMIT 0".format(name))
        return [d[0] for d in cur.description]
    finally:
        conn.close()


requires_warehouse = pytest.mark.skipif(
    not os.path.exists(WAREHOUSE),
    reason="warehouse not built; run scripts/refresh_all.py",
)


# --------------------------------------------------------------------------
# coverage — the default-deny guarantee
# --------------------------------------------------------------------------

def test_every_api_served_mart_is_mapped(registry):
    """Fails when the API queries a mart with no provenance entry."""
    served = _api_served_objects() - KNOWN_MISSING_FROM_WAREHOUSE
    marts = registry["marts"]
    modes = {m: spec["mode"] for m, spec in marts.items()}
    n_col = sum(1 for v in modes.values() if v == "column")
    n_pay = sum(1 for v in modes.values() if v == "payload")
    n_cols = sum(len(spec.get("columns") or {})
                 for spec in marts.values() if spec["mode"] == "column")
    n_empty = sum(1 for _m, _c, e in _all_column_entries(registry)
                  if not _entry_domains(e))
    n_empty += sum(1 for spec in marts.values()
                   if spec["mode"] == "payload" and not (spec.get("domains") or []))
    print(NEWLINE + "[provenance] {} API-served marts mapped "
          "({} column / {} payload), {} columns, {} source-free"
          .format(len(marts), n_col, n_pay, n_cols, n_empty))

    missing = sorted(served - set(marts))
    assert not missing, (
        "API-served mart(s) with no provenance entry — add them to "
        "config/metric_provenance.yml:" + NEWLINE + "  "
        + (NEWLINE + "  ").join(missing))


def test_registry_has_no_entries_for_marts_the_api_does_not_serve(registry):
    served = _api_served_objects()
    stale = sorted(set(registry["marts"]) - served)
    assert not stale, (
        "provenance entries for marts the API does not query:" + NEWLINE + "  "
        + (NEWLINE + "  ").join(stale))


@requires_warehouse
def test_column_mode_marts_map_every_column(registry):
    missing = []
    for mart, spec in registry["marts"].items():
        if spec.get("mode") != "column":
            continue
        for col in _columns_of(mart):
            if col not in (spec.get("columns") or {}):
                missing.append("{}.{}".format(mart, col))
    assert not missing, (
        "column-mode mart(s) with unmapped column(s):" + NEWLINE + "  "
        + (NEWLINE + "  ").join(missing))


@requires_warehouse
def test_api_references_that_do_not_exist():
    """A router querying a non-existent object is a guaranteed 500.

    mart_wps_status is referenced by GET /api/compliance/wps and does not
    exist in the warehouse — a pre-existing defect surfaced by this audit, not
    introduced by it. Pinned so the list cannot grow unnoticed.
    """
    absent = sorted(_api_served_objects() - _warehouse_objects())
    assert set(absent) == KNOWN_MISSING_FROM_WAREHOUSE, (
        "API references to objects absent from the warehouse changed: {}"
        .format(absent))


# --------------------------------------------------------------------------
# mode
# --------------------------------------------------------------------------

def test_every_mart_declares_a_valid_mode(registry):
    bad = [m for m, spec in registry["marts"].items()
           if spec.get("mode") not in ("column", "payload")]
    assert not bad, "mart(s) with a missing or invalid mode: {}".format(bad)


def test_mode_shape_matches_mode(registry):
    """column marts carry `columns`; payload marts carry `domains`. Mixing the
    two would make suppression ambiguous."""
    wrong = []
    for m, spec in registry["marts"].items():
        if spec["mode"] == "column":
            if not spec.get("columns") or "domains" in spec:
                wrong.append("{}: column mode needs `columns` and no top-level "
                             "`domains`".format(m))
        else:
            if "columns" in spec or "domains" not in spec:
                wrong.append("{}: payload mode needs `domains` and no "
                             "`columns`".format(m))
    assert not wrong, NEWLINE + "  " + (NEWLINE + "  ").join(wrong)


def test_column_mode_is_reserved_for_mixed_provenance(registry):
    """`mode: column` exists to express a single row whose columns have
    different provenance. If every column shared one domain set the mart
    should be payload, or the distinction stops meaning anything."""
    uniform = []
    for m, spec in registry["marts"].items():
        if spec["mode"] != "column":
            continue
        sets = {tuple(sorted(_entry_domains(e)))
                for e in (spec.get("columns") or {}).values()}
        if len(sets) == 1:
            uniform.append(m)
    assert not uniform, (
        "column-mode mart(s) with uniform provenance — these should be "
        "payload: {}".format(uniform))


def test_every_referenced_domain_is_declared(registry, known_domains):
    unknown = []
    for mart, spec in registry["marts"].items():
        entries = (list((spec.get("columns") or {}).items())
                   if spec["mode"] == "column"
                   else [("<payload>", spec.get("domains"))])
        for col, entry in entries:
            for d in _entry_domains(entry):
                if d not in known_domains:
                    unknown.append("{}.{} -> {}".format(mart, col, d))
    assert not unknown, (
        "reference(s) to an undeclared domain:" + NEWLINE + "  "
        + (NEWLINE + "  ").join(unknown))


# --------------------------------------------------------------------------
# source-free entries stay small and justified
# --------------------------------------------------------------------------

def test_empty_domain_lists_carry_a_reason():
    """Under default-deny, `[]` is the only way to silence a coverage failure
    without reviewing the mart. Every one must say why, on the same line.

    Read as raw text, because YAML parsing discards comments.
    """
    lines = io.open(PROVENANCE_PATH, encoding="utf-8").read().splitlines()
    uncommented = []
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith("#") and ": []" in stripped:
            if "#" not in line.split(": []", 1)[1]:
                uncommented.append("line {}: {}".format(n, stripped))
    assert not uncommented, (
        "every `[]` entry must state why it has no source domain:"
        + NEWLINE + "  " + (NEWLINE + "  ").join(uncommented))


def test_source_free_entries_are_pinned(registry):
    empties = ["{}.{}".format(m, c) for m, c, e in _all_column_entries(registry)
               if not _entry_domains(e)]
    empties += ["{} (payload)".format(m) for m, spec in registry["marts"].items()
                if spec["mode"] == "payload" and not (spec.get("domains") or [])]
    print(NEWLINE + "[provenance] source-free entries: {} -> {}"
          .format(len(empties), sorted(empties)))
    assert set(empties) == {
        "mart_exec_kpis.report_month",
        "mart_command_center_overview.modules_healthy",
        "mart_command_center_overview.last_data_refresh",
        "mart_command_center_overview.latest_source_business_date",
        "base_command_center_report_context (payload)",
    }, ("the set of source-free entries changed: {}. Each bypasses "
        "suppression, so additions need review.".format(sorted(empties)))


def test_scope_to_provided_is_limited_to_the_ruled_metrics(registry):
    """Ruling 1's exception must not spread without a decision.

    mart_data_quality_exceptions was added by the same reasoning in step 2a:
    it describes the upload rather than the business, so suppressing it would
    hide the exceptions a client most needs during onboarding.
    """
    scoped = ["{}.{}".format(m, c) for m, c, e in _all_column_entries(registry)
              if isinstance(e, dict) and e.get("scope_to_provided")]
    scoped += ["{} (payload)".format(m) for m, spec in registry["marts"].items()
               if spec["mode"] == "payload" and spec.get("scope_to_provided")]
    assert set(scoped) == {
        "mart_data_quality_exceptions (payload)",
        "mart_exec_kpis.data_quality_score",
        "mart_data_quality_summary.data_quality_score",
        "mart_command_center_overview.data_quality_score",
        "mart_command_center_overview.total_active_exceptions",
    }, "scope_to_provided changed: {}".format(sorted(scoped))


# --------------------------------------------------------------------------
# consistency with metrics_dictionary.yml (step-1 ruling 2)
# --------------------------------------------------------------------------

def test_names_shared_with_metrics_dictionary_are_consistent(registry):
    """Different key spaces — metrics_dictionary.yml is keyed by global
    business metric name for a curated subset, this by mart -> column. Where a
    name appears in both, provenance must have one home."""
    if not os.path.exists(DICTIONARY_PATH):
        pytest.skip("metrics_dictionary.yml not present")
    dictionary = _load(DICTIONARY_PATH)

    names = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                names.add(str(k))
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(dictionary)
    conflicts = [
        c for _m, c, _e in _all_column_entries(registry)
        if c in names and isinstance(dictionary.get(c), dict)
        and ("domains" in dictionary[c] or "source_domain" in dictionary[c])
    ]
    assert not conflicts, (
        "metric(s) {} declare source domains in metrics_dictionary.yml as well "
        "as metric_provenance.yml. Provenance has one home.".format(conflicts))


# --------------------------------------------------------------------------
# registry well-formedness
# --------------------------------------------------------------------------

def test_registry_shape(registry):
    assert registry["version"] == 2
    assert set(registry["domains"]) == {"contracted", "uncontracted"}


def test_contracted_domains_match_the_contracts_directory(registry):
    import canonical_schema as cs
    assert set(registry["domains"]["contracted"]) == set(cs.available_tables())
