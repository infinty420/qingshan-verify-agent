"""对话：会话管理 + SSE 流式问答（智能体编排层入口）。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import orchestrator
from app.core.deps import get_current_user
from app.db.session import SessionFactory, get_db
from app.models import ChatSession, User
from app.schemas import ChatStreamIn, SessionCreateIn
from app.services import chat_service

router = APIRouter()


@router.get("/chat/sessions")
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    uid = None if user.role == "admin" else user.id
    return await chat_service.list_sessions(db, uid)


@router.post("/chat/sessions")
async def create_session(
    body: SessionCreateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    s = await chat_service.create_session(db, user.id, body.title)
    return {"id": s.id, "title": s.title}


@router.get("/chat/sessions/{session_id}/messages")
async def get_messages(
    session_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    s = await db.get(ChatSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    if user.role != "admin" and s.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    return await chat_service.get_messages(db, session_id)


@router.post("/chat/stream")
async def chat_stream(
    body: ChatStreamIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    s = await db.get(ChatSession, body.session_id)
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    if s.user_id != user.id:
        raise HTTPException(status_code=403, detail="只能在自己的会话中提问")

    orch = orchestrator()

    async def gen():
        # 流式响应生命周期长于请求级依赖，这里使用独立数据库会话
        async with SessionFactory() as sdb:
            sess = await sdb.get(ChatSession, body.session_id)
            async for ev in orch.handle(sdb, user, sess, body.content):
                yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
