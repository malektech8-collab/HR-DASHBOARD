import csv
import datetime
import io
import os
import sys
import subprocess
import shutil
import polars as pl
from typing import List, Dict, Any, Optional
from fastapi import (APIRouter, Body, Depends, File, HTTPException, Query,
                     UploadFile, status)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

import duckdb

from app.config import settings
from app.db.duckdb_client import get_db_connection

# P0-2 step 1c. Upload and refresh MUTATE client data and were reachable
# unauthenticated, while /api/governance/* has required a token since it was
# written. This makes the mutating data routes consistent with that; it does
# not touch the JWT layer itself, which is logged as Phase 3 hardening
# (docs/phase-2/p0-2-upload-validation-plan.md).
from app.api.dependencies.auth import get_current_user

router = APIRouter()

# Directory definitions relative to backend app
SAMPLE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/sample"))
SILVER_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/silver"))

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scripts"))
CONTRACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/contracts"))

# For production container environment, default to /app/data/silver, /app/data/sample, /app/scripts
CONTAINER_SILVER_DIR = "/app/data/silver"
CONTAINER_SAMPLE_DIR = "/app/data/sample"
CONTAINER_SCRIPTS_DIR = "/app/scripts"
CONTAINER_CONTRACTS_DIR = "/app/data/contracts"

def get_silver_dir() -> str:
    if os.path.exists(CONTAINER_SILVER_DIR):
        return CONTAINER_SILVER_DIR
    os.makedirs(SILVER_DATA_DIR, exist_ok=True)
    return SILVER_DATA_DIR

def get_sample_dir() -> str:
    if os.path.exists(CONTAINER_SAMPLE_DIR):
        return CONTAINER_SAMPLE_DIR
    return SAMPLE_DATA_DIR

def get_scripts_dir() -> str:
    if os.path.exists(CONTAINER_SCRIPTS_DIR):
        return CONTAINER_SCRIPTS_DIR
    return SCRIPTS_DIR

def get_contracts_dir() -> str:
    if os.path.exists(CONTAINER_CONTRACTS_DIR):
        return CONTAINER_CONTRACTS_DIR
    return CONTRACTS_DIR

class TemplateInfo(BaseModel):
    name: str
    filename: str
    description: str
    available: bool = True
    unavailable_reason: Optional[str] = None

class RefreshReport(BaseModel):
    status: str
    return_code: int
    stdout: str
    stderr: str
    execution_time_seconds: float

# compile_csv_to_parquet WAS HERE, and is deleted rather than fixed.
#
# It was a SECOND implementation of scripts/ingest_raw.py's typing, with a
# comment claiming the two must "behave identically". Measured, they did not:
# ingest_raw types 21 tables and this typed 5, so 17 - including the
# CONTRACTED hr_requests - reached data/silver as all-strings. It also carried
# its own copy of the is_saudi derivation, which had already drifted:
# ingest_raw RAISES when neither is_saudi nor nationality is present, this
# silently skipped.
#
# Fixing it would mean maintaining the 21-table type map twice. Deleting it
# means the upload path has no opinion about types at all: a committed file
# goes to data/raw/ and scripts/ingest_raw.py does the work, once.

# --- Template generation (Phase 1 hotfix) -------------------------------------
# The template served to a client MUST NOT contain data. Before this change the
# endpoint returned data/sample/{table}_sample.csv verbatim — fabricated employee
# records (names, salaries, national context) presented as an onboarding artefact.
# That violated the project principle "never present a fabricated number as real".
#
# Interim behaviour: a header-only CSV generated from the domain's contract.
# Correct canonical column names, zero data rows. The full bilingual Excel
# generator (instructions sheet, dropdowns, example rows) is the Phase 1
# deliverable and replaces this.
#
# Column names come from the shared canonical-schema loader (scripts/canonical_schema.py).

CRLF = chr(13) + chr(10)



def _canonical_schema():
    """Import the shared canonical-schema loader from scripts/.

    Phase 1a placement: the loader lives in scripts/ because the backend image
    build context is ./backend and cannot see a repo-root package. compose
    bind-mounts ./scripts to /app/scripts. Promotion to an hr_schema/ package
    is cycle 1b.
    """
    scripts_dir = get_scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import canonical_schema
    return canonical_schema


def _contract_columns(table: str) -> Optional[List[str]]:
    """Canonical column names for a table, or None when no contract exists.

    Returning None (rather than falling back to sample data) is deliberate: a
    domain without a contract has no template, and serving fabricated rows in
    its place is the exact defect this endpoint no longer has.
    """
    cs = _canonical_schema()
    if not cs.has_schema(table):
        return None
    try:
        return cs.column_names(table)
    except cs.SchemaNotFoundError:
        return None


def _header_only_csv(columns: List[str]) -> str:
    """One CRLF-terminated header row. No data rows, ever."""
    buf = io.StringIO()
    # CRLF: Excel on Windows is the primary consumer of these templates.
    csv.writer(buf, lineterminator=CRLF).writerow(columns)
    return buf.getvalue()


@router.get("/templates")
def get_templates(
    name: Optional[str] = Query(None, description="Optional name of the template to download"),
    locale: str = Query("en", description="Label locale: en or ar"),
):
    """
    Download a data template or list available data templates.

    The catalogue is DERIVED from data/contracts/. A template exists if and
    only if a contract exists — the invariant this endpoint should always have
    enforced. Previously the domain list was hardcoded here, a third place it
    was written down after the contracts directory and REAL_SOURCEABLE, and it
    disagreed with both: hr_requests was contracted but absent, and
    employee_relations was listed but had no contract.

    Labels and descriptions come from the contract's own bilingual text, so
    they cannot drift from the schema either.

    Templates contain headers only — never sample or client data.
    """
    cs = _canonical_schema()
    tables = cs.available_tables()

    if name:
        if name not in tables:
            raise HTTPException(
                status_code=404,
                detail=f"No template for '{name}': no contract at "
                       f"data/contracts/{name}_schema.yml.",
            )
        return Response(
            content=_header_only_csv(cs.column_names(name)),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{name}_template.csv"'
            },
        )

    templates = []
    for table in tables:
        spec = cs.describe(table, locale)
        templates.append({
            "name": table,
            "filename": f"{table}_template.csv",
            "label": spec["label"],
            "description": spec["description"],
            "available": True,
        })
    return templates

# P0-2 step 1. Neither of these may be decided by the uploaded file.
#
# FORMAT. `.parquet` is refused. Not "never" - NOT YET, and the precondition is
# named: parquet becomes acceptable once validate_csv's rule engine runs
# against a polars FRAME, with the CSV reader as one adapter and a parquet
# reader as another. One rule implementation, two readers. Accepting parquet
# before that means a SECOND implementation of the contract rules, which is
# exactly what produced the 17-table typing divergence between this path and
# scripts/ingest_raw.py. Until then the branch it replaces was a
# shutil.copyfileobj straight into silver: any file named *.parquet became a
# domain's table, with no read at all.
#
# TABLE. The target domain is an explicit parameter checked against
# data/contracts/. It used to be os.path.splitext(filename)[0], so
# `payroll.csv` renamed `employees.csv` silently replaced the employee master,
# and `employees (3).csv` created a table called `employees (3)`.
ACCEPTED_UPLOAD_EXTENSIONS = {".csv"}

PARQUET_REFUSAL = (
    "Parquet uploads are not accepted yet. Contract validation reads CSV rows "
    "and reports the row and column of each violation; accepting parquet "
    "requires the same rules running against a dataframe, which is planned but "
    "not built. Please upload the CSV export instead."
)


def _validated_table(table: Optional[str]) -> str:
    """The target domain, from the request - never from the filename."""
    cs = _canonical_schema()
    known = cs.available_tables()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A target table is required. It is no longer inferred from "
                   "the filename. Choose one of: {}.".format(", ".join(known)),
        )
    if table not in known:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown table '{}': no contract at "
                   "data/contracts/{}_schema.yml. Choose one of: {}.".format(
                       table, table, ", ".join(known)),
        )
    return table


def _validated_extension(filename: Optional[str]) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = os.path.splitext(os.path.basename(filename))[1].lower()
    if ext == ".parquet":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=PARQUET_REFUSAL)
    if ext not in ACCEPTED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden file type '{}'. Only {} is accepted.".format(
                ext, ", ".join(sorted(ACCEPTED_UPLOAD_EXTENSIONS))),
        )
    return ext


class StagedUpload(BaseModel):
    upload_id: str
    table: str
    original_filename: str
    size_bytes: int
    sha256: str
    staged_at: str
    committed_at: Optional[str] = None


class ViolationOut(BaseModel):
    rule: str
    row: Optional[int] = None
    column: Optional[str] = None
    # The client's OWN header, when a mapping profile renamed it. Without this
    # a violation names a canonical column they never wrote, at a row of a file
    # they never made - and the error report they open beside their spreadsheet
    # becomes unreadable. The validator stays canonical-only; the translation
    # happens here, at the edge.
    source_column: Optional[str] = None
    message_en: str
    message_ar: str


class MappingOut(BaseModel):
    """What the profile did, and what still needs a human."""
    applied: bool
    profile_version: Optional[int] = None
    renamed: Dict[str, str] = {}
    ignored: List[str] = []
    # Source headers with no decision. These BLOCK: a column is mapped,
    # explicitly ignored with a reason, or it stops the upload. Default-dropping
    # would let a renamed export silently lose a column.
    unmapped: List[str] = []
    derived: List[str] = []
    # canonical column -> values with no mapping, for columns where an
    # unmapped value BLOCKS. Surfaced as a mapping TASK with the canonical
    # options listed, never as a bare rejection.
    unmapped_values: Dict[str, List[str]] = {}
    reject_enum_options: Dict[str, List[str]] = {}
    # What a value mapping into each gated column DECIDES, in the client's
    # terms. An affirmation is worth nothing if it does not say what is being
    # affirmed, so the consequence travels with the options rather than living
    # in UI copy that can drift from the contract.
    reject_enum_consequences: Dict[str, str] = {}
    header_changed: bool = False


class UploadPreview(BaseModel):
    upload: StagedUpload
    row_count: int
    columns_present: List[str]
    columns_missing: List[str]
    columns_unexpected: List[str]
    rejects: List[ViolationOut]
    exceptions: List[ViolationOut]
    can_commit: bool
    # Category F: SUGGESTED, never applied. Ruling 3 says coverage is declared,
    # and a pre-filled value a human confirms IS a declaration - an inferred
    # value applied silently is not.
    suggested_coverage_start: Optional[str] = None
    suggested_coverage_end: Optional[str] = None
    coverage_required: bool = False
    history_required: bool = False
    mapping: Optional[MappingOut] = None


class CommitDeclaration(BaseModel):
    coverage_start: Optional[str] = None
    coverage_end: Optional[str] = None
    history_since: Optional[str] = None


def _scripts():
    scripts_dir = get_scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import onboarding
    import staging
    import validate_schema
    return staging, validate_schema, onboarding


def _mapping():
    scripts_dir = get_scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import mapping
    return mapping


def _violation_out(v, back_map=None):
    return ViolationOut(rule=v.rule, row=v.row, column=v.column,
                        source_column=(back_map or {}).get(v.column),
                        message_en=v.message_en, message_ar=v.message_ar)


def get_raw_dir() -> str:
    container = "/app/data/raw"
    if os.path.isdir(container):
        return container
    local = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         "../../../data/raw"))
    os.makedirs(local, exist_ok=True)
    return local


class DomainStatus(BaseModel):
    """One row of the onboarding checklist."""
    domain: str
    label_en: str
    label_ar: str
    kind: str                       # contracted | uncontracted
    contracted: bool
    declared: bool
    provided: bool
    row_count: int
    coverage_start: Optional[str] = None
    coverage_end: Optional[str] = None
    covered_days: Optional[int] = None
    expected_days: Optional[int] = None
    history_since: Optional[str] = None
    # `available` is FALSE for the uncontracted domains: they cannot be
    # onboarded at all, which is different from merely not being uploaded yet.
    # A client shown "missing" for a domain they cannot provide will keep
    # trying.
    available: bool = True
    unavailable_reason: Optional[str] = None


class OnboardingStatusResponse(BaseModel):
    data_mode: str
    report_month: Optional[str] = None
    domains: List[DomainStatus]


@router.get("/onboarding-status", response_model=OnboardingStatusResponse)
def get_onboarding_status(
    # current_user FIRST: FastAPI resolves dependencies in signature order, and
    # authentication should be decided before the database is opened. With the
    # other order, a missing warehouse turns an unauthenticated request into a
    # 500 instead of a 401.
    current_user: Dict[str, Any] = Depends(get_current_user),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
):
    """Which domains are declared, which are populated, what is still missing.

    A read of `domain_provenance`, which build_warehouse already writes. No new
    computation - the facts existed and had nowhere to be seen.
    """
    cs = _canonical_schema()
    contracted = set(cs.available_tables())

    rows = {}
    try:
        for record in conn.execute(
            "SELECT domain, kind, declared, row_count, provided, "
            "coverage_start, coverage_end, history_since FROM domain_provenance"
        ).fetchall():
            rows[record[0]] = record
    except Exception:
        # An older warehouse, or one whose build aborted. Report nothing rather
        # than inventing a state - the same default-deny step 2b applies.
        rows = {}

    coverage = {}
    try:
        record = conn.execute(
            "SELECT covered_days, expected_days FROM mart_attendance_coverage"
        ).fetchone()
        if record:
            coverage["attendance"] = record
    except Exception:
        pass

    report_month = None
    try:
        record = conn.execute(
            "SELECT report_month FROM base_command_center_report_context").fetchone()
        report_month = record[0] if record else None
    except Exception:
        pass

    domains = []
    for domain in sorted(set(rows) | contracted):
        record = rows.get(domain)
        is_contracted = domain in contracted
        spec = cs.describe(domain, "en") if is_contracted else None
        spec_ar = cs.describe(domain, "ar") if is_contracted else None
        days = coverage.get(domain)
        domains.append(DomainStatus(
            domain=domain,
            label_en=spec["label"] if spec else domain.replace("_", " ").title(),
            label_ar=spec_ar["label"] if spec_ar else domain,
            kind=(record[1] if record else ("contracted" if is_contracted
                                            else "uncontracted")),
            contracted=is_contracted,
            declared=bool(record[2]) if record else False,
            provided=bool(record[4]) if record else False,
            row_count=int(record[3]) if record else 0,
            coverage_start=str(record[5]) if record and record[5] else None,
            coverage_end=str(record[6]) if record and record[6] else None,
            covered_days=days[0] if days else None,
            expected_days=days[1] if days else None,
            history_since=str(record[7]) if record and record[7] else None,
            available=is_contracted,
            unavailable_reason=None if is_contracted else (
                "No contract yet, so this domain cannot be uploaded. It is "
                "served from sample data in demo and never in real mode."),
        ))

    return OnboardingStatusResponse(
        data_mode=str(settings.DATA_MODE or "demo").strip().lower(),
        report_month=report_month,
        domains=domains,
    )


@router.post("/uploads", response_model=StagedUpload)
def stage_upload(
    file: UploadFile = File(...),
    table: Optional[str] = Query(None, description="Target contracted domain"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """STAGE. Receive the bytes and do nothing else.

    Deliberately no validation here: validation is a separate, repeatable read
    (GET below), so a client who fixes their file re-uploads rather than
    re-running a hidden step, and staging never holds a half-validated state.

    A staged file is INERT. It is not in data/silver, so nothing serves it, and
    not in data/raw either, so no pipeline run picks it up.
    """
    _validated_extension(file.filename)
    table_name = _validated_table(table)
    staging, _vs, _onb = _scripts()
    manifest = staging.stage(table_name, file.filename, file.file)
    return StagedUpload(**manifest)


@router.get("/uploads", response_model=List[StagedUpload])
def list_uploads(current_user: Dict[str, Any] = Depends(get_current_user)):
    staging, _vs, _onb = _scripts()
    return [StagedUpload(**m) for m in staging.listing()]


@router.get("/uploads/{upload_id}", response_model=UploadPreview)
def preview_upload(upload_id: str,
                   current_user: Dict[str, Any] = Depends(get_current_user)):
    """PREVIEW. The SAME validate_csv that ingest runs, read-only.

    Same function, not an equivalent one: a preview that agrees with ingest
    only by intention is the defect this cycle removed from the write path.
    """
    staging, validate_schema, onboarding = _scripts()
    try:
        manifest = staging.load(upload_id)
        path = staging.data_path(upload_id)
    except staging.StagingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    table = manifest["table"]
    cs = _canonical_schema()
    contracted = cs.column_names(table)

    try:
        frame = pl.read_csv(path, null_values=[""])
        present = list(frame.columns)
        row_count = frame.height
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail="Unreadable CSV: {}".format(exc))

    # A mapping profile, if one exists, is applied BEFORE validation, so the
    # validator only ever sees canonical columns. The mapped file is written
    # beside the original - which is never modified, so a client can always be
    # shown their own headers and a re-map costs no re-upload.
    mapping_module = _mapping()
    mapping_out = MappingOut(applied=False)
    back_map = {}
    validated_path = path
    try:
        profile = mapping_module.load_profile(table)
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail="Mapping profile is invalid: {}".format(exc))

    if profile:
        try:
            mapped, mapping_report = mapping_module.apply_profile(
                frame, table, profile)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Mapping could not be applied: {}".format(exc))
        validated_path = staging.mapped_path(upload_id)
        mapped.write_csv(validated_path)
        back_map = mapping_report.back_map
        fingerprint = mapping_module.header_fingerprint(frame.columns)
        mapping_out = MappingOut(
            applied=True,
            profile_version=profile.get("version"),
            renamed=mapping_report.renamed,
            ignored=mapping_report.ignored,
            unmapped=mapping_report.unmapped,
            derived=mapping_report.derived,
            unmapped_values={k: sorted(v)
                             for k, v in mapping_report.unmapped_values.items()},
            reject_enum_options=mapping_module.reject_enum_columns(table),
            reject_enum_consequences={
                col: mapping_module.consequence(table, col)
                for col in mapping_module.reject_enum_columns(table)
                if mapping_module.consequence(table, col)},
            header_changed=(
                bool(profile.get("source_fingerprint"))
                and profile.get("source_fingerprint") != fingerprint),
        )

    result = validate_schema.validate_csv(validated_path, table)

    suggested_start = suggested_end = None
    coverage_required = table in onboarding.DATE_GRAINED
    if coverage_required:
        column = {"attendance": "attendance_date"}.get(table)
        if column and column in present:
            values = sorted(str(v)[:10] for v in frame[column].to_list() if v)
            if values:
                suggested_start, suggested_end = values[0], values[-1]

    return UploadPreview(
        upload=StagedUpload(**manifest),
        row_count=row_count,
        columns_present=present,
        columns_missing=[c for c in contracted if c not in present],
        columns_unexpected=[c for c in present if c not in contracted],
        rejects=[_violation_out(v, back_map) for v in result.rejects],
        exceptions=[_violation_out(v, back_map) for v in result.exceptions],
        # Unmapped headers and unmapped REJECT values block just as a
        # contract violation does - the file cannot be committed as it is.
        can_commit=(not result.rejects and not mapping_out.unmapped
                    and not mapping_out.unmapped_values),
        suggested_coverage_start=suggested_start,
        suggested_coverage_end=suggested_end,
        coverage_required=coverage_required,
        history_required=table in onboarding.HISTORY_DECLARING,
        mapping=mapping_out,
    )


# --------------------------------------------------------------------------
# mapping - the screen's two routes
# --------------------------------------------------------------------------

# Five is enough to settle a header and few enough that the response stays a
# glance rather than a data dump.
MAX_SAMPLES = 5


class MappingCandidate(BaseModel):
    canonical: str
    matched_by: str
    confidence: Optional[float] = None


class CanonicalColumn(BaseModel):
    name: str
    label_en: str
    label_ar: str
    required: bool
    allowed_values: Optional[List[str]] = None


class SourceColumn(BaseModel):
    header: str
    # THE CLIENT'S OWN VALUES. Read from the staged file at request time and
    # returned for display only. They are never written to the profile, the
    # manifest or a log: a profile accumulates as training substrate and
    # outlives the upload, which is the whole reason for the PII rule in
    # scripts/mapping.py. Showing someone their own file in their own session
    # is a different act from keeping it.
    samples: List[str] = []
    non_empty: int = 0
    candidates: List[MappingCandidate] = []
    current: Optional[str] = None
    decision: str = "undecided"


class MappingWorkspace(BaseModel):
    """Everything the mapping screen needs, in one request."""
    upload_id: str
    table: str
    row_count: int
    source_columns: List[SourceColumn]
    canonical_columns: List[CanonicalColumn]
    reject_enum_options: Dict[str, List[str]] = {}
    reject_enum_consequences: Dict[str, str] = {}
    derivation_rules: List[str] = []
    profile_version: Optional[int] = None


class MappingDecisionIn(BaseModel):
    header: str
    decision: str = "undecided"
    chosen: Optional[str] = None
    reason: Optional[str] = None


class SaveMappingRequest(BaseModel):
    upload_id: str
    decisions: List[MappingDecisionIn] = []
    values: Dict[str, Dict[str, str]] = {}
    derive: Dict[str, Dict[str, str]] = {}
    # column -> {client value: canonical value}, restated by the human as the
    # affirmation. `confirmed_by` is taken from the session, never from the
    # body - a signature the caller supplies for itself is not one.
    confirmations: Dict[str, Dict[str, str]] = {}


class SavedMapping(BaseModel):
    table: str
    version: int
    created_by: str
    created_at: str
    mapped: int
    ignored: int
    undecided: int


def _derivation_rules():
    scripts_dir = get_scripts_dir()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import derivations
    return sorted(derivations.REGISTRY)


@router.get("/uploads/{upload_id}/columns", response_model=MappingWorkspace)
def mapping_workspace(upload_id: str,
                      current_user: Dict[str, Any] = Depends(get_current_user)):
    """The client's own columns, with sample values, ranked candidates and the
    canonical targets to choose from.

    A separate route rather than a wider preview response, deliberately: this
    is the one endpoint whose PURPOSE is to return client data, and it should
    be reviewable as such instead of hidden inside a response everything calls.
    """
    staging, _vs, _onb = _scripts()
    mapping_module = _mapping()
    cs = _canonical_schema()
    try:
        manifest = staging.load(upload_id)
    except Exception:
        raise HTTPException(status_code=404, detail="No such upload.")
    table = manifest["table"]
    frame = pl.read_csv(staging.data_path(upload_id), null_values=[""])

    profile = mapping_module.load_profile(table) or {}
    mapped = {mapping_module.normalise(k): v
              for k, v in (profile.get("columns") or {}).items()}
    ignored = {mapping_module.normalise(
        e["header"] if isinstance(e, dict) else e)
        for e in (profile.get("ignored") or [])}
    ranked = mapping_module.suggest(table, list(frame.columns))

    source_columns = []
    for header in frame.columns:
        values = [str(v) for v in frame[header].to_list() if v not in (None, "")]
        key = mapping_module.normalise(header)
        current = mapped.get(key)
        source_columns.append(SourceColumn(
            header=header,
            samples=sorted(set(values))[:MAX_SAMPLES],
            non_empty=len(values),
            candidates=[MappingCandidate(**c) for c in ranked.get(header, [])],
            current=current,
            decision=("mapped" if current else
                      ("ignored" if key in ignored else "undecided")),
        ))

    return MappingWorkspace(
        upload_id=upload_id,
        table=table,
        row_count=frame.height,
        source_columns=source_columns,
        canonical_columns=[
            CanonicalColumn(
                name=c["name"],
                label_en=c.get("name_en") or c["name"],
                label_ar=c.get("name_ar") or c["name"],
                required=bool(c.get("required")),
                allowed_values=c.get("allowed_values"))
            for c in cs.columns(table)],
        reject_enum_options=mapping_module.reject_enum_columns(table),
        reject_enum_consequences={
            col: mapping_module.consequence(table, col)
            for col in mapping_module.reject_enum_columns(table)
            if mapping_module.consequence(table, col)},
        derivation_rules=_derivation_rules(),
        profile_version=profile.get("version"),
    )


@router.post("/mapping/{table}", response_model=SavedMapping)
def save_mapping(table: str, body: SaveMappingRequest = Body(...),
                 current_user: Dict[str, Any] = Depends(get_current_user)):
    """Append a profile version from the screen's decisions.

    The version is built by `mapping.build_version`, which computes evidence,
    matched_by, confidence and the rejected candidates from the staged frame.
    Nothing about provenance comes from the request body, because a caller that
    can assert its own provenance is not recording any.
    """
    table_name = _validated_table(table)
    staging, _vs, _onb = _scripts()
    mapping_module = _mapping()
    try:
        manifest = staging.load(body.upload_id)
    except Exception:
        raise HTTPException(status_code=404, detail="No such upload.")
    if manifest["table"] != table_name:
        raise HTTPException(
            status_code=400,
            detail="That upload is a {} file, not {}.".format(
                manifest["table"], table_name))

    frame = pl.read_csv(staging.data_path(body.upload_id), null_values=[""])
    who = current_user.get("email") or current_user.get("username") or ""
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    confirmations = {
        column: {"confirmed_by": who, "confirmed_at": stamp,
                 "pairs": dict(pairs)}
        for column, pairs in (body.confirmations or {}).items()}

    version = mapping_module.build_version(
        table_name, frame,
        {d.header: {"decision": d.decision, "chosen": d.chosen,
                    "reason": d.reason} for d in body.decisions},
        created_by=who,
        values=body.values, derive=body.derive, confirmations=confirmations)
    try:
        saved = mapping_module.save_version(table_name, version)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    undecided = sum(1 for e in saved["evidence"] if e["decision"] == "undecided")
    return SavedMapping(
        table=table_name, version=saved["version"],
        created_by=saved["created_by"], created_at=saved["created_at"],
        mapped=len(saved.get("columns") or {}),
        ignored=len(saved.get("ignored") or []), undecided=undecided)


@router.delete("/uploads/{upload_id}")
def discard_upload(upload_id: str,
                   current_user: Dict[str, Any] = Depends(get_current_user)):
    staging, _vs, _onb = _scripts()
    try:
        removed = staging.discard(upload_id)
    except staging.StagingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not removed:
        raise HTTPException(status_code=404, detail="no staged upload")
    return {"status": "discarded", "upload_id": upload_id}


@router.post("/uploads/{upload_id}/commit", response_model=RefreshReport)
def commit_upload(
    upload_id: str,
    declaration: CommitDeclaration = Body(default=CommitDeclaration()),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """COMMIT. Declare, move to data/raw, and run the pipeline that already exists.

    Nothing here writes silver, types a column, or applies a contract rule.
    data/raw + scripts/ingest_raw.py does all of it, which is the point: one
    ingest path, so the two cannot diverge again.

    Recoverable rather than transactional: the previous raw file and registry
    are kept until the pipeline exits 0, and restored if it does not.
    """
    staging, _validate_schema, onboarding = _scripts()
    try:
        manifest = staging.load(upload_id)
        staged_path = staging.data_path(upload_id)
    except staging.StagingError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    table = manifest["table"]

    # The declaration is REQUIRED for the domains Category F named, and it is
    # checked here so the client gets a 400 naming the field rather than a
    # pipeline abort.
    if table in onboarding.DATE_GRAINED and not (
            declaration.coverage_start and declaration.coverage_end):
        raise HTTPException(
            status_code=400,
            detail="'{}' is date-grained: coverage_start and coverage_end are "
                   "required. A working day outside the declared window is not "
                   "an absence, it is unreported - so the window cannot be "
                   "guessed from the file.".format(table))
    if table in onboarding.HISTORY_DECLARING and not declaration.history_since:
        raise HTTPException(
            status_code=400,
            detail="'{}' feeds point-in-time history: history_since is "
                   "required. Without it, historical months are null rather "
                   "than a derived-but-understated figure.".format(table))

    raw_dir = get_raw_dir()
    raw_path = os.path.join(raw_dir, "{}.csv".format(table))
    registry_path = os.path.join(get_scripts_dir(), "..", "data", "onboarding",
                                 "declared_domains.yml")
    registry_path = os.path.abspath(registry_path)
    if os.path.isdir("/app/data/onboarding"):
        registry_path = "/app/data/onboarding/declared_domains.yml"

    raw_existed = os.path.exists(raw_path)
    registry_existed = os.path.exists(registry_path)
    previous_raw = raw_path + ".previous" if raw_existed else None
    previous_registry = registry_path + ".previous" if registry_existed else None
    if previous_raw:
        shutil.copy2(raw_path, previous_raw)
    if previous_registry:
        shutil.copy2(registry_path, previous_registry)

    def _restore():
        """Put both back exactly as they were - including NOT EXISTING.

        The first version restored a previous file but left a NEW one behind,
        so a failed first-ever commit left a declaration with no data. The
        declared-domain guard would then abort every subsequent run with
        "declared but EMPTY" - loud, but a mess the operator has to clean up by
        hand for a commit that was supposed to have rolled back.
        """
        if previous_raw and os.path.exists(previous_raw):
            shutil.move(previous_raw, raw_path)
        elif not raw_existed and os.path.exists(raw_path):
            os.remove(raw_path)
        if previous_registry and os.path.exists(previous_registry):
            shutil.move(previous_registry, registry_path)
        elif not registry_existed and os.path.exists(registry_path):
            os.remove(registry_path)

    # The MAPPED file is what lands in data/raw, because data/raw is canonical
    # and scripts/ingest_raw.py revalidates it unchanged. That is what keeps
    # P0-2's single ingest path intact: nothing downstream knows profiles exist.
    mapping_module = _mapping()
    if mapping_module.load_profile(table):
        mapped = staging.mapped_path(upload_id)
        if not os.path.exists(mapped):
            raise HTTPException(
                status_code=400,
                detail="This upload has a mapping profile but has not been "
                       "previewed. Preview it first - the preview is where the "
                       "mapping is applied and checked.")
        staged_path = mapped

    try:
        shutil.copy2(staged_path, raw_path)
        onboarding.declare(
            table,
            declared_by=current_user.get("email"),
            coverage_start=declaration.coverage_start,
            coverage_end=declaration.coverage_end,
            history_since=declaration.history_since,
        )
        report = _run_pipeline()
    except Exception as exc:
        _restore()
        raise HTTPException(status_code=400,
                            detail="Commit failed and was rolled back: {}".format(exc))

    if report.return_code != 0:
        _restore()
        raise HTTPException(
            status_code=400,
            detail="Pipeline rejected the upload and it was rolled back. "
                   + (report.stderr or "")[-2000:])

    for leftover in (previous_raw, previous_registry):
        if leftover and os.path.exists(leftover):
            os.remove(leftover)
    staging.mark_committed(upload_id)
    return report


# A full ingest + 158-model dbt build. The old 180s was already optimistic on
# sample data and would not survive a real dataset; a timeout mid-run leaves
# the warehouse in whatever state dbt reached, which is the worst outcome here.
PIPELINE_TIMEOUT_SECONDS = 900


def _run_pipeline() -> RefreshReport:
    """The one way this API runs the pipeline. Used by /refresh and by commit."""
    import time

    script_path = os.path.join(get_scripts_dir(), "refresh_all.py")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=500,
                            detail="Refresh script not found at {}".format(script_path))
    start_time = time.time()
    try:
        result = subprocess.run([sys.executable, script_path],
                                capture_output=True, text=True,
                                timeout=PIPELINE_TIMEOUT_SECONDS)
        return RefreshReport(
            status="success" if result.returncode == 0 else "failed",
            return_code=result.returncode,
            # `or ""` because a None here would fail RefreshReport validation
            # and turn a SUCCESSFUL pipeline run into a 500 - which is how a
            # commit gets rolled back after its data has already landed.
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            execution_time_seconds=round(time.time() - start_time, 2),
        )
    except subprocess.TimeoutExpired as te:
        return RefreshReport(
            status="failed", return_code=-1, stdout=te.stdout or "",
            stderr="Pipeline execution timed out after {} seconds.".format(
                PIPELINE_TIMEOUT_SECONDS),
            execution_time_seconds=round(time.time() - start_time, 2))
    except Exception as exc:
        return RefreshReport(status="failed", return_code=-1, stdout="",
                             stderr=str(exc),
                             execution_time_seconds=round(time.time() - start_time, 2))


@router.post("/refresh", response_model=RefreshReport)
def trigger_refresh(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Run scripts/refresh_all.py and return the pipeline health report."""
    return _run_pipeline()
