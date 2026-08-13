# -*- coding: utf-8 -*-
"""A dbt ref() must never render inside a SQL string literal.

THE DEFECT THIS EXISTS FOR, and its history.

    `'{{ ref('stg_payroll') }}' AS module_key`

    renders the fully-qualified relation name INTO the string, so the value
    becomes '"hr_analytics"."main"."stg_payroll"'. Three Command Center
    modules carried that as their module_key and as their route_path, reaching
    backend/app/api/command_center.py and the frontend.

    It is a find/replace that rewrote bare table names into dbt refs and did
    not stop at FROM clauses.

WHY A STRUCTURAL TEST AND NOT A FIX.

    The corruption was SEEN BEFORE AND ROUTED AROUND. From
    docs/phase-0/phase-0-5a-resolver-report.md, written during cycle 5a:

        "(Note: pre-cycle, `attendance` and `compliance` also had a
        `module_key` mismatch - they queried 'attendance'/'compliance' but the
        freshness mart stores relation-expanded keys like
        '"hr_analytics"."main"."stg_attendance"'; reading
        base_command_center_report_context sidesteps that entirely.)"

    and, in the same report:

        "which also fixes the second latent bug (the attendance/compliance
        `module_key` mismatch) for free by not using `module_key` at all"

    The corrupted values were looked at, described, called fixed, and left in
    the data. They survived into a second set of models and went undetected for
    the life of the project. Fixing the twenty-seven literals again would leave
    the same door open; this test is the door.

DETECTION.

    Naive quote-counting does not work, because a ref CONTAINS quotes -
    `{{ ref('x') }}` - so splitting a line on `'` tears the expression apart.
    (Measured: the first attempt at this fix did exactly that and reported 0
    corrupted literals in a file that had 26.)

    So every `{{ ... }}` span is masked to a single quote-free sentinel FIRST,
    and only then is string state tracked across the masked text.
"""
import os
import re

MODELS = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "dbt_analytics", "models"))

JINJA = re.compile(r"\{\{.*?\}\}", re.S)
IS_REF = re.compile(r"\{\{\s*ref\s*\(")
SENTINEL = "\x00"

# ONLY ref() is a defect here, and the distinction is the whole point.
#
#   {{ var('start_date_str') }}  inside a literal renders a VALUE - a date
#       string - which is the established idiom in this project:
#           WHERE d BETWEEN DATE '{{ var('start_date_str') }}' AND ...
#       Measured: 140 legitimate occurrences. Flagging those would make this
#       test noise, and a noisy test gets deleted.
#
#   {{ ref('stg_payroll') }}     inside a literal renders a RELATION NAME -
#       "hr_analytics"."main"."stg_payroll" - which is never a value anyone
#       wants in a string. There is no correct use of it.


def jinja_inside_string_literals(sql, only_refs=True):
    """Positions (offset, expression) of every ref() inside a SQL string."""
    masked, spans = [], []
    last = 0
    for match in JINJA.finditer(sql):
        masked.append(sql[last:match.start()])
        spans.append((len("".join(masked)), match.group(0), match.start()))
        masked.append(SENTINEL)
        last = match.end()
    masked.append(sql[last:])
    masked = "".join(masked)

    in_string = False
    offenders = []
    index = 0
    while index < len(masked):
        char = masked[index]
        if char == "'":
            # '' inside a string is an escaped quote, not a close-then-open.
            if in_string and index + 1 < len(masked) and masked[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif char == SENTINEL and in_string:
            span = next(s for s in spans if s[0] == index)
            if not only_refs or IS_REF.match(span[1]):
                offenders.append(span)
        elif char == "-" and not in_string and masked[index:index + 2] == "--":
            # A line comment ends string tracking for that line.
            newline = masked.find("\n", index)
            index = len(masked) if newline == -1 else newline
            continue
        index += 1
    return offenders


def _line_of(sql, offset):
    return sql.count("\n", 0, offset) + 1


def test_no_dbt_ref_renders_inside_a_sql_string_literal():
    """The live defect class. A ref inside a literal becomes a relation name."""
    offenders = []
    for dirpath, _dirs, files in os.walk(MODELS):
        for name in sorted(files):
            if not name.endswith(".sql"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                sql = handle.read()
            for _pos, expression, offset in jinja_inside_string_literals(sql):
                offenders.append("{}:{}  {}".format(
                    name, _line_of(sql, offset), expression.strip()))
    assert not offenders, (
        "a dbt expression inside a SQL string literal renders the relation "
        "name into the value:\n  " + "\n  ".join(offenders))


def test_no_dbt_ref_appears_inside_a_sql_comment():
    """The same find/replace, in the harmless half of its blast radius.

    A ref in a comment does not corrupt data - jinja renders it, but nobody
    reads the output. It is included because it is the SAME edit, and because
    a comment reading "Overtime hours without
    "hr_analytics"."main"."stg_payroll" overtime amount" is worse than useless
    to the next person: it tells them the wrong thing about what the code does.
    """
    offenders = []
    for dirpath, _dirs, files in os.walk(MODELS):
        for name in sorted(files):
            if not name.endswith(".sql"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                for number, line in enumerate(handle, start=1):
                    stripped = line.strip()
                    if stripped.startswith("--") and "{{ ref(" in stripped:
                        offenders.append("{}:{}  {}".format(
                            name, number, stripped[:88]))
    assert not offenders, (
        "a dbt ref() in a comment is a find/replace artefact, not a "
        "reference:\n  " + "\n  ".join(offenders))


# --------------------------------------------------------------------------
# the detector itself, on known inputs - it is the whole test, so it is tested
# --------------------------------------------------------------------------

def test_the_detector_flags_the_real_defect():
    sql = "SELECT '{{ ref('stg_payroll') }}' AS module_key FROM x"
    assert len(jinja_inside_string_literals(sql)) == 1


def test_the_detector_flags_a_prefixed_literal():
    """route_path was '/{{ ref('stg_payroll') }}'."""
    sql = "SELECT '/{{ ref('stg_payroll') }}' AS route_path FROM x"
    assert len(jinja_inside_string_literals(sql)) == 1


def test_the_detector_leaves_a_legitimate_ref_alone():
    sql = "SELECT a, 'Missing Project' AS issue FROM {{ ref('stg_payroll') }}"
    assert jinja_inside_string_literals(sql) == []


def test_the_detector_survives_several_literals_on_one_line():
    """The naive rule's failure: quotes elsewhere on the line must not confuse
    it, and a ref contains quotes of its own."""
    sql = ("SELECT 'a' AS x, 'b' AS y, {{ var('report_month') }} AS m "
           "FROM {{ ref('stg_payroll') }} WHERE s IN ('Open', 'Closed')")
    assert jinja_inside_string_literals(sql) == []


def test_the_detector_ignores_a_ref_mentioned_in_a_line_comment():
    sql = "-- see {{ ref('stg_payroll') }}\nSELECT 1"
    assert jinja_inside_string_literals(sql) == []


def test_the_detector_allows_a_var_inside_a_literal():
    """The established idiom, and the reason this test is ref-only.

    A var renders a VALUE. Pinning date windows this way is what the Category F
    work standardised on, and there are 140 of them. A detector that flagged
    those would be noise, and noise gets deleted.
    """
    sql = ("SELECT 1 FROM x WHERE d BETWEEN DATE '{{ var('start_date_str') }}' "
           "AND DATE '{{ var('end_date_str') }}'")
    assert jinja_inside_string_literals(sql) == []
    # ...but the same spans ARE found when refs are not the only concern,
    # which is how we know the quote tracking sees them at all.
    assert len(jinja_inside_string_literals(sql, only_refs=False)) == 2


def test_the_detector_handles_an_escaped_quote_inside_a_literal():
    sql = "SELECT 'it''s fine' AS note FROM {{ ref('stg_payroll') }}"
    assert jinja_inside_string_literals(sql) == []
