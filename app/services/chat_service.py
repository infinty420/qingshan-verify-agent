"""对话服务：会话与消息管理。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, ChatSession, User, utcnow


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


async def create_session(db: AsyncSession, user_id: int, title: str = "新会话") -> ChatSession:
    s = ChatSession(user_id=user_id, title=(title or "新会话")[:100])
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def list_sessions(db: AsyncSession, user_id: int | None = None) -> list[dict]:
    """user_id=None 时返回全部（管理员视角），附带用户名与消息数。"""
    stmt = select(ChatSession, User.display_name).join(User, ChatSession.user_id == User.id)
    if user_id is not None:
        stmt = stmt.where(ChatSession.user_id == user_id)
    stmt = stmt.order_by(func.coalesce(ChatSession.last_message_at, ChatSession.created_at).desc())
    rows = (await db.execute(stmt)).all()
    counts = {
        sid: cnt
        for sid, cnt in (
            await db.execute(
                select(ChatMessage.session_id, func.count(ChatMessage.id)).group_by(
                    ChatMessage.session_id
                )
            )
        ).all()
    }
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": _iso(s.created_at),
            "last_message_at": _iso(s.last_message_at),
            "user_name": uname,
            "message_count": counts.get(s.id, 0),
        }
        for s, uname in rows
    ]


async def get_messages(db: AsyncSession, session_id: int) -> list[dict]:
    msgs = (
        await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)
        )
    ).scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "intent": m.intent,
            "citations": m.citations,
            "created_at": _iso(m.created_at),
        }
        for m in msgs
    ]


async def add_message(
    db: AsyncSession,
    session_id: int,
    role: str,
    content: str,
    intent: str | None = None,
    citations: list | None = None,
    llm_model: str | None = None,
) -> ChatMessage:
    m = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        intent=intent,
        citations=citations,
        llm_model=llm_model,
    )
    db.add(m)
    s = await db.get(ChatSession, session_id)
    if s:
        s.last_message_at = utcnow()
    await db.commit()
    return m
