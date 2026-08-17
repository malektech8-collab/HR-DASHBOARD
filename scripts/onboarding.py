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
import paths as _p

NEWLINE = chr(10)

REGISTRY_PATH = os.path.join("data", "onboarding", "declared_domains.yml")
# Resolution now goes through paths.py so an override reaches it. The
# constant is kept because tests and messages name it.
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


# Domains whose grain is a DATE rather than a period label. For these, knowing
# the client provided the domain says nothing about which DAYS arrived, and a
# calendar generator will invent the rest. They must declare a coverage window.
#
# Period-grained domains (payroll, compliance) carry one label per month, and
# the 2a.5 membership gate already establishes the label is present, so coverage
# is optional there and means "the whole reporting period".
#
# A list, not a heuristic: inferring grain from column types is the kind of
# guess this codebase has paid for three times.
DATE_GRAINED = {"attendance"}

# Domains a trend mart reads point-in-time, where the answer for a past period
# depends on how far back the file's history actually reaches.
HISTORY_DECLARING = {"employees"}


class OnboardingError(RuntimeError):
    """Raised when the declared state is missing, invalid, or contradicted."""


def registry_path():
    """The onboarding registry.

    THE ARTEFACT THIS WHOLE ISOLATION CYCLE IS ABOUT. A demo run rewriting a
    real client's absent_columns leaves the file internally inconsistent and
    silently re-fires every suppressed check. It follows the state root.
    """
    return _p.data("onboarding", "declared_domains.yml")


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


def _load_spec():
    path = registry_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _as_date(value, field, domain):
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value).strip())
    except Exception:
        raise OnboardingError(
            "{}: coverage.{}.{} is '{}', which is not a date. Expected "
            "YYYY-MM-DD.".format(registry_path(), domain, field, value))


def load_coverage():
    """Declared coverage windows, as {domain: (start, end)}.

    Category F. Knowing a client provided `attendance` says nothing about WHICH
    DAYS arrived, and the calendar generator invents the rest — one fabricated
    absence per employee per unreported working day. The window the client
    vouched for is the fact that makes a missing row mean "absent" instead of
    "not sent yet".

    DECLARED, never inferred from MIN/MAX(attendance_date). Inference would
    quietly shrink the window to whatever arrived, so a half-month upload would
    have its other half dropped instead of flagged — the `.uploaded` marker
    failure in a third costume.
    """
    spec = _load_spec()
    raw = spec.get("coverage") or {}
    if not isinstance(raw, dict):
        raise OnboardingError(
            "{}: 'coverage' must be a mapping of domain -> {{start, end}}."
            .format(registry_path()))
    coverage = {}
    for domain, window in raw.items():
        if not isinstance(window, dict):
            raise OnboardingError(
                "{}: coverage.{} must carry 'start' and 'end'."
                .format(registry_path(), domain))
        start = _as_date(window.get("start"), "start", domain)
        end = _as_date(window.get("end"), "end", domain)
        if end < start:
            raise OnboardingError(
                "{}: coverage.{} ends ({}) before it starts ({})."
                .format(registry_path(), domain, end, start))
        coverage[str(domain)] = (start, end)
    return coverage


def load_history_depth():
    """How far back each domain's file can actually speak, as {domain: date}.

    Category F, ruling 2 as amended. Point-in-time headcount is legitimate
    derivation from client-provided joining/termination dates — but only where
    the file reaches back far enough to contain the people who have since left.

    An active-only master does not merely understate past months. It understates
    each one by exactly the people who left since, so a flat or shrinking
    company renders as smooth growth: a false story that looks credible and
    therefore goes unquestioned. MIN(joining_date) cannot detect it, because
    long-tenured active staff carry old joining dates.

    So it is declared. Without a declared depth, historical months are NULL —
    never a derived-but-understated figure.
    """
    spec = _load_spec()
    raw = spec.get("history") or {}
    if not isinstance(raw, dict):
        raise OnboardingError(
            "{}: 'history' must be a mapping of domain -> {{since}}."
            .format(registry_path()))
    depth = {}
    for domain, window in raw.items():
        if isinstance(window, dict):
            value = window.get("since")
        else:
            value = window
        depth[str(domain)] = _as_date(value, "since", domain)
    return depth


def assert_coverage_declared(declared, coverage=None):
    """A date-grained domain must say which days it covers.

    Declared-but-not-covered fails loudly, exactly as declared-but-empty does:
    both are a declaration the data cannot back, and both are silent disasters
    if allowed through.
    """
    coverage = load_coverage() if coverage is None else coverage
    missing = sorted(d for d in declared if d in DATE_GRAINED and d not in coverage)
    if not missing:
        return True
    raise OnboardingError(
        "Declared domain(s) with no coverage period: {}.".format(missing)
        + NEWLINE +
        "A date-grained domain must state which days it covers, because a "
        "working day with no row is otherwise read as an absence. Add to {}:"
        .format(registry_path()) + NEWLINE +
        "  coverage:" + NEWLINE +
        "".join("    {}:{}      start: YYYY-MM-DD{}      end: YYYY-MM-DD{}"
                .format(d, NEWLINE, NEWLINE, NEWLINE) for d in missing) +
        "نطاقات معرّفة بدون فترة تغطية: {}. يجب تحديد الأيام المشمولة لأن يوم "
        "العمل بدون سجل يُقرأ كغياب.".format("، ".join(missing))
    )


def assert_history_supported(domain, earliest_row_date, declared_since=None):
    """The file must reach back as far as the history it claims.

    Declared-but-unsupported is the same failure shape as declared-but-empty:
    a claim the data cannot back. Silent, it would let a trend chart present
    months the file cannot speak to.
    """
    if declared_since is None:
        declared_since = load_history_depth().get(domain)
    if declared_since is None or earliest_row_date is None:
        return declared_since
    if earliest_row_date > declared_since:
        raise OnboardingError(
            "History depth for '{}' is declared as {}, but the earliest record "
            "in the file is {}. The file cannot speak to the period claimed."
            .format(domain, declared_since, earliest_row_date) + NEWLINE +
            "Either upload history back to {}, or set history.{}.since to {} "
            "or later.".format(declared_since, domain, earliest_row_date)
            + NEWLINE +
            "عمق السجل المعرّف للنطاق '{}' هو {} بينما أقدم سجل في الملف هو {}."
            .format(domain, declared_since, earliest_row_date)
        )
    return declared_since


def declare(domain, declared_by=None, note=None, contracted=None,
            coverage_start=None, coverage_end=None, history_since=None):
    """Add a domain to the registry, creating it if absent.

    Used by the upload commit step so a client never has to declare a domain
    by hand after providing it. `coverage_*` is required for date-grained
    domains (see DATE_GRAINED) and `history_since` for the ones a trend mart
    reads point-in-time.
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
    spec["version"] = 2
    spec["declared"] = sorted(set(current))
    if coverage_start or coverage_end:
        if not (coverage_start and coverage_end):
            raise OnboardingError(
                "coverage for '{}' needs both a start and an end.".format(domain))
        coverage = spec.get("coverage") or {}
        coverage[domain] = {"start": str(coverage_start), "end": str(coverage_end)}
        spec["coverage"] = coverage
    if history_since:
        history = spec.get("history") or {}
        history[domain] = {"since": str(history_since)}
        spec["history"] = history
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


def record_provided_columns(table, absent, path=None):
    """Record which OPTIONAL canonical columns the client did not supply.

    THE DISTINCTION THIS EXISTS FOR, and it is the whole point:

      a missing VALUE in a column the client PROVIDED
          -> a data-quality exception. This record is incomplete and someone
             should fix it.

      an entirely ABSENT COLUMN
          -> a coverage fact. The client does not track that concept, and no
             amount of HR work will change it.

    Every check in this codebase currently conflates them, and was entitled
    to: `required: true` meant the column was always there, so a NULL could
    only ever be the first kind. Relaxing that makes the distinction real, and
    makes the checks wrong unless they can tell the two apart.

    Once complete_canonical_shape() has run, nullness cannot answer the
    question - the column exists and is NULL either way. So it is recorded
    here, at the moment it is still knowable.

    Stored in the same registry as coverage and history, for the same reason:
    it is a fact about what the client provided, not about what the data says.
    """
    path = path or registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    spec = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f) or {}
    absent_map = spec.get("absent_columns") or {}
    absent_map[table] = sorted(absent)
    spec["absent_columns"] = absent_map
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)
    return sorted(absent)


def absent_columns(table, path=None):
    """Optional canonical columns the client did not supply, or []."""
    path = path or registry_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}
    return list((spec.get("absent_columns") or {}).get(table) or [])


def provides_column(table, column, path=None):
    """True unless the client's file was missing this column entirely.

    Defaults to True, deliberately: demo supplies every column, and a
    deployment with no registry entry has not been through an upload, so
    assuming provision keeps existing behaviour unchanged.
    """
    return column not in absent_columns(table, path)


def complete_canonical_shape(frame, table):
    """Add every ABSENT OPTIONAL canonical column as a typed NULL column.

    WHY THIS EXISTS. `required: true` guaranteed two different things at once:
    the column is PRESENT in the client's file, and it therefore EXISTS in
    every frame and table downstream. Relaxing a column to optional removes
    the first. Nothing downstream was ever written for the second. Measured:

        pl.col('cost_center') on a frame without it
          -> ColumnNotFoundError
        COALESCE(e.cost_center, ...) on a table without it
          -> BinderException: Table "e" does not have a column named ...

    So `required: false` on its own would accept a client's file at the gate
    and then CRASH in validate_data or dbt - worse than an honest rejection.
    Twelve dbt references to cost_center alone; guarding each is twelve places
    to get right and one to forget.

    Completing the shape here means silver ALWAYS carries the full canonical
    column set, so everything downstream binds and reads NULL - a value those
    consumers already had to handle, because NULL was always possible for an
    optional column.

    A REQUIRED column is NEVER completed. Its absence is still a REJECT at the
    gate, and filling it silently would be the fabrication this whole phase
    exists to remove.

    Same reasoning as write_empty_table() one level up: an undeclared domain
    must produce an EMPTY table rather than a MISSING one. This is that rule
    at column grain.

    Returns (frame, added) where `added` is the sorted list of column names
    that were absent - which is what record_provided_columns() records, so
    "the client did not supply this column" stays distinguishable from "the
    client supplied it and left it blank".
    """
    import polars as pl

    schema = empty_frame_schema(table)
    required = set(_cs.required_columns(table))
    # DERIVED columns are never completed. `is_saudi` is produced from
    # nationality at ingest, and ingest derives it only when the column is
    # ABSENT. Adding it as a typed NULL first would make the derivation skip
    # itself, and every Saudization figure would be computed from nulls -
    # a silent, favourable-looking zero. Completion runs after derivation
    # today, so this is belt and braces; it is here because the ordering is
    # not obvious and the failure would be quiet.
    derived = {c["name"] for c in _cs.columns(table)
               if c.get("derived_from") or c.get("derivation")}
    present = set(frame.columns)
    added = sorted(name for name in schema
                   if name not in present
                   and name not in required
                   and name not in derived)
    if added:
        frame = frame.with_columns(
            [pl.lit(None, dtype=schema[name]).alias(name) for name in added])
    return frame, added


def write_empty_table(table, silver_dir=None):
    """Write a typed zero-row silver parquet for an undeclared domain.

    Overwrites any file left by a previous run — otherwise yesterday's real or
    sample rows would survive as this client's data.
    """
    import polars as pl
    silver_dir = silver_dir or _p.data("silver")
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
