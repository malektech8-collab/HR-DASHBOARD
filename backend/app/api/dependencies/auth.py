# -*- coding: utf-8 -*-
"""Who is making this request, and may they.

THE 503 THAT IS NOT A 401.

    A deployment with zero users is not refusing an unauthorised caller - it
    has not been set up. Returning 401 there invites guessing and tells an
    attacker the shape of the door. 503 with "this deployment has not been
    initialised" is the truth, and it makes an uninitialised deployment
    obviously broken rather than quietly open.

THE ROLE IS READ PER REQUEST, NOT TAKEN FROM THE TOKEN.

    Retained from the previous implementation on purpose. Deactivating a user
    or changing their role takes effect on the NEXT REQUEST, not their next
    login. The cost is one indexed read from a local SQLite file.
"""
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core import users
from app.core.security import Role, SecretNotConfigured, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/governance/token")

UNINITIALISED = (
    "This deployment has not been initialised: it has no user accounts. "
    "Create the first administrator with "
    "`python -m app.cli create-admin --email you@example.com`, or use the "
    "one-time bootstrap token printed in the container log."
)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """The authenticated user, or 401. 503 if the deployment has no users."""
    if not users.is_initialised():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=UNINITIALISED)
    try:
        payload = decode_access_token(token)
    except SecretNotConfigured as exc:
        # Real mode with no usable secret. Not the caller's fault and not a
        # credential problem - the deployment cannot verify anything.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if payload is None:
        raise _credentials_exception()

    email = payload.get("sub", "")
    if not email:
        raise _credentials_exception()

    # Read-through to the store on EVERY request. See module docstring.
    user = users.get(email)
    if user is None:
        raise _credentials_exception()
    return user


class RoleChecker:
    """Require one of `allowed_roles`.

    The MECHANISM lands this cycle; the POLICY - which role may see an
    individual salary - is a product and legal decision per client under PDPL
    data minimisation, and belongs with a real client rather than with an
    engineer. docs/phase-3/auth-report.md carries the endpoint list it owes.
    """

    def __init__(self, allowed_roles: List[Role]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Dict[str, Any] = Depends(get_current_user)
                 ) -> Dict[str, Any]:
        if current_user.get("role") not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions")
        return current_user
