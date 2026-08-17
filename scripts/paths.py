# -*- coding: utf-8 -*-
"""Where generated STATE lives. One resolver, consulted by everything.

WHY THIS EXISTS.

    Measured on the first real load: a `pytest` run rewrote the operator's
    onboarding registry and rebuilt their warehouse in demo mode. The damage
    was not the warehouse - that rebuilds from data/raw in ninety seconds - it
    was the registry, which came out INTERNALLY INCONSISTENT: the client's
    `declared` and `history_since` beside demo's `absent_columns`. That flips
    provides_column() to True and silently returns thousands of suppressed
    warnings to a client's Data Quality page.

    It is invisible to CI by construction. CI has no profile, no client load
    and no declared registry, so clobbering those is indistinguishable from
    correct behaviour. It can only ever bite on the machine where real data
    lives. GAP-002's family, and now GAP-003.

STATE versus SOURCE, which is the whole distinction.

    STATE is generated or operator-owned: raw, bronze, silver, gold, sample,
    staging, mapping profiles, the onboarding registry, the warehouse. It is
    written by the pipeline and it is what a test must never touch.

    SOURCE is repository content: data/contracts, config/. Humans edit it, git
    tracks it, and the pipeline only READS it. It must NOT move when state
    does - a test pointing at a temp root still has to validate against the
    real contracts, or it is testing a copy of itself.

    The rule this file encodes: isolate WRITES, not reads.

RESOLUTION ORDER, highest priority first:

    1. HRDASH_DATA_ROOT   - an explicit override. Set by the test suite, and
                            available to an operator who wants a scratch root.
    2. /app/data          - the container layout, when it exists.
    3. <repo>/data        - the developer and operator default.

WHY AN ENV VAR AND NOT A FIXTURE. `test_refresh_trigger` POSTs
/api/data/refresh, and the API runs refresh_all.py as a SUBPROCESS. A
monkeypatch lives in the pytest process and cannot cross that boundary, so the
single worst offender is exactly the one a fixture cannot reach. An env var is
inherited by the child, by dbt, and by anything else spawned downstream.
"""
import os

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ENV_VAR = "HRDASH_DATA_ROOT"
CONTAINER_DATA_DIR = "/app/data"
CONTAINER_WAREHOUSE_DIR = "/app/warehouse"


def repo_root():
    """The repository itself. Never redirected - SOURCE lives here."""
    return _REPO_ROOT


def data_root():
    """The root of generated STATE."""
    override = os.environ.get(ENV_VAR)
    if override:
        return os.path.abspath(os.path.join(override, "data"))
    if os.path.isdir(CONTAINER_DATA_DIR):
        return CONTAINER_DATA_DIR
    return os.path.join(_REPO_ROOT, "data")


def warehouse_root():
    """The DuckDB warehouse directory. State, so it follows the override."""
    override = os.environ.get(ENV_VAR)
    if override:
        return os.path.abspath(os.path.join(override, "warehouse"))
    if os.path.isdir(CONTAINER_WAREHOUSE_DIR):
        return CONTAINER_WAREHOUSE_DIR
    return os.path.join(_REPO_ROOT, "warehouse")


def data(*parts):
    """A path under the STATE root. `data('silver', 'employees.parquet')`."""
    return os.path.join(data_root(), *parts)


def ensure(*parts):
    """`data(*parts)` as a DIRECTORY, created if absent."""
    path = data(*parts)
    os.makedirs(path, exist_ok=True)
    return path


def warehouse_path(name="hr_analytics.duckdb"):
    return os.path.join(warehouse_root(), name)


# -- SOURCE. Deliberately NOT redirected. -------------------------------------

def contracts_dir():
    """Canonical schemas. Repository content that the pipeline only reads.

    A test running against a temp root must still validate against the REAL
    contracts; pointing this at a copy would mean the suite checks its own
    fixtures instead of the thing that ships.
    """
    container = os.path.join(CONTAINER_DATA_DIR, "contracts")
    if os.path.isdir(container):
        return container
    return os.path.join(_REPO_ROOT, "data", "contracts")


def config_dir():
    container = "/app/config"
    if os.path.isdir(container):
        return container
    return os.path.join(_REPO_ROOT, "config")


# -- convenience for the layers that get written most -------------------------

def raw(*parts):
    return data("raw", *parts)


def bronze(*parts):
    return data("bronze", *parts)


def silver(*parts):
    return data("silver", *parts)


def gold(*parts):
    return data("gold", *parts)


def sample(*parts):
    return data("sample", *parts)
