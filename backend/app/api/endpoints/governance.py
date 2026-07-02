from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
import os
import yaml
from typing import Dict, Any
from app.core.security import create_access_token, MOCK_USER_DB, Role
from app.api.dependencies.auth import RoleChecker

router = APIRouter()

CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../config/milestone_3l_governance_config.yml"
    )
)

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, Any]:
    """
    Authenticate synthetic users and return a JWT access token.
    """
    user = MOCK_USER_DB.get(form_data.username)
    if not user or user["hashed_password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/status")
def get_governance_status(
    current_user: Dict[str, Any] = Depends(RoleChecker([Role.SYSTEM_ADMIN, Role.EXECUTIVE]))
) -> Dict[str, Any]:
    """
    Fetch the system governance status. Restriced to SYSTEM_ADMIN and EXECUTIVE roles.
    """
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(
            status_code=404,
            detail=f"Governance status configuration not found at {CONFIG_PATH}"
        )
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        status_data = config_data.get("governance_status", {})

        # Enforce safety defaults in API layer as well to protect against config tampering
        return {
            "current_gate": status_data.get("current_gate", "Gate 5 - Authorization Evidence Pending"),
            "current_status": status_data.get("current_status", "Authorization Evidence Pending"),
            "evidence_status": status_data.get("evidence_status", "Not Provided"),
            "synthetic_validation_status": status_data.get("synthetic_validation_status", "Synthetic Validation Only"),
            "decision_recommendation": status_data.get("decision_recommendation", "Hold"),
            "real_data_execution_approved": False, # Strict override
            "real_authorization_evidence_approved": False, # Strict override
            "load_scheduling_approved": False, # Strict override
            "go_no_go_meeting_held": False, # Strict override
            "stop_criteria_count": int(status_data.get("stop_criteria_count", 22)),
            "last_completed_milestone": status_data.get("last_completed_milestone", "3K"),
            "milestone_3i_status": status_data.get("milestone_3i_status", "Authorization Evidence Pending"),
            "milestone_3j_status": status_data.get("milestone_3j_status", "Planning Only"),
            "milestone_3k_status": status_data.get("milestone_3k_status", "Synthetic Validation Only")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
