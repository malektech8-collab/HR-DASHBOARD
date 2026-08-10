"""P0-3 step 1: the metric provenance registry must stay complete and honest.

No suppression behaviour exists yet — this cycle is the registry and the tests
that keep it correct. The coverage test is the load-bearing one: under
default-deny an unmapped column is suppressed, so a metric added without an
entry becomes invisible rather than fabricated. That is the safe failure
direction, but it is still a failure, and CI should say so at the point the
column is added rather than when someone notices a blank on a dashboard.
"""
import io
import os
import sys

import pytest
import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

PROVENANCE_PATH = os.path.join(_ROOT, "config", "metric_provenance.yml")
DICTIONARY_PATH = os.path.join(_ROOT, "config", "metrics_dictionary.yml")
WAREHOUSE = os.path.join(_ROOT, "warehouse", "hr_analytics.duckdb")
NEWLINE = chr(10)

KPI_MART_SQL = (
    "SELECT view_name FROM duckdb_views() "
    "WHERE view_name LIKE 'mart_%kpis' "
    "   OR view_name IN ('mart_command_center_overview', "
    "                    'mart_data_quality_summary') "
    "ORDER BY 1"
)


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
    """A metric entry is either a bare list or a mapping with `domains`."""
    if isinstance(entry, dict):
        return list(entry.get("domains") or [])
    return list(entry or [])


def _warehouse_kpi_columns():
    """{mart: [columns]} straight from the built warehouse.

    Read from the warehouse rather than parsed from SQL: the warehouse is what
    the API actually queries, so it cannot drift from what needs covering.
    """
    import duckdb
    conn = duckdb.connect(WAREHOUSE, read_only=True)
    try:
        marts = [r[0] for r in conn.execute(KPI_MART_SQL).fetchall()]
        out = {}
        for m in marts:
            cur = conn.execute("SELECT * FROM {} LIMIT 0".format(m))
            out[m] = [d[0] for d in cur.description]
        return out
    finally:
        conn.close()


requires_warehouse = pytest.mark.skipif(
    not os.path.exists(WAREHOUSE),
    reason="warehouse not built; run scripts/refresh_all.py",
)


# --------------------------------------------------------------------------
# coverage — the default-deny guarantee
# --------------------------------------------------------------------------

@requires_warehouse
def test_every_kpi_mart_column_is_mapped(registry):
    """Fails when a KPI mart column has no provenance entry.

    Add a column to any KPI mart without adding it here and this test fails,
    naming the column. That is the intended workflow.
    """
    actual = _warehouse_kpi_columns()
    mapped = registry["metrics"]
    n_empty = sum(1 for entries in mapped.values() for e in entries.values()
                  if not _entry_domains(e))
    n_total = sum(len(v) for v in mapped.values())
    print(NEWLINE + "[provenance] {} mapped columns; {} source-free (`domains: []`) "
          "— these bypass suppression by design".format(n_total, n_empty))
    missing = []
    for mart, cols in actual.items():
        entries = mapped.get(mart)
        if entries is None:
            missing.append("{} (entire mart unmapped)".format(mart))
            continue
        for col in cols:
            if col not in entries:
                missing.append("{}.{}".format(mart, col))
    assert not missing, (
        "unmapped KPI mart column(s) — add them to config/metric_provenance.yml "
        "with their source domains:\n  " + "\n  ".join(missing))


@requires_warehouse
def test_registry_has_no_entries_for_columns_that_do_not_exist(registry):
    """A stale entry is a quieter problem than a missing one, but it still
    means the registry and the warehouse disagree."""
    actual = _warehouse_kpi_columns()
    stale = []
    for mart, entries in registry["metrics"].items():
        if mart not in actual:
            stale.append("{} (mart no longer exists)".format(mart))
            continue
        for col in entries:
            if col not in actual[mart]:
                stale.append("{}.{}".format(mart, col))
    assert not stale, "stale provenance entries:\n  " + "\n  ".join(stale)


def test_every_referenced_domain_is_declared(registry, known_domains):
    unknown = []
    for mart, entries in registry["metrics"].items():
        for col, entry in entries.items():
            for d in _entry_domains(entry):
                if d not in known_domains:
                    unknown.append("{}.{} -> {}".format(mart, col, d))
    assert not unknown, (
        "metric(s) reference a domain not defined under `domains:`:\n  "
        + "\n  ".join(unknown))


def test_empty_domain_lists_carry_a_reason():
    """Under default-deny, `[]` is the only way to silence a coverage failure
    without reviewing the metric. Every one must say why, in a comment on the
    same line, so the list stays small and visible rather than becoming a
    dumping ground for anything awkward to classify.

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
        "every `domains: []` entry must state why it has no source domain:"
        + NEWLINE + "  " + (NEWLINE + "  ").join(uncommented))


def test_empty_domain_lists_are_deliberate(registry):
    """`domains: []` means "no source domain", which is a real answer for a
    period label or a timestamp — but it must be a small, reviewable set."""
    empties = [
        "{}.{}".format(mart, col)
        for mart, entries in registry["metrics"].items()
        for col, entry in entries.items()
        if not _entry_domains(entry)
    ]
    print(NEWLINE + "[provenance] source-free (`domains: []`) entries: {} -> {}"
          .format(len(empties), sorted(empties)))
    assert set(empties) == {
        "mart_exec_kpis.report_month",
        "mart_command_center_overview.modules_healthy",
        "mart_command_center_overview.last_data_refresh",
        "mart_command_center_overview.latest_source_business_date",
    }, ("the set of source-free metrics changed: {}. Each one bypasses "
        "suppression, so additions need review.".format(sorted(empties)))


def test_scope_to_provided_is_limited_to_the_ruled_metrics(registry):
    """Ruling 1 scopes data_quality_score rather than suppressing it. That is
    an exception, so it should not spread without a decision."""
    scoped = [
        "{}.{}".format(mart, col)
        for mart, entries in registry["metrics"].items()
        for col, entry in entries.items()
        if isinstance(entry, dict) and entry.get("scope_to_provided")
    ]
    assert set(scoped) == {
        "mart_exec_kpis.data_quality_score",
        "mart_data_quality_summary.data_quality_score",
        "mart_command_center_overview.data_quality_score",
        "mart_command_center_overview.total_active_exceptions",
    }, "scope_to_provided changed: {}".format(sorted(scoped))


# --------------------------------------------------------------------------
# consistency with metrics_dictionary.yml (ruling 2)
# --------------------------------------------------------------------------

def test_names_shared_with_metrics_dictionary_are_consistent(registry):
    """The two files have different key spaces — metrics_dictionary.yml is
    keyed by global business metric name for a curated subset, this one by
    mart -> column for every KPI column. Where a name appears in both, it must
    mean the same thing.
    """
    if not os.path.exists(DICTIONARY_PATH):
        pytest.skip("metrics_dictionary.yml not present")
    dictionary = _load(DICTIONARY_PATH)

    dict_names = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    dict_names.add(str(k))
                    walk(v)
                else:
                    dict_names.add(str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(dictionary)

    registry_cols = {
        col for entries in registry["metrics"].values() for col in entries
    }
    shared = sorted(registry_cols & dict_names)

    # The check is that a shared name is not defined twice with conflicting
    # source domains. metrics_dictionary.yml carries no domain field today, so
    # there is nothing to conflict with — this asserts that stays true, and
    # fails loudly the day a domain/source key is added there instead of here.
    conflicts = []
    for name in shared:
        entry = dictionary.get(name)
        if isinstance(entry, dict) and ("domains" in entry or "source_domain" in entry):
            conflicts.append(name)
    assert not conflicts, (
        "metric(s) {} declare source domains in metrics_dictionary.yml as well "
        "as metric_provenance.yml. Provenance has one home."
        .format(conflicts))


# --------------------------------------------------------------------------
# the registry is well-formed
# --------------------------------------------------------------------------

def test_registry_shape(registry):
    assert registry["version"] == 1
    assert set(registry["domains"]) == {"contracted", "uncontracted"}
    assert set(registry["domains"]["contracted"]) == {
        "employees", "payroll", "attendance", "compliance",
        "hr_requests", "employee_relations"}


def test_contracted_domains_match_the_contracts_directory(registry):
    """The contracted half must not drift from data/contracts/."""
    import canonical_schema as cs
    assert set(registry["domains"]["contracted"]) == set(cs.available_tables())
