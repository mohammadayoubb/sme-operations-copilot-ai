from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.services import agent_service

router = APIRouter(prefix="/api/agent", tags=["Agent"])


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []


class ToolCallLog(BaseModel):
    tool: str
    args: dict
    result: dict


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallLog]


@router.post("/chat/stream")
def agent_chat_stream(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        gen = agent_service.chat_stream(
            db,
            message=body.message,
            history=[h.model_dump() for h in body.history],
            business_id=current_user.business_id,
        )
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/chat", response_model=ChatResponse)
def agent_chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        result = agent_service.chat(
            db,
            message=body.message,
            history=[h.model_dump() for h in body.history],
            business_id=current_user.business_id,
        )
        return ChatResponse(
            response=result["response"],
            tool_calls=[ToolCallLog(**tc) for tc in result["tool_calls"]],
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
