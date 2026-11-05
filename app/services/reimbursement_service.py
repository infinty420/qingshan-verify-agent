"""报销服务：草稿生成、提交、查询。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Reimbursement, User, utcnow


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def to_out(r: Reimbursement, user_name: str | None = None) -> dict:
    return {
        "id": r.id,
        "user_name": user_name,
        "session_id": r.session_id,
        "expense_type": r.expense_type,
        "amount": r.amount,
        "expense_date": r.expense_date,
        "description": r.description,
        "policy_refs": r.policy_refs or [],
        "status": r.status,
        "created_at": _iso(r.created_at),
        "submitted_at": _iso(r.submitted_at),
    }


async def create_draft(
    db: AsyncSession,
    user_id: int,
    session_id: int | None,
    expense_type: str,
    amount: float,
    expense_date: str,
    description: str,
    policy_refs: list | None,
) -> Reimbursement:
    r = Reimbursement(
        user_id=user_id,
        session_id=session_id,
        expense_type=expense_type or "日常费用",
        amount=float(amount or 0),
        expense_date=expense_date or "",
        description=(description or "")[:500],
        policy_refs=policy_refs or [],
        status="draft",
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def submit(db: AsyncSession, reimb_id: int, user) -> Reimbursement | None:
    """仅本人或管理员可提交。"""
    r = await db.get(Reimbursement, reimb_id)
    if not r:
        return None
    if user.role != "admin" and r.user_id != user.id:
        return None
    r.status = "submitted"
    r.submitted_at = utcnow()
    await db.commit()
    await db.refresh(r)
    return r


async def list_reimbursements(db: AsyncSession, user_id: int | None = None) -> list[dict]:
    stmt = (
        select(Reimbursement, User.display_name)
        .join(User, Reimbursement.user_id == User.id)
        .order_by(Reimbursement.id.desc())
    )
    if user_id is not None:
        stmt = stmt.where(Reimbursement.user_id == user_id)
    rows = (await db.execute(stmt)).all()
    return [to_out(r, uname) for r, uname in rows]
