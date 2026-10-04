"""角色对话（M02.F01 SSE 流 + M02.F03 会话收束）。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from kids_english.agent.tutor import ChatTutor
from kids_english.api.helpers import chat_llm, child_or_404, get_engine, get_store, sse_line

router = APIRouter(tags=["chat"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    session_id: str | None = None


class EndIn(BaseModel):
    child_id: str
    notes: str = "家长手动结束"


@router.post("/api/children/{child_id}/chat")
def chat(child_id: str, body: ChatIn, request: Request):
    child_or_404(request, child_id)
    tutor = ChatTutor(
        llm=chat_llm(request, child_id),
        store=get_store(request),
        engine=get_engine(request),
        child_id=child_id,
    )
    return StreamingResponse(
        (sse_line(ev) for ev in tutor.reply(body.session_id, body.text)),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/api/sessions/{session_id}/end")
def end_session(session_id: str, body: EndIn, request: Request):
    child_or_404(request, body.child_id)
    tutor = ChatTutor(
        llm=chat_llm(request, body.child_id),
        store=get_store(request),
        engine=get_engine(request),
        child_id=body.child_id,
    )
    result = tutor.end_session(session_id, body.notes)
    if not result.get("ok"):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=result.get("error", "session 不存在"))
    return result
