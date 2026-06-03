from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import agent_service

router = APIRouter(prefix="/api/agent", tags=["Agent"])


class HistoryMessage(BaseModel):
    role: str   # "user" or "assistant"
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
def agent_chat_stream(body: ChatRequest, db: Session = Depends(get_db)):
    """Streaming version — yields SSE events as the agent thinks and calls tools."""
    try:
        gen = agent_service.chat_stream(
            db,
            message=body.message,
            history=[h.model_dump() for h in body.history],
        )
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/chat", response_model=ChatResponse)
def agent_chat(body: ChatRequest, db: Session = Depends(get_db)):
    try:
        result = agent_service.chat(
            db,
            message=body.message,
            history=[h.model_dump() for h in body.history],
        )
        return ChatResponse(
            response=result["response"],
            tool_calls=[ToolCallLog(**tc) for tc in result["tool_calls"]],
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
