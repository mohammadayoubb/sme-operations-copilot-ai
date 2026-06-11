"""Widget API — token management and tenant-scoped agent stream."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.widget_token import WidgetToken
from app.services import agent_service

router = APIRouter(prefix="/api/widget", tags=["Widget"])


class TokenCreateRequest(BaseModel):
    label: str = "My Widget"


class WidgetChatRequest(BaseModel):
    token: str
    message: str
    history: list[dict] = []


def _resolve_token(token: str, db: Session) -> WidgetToken:
    wt = db.query(WidgetToken).filter(WidgetToken.token == token).first()
    if not wt:
        raise HTTPException(401, "Invalid widget token")
    return wt


@router.post("/tokens")
def create_token(
    body: TokenCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    wt = WidgetToken(token=str(uuid.uuid4()), business_id=current_user.business_id, label=body.label)
    db.add(wt)
    db.commit()
    db.refresh(wt)
    return {"token": wt.token, "label": wt.label, "business_id": wt.business_id, "created_at": str(wt.created_at)}


@router.get("/tokens")
def list_tokens(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    tokens = db.query(WidgetToken).filter(WidgetToken.business_id == current_user.business_id).all()
    return [
        {"token": wt.token, "label": wt.label, "business_id": wt.business_id, "created_at": str(wt.created_at)}
        for wt in tokens
    ]


@router.delete("/tokens/{token}")
def delete_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    wt = db.query(WidgetToken).filter(
        WidgetToken.token == token,
        WidgetToken.business_id == current_user.business_id,
    ).first()
    if not wt:
        raise HTTPException(404, "Token not found")
    db.delete(wt)
    db.commit()
    return {"deleted": True}


@router.post("/chat/stream")
def widget_chat_stream(body: WidgetChatRequest, db: Session = Depends(get_db)):
    """Streaming agent endpoint authenticated via widget token (no JWT needed)."""
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
