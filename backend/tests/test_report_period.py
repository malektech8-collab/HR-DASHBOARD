"""Phase 2 P0-3 step 2a.5: the reporting period fails closed in real mode.

Step 2a.5 converged eight payroll-derived anchors onto `var('report_month')`.
That fixed a NULL anchor, and in doing so made the fallback chain's last link
reachable: with payroll AND compliance absent, `report_month` resolved to
`settings.DEFAULT_REPORT_MONTH` — a literal committed to this repository.

    before convergence: NULL anchor     -> 0, wrong and it LOOKS wrong
    after  convergence: constant anchor -> 2, wrong and it LOOKS RIGHT

These tests pin the three things that close it:
  * real mode ABORTS rather than guessing, naming REPORT_MONTH
  * an explicit REPORT_MONTH is honoured in both modes and beats derivation
  * an operator period the payroll file does not contain is a validation error
    at ingest, naming both periods — not a silent zero downstream

Synthetic only. Nothing here touches data/sample, data/raw, or client data.
"""
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import report_period as rp  # noqa: E402
from app.config import settings  # noqa: E402

DEFAULT = settings.DEFAULT_REPORT_MONTH


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """No ambient REPORT_MONTH / DATA_MODE leaking in from the shell or .env."""
    monkeypatch.delenv("REPORT_MONTH", raising=False)
    monkeypatch.delenv("DATA_MODE", raising=False)
    monkeypatch.setattr(settings, "REPORT_MONTH", None, raising=False)
    monkeypatch.setattr(settings, "DATA_MODE", "demo", raising=False)
    monkeypatch.chdir(_ROOT)


def _set_operator(monkeypatch, value):
    monkeypatch.setenv("REPORT_MONTH", value)


# --------------------------------------------------------------------------
# item 1 — real mode fails closed
# --------------------------------------------------------------------------

def test_real_mode_aborts_when_the_period_cannot_be_derived():
    """Payroll and compliance both absent. This is ordinary employees-first
    onboarding, not an edge case."""
    with pytest.raises(rp.ReportMonthUnresolvedError):
        rp.resolve_report_month(derived=None, mode="real")


def test_the_abort_message_names_the_setting_and_explains_why():
    with pytest.raises(rp.ReportMonthUnresolvedError) as excinfo:
        rp.resolve_report_month(derived=None, mode="real")
    message = str(excinfo.value)
    # names the setting the operator must supply, with an example
    assert "REPORT_MONTH" in message
    assert "YYYY-MM" in message
    # says why it cannot be guessed, not merely that it failed
    assert "cannot be guessed" in message
    # bilingual, like every other operator-facing onboarding error
    assert "فترة التقرير" in message


def test_real_mode_aborts_on_a_derived_value_that_is_not_a_period():
    """A payroll_period column that does not hold periods is a data problem.
    Coercing it, or falling back, would anchor the client to a guess."""
    with pytest.raises(rp.ReportMonthUnresolvedError):
        rp.resolve_report_month(derived="not-a-month", mode="real")


def test_real_mode_resolves_normally_when_the_data_carries_a_period():
    month, source = rp.resolve_report_month(derived="2026-08", mode="real")
    assert (month, source) == ("2026-08", rp.SOURCE_DATA)


def test_a_derived_full_date_is_normalised_to_its_month():
    """MAX(payroll_period) can come back as YYYY-MM-DD."""
    assert rp.resolve_report_month(derived="2026-08-31", mode="real")[0] == "2026-08"


# --------------------------------------------------------------------------
# item 1 — DEFAULT_REPORT_MONTH is demo-only
# --------------------------------------------------------------------------

def test_demo_mode_still_falls_back_to_the_default():
    """Unchanged behaviour in demo — this is what keeps the demo gate identical."""
    month, source = rp.resolve_report_month(derived=None, mode="demo")
    assert (month, source) == (DEFAULT, rp.SOURCE_DEMO_DEFAULT)


def test_default_report_month_is_unreachable_in_real_mode(monkeypatch):
    """Sweep every real-mode input shape. The default must never be returned
    unless the operator or the data asked for that exact month."""
    for derived in (None, "", "   ", "garbage", "2026-13", "2026"):
        with pytest.raises(rp.ReportMonthUnresolvedError):
            rp.resolve_report_month(derived=derived, mode="real")

    # and with an operator period set, the answer is the operator's, never the default
    _set_operator(monkeypatch, "2026-08")
    assert DEFAULT != "2026-08", "fixture assumes the default is not August 2026"
    for derived in (None, "garbage", "2026-01", DEFAULT):
        month, source = rp.resolve_report_month(derived=derived, mode="real")
        assert (month, source) == ("2026-08", rp.SOURCE_OPERATOR)


def test_the_demo_default_has_exactly_three_readers():
    """Structural pin. `DEFAULT_REPORT_MONTH` is demo-only by policy, which is
    only durable if the set of code that reads it cannot quietly grow. The
    three readers are: the definition, the pipeline resolver (demo branch), and
    the API resolver (demo branch). A fourth reader is a new fallback path and
    has to be justified here, deliberately."""
    allowed = {
        os.path.join("backend", "app", "config.py"),
        os.path.join("scripts", "report_period.py"),
        os.path.join("backend", "app", "api", "_report_period.py"),
    }
    searched = [
        os.path.join(_ROOT, "backend", "app"),
        os.path.join(_ROOT, "scripts"),
        os.path.join(_ROOT, "dbt_analytics"),
    ]
    found = set()
    for root_dir in searched:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames
                           if d not in {"__pycache__", "target", "dbt_packages"}]
            for name in filenames:
                if not name.endswith((".py", ".sql", ".yml")):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, "r", encoding="utf-8") as handle:
                    if "DEFAULT_REPORT_MONTH" in handle.read():
                        found.add(os.path.relpath(path, _ROOT))
    assert found == allowed, (
        "unexpected DEFAULT_REPORT_MONTH readers: {}".format(sorted(found - allowed)))


# --------------------------------------------------------------------------
# item 2 — an explicit operator period is honoured in both modes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["real", "demo"])
def test_operator_period_overrides_derivation(monkeypatch, mode):
    _set_operator(monkeypatch, "2026-08")
    month, source = rp.resolve_report_month(derived="2026-01", mode=mode)
    assert (month, source) == ("2026-08", rp.SOURCE_OPERATOR)


@pytest.mark.parametrize("mode", ["real", "demo"])
def test_operator_period_resolves_with_no_data_at_all(monkeypatch, mode):
    _set_operator(monkeypatch, "2026-08")
    assert rp.resolve_report_month(derived=None, mode=mode)[0] == "2026-08"


@pytest.mark.parametrize("mode", ["real", "demo"])
def test_a_malformed_operator_period_is_rejected_not_ignored(monkeypatch, mode):
    """Falling back on a typo is the same silent substitution this removes."""
    _set_operator(monkeypatch, "2026-13")
    with pytest.raises(rp.ReportMonthUnresolvedError) as excinfo:
        rp.resolve_report_month(derived="2026-01", mode=mode)
    assert "2026-13" in str(excinfo.value)


def test_an_empty_operator_period_means_unset(monkeypatch):
    _set_operator(monkeypatch, "   ")
    assert rp.operator_report_month() is None


def test_the_settings_field_is_honoured_when_no_env_var_is_set(monkeypatch):
    """The operator may set it in .env rather than the environment."""
    monkeypatch.setattr(settings, "REPORT_MONTH", "2026-09", raising=False)
    assert rp.operator_report_month() == "2026-09"


# --------------------------------------------------------------------------
# item 3 — the interaction convergence created: operator period vs payroll file
# --------------------------------------------------------------------------

def test_a_period_the_payroll_file_does_not_contain_is_an_error():
    with pytest.raises(rp.ReportMonthMismatchError):
        rp.assert_payroll_period_matches(["2026-06", "2026-06"], month="2026-08")


def test_the_mismatch_message_names_both_periods():
    with pytest.raises(rp.ReportMonthMismatchError) as excinfo:
        rp.assert_payroll_period_matches(["2026-06"], month="2026-08")
    message = str(excinfo.value)
    assert "2026-08" in message and "2026-06" in message
    assert "REPORT_MONTH" in message
    # says what the client would otherwise have seen
    assert "0" in message
    assert "عدم تطابق فترة التقرير" in message


def test_a_period_present_in_the_payroll_file_passes():
    assert rp.assert_payroll_period_matches(
        ["2026-06", "2026-07", "2026-08"], month="2026-08") == "2026-08"


def test_no_operator_period_means_no_mismatch_check():
    """Derivation cannot disagree with itself, so there is nothing to check."""
    assert rp.assert_payroll_period_matches(["2026-06"]) is None


def test_an_empty_payroll_file_is_not_a_mismatch():
    """Zero rows is the declared-domain guard's job, not this one's; reporting
    it here too would name a period the file does not have."""
    assert rp.assert_payroll_period_matches([], month="2026-08") == "2026-08"


# --------------------------------------------------------------------------
# item 3 — the same check, wired into ingest
# --------------------------------------------------------------------------

def _payroll_csv(tmp_path, periods):
    path = tmp_path / "payroll.csv"
    pl.DataFrame({
        "payroll_id": ["P{}".format(i) for i in range(len(periods))],
        "payroll_period": list(periods),
        "gross_pay": [1000.0] * len(periods),
    }).write_csv(path)
    return str(path)


def test_ingest_rejects_a_payroll_file_from_a_different_period(tmp_path, monkeypatch):
    import ingest_raw

    _set_operator(monkeypatch, "2026-08")
    path = _payroll_csv(tmp_path, ["2026-06", "2026-06"])
    with pytest.raises(rp.ReportMonthMismatchError) as excinfo:
        ingest_raw.check_payroll_period_matches_report_month(path)
    assert "2026-08" in str(excinfo.value) and "2026-06" in str(excinfo.value)


def test_ingest_accepts_a_payroll_file_covering_the_operator_period(tmp_path, monkeypatch):
    import ingest_raw

    _set_operator(monkeypatch, "2026-08")
    path = _payroll_csv(tmp_path, ["2026-07", "2026-08"])
    assert ingest_raw.check_payroll_period_matches_report_month(path) == "2026-08"


def test_ingest_skips_the_check_for_an_undeclared_payroll_domain(monkeypatch):
    """An undeclared domain points at the sentinel path, which cannot exist."""
    import ingest_raw

    _set_operator(monkeypatch, "2026-08")
    sentinel = "{}/payroll.csv".format(ingest_raw.UNDECLARED_SENTINEL_DIR)
    assert ingest_raw.check_payroll_period_matches_report_month(sentinel) is None


def test_ingest_skips_the_check_when_no_operator_period_is_set(tmp_path):
    import ingest_raw

    path = _payroll_csv(tmp_path, ["2026-06"])
    assert ingest_raw.check_payroll_period_matches_report_month(path) is None


# --------------------------------------------------------------------------
# the API resolver must not label real data with the demo default either
# --------------------------------------------------------------------------

class _DeadConnection:
    """The warehouse has not been built, or was built without a period."""

    def execute(self, *_args, **_kwargs):
        raise RuntimeError("no such table: base_command_center_report_context")


def test_the_api_serves_the_default_in_demo_when_the_mart_is_unreadable(monkeypatch):
    from app.api import _report_period as api_rp

    monkeypatch.setattr(settings, "DATA_MODE", "demo", raising=False)
    assert api_rp.get_report_month(_DeadConnection()) == DEFAULT


def test_the_api_refuses_to_serve_the_default_in_real_mode(monkeypatch):
    from fastapi import HTTPException

    from app.api import _report_period as api_rp

    monkeypatch.setattr(settings, "DATA_MODE", "real", raising=False)
    with pytest.raises(HTTPException) as excinfo:
        api_rp.get_report_month(_DeadConnection())
    assert excinfo.value.status_code == 503
    assert "REPORT_MONTH" in excinfo.value.detail


def test_the_api_honours_an_operator_period_in_real_mode(monkeypatch):
    from app.api import _report_period as api_rp

    monkeypatch.setattr(settings, "DATA_MODE", "real", raising=False)
    monkeypatch.setattr(settings, "REPORT_MONTH", "2026-08", raising=False)
    assert api_rp.get_report_month(_DeadConnection()) == "2026-08"


# --------------------------------------------------------------------------
# the same guard for the other two period-narrowed domains
#
# Attendance and compliance are NOT the payroll case with different columns.
# Payroll can only disagree under an operator override, because derivation
# takes the period FROM payroll. These two disagree under pure derivation: the
# period is the payroll close, and nothing obliges a client's attendance or
# compliance file to be that same month.
# --------------------------------------------------------------------------

def test_attendance_that_misses_the_period_is_rejected():
    with pytest.raises(rp.ReportMonthMismatchError) as excinfo:
        rp.assert_period_is_covered(
            ["2026-07-01", "2026-07-31"], month="2026-08", source="attendance")
    message = str(excinfo.value)
    assert "2026-08" in message and "2026-07" in message
    # names the consequence, not merely the mismatch
    assert "absent on every working day" in message
    assert "غائبين" in message


def test_attendance_partially_covering_the_period_passes():
    """A mid-month upload is legitimate; only zero overlap is the failure."""
    assert rp.assert_period_is_covered(
        ["2026-07-30", "2026-08-01", "2026-08-02"],
        month="2026-08", source="attendance") == "2026-08"


def test_compliance_that_misses_the_period_is_rejected():
    with pytest.raises(rp.ReportMonthMismatchError) as excinfo:
        rp.assert_period_is_covered(["2026-06"], month="2026-08",
                                    source="compliance")
    message = str(excinfo.value)
    assert "missing GOSI, Qiwa and insurance registration" in message


def test_dates_and_month_labels_reduce_to_the_same_period():
    assert rp.normalise_month("2026-08-14") == "2026-08"
    assert rp.normalise_month("2026-08") == "2026-08"
    assert rp.normalise_month("not a date") is None


# --------------------------------------------------------------------------
# resolving the period at ingest, the way the pipeline will resolve it later
# --------------------------------------------------------------------------

def _csv(tmp_path, name, column, values, extra="employee_id"):
    path = tmp_path / name
    pl.DataFrame({extra: ["E{}".format(i) for i in range(len(values))],
                  column: list(values)}).write_csv(path)
    return str(path)


def _files(tmp_path, payroll=None, compliance=None, attendance=None):
    # `compliance` is the GOSI platform table now - the period-bearing one
    # ingest reads for derivation. The split renamed the source; the
    # period logic is unchanged.
    missing = str(tmp_path / "__absent__.csv")
    return {
        "payroll": payroll or missing,
        "compliance_gosi": compliance or missing,
        "attendance": attendance or missing,
    }


def test_ingest_resolves_the_period_from_the_payroll_close(tmp_path):
    import ingest_raw

    files = _files(tmp_path, payroll=_csv(
        tmp_path, "payroll.csv", "payroll_period", ["2026-06", "2026-08", "2026-07"]))
    assert ingest_raw.resolve_ingest_report_month(files) == ("2026-08", rp.SOURCE_DATA)


def test_ingest_falls_back_to_compliance_when_payroll_is_absent(tmp_path):
    import ingest_raw

    files = _files(tmp_path, compliance=_csv(
        tmp_path, "compliance.csv", "period", ["2026-07"]))
    assert ingest_raw.resolve_ingest_report_month(files) == ("2026-07", rp.SOURCE_DATA)


def test_ingest_period_resolution_prefers_the_operator(tmp_path, monkeypatch):
    import ingest_raw

    _set_operator(monkeypatch, "2026-09")
    files = _files(tmp_path, payroll=_csv(
        tmp_path, "payroll.csv", "payroll_period", ["2026-06"]))
    assert ingest_raw.resolve_ingest_report_month(files) == (
        "2026-09", rp.SOURCE_OPERATOR)


def test_ingest_has_no_period_when_nothing_carries_one(tmp_path):
    import ingest_raw

    assert ingest_raw.resolve_ingest_report_month(_files(tmp_path)) == (None, None)


# --------------------------------------------------------------------------
# the coverage gate as ingest calls it
# --------------------------------------------------------------------------

def test_attendance_from_another_month_is_caught_under_pure_derivation(tmp_path):
    """No operator override anywhere. The period is July because that is the
    payroll close; the attendance file is August. Nothing else in the system
    would notice."""
    import ingest_raw

    files = _files(
        tmp_path,
        payroll=_csv(tmp_path, "payroll.csv", "payroll_period", ["2026-07"]),
        attendance=_csv(tmp_path, "attendance.csv", "attendance_date",
                        ["2026-08-03", "2026-08-04"]),
    )
    with pytest.raises(rp.ReportMonthMismatchError) as excinfo:
        ingest_raw.check_period_coverage(files)
    assert "2026-07" in str(excinfo.value) and "2026-08" in str(excinfo.value)


def test_compliance_from_another_month_is_caught_under_pure_derivation(tmp_path):
    import ingest_raw

    files = _files(
        tmp_path,
        payroll=_csv(tmp_path, "payroll.csv", "payroll_period", ["2026-07"]),
        compliance=_csv(tmp_path, "compliance.csv", "period", ["2026-05"]),
    )
    with pytest.raises(rp.ReportMonthMismatchError):
        ingest_raw.check_period_coverage(files)


def test_the_payroll_check_is_vacuous_under_derivation(tmp_path):
    """Not a special case — the period IS payroll's latest close, so membership
    holds by construction. Same rule, no exemption."""
    import ingest_raw

    files = _files(tmp_path, payroll=_csv(
        tmp_path, "payroll.csv", "payroll_period", ["2026-06", "2026-07"]))
    month, source, checked = ingest_raw.check_period_coverage(files)
    assert (month, source, checked) == ("2026-07", rp.SOURCE_DATA, ["payroll"])


def test_all_three_domains_agreeing_passes(tmp_path):
    import ingest_raw

    files = _files(
        tmp_path,
        payroll=_csv(tmp_path, "payroll.csv", "payroll_period", ["2026-08"]),
        compliance=_csv(tmp_path, "compliance.csv", "period", ["2026-08"]),
        attendance=_csv(tmp_path, "attendance.csv", "attendance_date",
                        ["2026-08-03"]),
    )
    month, _, checked = ingest_raw.check_period_coverage(files)
    assert month == "2026-08"
    # `compliance_gosi` since the split: the GOSI export is the
    # period-bearing compliance file, and the one derivation reads.
    assert checked == ["attendance", "compliance_gosi", "payroll"]


def test_no_resolvable_period_means_no_gate(tmp_path):
    """Employees-only onboarding: nothing carries a period, and build_warehouse
    aborts a few steps later. Reporting a mismatch here would be noise."""
    import ingest_raw

    files = _files(tmp_path, attendance=_csv(
        tmp_path, "attendance.csv", "attendance_date", ["2026-08-03"]))
    assert ingest_raw.check_period_coverage(files) == (None, None, [])


def test_an_undeclared_domain_is_skipped_by_the_gate(tmp_path, monkeypatch):
    import ingest_raw

    _set_operator(monkeypatch, "2026-08")
    files = _files(tmp_path, payroll=_csv(
        tmp_path, "payroll.csv", "payroll_period", ["2026-08"]))
    files["attendance"] = "{}/attendance.csv".format(
        ingest_raw.UNDECLARED_SENTINEL_DIR)
    month, _, checked = ingest_raw.check_period_coverage(files)
    assert (month, checked) == ("2026-08", ["payroll"])
