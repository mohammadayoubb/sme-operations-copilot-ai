"""FastAPI dependency: resolve the current authenticated user from a Bearer token."""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    username: str
    business_id: Optional[int]
    role: str = "owner"


def _decode_bearer(creds: HTTPAuthorizationCredentials | None) -> dict:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(creds.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """Validate Bearer token and return a CurrentUser with business_id, or raise 401.

    Rejects superadmin tokens — they must use get_current_superadmin instead.
    """
    payload = _decode_bearer(creds)
    bid = payload.get("business_id")
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        username=payload["sub"],
        business_id=int(bid),
        role=payload.get("role", "owner"),
    )


def get_current_superadmin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """Validate Bearer token and return a CurrentUser only if role == superadmin."""
    payload = _decode_bearer(creds)
    if payload.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return CurrentUser(
        username=payload["sub"],
        business_id=None,
        role="superadmin",
    )
