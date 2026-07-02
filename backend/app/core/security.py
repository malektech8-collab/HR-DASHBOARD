import jwt
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, Optional

# Security configuration variables
SECRET_KEY = "SYNTHETIC_JWT_SECRET_DO_NOT_USE_IN_PROD"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class Role(str, Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    HR_ANALYST = "HR_ANALYST"
    EXECUTIVE = "EXECUTIVE"

# Mock synthetic user database
MOCK_USER_DB: Dict[str, Dict[str, Any]] = {
    "admin@synthetic.local": {
        "email": "admin@synthetic.local",
        "hashed_password": "adminpassword",  # In synthetic mode, direct check is fine
        "role": Role.SYSTEM_ADMIN
    },
    "hr@synthetic.local": {
        "email": "hr@synthetic.local",
        "hashed_password": "hrpassword",
        "role": Role.HR_ANALYST
    },
    "exec@synthetic.local": {
        "email": "exec@synthetic.local",
        "hashed_password": "execpassword",
        "role": Role.EXECUTIVE
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a synthetic JWT token with expiration and user payload data.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes the synthetic JWT and returns the payload data. Returns None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
