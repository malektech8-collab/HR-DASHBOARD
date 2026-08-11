"""The coverage surface: partial coverage is visible, and it is not a suppression.

Category F made the numbers honest. This makes them explicable. The rulings
pinned here:

  * `coverage_notes` is a SIBLING of `suppressed`, never a fourth reason code
    inside it. `suppressed` carries every P0 guarantee from step 2b; if it ever
    also meant "shown but qualified", a reader could no longer infer absence
    from a suppression, and the damage would be invisible until somebody
    trusted the wrong number.
  * covered_days counts WORKING DAYS INSIDE THE DECLARED WINDOW, not days with
    rows.
  * a note fires only when covered < expected.

Synthetic only.
"""
import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.api import _provenance as p  # noqa: E402

REGISTRY = {
    "domains": {
        "contracted": {"employees": ["employees"], "attendance": ["attendance"]},
        "uncontracted": {},
    },
    "marts": {
        "mart_attendance_kpis": {
            "mode": "column",
            "columns": {"absence_days": ["attendance", "employees"]},
        },
        "mart_attendance_by_project": {"mode": "payload",
                                       "domains": ["attendance"]},
        "mart_workforce_kpis": {"mode": "column",
                                "columns": {"active_headcount": ["employees"]}},
    },
}

PARTIAL = p.Coverage("attendance", "2026-08-01", "2026-08-07", 6, 27)
FULL = p.Coverage("attendance", "2026-06-01", "2026-06-30", 26, 26)


def prov(*provided, coverage=None):
    return p.Provenance(provided=set(provided), registry=REGISTRY,
                        data_mode="real",
                        coverage={"attendance": coverage} if coverage else {})


# --------------------------------------------------------------------------
# the noise rule
# --------------------------------------------------------------------------

def test_partial_coverage_emits_a_note():
    provenance = prov("attendance", "employees", coverage=PARTIAL)
    provenance.note_coverage("mart_attendance_by_project")
    block = provenance.coverage_block()
    assert len(block) == 1
    item = block[0]
    assert (item.covered_days, item.expected_days) == (6, 27)
    assert "6 of 27 working days" in item.message_en
    assert "2026-08-01" in item.message_en and "2026-08-07" in item.message_en


def test_full_coverage_emits_nothing():
    """'27 of 27 working days' on every card trains people to stop reading
    notes, and it is also what keeps demo byte-identical."""
    provenance = prov("attendance", "employees", coverage=FULL)
    provenance.note_coverage("mart_attendance_by_project")
    assert provenance.coverage_block() == []
    assert provenance.any_coverage_note is False


def test_a_mart_that_does_not_read_the_domain_gets_no_note():
    provenance = prov("attendance", "employees", coverage=PARTIAL)
    provenance.note_coverage("mart_workforce_kpis")
    assert provenance.coverage_block() == []


def test_column_mode_marts_are_noted_through_their_columns():
    provenance = prov("attendance", "employees", coverage=PARTIAL)
    provenance.note_coverage("mart_attendance_kpis")
    assert len(provenance.coverage_block()) == 1


def test_the_note_is_recorded_once_per_domain():
    provenance = prov("attendance", "employees", coverage=PARTIAL)
    for _ in range(3):
        provenance.note_coverage("mart_attendance_by_project")
        provenance.note_coverage("mart_attendance_kpis")
    assert len(provenance.coverage_block()) == 1


# --------------------------------------------------------------------------
# it is not a suppression
# --------------------------------------------------------------------------

def test_a_partially_covered_payload_is_still_SERVED():
    """The whole point of the sibling block: qualified, not withheld."""
    provenance = prov("attendance", "employees", coverage=PARTIAL)
    assert provenance.payload("mart_attendance_by_project") is True
    provenance.note_coverage("mart_attendance_by_project")
    assert provenance.block() == [], "a coverage note must not suppress anything"
    assert provenance.coverage_block(), "and it must still be explained"


def test_an_absent_domain_gets_ONE_explanation_not_two():
    """With attendance absent, `suppressed` already says so. A coverage note
    beside it would be a second explanation of the same emptiness."""
    provenance = prov("employees", coverage=PARTIAL)
    assert provenance.payload("mart_attendance_by_project") is False
    provenance.note_coverage("mart_attendance_by_project")
    assert len(provenance.block()) == 1
    assert provenance.coverage_block() == []


def test_the_two_blocks_are_separate_keys_on_the_response():
    from app.schemas.attendance import AttendanceByProjectResponse

    fields = AttendanceByProjectResponse.model_fields
    assert "suppressed" in fields and "coverage_notes" in fields
    assert fields["suppressed"].annotation != fields["coverage_notes"].annotation


# --------------------------------------------------------------------------
# the collision that Python accepted and TypeScript caught
# --------------------------------------------------------------------------

def test_the_succession_coverage_field_still_holds_succession_coverage():
    """The new block was first called `coverage`, which collided with
    SuccessionCoverageResponse's own field. Python took the LAST definition and
    silently replaced the succession list; the whole suite still passed. Renamed
    to `coverage_notes`; this pins the field it displaced."""
    from app.schemas.talent import SuccessionCoverageItem, SuccessionCoverageResponse

    annotation = str(SuccessionCoverageResponse.model_fields["coverage"].annotation)
    assert SuccessionCoverageItem.__name__ in annotation, annotation
    assert "coverage_notes" in SuccessionCoverageResponse.model_fields


def test_no_response_model_has_a_field_shadowed_by_a_later_definition():
    """The general form. A duplicate field name in a Pydantic model is silently
    resolved in favour of the later one, so it cannot be caught by reading the
    field list - only by reading the source."""
    import glob

    offenders = []
    for path in glob.glob(os.path.join(_ROOT, "backend", "app", "schemas", "*.py")):
        current, seen = None, set()
        for line in open(path, encoding="utf-8"):
            klass = re.match(r"^class (\w+)\(", line)
            if klass:
                current, seen = klass.group(1), set()
                continue
            field = re.match(r"^    (\w+)\s*:", line)
            if current and field:
                if field.group(1) in seen:
                    offenders.append("{}.{}".format(current, field.group(1)))
                seen.add(field.group(1))
    assert not offenders, "fields silently shadowed: {}".format(offenders)


# --------------------------------------------------------------------------
# the definition most likely to be "corrected" by a future reader
# --------------------------------------------------------------------------

def test_covered_days_counts_declared_days_not_days_with_rows():
    """Ruling 2 of this cycle, pinned with its reasoning.

    A day INSIDE the declared window with no attendance row is a real absence -
    that is Category F's central inversion. Counting rows here would treat it
    as missing coverage instead, double-counting the very thing that design
    separated, and quietly shrinking the window back to whatever arrived.
    """
    with open(os.path.join(_ROOT, "dbt_analytics", "models", "marts",
                           "mart_attendance_coverage.sql"), encoding="utf-8") as f:
        sql = f.read()
    assert "coverage_status = 'covered'" in sql, (
        "covered_days must be counted from coverage_status, which is the "
        "DECLARED window - not from attendance_date, which is rows")
    assert "attendance_date" not in sql, (
        "counting rows would double-count what Category F separated: a day "
        "inside the window with no row is an absence, not missing coverage")
    assert "DISTINCT" in sql, (
        "the base model is one row per employee per day; this is about days")


def test_the_coverage_mart_is_registered():
    """A new surface must not bypass provenance. This is already enforced by
    test_every_api_served_mart_is_mapped; asserted here so the reason is
    written down next to the surface it protects."""
    import yaml

    with open(os.path.join(_ROOT, "config", "metric_provenance.yml"),
              encoding="utf-8") as f:
        registry = yaml.safe_load(f)
    entry = registry["marts"]["mart_attendance_coverage"]
    assert entry["mode"] == "payload"
    assert entry["domains"] == ["attendance"]


def test_the_api_reads_the_coverage_mart_by_name():
    """The literal has to appear in the API source, or the registry-coverage
    test cannot see the read and the mart would drop out of provenance."""
    with open(os.path.join(_ROOT, "backend", "app", "api", "_provenance.py"),
              encoding="utf-8") as f:
        assert "FROM mart_attendance_coverage" in f.read()


# --------------------------------------------------------------------------
# message shape
# --------------------------------------------------------------------------

def test_the_message_is_bilingual_with_western_digits():
    """One convention across every bilingual message in the product."""
    item = PARTIAL.as_dict()
    assert "يغطي" in item["message_ar"]        # يغطي
    assert "6" in item["message_ar"] and "27" in item["message_ar"]
    assert not any(ch in item["message_ar"] for ch in "٠١٢٣٤٥٦٧٨٩")
    assert "إلى" in item["message_ar"]              # إلى


def test_coverage_pct_is_carried_but_the_text_uses_day_counts():
    """A percentage invites comparison the declaration does not support, so it
    stays in the payload and out of the sentence."""
    item = PARTIAL.as_dict()
    assert item["coverage_pct"] == pytest.approx(22.2)
    assert "22" not in item["message_en"]


def test_a_missing_coverage_mart_means_no_notes_not_an_error():
    """An older warehouse serves every figure exactly as it did before."""
    class _NoMart:
        def execute(self, *_a, **_kw):
            raise RuntimeError("no such table: mart_attendance_coverage")

    assert p.domain_coverage(_NoMart()) == {}
