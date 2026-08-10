"""Declared-domain registry (Phase 2 P0, step 1).

A client onboards incrementally, and the system must know which domains they
have DECLARED they are providing. That declaration is an input, not something
inferred from whether a table happens to have rows.

The distinction is the whole point. If populated-ness were inferred, a genuine
defect that drops every row — a broken join, a failed ingest, a resolver
regression — would look exactly like "the client hasn't uploaded this yet", and
the checks would go quiet precisely when they should fire. This codebase has
already produced that failure once: a stale `.uploaded` marker froze employees
ingest and zeroed four Attendance widgets while everything reported green.

One mechanism, three consumers:
  * ingest      - fail-closed on missing domains; never fall back to sample
  * the guard   - declared == populated, checked before the warehouse builds
  * the API     - per-domain provenance, so a client can tell whose numbers
                  they are looking at

FILE ONLY, by ruling. No environment-variable form: the commit step writes to
the registry, an env var is not writable, and "both" would create a source of
truth that one code path cannot update.

Demo mode never consults any of this.
"""
import datetime
import os

import yaml

import canonical_schema as _cs

REGISTRY_PATH = os.path.join("data", "onboarding", "declared_domains.yml")
CONTAINER_REGISTRY_PATH = "/app/data/onboarding/declared_domains.yml"

# Contract type -> the polars dtype ingest produces in silver.
_PL_TYPES = {
    "VARCHAR": "Utf8",
    "INTEGER": "Int64",
    "DECIMAL": "Float64",
    "DATE": "Date",
    "TIMESTAMP": "Datetime",
    "BOOLEAN": "Boolean",
}


class OnboardingError(RuntimeError):
    """Raised when the declared state is missing, invalid, or contradicted."""


def registry_path():
    if os.path.exists(os.path.dirname(CONTAINER_REGISTRY_PATH)):
        return CONTAINER_REGISTRY_PATH
    return REGISTRY_PATH


def registry_exists():
    return os.path.exists(registry_path())


def load_declared(contracted=None):
    """Domains the client has declared. Empty set when no registry exists.

    Every entry must be a contracted table. An unknown name is a hard error,
    not a warning — a typo that silently declares nothing would reintroduce the
    exact ambiguity this registry removes.
    """
    path = registry_path()
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}
    declared = spec.get("declared") or []
    if not isinstance(declared, list):
        raise OnboardingError(
            "{}: 'declared' must be a list of domain names.".format(path))
    declared = {str(d).strip() for d in declared if str(d).strip()}
    known = set(contracted if contracted is not None else _cs.available_tables())
    unknown = sorted(declared - known)
    if unknown:
        raise OnboardingError(
            "{}: declared domain(s) {} have no contract. Contracted domains "
            "are {}.".format(path, unknown, sorted(known)))
    return declared


def declare(domain, declared_by=None, note=None, contracted=None):
    """Add a domain to the registry, creating it if absent.

    Used by the upload commit step so a client never has to declare a domain
    by hand after providing it.
    """
    known = set(contracted if contracted is not None else _cs.available_tables())
    if domain not in known:
        raise OnboardingError(
            "cannot declare '{}': no contract at data/contracts/{}_schema.yml."
            .format(domain, domain))
    path = registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    spec = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f) or {}
    current = [str(d) for d in (spec.get("declared") or [])]
    if domain not in current:
        current.append(domain)
    spec["version"] = spec.get("version", 1)
    spec["declared"] = sorted(set(current))
    if declared_by:
        spec["declared_by"] = declared_by
    spec["declared_at"] = datetime.date.today().isoformat()
    if note:
        spec["note"] = note
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)
    return set(spec["declared"])


def empty_frame_schema(table):
    """Polars schema for a typed zero-row frame of `table`.

    An undeclared domain must produce an EMPTY table, not a missing one: a
    missing parquet is skipped by build_warehouse, and dbt then fails with a
    catalog error. Typed and empty is the honest representation of "the client
    has not provided this".
    """
    import polars as pl
    schema = {}
    for c in _cs.columns(table):
        schema[c["name"]] = getattr(
            pl, _PL_TYPES.get(str(c.get("type", "VARCHAR")).upper(), "Utf8"))
    return schema


def write_empty_table(table, silver_dir="data/silver"):
    """Write a typed zero-row silver parquet for an undeclared domain.

    Overwrites any file left by a previous run — otherwise yesterday's real or
    sample rows would survive as this client's data.
    """
    import polars as pl
    os.makedirs(silver_dir, exist_ok=True)
    path = os.path.join(silver_dir, "{}.parquet".format(table))
    pl.DataFrame(schema=empty_frame_schema(table)).write_parquet(path)
    return path


def assert_declared_matches_populated(row_counts, declared=None):
    """The guard. Raises OnboardingError on any divergence.

    | declared | rows | meaning                              | action |
    |----------|------|--------------------------------------|--------|
    | yes      | > 0  | normal                               | ok     |
    | yes      | 0    | a real defect - ingest dropped rows  | ABORT  |
    | no       | 0    | not onboarded yet                    | ok     |
    | no       | > 0  | stale registry, or a leaked path     | ABORT  |

    Making divergence fatal is what lets the dbt tests stay untouched: an empty
    mart for an undeclared domain is *provably* "not uploaded yet" rather than
    "silently broken", because declared-but-empty can never get this far.
    """
    declared = set(declared if declared is not None else load_declared())
    declared_empty = sorted(t for t in declared if row_counts.get(t, 0) == 0)
    undeclared_populated = sorted(
        t for t, n in row_counts.items() if n > 0 and t not in declared)

    problems = []
    if declared_empty:
        problems.append(
            "declared but EMPTY: {}. These domains were declared as provided, "
            "so zero rows indicates a load failure, not an absence."
            .format(declared_empty))
    if undeclared_populated:
        problems.append(
            "populated but NOT declared: {}. Either the registry is stale or "
            "data reached these tables by an unintended path."
            .format(undeclared_populated))
    if problems:
        raise OnboardingError(
            "Declared-domain guard failed.\n  " + "\n  ".join(problems)
            + "\n  Registry: {}".format(registry_path()))
    return True
