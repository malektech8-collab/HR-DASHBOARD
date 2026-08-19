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
from app.schemas.kpi import CoverageItem, SuppressionItem
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
    # `locations` became reachable as a suppression reason when
    # missing_project_count was corrected to depend on it. Until then no
    # client-facing message named this domain, and it read as
    # "Not yet provided: locations." - lowercase and, worse, untranslated.
    "locations": "Locations",
    # One per government platform. `compliance` stays as the alias over
    # the four, so a metric still declaring it reads sensibly.
    "compliance_gosi": "GOSI",
    "compliance_qiwa": "Qiwa",
    "compliance_wps": "Wage Protection (Mudad)",
    "compliance_health": "Health Insurance",
}
DOMAIN_LABELS_AR = {
    "employees": "الموظفون", "payroll": "الرواتب", "attendance": "الحضور",
    "compliance": "الالتزام", "hr_requests": "طلبات الموارد البشرية",
    "employee_relations": "علاقات الموظفين", "recruitment": "التوظيف",
    "talent": "المواهب",
    "locations": "المواقع",
    "compliance_gosi": "التأمينات الاجتماعية",
    "compliance_qiwa": "قوى",
    "compliance_wps": "حماية الأجور (مدد)",
    "compliance_health": "الضمان الصحي",
}

# Where each date-grained domain's coverage comes from. The mart name appears
# as a literal so the registry-coverage test can see that the API reads it -
# that test is what forces this new surface into metric_provenance.yml instead
# of letting it bypass provenance.
COVERAGE_QUERIES = {
    "attendance": (
        "SELECT declared_start, declared_end, covered_days, expected_days "
        "FROM mart_attendance_coverage"
    ),
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


class Coverage:
    """How much of the reporting period one domain's upload covers."""

    __slots__ = ("domain", "declared_start", "declared_end",
                 "covered_days", "expected_days")

    def __init__(self, domain, declared_start, declared_end,
                 covered_days, expected_days):
        self.domain = domain
        self.declared_start = declared_start
        self.declared_end = declared_end
        self.covered_days = int(covered_days or 0)
        self.expected_days = int(expected_days or 0)

    @property
    def is_partial(self):
        """The noise rule: a note only where there is something to say.

        Full coverage says nothing worth reading, and a note on every card
        trains people to stop reading notes - which would cost most on the one
        case that needs an explanation, the unmeasurable em dash.
        """
        return self.expected_days > 0 and self.covered_days < self.expected_days

    def _window(self, connector):
        if not (self.declared_start and self.declared_end):
            return ""
        return " ({} {} {})".format(
            self.declared_start, connector, self.declared_end)

    def as_dict(self):
        pct = (100.0 * self.covered_days / self.expected_days
               if self.expected_days else 0.0)
        # Western digits inside the Arabic text, matching every other bilingual
        # message in the product. One convention, settled here.
        return {
            "domain": self.domain,
            "domain_label_en": DOMAIN_LABELS_EN.get(self.domain, self.domain),
            "domain_label_ar": DOMAIN_LABELS_AR.get(self.domain, self.domain),
            "declared_start": str(self.declared_start) if self.declared_start else None,
            "declared_end": str(self.declared_end) if self.declared_end else None,
            "covered_days": self.covered_days,
            "expected_days": self.expected_days,
            "coverage_pct": round(pct, 1),
            "message_en": "Covers {} of {} working days{}.".format(
                self.covered_days, self.expected_days, self._window("to")),
            "message_ar": "\u064a\u063a\u0637\u064a {} \u0645\u0646 {} "
                          "\u064a\u0648\u0645 \u0639\u0645\u0644{}.".format(
                              self.covered_days, self.expected_days,
                              self._window("إلى")),
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

    def __init__(self, provided: Set[str], registry: Dict, data_mode: str = "demo",
                 coverage: Optional[Dict[str, "Coverage"]] = None):
        self.provided = set(provided)
        self.registry = registry or {}
        self.marts = self.registry.get("marts") or {}
        self.data_mode = data_mode
        self._coverage = coverage or {}
        self._suppressed: Dict[str, Suppression] = {}
        self._noted: Dict[str, Coverage] = {}

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

    # -- coverage: present, but measured over less than the whole period ----

    def mart_domains(self, mart) -> List[str]:
        """Every domain a mart depends on, whichever mode it declares."""
        spec = self.entry(mart)
        if spec is None:
            return []
        if spec.get("mode") == "column":
            found = set()
            for entry in (spec.get("columns") or {}).values():
                found.update(_entry_domains(entry)[0])
            return sorted(found)
        return sorted(_entry_domains(spec.get("domains"))[0])

    def coverage(self, domain) -> Optional["Coverage"]:
        """The declared window and day counts for a domain, or None."""
        return self._coverage.get(domain)

    def note_coverage(self, mart) -> List["Coverage"]:
        """Record a note for every partially-covered domain this mart reads.

        Gated on the domain being PROVIDED: with the domain absent, the
        `suppressed` block already explains the emptiness, and a coverage note
        beside it would be a second explanation of the same thing.
        """
        noted = []
        for domain in self.mart_domains(mart):
            if domain not in self.provided:
                continue
            found = self._coverage.get(domain)
            if found is not None and found.is_partial:
                self._noted.setdefault(domain, found)
                noted.append(found)
        return noted

    def coverage_block(self) -> List[CoverageItem]:
        return [CoverageItem(**c.as_dict()) for c in sorted(
            self._noted.values(), key=lambda c: c.domain)]

    @property
    def any_coverage_note(self) -> bool:
        return bool(self._noted)

    # -- the sibling block -------------------------------------------------

    def _record(self, suppression):
        self._suppressed.setdefault(
            "{}::{}".format(suppression.mart, suppression.key), suppression)

    def block(self) -> List[SuppressionItem]:
        # Built as models, not dicts: assigning dicts to a typed field works
        # but makes Pydantic warn, and a warning nobody reads is how the next
        # shape mismatch gets through.
        return [SuppressionItem(**s.as_dict()) for s in sorted(
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


def domain_coverage(conn) -> Dict[str, Coverage]:
    """Read each date-grained domain's coverage from its mart.

    A missing mart means the warehouse predates the coverage surface, which is
    not an error: no coverage read means no note, and every figure is served
    exactly as it was before.
    """
    found = {}
    for domain, query in COVERAGE_QUERIES.items():
        try:
            row = conn.execute(query).fetchone()
        except Exception:
            continue
        if row:
            found[domain] = Coverage(domain, row[0], row[1], row[2], row[3])
    return found


def get_provenance(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> Provenance:
    return Provenance(
        provided=provided_domains(conn),
        registry=load_registry(),
        data_mode=str(settings.DATA_MODE or "demo").strip().lower(),
        coverage=domain_coverage(conn),
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
            for mart in marts:
                prov.note_coverage(mart)
            result = func(**kwargs)
            if hasattr(result, "suppressed") and not result.suppressed:
                result.suppressed = prov.block()
            if hasattr(result, "coverage_notes") and not result.coverage_notes:
                result.coverage_notes = prov.coverage_block()
            return result
        wrapper.__suppressible_marts__ = marts
        return wrapper
    return decorate
