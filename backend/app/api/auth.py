import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.business import Business
from app.models.password_reset import PasswordResetToken
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    business_name: str
    username: str
    password: str
    email: Optional[EmailStr] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    business_id: Optional[int] = None
    role: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new business + owner account. Returns a ready-to-use JWT."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    business = Business(name=payload.business_name)
    db.add(business)
    db.flush()

    user = User(
        business_id=business.id,
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    db.commit()

    token = create_access_token(sub=user.username, business_id=business.id, role="owner")
    return TokenResponse(access_token=token, username=user.username, business_id=business.id, role="owner")


@router.post("/forgot-password", status_code=202)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Send a password-reset email if the address is registered.

    Always returns 202 regardless of whether the email exists — prevents
    user enumeration.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return {"detail": "If that email is registered, a reset link has been sent."}

    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).delete(synchronize_session=False)

    token_str = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(PasswordResetToken(user_id=user.id, token=token_str, expires_at=expires))
    db.commit()

    from app.services.email_service import send_password_reset
    background_tasks.add_task(send_password_reset, user.email, token_str)

    return {"detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Validate the reset token and set a new password."""
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")
    if record.used:
        raise HTTPException(status_code=400, detail="This reset link has already been used.")
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired.")

    user = db.get(User, record.user_id)
    user.hashed_password = hash_password(payload.new_password)
    record.used = True
    db.commit()

    return {"detail": "Password updated successfully."}


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
