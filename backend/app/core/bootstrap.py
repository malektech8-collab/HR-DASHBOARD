# -*- coding: utf-8 -*-
"""The one-time bootstrap token, for a deployment with no shell.

The CLI (app/cli.py) is the primary path and is better: an operator with a
shell types a password into getpass and nothing is ever written down. This is
the fallback for vendor-hosted, where the operator's only channel is
`docker compose logs`.

PROPERTIES, each of which is the point:

  * generated ONLY when the store has zero users
  * held in process memory - never written to disk, never in an env var
  * single use
  * expires in 60 minutes
  * destroyed the moment any account exists

So there is no credential at rest at any moment, which is the requirement the
hardcoded dict could not meet.
"""
import datetime
import secrets
from typing import Optional

from app.core import users

TOKEN_TTL_MINUTES = 60

_token: Optional[str] = None
_expires_at: Optional[datetime.datetime] = None


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def issue_if_needed() -> Optional[str]:
    """Called at startup. Returns the token if one is needed, else None."""
    global _token, _expires_at
    users.initialise()
    if users.is_initialised():
        _token, _expires_at = None, None
        return None
    _token = secrets.token_urlsafe(48)
    _expires_at = _now() + datetime.timedelta(minutes=TOKEN_TTL_MINUTES)
    return _token


def announce(token: str) -> None:
    line = "=" * 68
    print(line)
    print(" THIS DEPLOYMENT HAS NO USERS.")
    print("")
    print(" Create the first administrator, either:")
    print("   python -m app.cli create-admin --email you@example.com")
    print(" or POST /api/governance/bootstrap with this one-time token:")
    print("")
    print("   {}".format(token))
    print("")
    print(" Single use. Expires in {} minutes. Not stored on disk, and"
          .format(TOKEN_TTL_MINUTES))
    print(" destroyed the moment the first account exists.")
    print(line)


def consume(token: str) -> bool:
    """True if `token` is the live bootstrap token. Invalidates it either way
    it is used successfully."""
    global _token, _expires_at
    if users.is_initialised():
        _token, _expires_at = None, None
        return False
    if not _token or not token:
        return False
    if _expires_at and _now() > _expires_at:
        _token, _expires_at = None, None
        return False
    if not secrets.compare_digest(_token, token):
        return False
    _token, _expires_at = None, None
    return True


def is_pending() -> bool:
    return _token is not None and not users.is_initialised()


def _reset_for_tests() -> None:
    global _token, _expires_at
    _token, _expires_at = None, None
