from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import executive, data_quality, workforce, payroll, attendance, compliance, er, recruitment, talent, command_center, data
from app.api.endpoints import governance
from app.schemas.kpi import RefreshStatusResponse, AppConfigResponse
from fastapi import HTTPException, Query
from typing import Optional
from app.config import settings
from app.api.dependencies.auth import get_current_user
import os
from datetime import datetime

app = FastAPI(
    title="HR Analytics Command Center API",
    description="Backend API serving metric models and data quality reports from DuckDB",
    version="1.0.0"
)

# Enable CORS dynamically based on configuration
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# Meta refresh status endpoint
# Operational metadata. Carries no employee data, but it does tell an
# anonymous caller that a warehouse exists and when it was last built,
# and the UI only shows it after login - so it is protected rather than
# exempted. Protected-by-default means the exemption needs the argument,
# not the protection.
@app.get("/api/meta/refresh-status", response_model=RefreshStatusResponse,
         dependencies=[Depends(get_current_user)])
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

# Meta app-config endpoint (exposes the active data_mode to the frontend)
@app.get("/api/meta/app-config", response_model=AppConfigResponse)
def get_app_config():
    return AppConfigResponse(data_mode=settings.DATA_MODE)

# Canonical schema endpoint — labels/metadata for the UI. Never returns data.
@app.get("/api/meta/schema")
def get_meta_schema(
    table: Optional[str] = Query(None, description="Single table; omit for all"),
    locale: str = Query("en", description="Label locale: en or ar"),
):
    """Bilingual canonical schema, for UI labels and localized messages.

    One definition, four consumers (template, validation, labels, errors) —
    this is the labels consumer. Contains column metadata only; no row data.
    """
    from app.api.data import _canonical_schema
    cs = _canonical_schema()
    if table:
        if not cs.has_schema(table):
            raise HTTPException(status_code=404, detail=f"No contract for table '{table}'")
        return cs.describe(table, locale)
    return {"locale": locale if locale in cs.LOCALES else cs.DEFAULT_LOCALE,
            "tables": cs.describe_all(locale)}


@app.on_event("startup")
def _initialise_auth() -> None:
    """Prepare the user store, and say so loudly if there is nobody in it."""
    from app.core import bootstrap as bootstrap_tokens
    from app.core import users
    users.initialise()
    users.seed_demo_users()          # demo mode only; refuses in real mode
    token = bootstrap_tokens.issue_if_needed()
    if token:
        bootstrap_tokens.announce(token)


# Include API routers.
#
# AUTHENTICATION IS APPLIED AT THE ROUTER, not per route. Measured before this
# change: 83 routes existed and `get_current_user` appeared in ONE file, so a
# request with no token got
#
#     /api/payroll/summary      -> 200
#     /api/workforce/exceptions -> 200  {"employee_name": "Fahad Al-Otaibi"...}
#
# P0-2 had protected the six routes that WRITE. The seventy-seven that READ -
# salaries, GOSI status, Iqama expiry, named employees - were open. Putting the
# dependency on each route would mean the next route added is unprotected until
# someone remembers; putting it on the router means it is protected by default
# and an exemption has to be written down.
#
# test_route_coverage.py enumerates every route and asserts each is either
# authenticated or on the PUBLIC_ROUTES list with a reason.
PROTECTED = [Depends(get_current_user)]

app.include_router(executive.router, prefix="/api/executive", tags=["Executive"], dependencies=PROTECTED)
app.include_router(data_quality.router, prefix="/api/data-quality", tags=["Data Quality"], dependencies=PROTECTED)
app.include_router(workforce.router, prefix="/api/workforce", tags=["Workforce"], dependencies=PROTECTED)
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"], dependencies=PROTECTED)
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"], dependencies=PROTECTED)
app.include_router(compliance.router, prefix="/api/compliance", tags=["Compliance"], dependencies=PROTECTED)
app.include_router(er.router, prefix="/api/er", tags=["Employee Relations"], dependencies=PROTECTED)
app.include_router(recruitment.router, prefix="/api/recruitment", tags=["Recruitment"], dependencies=PROTECTED)
app.include_router(talent.router, prefix="/api/talent", tags=["Talent"], dependencies=PROTECTED)
app.include_router(command_center.router, prefix="/api/command-center", tags=["Command Center"], dependencies=PROTECTED)
# governance carries /token, which MUST stay public - it is how a caller gets a
# token in the first place. Its other routes gate themselves with RoleChecker.
app.include_router(governance.router, prefix="/api/governance", tags=["Governance"])
app.include_router(data.router, prefix="/api/data", tags=["Data Management"], dependencies=PROTECTED)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
