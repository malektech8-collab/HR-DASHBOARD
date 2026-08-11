"""Phase 2 P0-3 step 2a.5: no date window may be pinned to a repo literal.

The generalised form of `test_the_demo_default_has_exactly_three_readers`.
That test pins one constant by name; this one pins the whole class, by shape,
so the next instance is caught mechanically rather than by someone noticing.

The class, stated once:

    a var declared in dbt_project.yml with a DATE-SHAPED value,
    consumed by at least one model,
    and NOT overridden in build_warehouse.py's dbt_vars
      => every client's window is a period this repository chose.

Three instances of it had already shipped when this test was written:

  * `report_month` itself, whose last fallback was settings.DEFAULT_REPORT_MONTH
  * `start_date_str` / `end_date_str`, the attendance window — and this one
    needed no operator override to go wrong. Any client whose payroll close
    was not 2026-06 got a correctly resolved report_month AND attendance
    filtered to June by `base_attendance_current`, plus a June calendar out of
    `base_expected_attendance`.
  * `trend_m1` / `trend_m1_end` / `trend_m2` / `trend_m2_end`, whose own
    dbt_project.yml comment said they were "to be replaced by report_month-
    relative derivation in the resolver cycle (5a)" — which did not happen.

Detection is by VALUE SHAPE, not by name. A name-based rule only finds vars
someone already thought to call a date.
"""
import os
import re

import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PROJECT_YML = os.path.join(_ROOT, "dbt_analytics", "dbt_project.yml")
_MODELS_DIR = os.path.join(_ROOT, "dbt_analytics", "models")
_BUILD_WAREHOUSE = os.path.join(_ROOT, "scripts", "build_warehouse.py")

# YYYY-MM or YYYY-MM-DD.
_DATE_SHAPED = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-\d{2})?$")


def _declared_vars():
    with open(_PROJECT_YML, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle).get("vars") or {}


def _date_shaped_vars():
    return {name: value for name, value in _declared_vars().items()
            if isinstance(value, str) and _DATE_SHAPED.match(value.strip())}


def _consumed_vars():
    """Every var name any model actually reads."""
    consumed = {}
    pattern = re.compile(r"var\(\s*['\"]([A-Za-z0-9_]+)['\"]")
    for dirpath, dirnames, filenames in os.walk(_MODELS_DIR):
        dirnames[:] = [d for d in dirnames if d not in {"target", "dbt_packages"}]
        for name in filenames:
            if not name.endswith(".sql"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, "r", encoding="utf-8") as handle:
                for var_name in pattern.findall(handle.read()):
                    consumed.setdefault(var_name, set()).add(
                        os.path.relpath(path, _MODELS_DIR).replace("\\", "/"))
    return consumed


def _overridden_vars():
    """Keys the pipeline passes through --vars.

    Raw-text parse of the `dbt_vars = {...}` literal, the same technique the
    provenance registry's reason test uses. Importing build_warehouse would
    mean running the pipeline; the dict is local to the function.
    """
    with open(_BUILD_WAREHOUSE, "r", encoding="utf-8") as handle:
        source = handle.read()
    start = source.index("dbt_vars = {")
    depth = 0
    for offset in range(start, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                block = source[start:offset + 1]
                break
    else:  # pragma: no cover - unbalanced literal would be a syntax error
        raise AssertionError("could not find the end of the dbt_vars literal")
    # keys only: `"name":` at the start of a line, so nested .get() defaults
    # and dict literals inside values cannot be mistaken for keys
    return set(re.findall(r'^\s{8}"([A-Za-z0-9_]+)":', block, re.MULTILINE))


def test_no_date_shaped_var_reaches_a_model_as_a_repo_literal():
    date_shaped = _date_shaped_vars()
    consumed = _consumed_vars()
    overridden = _overridden_vars()

    pinned = {}
    for name in sorted(date_shaped):
        if name in consumed and name not in overridden:
            pinned[name] = sorted(consumed[name])

    print("\n[dbt vars] date-shaped declared : {}".format(len(date_shaped)))
    print("[dbt vars] of those, consumed   : {}".format(
        len([n for n in date_shaped if n in consumed])))
    print("[dbt vars] of those, overridden : {}".format(
        len([n for n in date_shaped if n in consumed and n in overridden])))
    for name in sorted(date_shaped):
        state = ("PINNED  " if name in pinned else
                 "ok      " if name in consumed else "unused  ")
        print("[dbt vars]   {} {:<20} = {}".format(state, name, date_shaped[name]))

    assert not pinned, (
        "date-shaped dbt vars consumed by a model but never overridden by the "
        "pipeline — each one pins a client's window to a literal in this "
        "repository: {}".format(pinned))


def test_date_shaped_vars_that_nothing_reads_are_named():
    """Not a failure, but it should not be silent.

    An overridden var no model consumes is dead weight, and a var that looks
    live in build_warehouse.py while nothing reads it is how someone concludes
    a window is derived when it is not. `talent_month_start` is the current
    case: passed every run, read by nothing (only `talent_month_end` is).
    """
    date_shaped = _date_shaped_vars()
    consumed = _consumed_vars()
    unread = sorted(n for n in date_shaped if n not in consumed)
    print("\n[dbt vars] declared but read by no model: {}".format(unread))
    assert unread == ["talent_month_start"], (
        "the set of unread date-shaped vars changed: {}".format(unread))


def test_the_attendance_window_is_the_reporting_period(monkeypatch):
    """The specific pin, stated as an equality rather than a presence check.

    `start_date_str`/`end_date_str` must BE `report_month_start`/`_end` — the
    same resolved period under the names the two attendance models read, not a
    second derivation that could drift from it.
    """
    with open(_BUILD_WAREHOUSE, "r", encoding="utf-8") as handle:
        source = handle.read()
    assert '"start_date_str": cc_report_month_start,' in source
    assert '"end_date_str": cc_report_month_end,' in source


def test_the_trend_anchors_are_the_two_months_before_the_period():
    """report_month minus 2 and minus 1, across a year boundary."""
    import calendar

    def month_before(year, month, offset):
        index = year * 12 + (month - 1) - offset
        y, m = divmod(index, 12)
        m += 1
        return "{:04d}-{:02d}".format(y, m), "{:04d}-{:02d}-{:02d}".format(
            y, m, calendar.monthrange(y, m)[1])

    # demo: the derivation must reproduce the committed literals exactly,
    # which is what keeps the demo gate byte-identical
    assert month_before(2026, 6, 2) == ("2026-04", "2026-04-30")
    assert month_before(2026, 6, 1) == ("2026-05", "2026-05-31")
    # year boundary, and a February whose length the old literals never had
    assert month_before(2026, 1, 2) == ("2025-11", "2025-11-30")
    assert month_before(2026, 1, 1) == ("2025-12", "2025-12-31")
    assert month_before(2028, 4, 2) == ("2028-02", "2028-02-29")
