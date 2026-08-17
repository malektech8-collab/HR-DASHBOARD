# -*- coding: utf-8 -*-
"""Every CSV boundary is a TEXT boundary. Types come from the contract.

THE DEFECT, four times over. `pl.read_csv` infers a dtype from the first N
rows. A salary column holding whole numbers early and a decimal later raises

    ComputeError: could not parse `1584.91` as dtype `i64`

The client's file is fine; the reader guessed. It was fixed at the API and CLI
sites, then found again in `ingest_raw` when the first real commit was
rejected, then found again in three period probes where the exception was
being swallowed. Each time the count was "the ones we knew about".

This test replaces the count with a rule.

WHY AST AND NOT REGEX. These calls span lines:

    pl.read_csv(files["employees"], infer_schema_length=0,
                null_values=[""])

A regex either misses the keyword on the continuation line or matches comments
and strings. `ast` parses the call, so a keyword is found wherever it sits.
Verified by a multi-line fixture below.

TWO LIMITS, STATED (ruling 3):

  1. It cannot see a read built indirectly - `getattr(pl, "read_csv")(...)`,
     or a reader passed as a callable. Nothing in this repository does that,
     and if something starts to, this test will not notice.

  2. It checks that `infer_schema_length` is PRESENT, not that it is `0`. A
     non-zero literal is caught by the value check below, but an expression
     (`infer_schema_length=n`) is not evaluated. Presence is the property that
     stops the defect; the value check is opportunistic.

DuckDB's `read_csv_auto` is in scope because it has the identical sampling
sniffer and would reintroduce the same failure by another route.
"""
import ast
import io
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Directories on a pipeline path. `scratch/` is excluded from pytest by
# pytest.ini and is on no path a client's data travels.
_SCANNED = [
    os.path.join(_ROOT, "scripts"),
    os.path.join(_ROOT, "backend", "app"),
]

_GUARD = "infer_schema_length"


def _python_files():
    for base in _SCANNED:
        for folder, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs
                       if d not in {"__pycache__", ".venv", "node_modules"}]
            for name in sorted(files):
                if name.endswith(".py"):
                    yield os.path.join(folder, name)


def _reads_without_guard(source, filename="<src>"):
    """(lineno, why) for every read_csv call missing the guard."""
    found = []
    for node in ast.walk(ast.parse(source, filename)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(
            func, "id", None)
        if name != "read_csv":
            continue
        keyword = next((k for k in node.keywords if k.arg == _GUARD), None)
        if keyword is None:
            found.append((node.lineno, "no {}".format(_GUARD)))
            continue
        # Limit 2: only a literal is checked. An expression is left alone.
        value = keyword.value
        if isinstance(value, ast.Constant) and value.value != 0:
            found.append((node.lineno,
                          "{}={!r}".format(_GUARD, value.value)))
    return found


def _sniffing_sql(source, filename="<src>"):
    """DuckDB's own sampling sniffer, in any string literal."""
    hits = []
    for node in ast.walk(ast.parse(source, filename)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "read_csv_auto" in node.value:
                hits.append(node.lineno)
    return hits


# --------------------------------------------------------------------------
# the rule
# --------------------------------------------------------------------------

def test_every_csv_read_is_a_text_read():
    offenders = []
    for path in _python_files():
        source = io.open(path, encoding="utf-8").read()
        for lineno, why in _reads_without_guard(source, path):
            offenders.append("{}:{}: {}".format(
                os.path.relpath(path, _ROOT), lineno, why))
    assert not offenders, (
        "a CSV read must not infer dtypes - pass infer_schema_length=0 and "
        "type explicitly from the contract:\n  " + "\n  ".join(offenders))


def test_no_duckdb_sniffer_on_a_pipeline_path():
    """`read_csv_auto` samples rows to guess types, exactly as polars did."""
    offenders = []
    for path in _python_files():
        source = io.open(path, encoding="utf-8").read()
        for lineno in _sniffing_sql(source, path):
            offenders.append("{}:{}".format(
                os.path.relpath(path, _ROOT), lineno))
    assert not offenders, (
        "read_csv_auto samples rows to infer types. Name the columns, or read "
        "the file with polars and type it from the contract:\n  "
        + "\n  ".join(offenders))


# --------------------------------------------------------------------------
# the tampers - SP-001. A rule that matches nothing passes forever.
# --------------------------------------------------------------------------

def test_it_catches_a_bare_read():
    assert _reads_without_guard('df = pl.read_csv(path)')


def test_it_catches_one_hidden_among_guarded_siblings():
    """The fifty-first arrives beside fifty correct ones, not alone."""
    source = (
        'a = pl.read_csv(x, infer_schema_length=0)\n'
        'b = pl.read_csv(y, infer_schema_length=0, null_values=[""])\n'
        'c = pl.read_csv(z)\n'
    )
    found = _reads_without_guard(source)
    assert [lineno for lineno, _ in found] == [3]


def test_it_accepts_the_keyword_on_a_CONTINUATION_line():
    """The reason this is AST and not regex - the codebase writes these."""
    source = ('df = pl.read_csv(\n'
              '    files["employees"],\n'
              '    infer_schema_length=0,\n'
              '    null_values=[""],\n'
              ')\n')
    assert _reads_without_guard(source) == []


def test_it_catches_a_NON_ZERO_guard():
    """`infer_schema_length=10000` is the fix people reach for first, and it
    only moves the row at which the guess goes wrong."""
    found = _reads_without_guard('pl.read_csv(p, infer_schema_length=10000)')
    assert found and "10000" in found[0][1]


def test_it_is_not_fooled_by_a_similarly_named_call():
    assert _reads_without_guard('pl.read_parquet(p)') == []
    assert _reads_without_guard('read_csv_but_different(p)') == []


def test_it_catches_the_duckdb_sniffer():
    assert _sniffing_sql(
        'con.execute("SELECT * FROM read_csv_auto(\'x.csv\')")')
    assert _sniffing_sql('q = "read_parquet(\'x.parquet\')"') == []


# --------------------------------------------------------------------------
# the count, pinned
# --------------------------------------------------------------------------

def test_ingest_raw_reads_every_domain_as_text():
    """`ingest_raw` is where a client's file first becomes rows. Pinned by
    count as well as by rule, so a read DISAPPEARING is noticed too - a domain
    that stops being ingested is its own defect."""
    source = io.open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                     encoding="utf-8").read()
    reads = [n for n in ast.walk(ast.parse(source))
             if isinstance(n, ast.Call)
             and (getattr(n.func, "attr", None)
                  or getattr(n.func, "id", None)) == "read_csv"]
    assert len(reads) == 47, (
        "ingest_raw has {} read_csv calls, expected 47 - if a domain was "
        "added or removed, update this number in the same commit".format(
            len(reads)))
    assert _reads_without_guard(source) == []


@pytest.mark.parametrize("column,domain", [
    ("is_saudi", "employees"),
    ("overtime_approved", "attendance"),
    ("sla_breached", "hr_requests"),
    ("contract_authenticated", "compliance"),
    ("escalated", "employee_relations"),
    ("is_critical", "succession_plans"),
])
def test_boolean_columns_are_parsed_not_cast(column, domain):
    """`Utf8 -> Boolean` raises; text booleans need an explicit parse. Pinned
    per column so a future domain cannot quietly reintroduce the bare cast."""
    source = io.open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                     encoding="utf-8").read()
    assert '_bool_col("{}")'.format(column) in source, domain
    assert 'pl.col("{}").cast(pl.Boolean'.format(column) not in source, domain
