import os
import sys
import subprocess
import shutil
import polars as pl
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()

# Directory definitions relative to backend app
SAMPLE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/sample"))
SILVER_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/silver"))

# For production container environment, default to /app/data/silver
CONTAINER_SILVER_DIR = "/app/data/silver"

def get_silver_dir() -> str:
    if os.path.exists(CONTAINER_SILVER_DIR):
        return CONTAINER_SILVER_DIR
    os.makedirs(SILVER_DATA_DIR, exist_ok=True)
    return SILVER_DATA_DIR

class TemplateInfo(BaseModel):
    name: str
    filename: str
    description: str

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
        
        # Apply specific type casting based on table name
        if table_name == "employees":
            df = df.with_columns([
                pl.col("is_saudi").cast(pl.Boolean, strict=False),
                pl.col("joining_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("termination_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("contract_end_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("basic_salary").cast(pl.Float64, strict=False),
                pl.col("housing_allowance").cast(pl.Float64, strict=False),
                pl.col("transport_allowance").cast(pl.Float64, strict=False),
            ])
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
            df = df.with_columns([
                pl.col("attendance_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("scheduled_start").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
                pl.col("scheduled_end").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
                pl.col("actual_check_in").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
                pl.col("actual_check_out").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
                pl.col("late_minutes").cast(pl.Int64, strict=False),
                pl.col("excused_late_minutes").cast(pl.Int64, strict=False),
                pl.col("net_late_minutes").cast(pl.Int64, strict=False),
                pl.col("absence_days").cast(pl.Float64, strict=False),
                pl.col("overtime_hours").cast(pl.Float64, strict=False),
                pl.col("overtime_approved").cast(pl.Boolean, strict=False),
                pl.col("missing_punch_count").cast(pl.Int64, strict=False),
            ])
        elif table_name == "compliance":
            df = df.with_columns([
                pl.col("contract_authenticated").cast(pl.Boolean, strict=False),
                pl.col("gosi_salary").cast(pl.Float64, strict=False),
                pl.col("payroll_basic_salary").cast(pl.Float64, strict=False),
                pl.col("work_permit_expiry").str.to_date("%Y-%m-%d", strict=False),
                pl.col("iqama_expiry").str.to_date("%Y-%m-%d", strict=False),
            ])
        elif table_name == "employee_relations":
            df = df.with_columns([
                pl.col("created_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("target_due_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("closed_date").str.to_date("%Y-%m-%d", strict=False),
                pl.col("escalated").cast(pl.Boolean, strict=False),
            ])
            
        df.write_parquet(parquet_path)
    except Exception as e:
        raise ValueError(f"Polars compilation to Parquet failed: {str(e)}")

@router.get("/templates")
def get_templates(
    name: Optional[str] = Query(None, description="Optional name of the template to download")
):
    """
    Download a data template or list available data templates.
    """
    templates = [
        {"name": "employees", "filename": "employees_sample.csv", "description": "Employee demographics, payroll base, and contract terms."},
        {"name": "payroll", "filename": "payroll_sample.csv", "description": "Monthly payroll metrics including basic salary and deductions."},
        {"name": "attendance", "filename": "attendance_sample.csv", "description": "Daily attendance timesheets and overtime hours."},
        {"name": "compliance", "filename": "compliance_sample.csv", "description": "Saudization quotas, GOSI contributions, and Iqama status."},
        {"name": "employee_relations", "filename": "employee_relations_sample.csv", "description": "Employee complaints, disputes, and active labor cases."}
    ]
    
    if name:
        target = next((t for t in templates if t["name"] == name), None)
        if not target:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Security validation against path traversal
        safe_filename = os.path.basename(target["filename"])
        file_path = os.path.join(SAMPLE_DATA_DIR, safe_filename)
        
        # Verify file actually exists and path is safe
        if not os.path.exists(file_path) or not file_path.startswith(SAMPLE_DATA_DIR):
            raise HTTPException(status_code=404, detail=f"Template file {target['filename']} not found on server")
        
        return FileResponse(
            path=file_path,
            filename=target["filename"],
            media_type="text/csv"
        )
        
    return templates

@router.post("/upload")
def upload_data_file(file: UploadFile = File(...)):
    """
    Upload a CSV or Parquet data file directly to the /app/data/silver/ directory.
    """
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    # Standard file type validation (.csv or .parquet)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".csv", ".parquet"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden file type. Only .csv and .parquet files are allowed."
        )
        
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    table_name = os.path.splitext(safe_filename)[0].replace("_sample", "")
    
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
        else:
            # Write parquet directly
            dest_path = os.path.join(dest_dir, f"{table_name}.parquet")
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
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
def trigger_refresh():
    """
    Systematically run scripts/refresh_all.py via Python subprocess and return pipeline health report.
    """
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scripts/refresh_all.py"))
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
