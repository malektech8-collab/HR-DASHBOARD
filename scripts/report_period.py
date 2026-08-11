"""Single owner of the reporting-period decision (Phase 2 P0-3, step 2a.5).

A reporting period is an OPERATOR decision, not a data artefact.

Why this module exists
----------------------
Step 2a.5 converged eight payroll-derived anchors onto `var('report_month')`,
which fixed a NULL anchor but made a worse failure reachable. The old chain was

    MAX(payroll_period) -> MAX(compliance.period) -> settings.DEFAULT_REPORT_MONTH

and that last link is a literal committed to this repository. With payroll AND
compliance both absent - an entirely ordinary employees-first onboarding - the
period resolved to that constant and every date window was anchored to it.

    before convergence: NULL anchor     -> 0, wrong and it LOOKS wrong
    after  convergence: constant anchor -> 2, wrong and it LOOKS RIGHT

The second is strictly more dangerous, and convergence is what makes it
reachable, so convergence has to close it. Real mode therefore FAILS CLOSED:
when the period cannot be derived from the client's own data, the run aborts
and names the setting the operator must supply. There is no configuration under
which real mode reports against a period this repository invented.

Precedence, in both modes:

    1. operator-set REPORT_MONTH   (explicit; overrides everything)
    2. derived from client data    (payroll close, then compliance period)
    3. real mode -> ABORT          demo mode -> DEFAULT_REPORT_MONTH

Derivation order is deliberate and unchanged: payroll_period is the canonical
monthly HR close, so it self-tracks the period the client is actually reporting
on; compliance period is the fallback signal.
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# Local dev layout: scripts/../backend/app. Container layout: backend contents
# are flattened under /app, so scripts/.. already holds the app package.
_BACKEND = os.path.abspath(os.path.join(_HERE, "..", "backend"))
if not os.path.isdir(os.path.join(_BACKEND, "app")):
    _BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.append(_BACKEND)

from app.config import settings  # noqa: E402

NEWLINE = chr(10)

# YYYY-MM. Anything else is rejected rather than coerced: a period silently
# reinterpreted is the same class of bug as a period silently invented.
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

SETTING_NAME = "REPORT_MONTH"

# Resolution sources, reported by resolve_report_month() so a caller (and a
# test) can assert WHERE the period came from, not merely what it is.
SOURCE_OPERATOR = "operator"
SOURCE_DATA = "data"
SOURCE_DEMO_DEFAULT = "demo-default"


class ReportMonthError(RuntimeError):
    """Base for every reporting-period failure."""


class ReportMonthUnresolvedError(ReportMonthError):
    """Real mode cannot determine the reporting period. Never guess one."""


class ReportMonthMismatchError(ReportMonthError):
    """The operator-set period is absent from the uploaded payroll file."""


def data_mode(mode=None):
    if mode is not None:
        return str(mode).strip().lower()
    return str(os.getenv("DATA_MODE", settings.DATA_MODE) or "demo").strip().lower()


def _normalise(value):
    """Return a valid YYYY-MM, or None. Never raises."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # Accept a full date: MAX(payroll_period) may come back as YYYY-MM-DD.
    candidate = text[:7]
    return candidate if MONTH_RE.match(candidate) else None


def operator_report_month():
    """The operator's explicit REPORT_MONTH, or None if unset.

    A malformed value is an error in BOTH modes. Falling back on a typo would
    reintroduce exactly the silent substitution this module removes.
    """
    raw = os.getenv(SETTING_NAME, getattr(settings, SETTING_NAME, None) or "")
    raw = str(raw or "").strip()
    if not raw:
        return None
    if not MONTH_RE.match(raw):
        raise ReportMonthUnresolvedError(
            "{} is set to '{}', which is not a valid reporting period. "
            "Expected YYYY-MM (for example 2026-08).".format(SETTING_NAME, raw)
            + NEWLINE +
            "قيمة {} هي '{}' وهي فترة تقرير غير صالحة. الصيغة المتوقعة "
            "YYYY-MM (مثال 2026-08).".format(SETTING_NAME, raw)
        )
    return raw


def _unresolved_error():
    name = SETTING_NAME
    return ReportMonthUnresolvedError(
        "Cannot determine the reporting period. No payroll or compliance data "
        "is present to derive it from, and {name} is not set.".format(name=name)
        + NEWLINE +
        "Set {name}=YYYY-MM (for example {name}=2026-08) in .env or the "
        "environment, and re-run.".format(name=name) + NEWLINE +
        "It cannot be guessed: the reporting period decides every date window "
        "on the dashboard - probation, contract and Iqama expiry, payroll "
        "period. Defaulting it would anchor a client's numbers to a period "
        "nobody chose, and the result would look correct." + NEWLINE +
        "تعذّر تحديد فترة التقرير. لا توجد بيانات رواتب أو التزام لاشتقاقها "
        "منها، والإعداد {name} غير محدد. الرجاء ضبط {name}=YYYY-MM "
        "(مثال {name}=2026-08) ثم إعادة التشغيل. لا يمكن تخمين الفترة لأنها "
        "تحدد كل النوافذ الزمنية في لوحة المعلومات.".format(name=name)
    )


def resolve_report_month(derived=None, mode=None):
    """Resolve the reporting period. Returns (month, source).

    `derived` is whatever the caller could read from the client's data, or None.
    An unparseable derived value is treated as no value at all - in real mode
    that aborts, which is the correct outcome for a payroll_period column that
    does not hold periods.
    """
    mode = data_mode(mode)

    operator = operator_report_month()
    if operator:
        return operator, SOURCE_OPERATOR

    normalised = _normalise(derived)
    if normalised:
        return normalised, SOURCE_DATA
    if derived not in (None, ""):
        print("[report_month] ignoring unparseable value {!r} from source data."
              .format(derived))

    if mode == "real":
        raise _unresolved_error()

    # Demo only. Sample data always derives, so this is reached solely when the
    # demo pipeline runs before any sample data exists.
    return settings.DEFAULT_REPORT_MONTH, SOURCE_DEMO_DEFAULT


def assert_payroll_period_matches(periods, month=None, source="payroll"):
    """Guard the interaction step 2a.5's convergence created.

    Every converged site filters `payroll_period = var('report_month')`. Under
    derivation the two agree by construction. Under an operator override they
    can disagree, and then the filter matches nothing: payroll_cost 0 with
    payroll DECLARED and POPULATED, and the declared-domain guard passing,
    because silver is perfectly correct. A zero with every check green is worse
    than a crash, so this is a validation error at ingest, naming both periods.

    `periods` is the set of payroll_period values in the uploaded file. Returns
    the agreed month, or None when no operator period is set (derivation cannot
    disagree with itself).
    """
    month = month or operator_report_month()
    if not month:
        return None
    found = sorted({p for p in (_normalise(x) for x in periods) if p})
    if not found or month in found:
        return month
    name = SETTING_NAME
    found_en = ", ".join(found)
    found_ar = "، ".join(found)
    raise ReportMonthMismatchError(
        "Reporting period mismatch. {name} is set to {month}, but the uploaded "
        "{source} data covers {found}. Every payroll figure filters on the "
        "reporting period, so this run would report a payroll cost of 0 "
        "against a payroll file that is present and valid.".format(
            name=name, month=month, source=source, found=found_en)
        + NEWLINE +
        "Either set {name} to one of {found}, or upload the {month} {source} "
        "file.".format(name=name, month=month, source=source, found=found_en)
        + NEWLINE +
        "عدم تطابق فترة التقرير: الإعداد {name} محدد بـ {month} بينما ملف "
        "{source} المرفوع يغطي {found}. سيؤدي ذلك إلى عرض تكلفة رواتب صفرية "
        "رغم وجود ملف رواتب صالح.".format(
            name=name, month=month, source=source, found=found_ar)
    )
