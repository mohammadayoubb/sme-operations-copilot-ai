from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.business import Business
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    business_name: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    business_id: Optional[int] = None
    role: Optional[str] = None


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new business + owner account. Returns a ready-to-use JWT."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    business = Business(name=payload.business_name)
    db.add(business)
    db.flush()  # get business.id before creating the user

    user = User(
        business_id=business.id,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    db.commit()

    token = create_access_token(sub=user.username, business_id=business.id, role="owner")
    return TokenResponse(access_token=token, username=user.username, business_id=business.id, role="owner")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a JWT carrying the user's business_id.

    Falls back to the hardcoded admin credentials from config so existing
    single-tenant data (business_id=1) remains accessible during the demo.
    """
    from app.core.config import settings
    from app.core.security import verify_admin_password
    from app.repositories.product_repo import get_or_create_default_business

    # 1. Try DB user first
    user = db.query(User).filter(User.username == payload.username).first()
    if user is not None and verify_password(payload.password, user.hashed_password):
        token = create_access_token(sub=user.username, business_id=user.business_id, role=user.role or "owner")
        return TokenResponse(access_token=token, username=user.username, business_id=user.business_id, role=user.role)

    # 2. Fallback: hardcoded admin from config (preserves existing demo data)
    if payload.username == settings.admin_username and verify_admin_password(payload.password):
        business = get_or_create_default_business(db)
        db.commit()
        token = create_access_token(sub=settings.admin_username, business_id=business.id, role="owner")
        return TokenResponse(access_token=token, username=settings.admin_username, business_id=business.id, role="owner")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )
