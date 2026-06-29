from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import executive, data_quality, workforce, payroll, attendance, compliance, er, recruitment, talent, command_center
from app.schemas.kpi import RefreshStatusResponse
from app.config import settings
import os
from datetime import datetime

app = FastAPI(
    title="HR Analytics Command Center API",
    description="Backend API serving metric models and data quality reports from DuckDB",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# Meta refresh status endpoint
@app.get("/api/meta/refresh-status", response_model=RefreshStatusResponse)
def get_refresh_status():
    last_refresh_str = "Unknown"
    status_str = "no_database"
    
    if os.path.exists(settings.DATABASE_PATH):
        mtime = os.path.getmtime(settings.DATABASE_PATH)
        last_refresh_str = datetime.fromtimestamp(mtime).isoformat()
        status_str = "success"
        
    return RefreshStatusResponse(
        last_refresh_at=last_refresh_str,
        status=status_str
    )

# Include API routers
app.include_router(executive.router, prefix="/api/executive", tags=["Executive"])
app.include_router(data_quality.router, prefix="/api/data-quality", tags=["Data Quality"])
app.include_router(workforce.router, prefix="/api/workforce", tags=["Workforce"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["Compliance"])
app.include_router(er.router, prefix="/api/er", tags=["Employee Relations"])
app.include_router(recruitment.router, prefix="/api/recruitment", tags=["Recruitment"])
app.include_router(talent.router, prefix="/api/talent", tags=["Talent"])
app.include_router(command_center.router, prefix="/api/command-center", tags=["Command Center"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

