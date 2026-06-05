"""Widget API — token management and tenant-scoped agent stream."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.widget_token import WidgetToken
from app.repositories import product_repo
from app.services import agent_service

router = APIRouter(prefix="/api/widget", tags=["Widget"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class TokenCreateRequest(BaseModel):
    label: str = "My Widget"


class WidgetChatRequest(BaseModel):
    token: str
    message: str
    history: list[dict] = []


# ── Token helpers ─────────────────────────────────────────────────────────────

def _resolve_token(token: str, db: Session) -> WidgetToken:
    wt = db.query(WidgetToken).filter(WidgetToken.token == token).first()
    if not wt:
        raise HTTPException(401, "Invalid widget token")
    return wt


# ── Token management endpoints ────────────────────────────────────────────────

@router.post("/tokens")
def create_token(body: TokenCreateRequest, db: Session = Depends(get_db)):
    """Generate a new embed token for the default business."""
    business = product_repo.get_or_create_default_business(db)
    db.flush()
    wt = WidgetToken(token=str(uuid.uuid4()), business_id=business.id, label=body.label)
    db.add(wt)
    db.commit()
    db.refresh(wt)
    return {"token": wt.token, "label": wt.label, "business_id": wt.business_id, "created_at": str(wt.created_at)}


@router.get("/tokens")
def list_tokens(db: Session = Depends(get_db)):
    """List all embed tokens for the default business."""
    business = product_repo.get_or_create_default_business(db)
    db.flush()
    tokens = db.query(WidgetToken).filter(WidgetToken.business_id == business.id).all()
    return [
        {"token": wt.token, "label": wt.label, "business_id": wt.business_id, "created_at": str(wt.created_at)}
        for wt in tokens
    ]


@router.delete("/tokens/{token}")
def delete_token(token: str, db: Session = Depends(get_db)):
    wt = db.query(WidgetToken).filter(WidgetToken.token == token).first()
    if not wt:
        raise HTTPException(404, "Token not found")
    db.delete(wt)
    db.commit()
    return {"deleted": True}


# ── Widget chat stream ────────────────────────────────────────────────────────

@router.post("/chat/stream")
def widget_chat_stream(body: WidgetChatRequest, db: Session = Depends(get_db)):
    """Streaming agent endpoint authenticated via widget token."""
    wt = _resolve_token(body.token, db)
    gen = agent_service.chat_stream(
        db,
        message=body.message,
        history=body.history,
        business_id=wt.business_id,
    )
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
