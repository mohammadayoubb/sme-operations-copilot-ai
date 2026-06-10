"""JWT auth helpers — HS256, database-backed multi-tenant users."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)


@lru_cache(maxsize=1)
def _admin_hash() -> str:
    from app.core.config import settings
    return _ctx.hash(settings.admin_password)


def verify_admin_password(plain: str) -> bool:
    return _ctx.verify(plain, _admin_hash())


def create_access_token(sub: str, business_id: Optional[int], role: str = "owner") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload: Dict[str, Any] = {"sub": sub, "role": role, "exp": expire}
    if business_id is not None:
        payload["business_id"] = business_id
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Return the payload dict, or None if the token is invalid/expired."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
