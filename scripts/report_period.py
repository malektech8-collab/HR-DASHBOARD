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


def normalise_month(value):
    """Return a valid YYYY-MM, or None. Never raises.

    Accepts a full date, so a `2026-08-14` attendance row and a `2026-08`
    payroll label reduce to the same period.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    candidate = text[:7]
    return candidate if MONTH_RE.match(candidate) else None


_normalise = normalise_month  # internal alias, kept for readability below


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


# What a domain loses when its file does not cover the reporting period. Each
# entry is the concrete consequence, named in the error, because "period
# mismatch" alone does not tell an operator what they are about to look at.
CONSEQUENCE_EN = {
    "payroll": ("Every payroll figure filters on the reporting period, so this "
                "run would report a payroll cost of 0 against a payroll file "
                "that is present and valid."),
    "compliance": ("Compliance records join to employees on the reporting "
                   "period, so this run would show every employee as missing "
                   "GOSI, Qiwa and insurance registration."),
    "attendance": ("Attendance is filtered to the reporting period and absence "
                   "is inferred from its absence, so this run would show every "
                   "employee absent on every working day."),
}
CONSEQUENCE_AR = {
    "payroll": "سيؤدي ذلك إلى عرض تكلفة رواتب صفرية رغم وجود ملف رواتب صالح.",
    "compliance": ("سيؤدي ذلك إلى إظهار جميع الموظفين كغير مسجلين في التأمينات "
                   "وقوى والتأمين الصحي."),
    "attendance": "سيؤدي ذلك إلى إظهار جميع الموظفين كغائبين في كل أيام العمل.",
}


def assert_period_is_covered(values, month, source):
    """The uploaded file must contain at least one row inside the period.

    Guards the interaction step 2a.5's convergence created, in the three places
    it exists. Every one of these narrows to the reporting period:

        base_payroll_current      payroll_period   = var('report_month')
        base_compliance_current   c.period         = var('report_month')   (JOIN)
        base_attendance_current   attendance_date BETWEEN start .. end

    When the file does not cover that period the filter matches nothing, and
    the domain is DECLARED and POPULATED and silver is perfectly correct, so
    the declared-domain guard passes and dbt is green. What reaches the client
    is a zero, or a universal exception, that no check in the system disagrees
    with. That is worse than a crash, so it is a validation error at ingest
    with both periods named.

    `values` are the file's period labels (`2026-08`) or dates (`2026-08-14`);
    both reduce to a month. Returns the month on success.
    """
    if not month:
        return None
    found = sorted({p for p in (normalise_month(x) for x in values) if p})
    if not found or month in found:
        # No parseable periods at all is the declared-domain guard's business,
        # not this one's; naming a range the file does not have would mislead.
        return month
    name = SETTING_NAME
    found_en = ", ".join(found)
    found_ar = "، ".join(found)
    raise ReportMonthMismatchError(
        "Reporting period mismatch. The reporting period is {month}, but the "
        "uploaded {source} data covers {found}. {why}".format(
            month=month, source=source, found=found_en,
            why=CONSEQUENCE_EN.get(source, ""))
        + NEWLINE +
        "Either set {name} to one of {found}, or upload the {month} {source} "
        "file.".format(name=name, month=month, source=source, found=found_en)
        + NEWLINE +
        "عدم تطابق فترة التقرير: فترة التقرير هي {month} بينما ملف {source} "
        "المرفوع يغطي {found}. {why}".format(
            month=month, source=source, found=found_ar,
            why=CONSEQUENCE_AR.get(source, ""))
    )


def assert_payroll_period_matches(periods, month=None, source="payroll"):
    """The payroll case, with the operator period as the default subject."""
    month = month or operator_report_month()
    return assert_period_is_covered(periods, month=month, source=source)
