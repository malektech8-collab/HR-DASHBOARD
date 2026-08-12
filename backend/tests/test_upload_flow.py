"""P0-2: upload -> stage -> validate -> preview -> commit.

The three proofs this cycle owes:

  (a) a mismatched filename can no longer target another table
  (b) unvalidated data cannot reach silver by any path
  (c) the 17-table typing divergence is gone, because there is one ingest path

Everything else here supports one of those. Synthetic only; no commit is run
against the real warehouse - the commit path is exercised through its guards,
which is where the failures it must produce live.
"""
import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.main import app  # noqa: E402

client = TestClient(app)

EMPLOYEES_CSV = (
    "employee_id,employee_name,nationality,is_saudi,company,department,project,"
    "job_title,job_family,grade,manager_id,cost_center,employment_type,"
    "contract_type,joining_date,termination_date,contract_end_date,status,"
    "basic_salary,housing_allowance,transport_allowance,work_unit,"
    "end_of_service_type\n"
    "EMP001,Ahmad,Saudi,true,ACME,Ops,P1,Analyst,HR,G5,,CC1,Full-time,"
    "Unlimited,2024-01-15,,2027-01-01,Active,12000,3000,1000,,\n"
)


def auth():
    from app.core.security import MOCK_USER_DB

    email = next(iter(MOCK_USER_DB))
    token = client.post("/api/governance/token",
                        data={"username": email,
                              "password": MOCK_USER_DB[email]["hashed_password"]}
                        ).json()["access_token"]
    return {"Authorization": "Bearer {}".format(token)}


@pytest.fixture
def staged():
    """Stage a valid employees CSV; discard it afterwards."""
    ids = []

    def _stage(table="employees", filename="anything.csv", body=EMPLOYEES_CSV):
        response = client.post(
            "/api/data/uploads?table={}".format(table),
            files={"file": (filename, body.encode("utf-8"), "text/csv")},
            headers=auth())
        assert response.status_code == 200, response.text
        ids.append(response.json()["upload_id"])
        return response.json()

    yield _stage
    for upload_id in ids:
        client.delete("/api/data/uploads/{}".format(upload_id), headers=auth())


# --------------------------------------------------------------------------
# (a) the filename cannot target another table
# --------------------------------------------------------------------------

def test_the_target_table_comes_from_the_request_not_the_filename(staged):
    """Before P0-2: table_name = os.path.splitext(filename)[0]. So payroll.csv
    renamed employees.csv replaced the employee master."""
    manifest = staged(table="employees", filename="payroll.csv")
    assert manifest["table"] == "employees"
    assert manifest["original_filename"] == "payroll.csv"
    # the filename is recorded, and it decides nothing
    assert manifest["table"] != os.path.splitext(manifest["original_filename"])[0]


def test_a_table_is_required():
    response = client.post(
        "/api/data/uploads",
        files={"file": ("employees.csv", EMPLOYEES_CSV.encode(), "text/csv")},
        headers=auth())
    assert response.status_code == 400
    assert "no longer inferred from the filename" in response.json()["detail"]


def test_the_table_must_be_contracted():
    response = client.post(
        "/api/data/uploads?table=../../silver/employees",
        files={"file": ("x.csv", EMPLOYEES_CSV.encode(), "text/csv")},
        headers=auth())
    assert response.status_code == 400
    assert "no contract" in response.json()["detail"]


def test_a_weird_filename_creates_no_weird_table(staged):
    """`employees (3).csv` used to create a table called `employees (3)`."""
    manifest = staged(table="employees", filename="employees (3).csv")
    assert manifest["table"] == "employees"


# --------------------------------------------------------------------------
# (b) unvalidated data cannot reach silver by any path
# --------------------------------------------------------------------------

def test_staging_does_not_touch_silver(staged):
    """A staged file is INERT: not in silver, so nothing serves it, and not in
    data/raw either, so no pipeline run picks it up."""
    from app.api.data import get_raw_dir, get_silver_dir

    before_silver = set(os.listdir(get_silver_dir()))
    before_raw = set(os.listdir(get_raw_dir()))
    manifest = staged()
    assert set(os.listdir(get_silver_dir())) == before_silver
    assert set(os.listdir(get_raw_dir())) == before_raw
    # and it really is on disk, in its own place
    import staging

    assert os.path.exists(staging.data_path(manifest["upload_id"]))


def test_no_api_route_writes_to_silver():
    """The structural form of (b). Only scripts/ingest_raw.py may put a file in
    data/silver, because everything that makes a file safe to serve - contract
    validation, derivations, the exception routing - lives there.

    Comments and docstrings are stripped first: the first version of this test
    failed on its own prose ("Nothing here writes silver") sitting near a
    shutil.copy2 that targets data/raw.
    """
    import ast

    api_dir = os.path.join(_ROOT, "backend", "app", "api")
    WRITERS = ("write_parquet", "copyfileobj", "copy", "copy2", "move")
    offenders = []
    for dirpath, _dirs, files in os.walk(api_dir):
        if "__pycache__" in dirpath:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                label = getattr(func, "attr", getattr(func, "id", ""))
                if label == "get_silver_dir":
                    offenders.append("{}: calls get_silver_dir()".format(name))
                if label in WRITERS or label == "open":
                    rendered = ast.unparse(node)
                    if "silver" in rendered.lower():
                        offenders.append("{}: {}".format(name, rendered[:80]))
    assert not offenders, (
        "the API must not write to, or even resolve, data/silver: {}".format(
            offenders))


def test_the_preview_runs_the_same_validator_as_ingest(staged):
    """Not an equivalent one. A preview that agrees with ingest only by
    intention is the defect this cycle removed from the write path."""
    import inspect

    from app.api import data as data_api

    source = inspect.getsource(data_api.preview_upload)
    assert "validate_schema.validate_csv" in source

    manifest = staged()
    preview = client.get("/api/data/uploads/{}".format(manifest["upload_id"]),
                         headers=auth()).json()
    assert preview["row_count"] == 1
    assert preview["can_commit"] is True
    assert preview["columns_missing"] == []


def test_a_reject_violation_blocks_the_commit(staged):
    """One test for the whole cycle: a file the contract rejects cannot be
    committed, so it cannot reach silver."""
    bad = EMPLOYEES_CSV.replace("2024-01-15", "1820-01-15")  # outside the DATE range
    manifest = staged(body=bad)
    preview = client.get("/api/data/uploads/{}".format(manifest["upload_id"]),
                         headers=auth()).json()
    assert preview["rejects"], "the 1b-i DATE range rule should have fired"
    assert preview["can_commit"] is False


def test_preview_is_read_only_and_repeatable(staged):
    from app.api.data import get_silver_dir

    manifest = staged()
    before = set(os.listdir(get_silver_dir()))
    for _ in range(3):
        response = client.get("/api/data/uploads/{}".format(manifest["upload_id"]),
                              headers=auth())
        assert response.status_code == 200
    assert set(os.listdir(get_silver_dir())) == before


# --------------------------------------------------------------------------
# (c) one ingest path
# --------------------------------------------------------------------------

def test_the_second_ingest_implementation_is_gone():
    """compile_csv_to_parquet typed 5 tables where scripts/ingest_raw.py types
    21 - a 17-table divergence including the CONTRACTED hr_requests - and
    carried its own drifted copy of the is_saudi derivation. It is deleted, not
    dormant."""
    source = open(os.path.join(_ROOT, "backend", "app", "api", "data.py"),
                  encoding="utf-8").read()
    assert "def compile_csv_to_parquet" not in source
    assert "derive_column" not in source, (
        "the API must not derive columns; scripts/ingest_raw.py owns that")


def test_the_api_types_no_tables_at_all():
    """The positive form: there is nothing left in the API that knows a
    column's type, so there is nothing left to diverge."""
    source = open(os.path.join(_ROOT, "backend", "app", "api", "data.py"),
                  encoding="utf-8").read()
    for marker in ("str.to_date", "cast(pl.Float64", "cast(pl.Int64",
                   "cast(pl.Boolean", "write_parquet"):
        assert marker not in source, marker


def test_ingest_still_types_every_table_it_did_before():
    """The other half of (c): consolidating on one path must not have dropped
    a table from the path that survived."""
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    typed = re.findall(r'if os\.path\.exists\(files\["(\w+)"\]\):', source)
    assert len(typed) == 21, sorted(typed)
    assert "hr_requests" in typed, (
        "hr_requests is contracted and was one of the 17 the upload path "
        "never typed")
    print("\n[p0-2] tables typed by the single ingest path: {}".format(len(typed)))


# --------------------------------------------------------------------------
# the declaration Category F requires
# --------------------------------------------------------------------------

def test_commit_without_coverage_is_refused_for_a_date_grained_domain(staged):
    manifest = staged(table="attendance", body="attendance_date,employee_id\n")
    response = client.post(
        "/api/data/uploads/{}/commit".format(manifest["upload_id"]),
        json={}, headers=auth())
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "coverage_start" in detail and "coverage_end" in detail
    assert "not an absence" in detail


def test_commit_without_history_is_refused_for_employees(staged):
    manifest = staged(table="employees")
    response = client.post(
        "/api/data/uploads/{}/commit".format(manifest["upload_id"]),
        json={}, headers=auth())
    assert response.status_code == 400
    assert "history_since" in response.json()["detail"]


def test_the_preview_suggests_coverage_but_does_not_apply_it(staged):
    """Ruling 3 of Category F: a suggestion a human confirms is a declaration;
    an inferred value applied silently is not."""
    body = ("attendance_date,employee_id\n"
            "2026-08-03,EMP001\n2026-08-05,EMP001\n")
    manifest = staged(table="attendance", body=body)
    preview = client.get("/api/data/uploads/{}".format(manifest["upload_id"]),
                         headers=auth()).json()
    assert preview["coverage_required"] is True
    assert preview["suggested_coverage_start"] == "2026-08-03"
    assert preview["suggested_coverage_end"] == "2026-08-05"
    # suggested only - the commit still refuses without an explicit declaration
    response = client.post(
        "/api/data/uploads/{}/commit".format(manifest["upload_id"]),
        json={}, headers=auth())
    assert response.status_code == 400


# --------------------------------------------------------------------------
# the .uploaded marker
# --------------------------------------------------------------------------

def test_nothing_writes_an_uploaded_marker():
    """It had a known incident - a stale marker froze employees ingest and
    zeroed four Attendance widgets while every check reported green - and no
    remaining purpose once real mode never loads sample."""
    for relative in ("backend/app/api/data.py", "scripts/ingest_raw.py",
                     "scripts/generate_sample_data.py"):
        text = open(os.path.join(_ROOT, relative), encoding="utf-8").read()
        code = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith("#"))
        assert ".uploaded" not in code, relative


# --------------------------------------------------------------------------
# auth, from the start
# --------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("post", "/api/data/uploads"),
    ("get", "/api/data/uploads"),
    ("get", "/api/data/uploads/whatever"),
    ("delete", "/api/data/uploads/whatever"),
    ("post", "/api/data/uploads/whatever/commit"),
    ("post", "/api/data/refresh"),
])
def test_every_mutating_or_data_bearing_route_requires_auth(method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401, "{} {} is open".format(method, path)


# --------------------------------------------------------------------------
# staging hygiene
# --------------------------------------------------------------------------

def test_staging_is_gitignored():
    ignore = open(os.path.join(_ROOT, ".gitignore"), encoding="utf-8").read()
    assert any(line.strip() in ("data/staging/*", "data/staging/")
               for line in ignore.splitlines()), "client data must not be committable"


def test_nothing_downstream_reads_staging():
    """Staging is inert by construction, not by convention."""
    offenders = []
    for root in ("scripts", "dbt_analytics"):
        for dirpath, _dirs, files in os.walk(os.path.join(_ROOT, root)):
            if "__pycache__" in dirpath or "target" in dirpath:
                continue
            for name in files:
                if not name.endswith((".py", ".sql", ".yml")):
                    continue
                path = os.path.join(dirpath, name)
                if name == "staging.py":
                    continue
                if "data/staging" in open(path, encoding="utf-8").read():
                    offenders.append(os.path.relpath(path, _ROOT))
    assert not offenders, offenders


def test_an_upload_id_cannot_escape_the_staging_root():
    import staging

    with pytest.raises(staging.StagingError):
        staging.data_path("../silver")
