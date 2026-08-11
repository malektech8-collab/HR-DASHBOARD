import csv
import io
import os
import sys
import subprocess
import shutil
import polars as pl
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

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

def compile_csv_to_parquet(csv_path: str, parquet_path: str, table_name: str):
    """
    Reads a CSV file and compiles it to Parquet, enforcing types matching ingest_raw.py.
    """
    try:
        df = pl.read_csv(csv_path, null_values=[""])
        
        # Apply specific type casting based on table name.
        # Columns are only cast if present, since uploaded files may omit optional columns.
        if table_name == "employees":
            # Same derived-column rule as scripts/ingest_raw.py. The UI upload
            # is a second ingest path and a client is more likely to use it
            # than data/raw/, so it must behave identically: derive is_saudi
            # only when the column is absent, never guess an unknown value.
            if "is_saudi" not in df.columns and "nationality" in df.columns:
                scripts_dir = get_scripts_dir()
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                from derivations import derive_column
                import canonical_schema as _cs
                spec = next(c for c in _cs.columns("employees")
                            if c["name"] == "is_saudi")
                derived = derive_column(spec, df["nationality"].to_list())
                df = df.with_columns(pl.Series("is_saudi", derived, dtype=pl.Boolean))
            date_cols = ["joining_date", "termination_date", "contract_end_date"]
            numeric_cols = ["basic_salary", "housing_allowance", "transport_allowance"]
            df = df.with_columns(
                [pl.col(c).str.to_date("%Y-%m-%d", strict=False) for c in date_cols if c in df.columns] +
                [pl.col(c).cast(pl.Float64, strict=False) for c in numeric_cols if c in df.columns] +
                ([pl.col("is_saudi").cast(pl.Boolean, strict=False)] if "is_saudi" in df.columns else [])
            )
        elif table_name == "payroll":
            numeric_cols = [
                "basic_salary", "housing_allowance", "transport_allowance",
                "other_allowances", "overtime_amount", "deductions",
                "gross_pay", "net_pay"
            ]
            df = df.with_columns([
                pl.col(c).cast(pl.Float64, strict=False) for c in numeric_cols if c in df.columns
            ])
        elif table_name == "attendance":
            date_cols = ["attendance_date"]
            datetime_cols = ["scheduled_start", "scheduled_end", "actual_check_in", "actual_check_out"]
            int_cols = ["late_minutes", "excused_late_minutes", "net_late_minutes", "missing_punch_count"]
            float_cols = ["absence_days", "overtime_hours"]
            df = df.with_columns(
                [pl.col(c).str.to_date("%Y-%m-%d", strict=False) for c in date_cols if c in df.columns] +
                [pl.col(c).str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False) for c in datetime_cols if c in df.columns] +
                [pl.col(c).cast(pl.Int64, strict=False) for c in int_cols if c in df.columns] +
                [pl.col(c).cast(pl.Float64, strict=False) for c in float_cols if c in df.columns] +
                ([pl.col("overtime_approved").cast(pl.Boolean, strict=False)] if "overtime_approved" in df.columns else [])
            )
        elif table_name == "compliance":
            numeric_cols = ["gosi_salary", "payroll_basic_salary"]
            date_cols = ["work_permit_expiry", "iqama_expiry"]
            df = df.with_columns(
                [pl.col(c).cast(pl.Float64, strict=False) for c in numeric_cols if c in df.columns] +
                [pl.col(c).str.to_date("%Y-%m-%d", strict=False) for c in date_cols if c in df.columns] +
                ([pl.col("contract_authenticated").cast(pl.Boolean, strict=False)] if "contract_authenticated" in df.columns else [])
            )
        elif table_name == "employee_relations":
            date_cols = ["created_date", "target_due_date", "closed_date"]
            df = df.with_columns(
                [pl.col(c).str.to_date("%Y-%m-%d", strict=False) for c in date_cols if c in df.columns] +
                ([pl.col("escalated").cast(pl.Boolean, strict=False)] if "escalated" in df.columns else [])
            )
            
        df.write_parquet(parquet_path)
    except Exception as e:
        raise ValueError(f"Polars compilation to Parquet failed: {str(e)}")

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


@router.post("/upload")
def upload_data_file(
    file: UploadFile = File(...),
    table: Optional[str] = Query(None, description="Target contracted domain"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload a CSV data file directly to the /app/data/silver/ directory.
    """
    filename = file.filename
    _validated_extension(filename)
    table_name = _validated_table(table)
    ext = ".csv"

    safe_filename = os.path.basename(filename)
    dest_dir = get_silver_dir()
    os.makedirs(dest_dir, exist_ok=True)
    
    try:
        if ext == ".csv":
            # Direct disk compilation: write temporary CSV first, compile using Polars to Parquet
            temp_csv_path = os.path.join(dest_dir, f"{table_name}_temp.csv")
            with open(temp_csv_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Destination path is parquet in silver folder
            dest_parquet_path = os.path.join(dest_dir, f"{table_name}.parquet")
            compile_csv_to_parquet(temp_csv_path, dest_parquet_path, table_name)
            
            # Clean up temp file
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
            
            dest_path = dest_parquet_path
        else:  # pragma: no cover - _validated_extension permits only .csv
            raise HTTPException(status_code=400, detail=PARQUET_REFUSAL)

        # Generate .uploaded companion marker file
        marker_path = f"{dest_path}.uploaded"
        with open(marker_path, "w") as f:
            f.write(f"Uploaded: {safe_filename}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write/compile file to disk: {str(e)}")
        
    return {
        "status": "success",
        "filename": f"{table_name}.parquet",
        "destination_path": dest_path,
        "size_bytes": os.path.getsize(dest_path)
    }

@router.post("/refresh", response_model=RefreshReport)
def trigger_refresh(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Systematically run scripts/refresh_all.py via Python subprocess and return pipeline health report.
    """
    script_path = os.path.join(get_scripts_dir(), "refresh_all.py")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail=f"Refresh script not found at {script_path}")
        
    import time
    start_time = time.time()
    
    try:
        # Run subprocess using system's executable python context
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        execution_time = time.time() - start_time
        status_str = "success" if result.returncode == 0 else "failed"
        
        return RefreshReport(
            status=status_str,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time_seconds=round(execution_time, 2)
        )
    except subprocess.TimeoutExpired as te:
        return RefreshReport(
            status="failed",
            return_code=-1,
            stdout=te.stdout or "",
            stderr="Pipeline execution timed out after 180 seconds.",
            execution_time_seconds=round(time.time() - start_time, 2)
        )
    except Exception as e:
        return RefreshReport(
            status="failed",
            return_code=-1,
            stdout="",
            stderr=str(e),
            execution_time_seconds=round(time.time() - start_time, 2)
        )
