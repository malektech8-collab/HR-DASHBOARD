from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
import os
import yaml
from typing import Dict, Any
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.core import bootstrap as bootstrap_tokens
from app.core import users
from app.core.security import (Role, SecretNotConfigured,
                               create_access_token, revoke)
from app.api.dependencies.auth import RoleChecker, get_current_user

router = APIRouter()

CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../config/milestone_3l_governance_config.yml"
    )
)

_bearer = OAuth2PasswordBearer(tokenUrl="/api/governance/token")


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, Any]:
    """Exchange a credential for a token. PUBLIC by necessity.

    `users.authenticate` returns None for "no such user", "wrong password" and
    "locked" alike, and this returns one message for all of them: a caller must
    not be able to enumerate accounts. The comparison it replaced was
    `user["hashed_password"] != form_data.password` - plaintext, and
    short-circuiting on the first differing byte.
    """
    if not users.is_initialised():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="This deployment has not been initialised: it has no user "
                   "accounts. Create the first administrator with "
                   "`python -m app.cli create-admin`.")
    user = users.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = create_access_token(data={"sub": user["email"]})
    except SecretNotConfigured as exc:
        # A CORRECT credential against a misconfigured deployment. This used to
        # be an uncaught raise, so the operator got a bare 500 - at the one
        # moment they most needed to be told which variable is missing. The
        # data routes already answered 503 with this message; login did not,
        # which meant the most informative message in the system was the one
        # place it could not be seen.
        #
        # It failed closed either way. It now fails helpfully.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return {"access_token": token, "token_type": "bearer"}


class BootstrapRequest(BaseModel):
    token: str
    email: str
    password: str


@router.post("/bootstrap")
def bootstrap(body: BootstrapRequest) -> Dict[str, Any]:
    """Create the FIRST administrator using the one-time startup token.

    PUBLIC by necessity - there is no account to authenticate against yet.
    What makes it safe is that the token exists only while the store is empty,
    lives only in process memory, is single-use, and expires. The moment an
    account exists this route can never succeed again.
    """
    if users.is_initialised():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This deployment already has users. Use the CLI to add "
                   "more.")
    if not bootstrap_tokens.consume(body.token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bootstrap token.")
    try:
        user = users.create(body.email, body.password, Role.SYSTEM_ADMIN)
    except users.UserStoreError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(exc))
    return {"email": user["email"], "role": Role.SYSTEM_ADMIN.value}


@router.post("/logout")
def logout(token: str = Depends(_bearer),
           current_user: Dict[str, Any] = Depends(get_current_user)
           ) -> Dict[str, Any]:
    """Revoke this token by its `jti`.

    There was no logout before: the token carried no id, so a token handed to
    the wrong person stayed valid for its full lifetime and nothing could stop
    it. Revocation is in-process, which is the honest scope for one backend
    container per deployment - a restart clears the list, and short expiry is
    the actual control.
    """
    return {"revoked": revoke(token)}

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
