"""记录与审计服务：全量操作留痕（只追加）。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


async def audit(
    db: AsyncSession,
    user_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id=None,
    detail: dict | None = None,
):
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=detail,
        )
    )
    await db.commit()


async def list_audit(db: AsyncSession, limit: int = 200) -> list[dict]:
    rows = (
        await db.execute(
            select(AuditLog, User.display_name)
            .join(User, AuditLog.user_id == User.id, isouter=True)
            .order_by(AuditLog.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": a.id,
            "user_name": uname or "系统",
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "detail": a.detail,
            "created_at": _iso(a.created_at),
        }
        for a, uname in rows
    ]
