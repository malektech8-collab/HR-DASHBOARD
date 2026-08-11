"""Central suppression dependency (Phase 2 P0-3, step 2b).

One question, asked once per request, answered from two files the pipeline
already wrote:

    domain_provenance   (warehouse table) - was this domain PROVIDED?
    metric_provenance.yml (registry)      - which domains does this mart need?

and one rule:

    a mart may be served only if EVERY domain it depends on was provided.

Everything else here is consequence.

Why a dependency and not a middleware
-------------------------------------
Suppression has to happen where the mart is read, because that is the only
place the mapping from a response field to a mart exists. A middleware would
see a finished payload of numbers with no record of where they came from.

The two modes, and why they are declared rather than inferred
-------------------------------------------------------------
`mode: column` nulls individual columns of a single row whose provenance is
mixed - `mart_exec_kpis` carries a headcount (employees) beside a payroll cost
(payroll), and at `declared: [employees]` the first is real and the second must
not be served. `mode: payload` suppresses the whole thing, because the ROWS are
fabricated and not merely their values: a breakdown over an absent domain
invents the categories it groups by.

A SUPPRESSED PAYLOAD IS None, NEVER []. An empty list renders as an empty
chart, and an empty chart is a claim that the period had no events. This is a
ruling, and `test_suppression.py` pins it.

DEFAULT-DENY: a mart with no registry entry is suppressed. The alternative -
pass through what we have not mapped - is how a fabricated number reaches a
client while every test passes.
"""
import functools
import os
from typing import Dict, List, Optional, Set

import duckdb
import yaml
from fastapi import Depends

from app.config import settings
from app.db.duckdb_client import get_db_connection

_HERE = os.path.dirname(os.path.abspath(__file__))
# Local dev: backend/app/api/../../../config. Container: app is flattened
# under /app, so the repo-root probe lands on /app/config.
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if not os.path.isdir(os.path.join(_ROOT, "config")):
    _ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
REGISTRY_PATH = os.path.join(_ROOT, "config", "metric_provenance.yml")

# Reason codes. `not_provided` is the only one 2b emits; the others exist so
# the frontend can branch without string-matching prose.
NOT_PROVIDED = "not_provided"
NOT_MAPPED = "not_mapped"

_REASON_EN = {
    NOT_PROVIDED: "Not yet provided: {domains}.",
    NOT_MAPPED: "No declared data source, so this figure cannot be attributed.",
}
_REASON_AR = {
    NOT_PROVIDED: "لم يتم تقديم البيانات بعد: {domains}.",
    NOT_MAPPED: "لا يوجد مصدر بيانات معرّف لهذا المؤشر.",
}

# Domain display names, so the client reads "Payroll" and not "payroll".
DOMAIN_LABELS_EN = {
    "employees": "Employees", "payroll": "Payroll", "attendance": "Attendance",
    "compliance": "Compliance", "hr_requests": "HR Requests",
    "employee_relations": "Employee Relations", "recruitment": "Recruitment",
    "talent": "Talent",
}
DOMAIN_LABELS_AR = {
    "employees": "الموظفون", "payroll": "الرواتب", "attendance": "الحضور",
    "compliance": "الالتزام", "hr_requests": "طلبات الموارد البشرية",
    "employee_relations": "علاقات الموظفين", "recruitment": "التوظيف",
    "talent": "المواهب",
}

_registry_cache = None


def load_registry(path=None):
    """The registry, parsed once per process. It is a committed file."""
    global _registry_cache
    if path is None and _registry_cache is not None:
        return _registry_cache
    with open(path or REGISTRY_PATH, "r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle) or {}
    if path is None:
        _registry_cache = spec
    return spec


def _entry_domains(entry):
    """Domains for a column entry, which may be a bare list or a dict."""
    if isinstance(entry, dict):
        return list(entry.get("domains") or []), bool(entry.get("scope_to_provided"))
    return list(entry or []), False


class Suppression:
    """One withheld figure, in the form the sibling block renders."""

    __slots__ = ("key", "mart", "missing_domains", "reason")

    def __init__(self, key, mart, missing_domains, reason=NOT_PROVIDED):
        self.key = key
        self.mart = mart
        self.missing_domains = sorted(missing_domains)
        self.reason = reason

    def _labels(self, mapping):
        return "، ".join(mapping.get(d, d) for d in self.missing_domains) \
            if mapping is DOMAIN_LABELS_AR \
            else ", ".join(mapping.get(d, d) for d in self.missing_domains)

    def as_dict(self):
        return {
            "key": self.key,
            "mart": self.mart,
            "missing_domains": self.missing_domains,
            "reason": self.reason,
            "message_en": _REASON_EN[self.reason].format(
                domains=self._labels(DOMAIN_LABELS_EN)),
            "message_ar": _REASON_AR[self.reason].format(
                domains=self._labels(DOMAIN_LABELS_AR)),
        }


class Provenance:
    """Per-request suppression decisions, plus the record of what was withheld.

    Callers use three methods and nothing else:

        prov.payload(mart)          -> True if the whole payload may be served
        prov.column(mart, column)   -> True if that one column may be served
        prov.rows(mart, loader)     -> the rows, or None if suppressed

    Every False also records a Suppression, so a withheld figure is never
    merely absent from the response - it is named, with the domains that would
    make it real.
    """

    def __init__(self, provided: Set[str], registry: Dict, data_mode: str = "demo"):
        self.provided = set(provided)
        self.registry = registry or {}
        self.marts = self.registry.get("marts") or {}
        self.data_mode = data_mode
        self._suppressed: Dict[str, Suppression] = {}

    # -- queries ----------------------------------------------------------

    def missing_for(self, domains) -> List[str]:
        return sorted(d for d in domains if d not in self.provided)

    def entry(self, mart) -> Optional[Dict]:
        return self.marts.get(mart)

    def payload(self, mart, key=None) -> bool:
        """May this mart's rows be served at all?"""
        spec = self.entry(mart)
        if spec is None:
            self._record(Suppression(key or mart, mart, [], NOT_MAPPED))
            return False
        domains, scope_to_provided = _entry_domains(spec.get("domains"))
        if spec.get("mode") == "column":
            # A column-mode mart is served row-wise; individual columns are
            # nulled by column(). Suppressing the row would take the real
            # figures down with the absent ones.
            return True
        if scope_to_provided or spec.get("scope_to_provided"):
            # Ruling 1's exception: filtered to provided domains rather than
            # withheld. The filtering itself is step 4.
            return True
        missing = self.missing_for(domains)
        if missing:
            self._record(Suppression(key or mart, mart, missing))
            return False
        return True

    def column(self, mart, column) -> bool:
        """May this one column of a column-mode mart be served?"""
        spec = self.entry(mart)
        if spec is None:
            self._record(Suppression(column, mart, [], NOT_MAPPED))
            return False
        columns = spec.get("columns") or {}
        if column not in columns:
            self._record(Suppression(column, mart, [], NOT_MAPPED))
            return False
        domains, scope_to_provided = _entry_domains(columns[column])
        if not domains or scope_to_provided:
            return True
        missing = self.missing_for(domains)
        if missing:
            self._record(Suppression(column, mart, missing))
            return False
        return True

    # -- helpers used at the call sites -----------------------------------

    def value(self, mart, column, value):
        """The value, or None when its column is suppressed."""
        return value if self.column(mart, column) else None

    def rows(self, mart, loader, key=None):
        """Rows from `loader()`, or None when the payload is suppressed.

        `loader` is a callable so a suppressed mart is never queried - the
        fabricated rows are not produced, discarded and hoped about; they are
        not read at all.
        """
        if not self.payload(mart, key=key):
            return None
        return loader()

    def kpis(self, mart, items):
        """Build only the KPI cards whose columns may be served.

        `items` is a list of (column, factory). The factory is a callable, not
        a built KPIItem, for two reasons: a suppressed card is never
        constructed, and the arithmetic that would have built it - `round(rate
        * 100, 2)`, `value > 0` - is never run against a fabricated or NULL
        figure. Suppression that still evaluates the thing it is suppressing
        is one refactor away from emitting it.

        A suppressed KPI is DROPPED from the list and named in the sibling
        block, rather than rendered as a card with a null value: a card that
        says nothing invites the reader to supply their own zero.

        When EVERY card is suppressed the result is None, not []. A partial
        list is honest - the missing cards are named in the block - but an
        empty list renders as "this module has no KPIs", which is the same
        claim an empty chart makes. `null, never []` applies to a KPI strip
        exactly as it does to a series.
        """
        built = [factory() for column, factory in items if self.column(mart, column)]
        if not built and items:
            return None
        return built

    # -- the sibling block -------------------------------------------------

    def _record(self, suppression):
        self._suppressed.setdefault(
            "{}::{}".format(suppression.mart, suppression.key), suppression)

    def block(self) -> List[Dict]:
        return [s.as_dict() for s in sorted(
            self._suppressed.values(), key=lambda s: (s.mart, s.key))]

    @property
    def any_suppressed(self) -> bool:
        return bool(self._suppressed)


def provided_domains(conn) -> Set[str]:
    """Domains the client provided, per the table build_warehouse wrote.

    A missing table means the warehouse predates step 2b. Default-deny would
    black out every page on an old warehouse, so this returns the empty set
    ONLY in real mode; demo falls back to "everything provided", which is what
    a demo warehouse means.
    """
    try:
        rows = conn.execute(
            "SELECT domain FROM domain_provenance WHERE provided").fetchall()
        return {r[0] for r in rows}
    except Exception:
        if str(settings.DATA_MODE or "demo").strip().lower() == "real":
            return set()
        registry = load_registry().get("domains") or {}
        return set(registry.get("contracted") or {}) | set(
            registry.get("uncontracted") or {})


def get_provenance(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> Provenance:
    return Provenance(
        provided=provided_domains(conn),
        registry=load_registry(),
        data_mode=str(settings.DATA_MODE or "demo").strip().lower(),
    )


def suppressible(response_model, *marts):
    """Gate a payload-mode endpoint on its marts, before the handler runs.

    Two things happen here that are easy to get wrong one endpoint at a time:

    * A suppressed endpoint never executes its query. The fabricated rows are
      not produced and then discarded - they are not produced. Anything that
      merely filters the result keeps the fabricator alive one refactor away.
    * Every response gets the sibling block attached on the way out, so a
      handler cannot forget it. A withheld figure with no entry naming it is
      indistinguishable from a bug.

    Declared per route rather than inferred from the SQL, for the same reason
    `mode` is declared in the registry: inference is what fails silently when
    someone adds a second mart to a handler.
    """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(**kwargs):
            prov = kwargs.get("prov")
            if prov is None:  # pragma: no cover - wiring error, not a state
                return func(**kwargs)
            if any(not prov.payload(mart) for mart in marts):
                return response_model(suppressed=prov.block())
            result = func(**kwargs)
            if hasattr(result, "suppressed") and not result.suppressed:
                result.suppressed = prov.block()
            return result
        wrapper.__suppressible_marts__ = marts
        return wrapper
    return decorate
