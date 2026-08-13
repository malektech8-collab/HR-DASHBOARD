# -*- coding: utf-8 -*-
"""Command Center reconciliation checks.

WHAT WAS WRONG WITH THE OLD ONES, exactly.

    build_warehouse.py, before this module:

        418:  cc_active_headcount = SELECT active_headcount FROM mart_workforce_kpis
        433:  INSERT INTO command_center_overview_data VALUES (cc_active_headcount, ...)
        ...
        439:  kpi_hc = SELECT active_headcount FROM mart_command_center_overview
        440:  ref_hc = SELECT active_headcount FROM mart_workforce_kpis
        441:  if kpi_hc != ref_hc: raise ValueError(...)

    The overview table was populated FROM the marts the checks then compared it
    against, fifteen lines earlier, in the same connection. Eight of eleven
    checks compared a value with the source it had just been copied from. They
    could not fail. Tampering mart_workforce_kpis with `+ 1` left the pipeline
    green, and "reconciliation PASSED" was quoted as evidence in every report
    this project has produced.

THE RULE THIS MODULE FOLLOWS.

    A check recomputes its figure INDEPENDENTLY, from the base models one layer
    below the mart it is validating - never from the mart, and never from the
    artefact being checked. It then compares that against what the Command
    Center will actually serve.

    So each check answers: does the number on the overview screen still equal
    the number you get by counting the underlying rows yourself?

    That catches a mart aggregation bug, a stale or unrefreshed view, and a
    wrong write into the overview table. The old shape caught none of them.

WHY THE CHECKS LIVE HERE AND NOT INLINE.

    Every check below is tamper-tested in backend/tests/test_reconciliation.py:
    the fixture proves the check passes on correct data AND fails on tampered
    data. That is only possible because they are callable. A check nobody has
    watched fail is not evidence, and this module exists because that lesson
    cost two cycles to learn twice.
"""

NEWLINE = chr(10)

# Absolute tolerance per check. Integers compare exactly; money to the cent;
# percentages to a hair, because they are ROUND()ed upstream.
EXACT = 0.0
CENT = 0.01
FRACTION = 0.001


class ReconciliationError(ValueError):
    """One or more Command Center figures disagree with the underlying rows."""


def _scalar(conn, sql):
    row = conn.execute(sql).fetchone()
    return None if row is None else row[0]


# --------------------------------------------------------------------------
# the eight value checks - each recomputed from BASE models, not from marts
# --------------------------------------------------------------------------

VALUE_CHECKS = [
    {
        "name": "active_headcount",
        "label": "Active Headcount",
        "served": "SELECT active_headcount FROM mart_command_center_overview",
        # mart_workforce_kpis counts DISTINCT employee_id over the active
        # workforce. Counting it here from base_active_workforce is the same
        # business rule reached without going through the mart.
        "independent":
            "SELECT COUNT(DISTINCT employee_id) FROM base_active_workforce",
        "tolerance": EXACT,
    },
    {
        "name": "payroll_cost",
        "label": "Payroll Cost",
        "served": "SELECT payroll_cost FROM mart_command_center_overview",
        "independent":
            "SELECT COALESCE(SUM(gross_pay), 0.0) FROM base_payroll_current",
        "tolerance": CENT,
    },
    {
        "name": "attendance_compliance_pct",
        "label": "Attendance Compliance",
        "served":
            "SELECT attendance_compliance_pct FROM mart_command_center_overview",
        # Category F: the denominator is MEASURED days. COUNT(absence_days)
        # skips the NULLs base_expected_attendance puts on days outside
        # declared coverage, and no measured days at all is NULL, not 1.0.
        # Restating that rule here is deliberate - if the mart ever loses it,
        # this check is what notices.
        "independent": """
            SELECT CASE WHEN COUNT(absence_days) = 0 THEN NULL
                        ELSE 1.0 - (COUNT(CASE WHEN calculated_net_late_minutes > 0
                                                  OR missing_punch_count > 0
                                                  OR absence_days > 0
                                             THEN 1 END)
                                    / CAST(COUNT(absence_days) AS DOUBLE))
                   END
            FROM base_expected_attendance
        """,
        "tolerance": FRACTION,
    },
    {
        "name": "saudization_pct",
        "label": "Saudization",
        "served": "SELECT saudization_pct FROM mart_command_center_overview",
        # Employees with no nationality are excluded from BOTH sides of the
        # ratio rather than counted as non-Saudi - a missing nationality is
        # unknown, not foreign, and Nitaqat banding turns on this figure.
        "independent": """
            SELECT CASE WHEN (saudi + non_saudi) = 0 THEN 0.0
                        ELSE ROUND(100.0 * saudi / (saudi + non_saudi), 2) END
            FROM (
                SELECT
                    COUNT(CASE WHEN is_saudi = TRUE
                                AND nationality IS NOT NULL
                                AND TRIM(nationality) != '' THEN 1 END) AS saudi,
                    COUNT(CASE WHEN is_saudi = FALSE
                                AND nationality IS NOT NULL
                                AND TRIM(nationality) != '' THEN 1 END) AS non_saudi
                FROM base_active_workforce
            )
        """,
        "tolerance": FRACTION,
    },
    {
        "name": "open_er_cases",
        "label": "Open ER Cases",
        "served": "SELECT open_er_cases FROM mart_command_center_overview",
        "independent": """
            SELECT COUNT(*) FROM base_er_case_population
            WHERE case_status IN ('Open', 'In Progress', 'Pending')
        """,
        "tolerance": EXACT,
    },
    {
        "name": "open_requisitions",
        "label": "Open Requisitions",
        "served": "SELECT open_requisitions FROM mart_command_center_overview",
        "independent": """
            SELECT COUNT(*) FROM base_recruitment_requisitions_current
            WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold')
        """,
        "tolerance": EXACT,
    },
    {
        "name": "review_completion_pct",
        "label": "Review Completion",
        "served":
            "SELECT review_completion_pct FROM mart_command_center_overview",
        "independent": """
            SELECT CASE WHEN pop.total = 0 THEN 0.0
                        ELSE ROUND(100.0 * rev.reviewed / pop.total, 2) END
            FROM (SELECT COUNT(*) AS total
                  FROM base_talent_employee_population) pop,
                 (SELECT COUNT(DISTINCT employee_id) AS reviewed
                  FROM base_performance_reviews_current) rev
        """,
        "tolerance": FRACTION,
    },
    {
        "name": "total_active_exceptions",
        "label": "Total Active Exceptions",
        "served":
            "SELECT total_active_exceptions FROM mart_command_center_overview",
        # base_command_center_exception_sources is a UNION ALL of these eight.
        # Summing them separately means a UNION arm that silently stops
        # contributing is caught, which counting the union itself cannot do.
        "independent": """
            SELECT (SELECT COUNT(*) FROM base_command_exception_data_quality)
                 + (SELECT COUNT(*) FROM base_command_exception_workforce)
                 + (SELECT COUNT(*) FROM base_command_exception_payroll)
                 + (SELECT COUNT(*) FROM base_command_exception_attendance)
                 + (SELECT COUNT(*) FROM base_command_exception_compliance)
                 + (SELECT COUNT(*) FROM base_command_exception_er)
                 + (SELECT COUNT(*) FROM base_command_exception_recruitment)
                 + (SELECT COUNT(*) FROM base_command_exception_talent)
        """,
        "tolerance": EXACT,
    },
]


# --------------------------------------------------------------------------
# the module registry checks
#
# These three used to assert `COUNT(*) = 9` and nothing else. They passed for
# the life of the project while three of the nine rows carried a corrupted
# module_key - '"hr_analytics"."main"."stg_payroll"' instead of 'payroll',
# from a find/replace that rewrote SQL string literals into dbt ref() calls -
# and a broken route_path to match. A row count cannot see that. The identity
# of the modules is the thing worth asserting, so that is what these assert.
# --------------------------------------------------------------------------

MODULES = ("attendance", "compliance", "data-quality", "er", "executive",
           "payroll", "recruitment", "talent", "workforce")

REGISTRY_CHECKS = [
    {
        "name": "module_registry",
        "label": "Module registry",
        "sql": "SELECT module_key FROM base_command_center_module_registry",
    },
    {
        "name": "module_freshness",
        "label": "Data freshness rows",
        "sql": "SELECT module_key FROM mart_command_center_data_freshness",
    },
    {
        "name": "module_navigation",
        "label": "Navigation status rows",
        "sql": "SELECT module_key FROM mart_command_center_navigation_status",
    },
]

ROUTE_CHECK = {
    "name": "module_routes",
    "label": "Module route paths",
    "sql": "SELECT module_key, route_path FROM base_command_center_module_registry",
}


def _compare(name, label, served, independent, tolerance):
    if served is None and independent is None:
        return None
    if served is None or independent is None:
        return ("{} ({}): served={!r} but independently computed {!r}. One is "
                "null and the other is not.".format(label, name, served,
                                                    independent))
    if abs(float(served) - float(independent)) > tolerance:
        return ("{} ({}): the Command Center serves {!r}, but recomputing it "
                "from the underlying rows gives {!r}.".format(
                    label, name, served, independent))
    return None


def check_values(conn):
    problems = []
    for check in VALUE_CHECKS:
        problems.append(_compare(
            check["name"], check["label"],
            _scalar(conn, check["served"]),
            _scalar(conn, check["independent"]),
            check["tolerance"]))
    return [p for p in problems if p]


def check_modules(conn):
    problems = []
    for check in REGISTRY_CHECKS:
        keys = sorted(r[0] for r in conn.execute(check["sql"]).fetchall())
        if keys != sorted(MODULES):
            missing = sorted(set(MODULES) - set(keys))
            unexpected = sorted(set(keys) - set(MODULES))
            problems.append(
                "{} ({}): expected the nine module keys. missing={} "
                "unexpected={}.".format(check["label"], check["name"],
                                        missing, unexpected))
    rows = conn.execute(ROUTE_CHECK["sql"]).fetchall()
    wrong = sorted("{} -> {}".format(k, p) for k, p in rows
                   if p != "/{}".format(k))
    if wrong:
        problems.append(
            "{} ({}): a route must be '/' + its module key. {}".format(
                ROUTE_CHECK["label"], ROUTE_CHECK["name"], wrong))
    return problems


def run(conn):
    """Raise ReconciliationError listing EVERY disagreement, not just the first.

    Reporting one failure at a time turns a broken pipeline into a sequence of
    reruns. The whole picture is usually the diagnosis.
    """
    problems = check_values(conn) + check_modules(conn)
    if problems:
        raise ReconciliationError(
            "Command Center reconciliation FAILED ({} of {} checks):".format(
                len(problems), len(VALUE_CHECKS) + len(REGISTRY_CHECKS) + 1)
            + NEWLINE + NEWLINE.join("  - " + p for p in problems))
    return len(VALUE_CHECKS) + len(REGISTRY_CHECKS) + 1
