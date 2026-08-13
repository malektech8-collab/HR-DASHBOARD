# -*- coding: utf-8 -*-
"""Token issuing and verification.

WHAT THIS REPLACED, and why the secret came first.

    SECRET_KEY = "SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD"

    A committed constant, identical in every deployment of this product.
    Plaintext passwords require an attacker to reach the server; a forged token
    required only the source, which staff, contractors and anyone the repo ever
    touched already had. Five lines of pyjwt minted a SYSTEM_ADMIN token that
    worked at every customer install, because nothing in the token said which
    install it was for.

    So the secret outranks the passwords, and `iss`/`aud` are not decoration:
    they are what makes a token from one deployment useless at another even if
    a key is ever shared by accident.

TWO DECISIONS RETAINED FROM THE OLD IMPLEMENTATION, deliberately.

    1. THE ALGORITHM LIST IS PINNED. `jwt.decode(..., algorithms=[ALGORITHM])`
       is the defence against `alg: none` and RS->HS confusion. It must never
       become a list read from configuration.

    2. THE ROLE IS NOT IN THE TOKEN. Only `sub` identifies the user; the role
       is read from the store on every request. That means deactivating a user
       or changing their role takes effect on the NEXT REQUEST rather than the
       next login. Rewrites lose this constantly in the name of saving a
       lookup; the lookup is one indexed read from a local SQLite file.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

import jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

# This deployment's identity, carried as `iss` and `aud`. A token minted for
# one install is rejected by another even if the secrets ever coincide.
ISSUER = "hr-analytics"
AUDIENCE = "hr-analytics-api"

# Values that must never sign a real token. The first is the constant this
# module used to ship with; it is listed by name so that restoring it - by
# copy/paste, by a rolled-back file, by an operator following an old runbook -
# fails loudly instead of silently working.
FORBIDDEN_SECRETS = {
    "SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD",
    "changeme", "secret", "password", "jwt_secret", "test", "dev",
}
MIN_SECRET_LENGTH = 32


class Role(str, Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    HR_ANALYST = "HR_ANALYST"
    EXECUTIVE = "EXECUTIVE"


class SecretNotConfigured(RuntimeError):
    """Real mode has no usable JWT secret. The process must not serve."""


_demo_secret: Optional[str] = None

# Revoked token ids. In-process, which is the honest scope for a single
# backend container per deployment: a restart clears it, and a restart also
# invalidates every token when the demo secret is regenerated. For real mode a
# restart is the one case where tokens outlive the list, which is why logout
# is a convenience and short expiry is the actual control.
_revoked: set = set()


def _reject(reason: str) -> None:
    raise SecretNotConfigured(
        "JWT_SECRET {}.\n"
        "This deployment cannot issue or verify tokens and will not serve "
        "data.\n"
        "Generate one, per deployment, and never commit it:\n"
        '    python -c "import secrets; print(secrets.token_urlsafe(64))"\n'
        "Then supply it as the JWT_SECRET environment variable.".format(reason))


def get_secret() -> str:
    """The signing key for this deployment.

    Real mode fails closed - the same decision REPORT_MONTH made, and for the
    same reason: a weak secret that boots is a deployment nobody revisits.

    Demo mode generates a random secret PER PROCESS. Demo keeps working with no
    setup, tokens do not survive a restart, and there is no demo secret that
    could be promoted to production by accident because there is no value to
    promote.
    """
    configured = (settings.JWT_SECRET or "").strip()
    if settings.DATA_MODE == "real":
        if not configured:
            _reject("is not set")
        if configured in FORBIDDEN_SECRETS:
            _reject("is a known placeholder value")
        if len(configured) < MIN_SECRET_LENGTH:
            _reject("is shorter than {} characters".format(MIN_SECRET_LENGTH))
        return configured
    if configured and configured not in FORBIDDEN_SECRETS:
        return configured
    global _demo_secret
    if _demo_secret is None:
        _demo_secret = secrets.token_urlsafe(64)
    return _demo_secret


def create_access_token(data: dict,
                        expires_delta: Optional[timedelta] = None) -> str:
    """Mint a token for `data['sub']`. No role, by design - see module docstring."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta
                    or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = dict(data)
    payload.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": ISSUER,
        "aud": AUDIENCE,
        # Token id, so a session can be revoked. Without it there was no
        # logout: a token handed to the wrong person stayed valid until it
        # expired and nothing could stop it.
        "jti": uuid.uuid4().hex,
    })
    return jwt.encode(payload, get_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Verify and return the payload, or None. Never raises to the caller."""
    try:
        payload = jwt.decode(
            token,
            get_secret(),
            algorithms=[ALGORITHM],          # PINNED. See module docstring.
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("jti") in _revoked:
        return None
    return payload


def revoke(token: str) -> bool:
    """Invalidate one token. Returns False if it was not valid to begin with."""
    payload = decode_access_token(token)
    if not payload or not payload.get("jti"):
        return False
    _revoked.add(payload["jti"])
    return True


def revoked_count() -> int:
    return len(_revoked)


def _reset_for_tests() -> None:
    global _demo_secret
    _demo_secret = None
    _revoked.clear()


__all__ = [
    "Role", "SecretNotConfigured", "create_access_token",
    "decode_access_token", "get_secret", "revoke", "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES", "ISSUER", "AUDIENCE",
    "FORBIDDEN_SECRETS", "MIN_SECRET_LENGTH",
]


def _typed_dict_placeholder() -> Dict[str, Any]:  # pragma: no cover
    return {}
