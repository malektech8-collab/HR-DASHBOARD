# -*- coding: utf-8 -*-
"""Organisational dimensions: location, project, department.

WHY THIS FILE EXISTS, precisely.

  The demo maps each site to a project of the same name. That identity mapping
  is what keeps the byte-identity gate meaningful across the rename - every
  GROUP BY key downstream is unchanged - but it means the DEMO NEVER EXERCISES
  A REAL ROLLUP. Several sites under one project, a site with no project, a
  site absent from the reference file: none of those appear in demo data, and
  a gate that cannot see a case cannot defend it.

  So the interesting behaviour is tested here, on a fixture warehouse built in
  a temp directory, rather than left to a demo that would have to change its
  own figures to show it.
"""
import os
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402


# --------------------------------------------------------------------------
# a real hierarchy: 4 sites, 2 projects, 1 unassigned, 1 missing from the file
# --------------------------------------------------------------------------

# location, project, region, phase.  "" is a site the organisation runs that
# belongs to no project - a flat-site case inside a hierarchical one.
LOCATIONS = [
    ("RUH-P1", "Riyadh Tower", "Central", "Phase 1"),
    ("RUH-P2", "Riyadh Tower", "Central", "Phase 2"),
    ("JED-1", "Jeddah Depot", "Western", "Phase 1"),
    ("HQ", "", "Central", ""),
]

# DEPARTMENT SPANS SITES AND PROJECTS, on purpose. Safety is a cross-cutting
# function: it exists at every site and belongs to none of them. If department
# were nested under location - as the employees contract wrongly claimed until
# this cycle - Safety@RUH-P1 and Safety@JED-1 would be different departments.
#
# YANBU-9 is deliberately absent from LOCATIONS: a site used in the data that
# the client never listed.
EMPLOYEES = [
    ("E1", "Safety", "RUH-P1", True),
    ("E2", "Safety", "RUH-P2", False),
    ("E3", "Safety", "JED-1", True),
    ("E4", "Ops", "RUH-P1", True),
    ("E5", "Ops", "HQ", False),
    ("E6", "Ops", "YANBU-9", True),
]


def _values(rows):
    def cell(v):
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        return "'{}'".format(v)
    return ", ".join("({})".format(", ".join(cell(v) for v in row))
                     for row in rows)


@pytest.fixture
def warehouse(tmp_path):
    """A warehouse with the reference join, built the way the models build it."""
    db = duckdb.connect(str(tmp_path / "fixture.duckdb"))
    db.execute("CREATE TABLE locations_src(location VARCHAR, project VARCHAR, "
               "region VARCHAR, phase VARCHAR)")
    db.execute("INSERT INTO locations_src VALUES " + _values(LOCATIONS))
    db.execute("CREATE TABLE employees_src(employee_id VARCHAR, "
               "department VARCHAR, location VARCHAR, is_saudi BOOLEAN)")
    db.execute("INSERT INTO employees_src VALUES " + _values(EMPLOYEES))
    # base_row_project, verbatim in shape: empty string normalised to NULL so
    # "" and "not supplied" cannot become two buckets.
    db.execute("""
        CREATE VIEW base_row_project AS
        SELECT l.location, NULLIF(TRIM(l.project), '') AS project,
               l.region, l.phase
        FROM locations_src l
    """)
    # stg_employees, verbatim in shape: LEFT JOIN, so an unmatched site keeps
    # its row and its measures.
    db.execute("""
        CREATE VIEW stg_employees AS
        SELECT e.*, p.project
        FROM employees_src e
        LEFT JOIN base_row_project p ON e.location = p.location
    """)
    yield db
    db.close()


# --------------------------------------------------------------------------
# the rollup the demo cannot show
# --------------------------------------------------------------------------

def test_several_sites_roll_up_into_one_project(warehouse):
    rows = dict(warehouse.execute(
        "SELECT project, COUNT(*) FROM stg_employees "
        "WHERE project IS NOT NULL GROUP BY 1").fetchall())
    # RUH-P1 (2 people) + RUH-P2 (1) = Riyadh Tower (3)
    assert rows == {"Riyadh Tower": 3, "Jeddah Depot": 1}


def test_a_site_with_no_project_has_no_project(warehouse):
    """An empty project is NULL, not a bucket called 'Unassigned'.

    HQ belongs to no project because this organisation genuinely has none for
    it. Rendering that as a pie slice would make an absence look like a
    grouping - the family of defect this whole cycle exists to remove.
    """
    project = warehouse.execute(
        "SELECT project FROM stg_employees WHERE location = 'HQ'").fetchone()[0]
    assert project is None


def test_an_unmatched_site_keeps_its_row_and_its_measures(warehouse):
    """YANBU-9 is on an employee but absent from the locations file.

    The row must survive. Dropping it would silently change a headcount, which
    is a worse failure than the one being fixed.
    """
    total = warehouse.execute("SELECT COUNT(*) FROM stg_employees").fetchone()[0]
    assert total == len(EMPLOYEES), "no row may be lost to the join"
    project = warehouse.execute(
        "SELECT project FROM stg_employees WHERE location = 'YANBU-9'").fetchone()[0]
    assert project is None


def test_the_unmatched_site_is_reportable_by_name(warehouse):
    """mart_unmatched_locations' shape: the client gets the site to fix."""
    missing = warehouse.execute("""
        SELECT DISTINCT e.location
        FROM stg_employees e
        LEFT JOIN base_row_project p ON e.location = p.location
        WHERE p.location IS NULL
    """).fetchall()
    assert missing == [("YANBU-9",)]


def test_project_totals_exclude_the_unmatched_but_headcount_does_not(warehouse):
    """The distinction that makes the exception honest.

    6 people. 4 are in a project, 2 are not (HQ has no project, YANBU-9 is not
    in the file). A dashboard that showed 6 in the by-project breakdown would
    be inventing; one that showed a headcount of 4 would be losing people.
    """
    headcount = warehouse.execute(
        "SELECT COUNT(*) FROM stg_employees").fetchone()[0]
    in_project = warehouse.execute(
        "SELECT COUNT(*) FROM stg_employees WHERE project IS NOT NULL").fetchone()[0]
    assert (headcount, in_project) == (6, 4)


# --------------------------------------------------------------------------
# department is orthogonal - the ruling, as a test
# --------------------------------------------------------------------------

def test_a_department_spans_projects_and_stays_one_department(warehouse):
    """Safety is at three sites across two projects and one no-project site.

    The employees contract asserted a nested Location -> Department -> Work
    Unit hierarchy until this cycle. Under that reading this would be three
    departments. It is one.
    """
    departments = warehouse.execute(
        "SELECT COUNT(DISTINCT department) FROM stg_employees "
        "WHERE department = 'Safety'").fetchone()[0]
    spread = warehouse.execute(
        "SELECT COUNT(DISTINCT location) FROM stg_employees "
        "WHERE department = 'Safety'").fetchone()[0]
    assert (departments, spread) == (1, 3)


def test_department_is_not_a_column_on_the_locations_contract():
    """Orthogonal means the reference dimension does not know about it."""
    assert "department" not in [c["name"] for c in cs.columns("locations")]


# --------------------------------------------------------------------------
# the contracts, after the rename
# --------------------------------------------------------------------------

@pytest.mark.parametrize("table",
                         ["employees", "payroll", "attendance", "hr_requests"])
def test_every_fact_table_carries_its_own_location(table):
    """Facts do NOT inherit the employee's site.

    An employee based at Site 1 booking a month of payroll at Site 2 is real,
    and collapsing that into their home site would invent an attribution the
    source never made.
    """
    names = [c["name"] for c in cs.columns(table)]
    assert "location" in names
    assert "project" not in names, "project is a reference dimension now"


def test_only_the_locations_contract_declares_a_project():
    carriers = [t for t in cs.available_tables()
                if "project" in [c["name"] for c in cs.columns(t)]]
    assert carriers == ["locations"]


def test_location_is_required_and_project_is_not():
    """A flat-site organisation has locations and no projects at all."""
    required = cs.required_columns("locations")
    assert required == ["location"]


def test_the_locations_contract_warns_about_re_assignment():
    """The SCD limitation must reach the CLIENT, not just the plan doc.

    Effective-dated locations are out of scope. That means re-assigning a site
    silently re-groups months already reported - something a client has to be
    TOLD before they upload, not discover in a board pack afterwards.
    """
    spec = cs.load_schema("locations")
    for locale in ("en", "ar"):
        text = spec.get("instructions_{}".format(locale)) or ""
        assert text, "locations must carry client-facing instructions"
    english = spec["instructions_en"]
    assert "no history" in english
    assert "already reported" in english

    described = cs.describe("locations", "ar")
    assert described["instructions"], "the API must serve it, in both locales"


def test_work_unit_records_the_correction_it_received():
    """The wrong text is quoted beside the right one, not silently replaced."""
    work_unit = next(c for c in cs.columns("employees")
                     if c["name"] == "work_unit")
    description = work_unit["description_en"]
    assert "previously" in description
    assert "Location -> Department -> Work Unit" in description, \
        "the original claim must survive so the correction is checkable"
    assert "ORTHOGONAL" in description
