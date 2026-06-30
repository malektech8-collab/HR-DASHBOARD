from fastapi import APIRouter, HTTPException
import os
import yaml

router = APIRouter()

CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../config/milestone_3l_governance_config.yml"
    )
)

@router.get("/status")
def get_governance_status():
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
