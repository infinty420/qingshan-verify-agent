"""报销：草稿创建、提交、查询。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import ReimburseIn
from app.services import record_service, reimbursement_service

router = APIRouter()


@router.get("/reimbursements")
async def list_reimbursements(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    uid = None if user.role == "admin" else user.id
    return await reimbursement_service.list_reimbursements(db, uid)


@router.post("/reimbursements")
async def create(
    body: ReimburseIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    r = await reimbursement_service.create_draft(
        db,
        user_id=user.id,
        session_id=body.session_id,
        expense_type=body.expense_type,
        amount=body.amount,
        expense_date=body.expense_date,
        description=body.description,
        policy_refs=None,
    )
    await record_service.audit(
        db, user.id, "reimb_create", "reimbursement", r.id, {"amount": r.amount, "type": r.expense_type}
    )
    return reimbursement_service.to_out(r, user.display_name)


@router.post("/reimbursements/{reimb_id}/submit")
async def submit(
    reimb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    r = await reimbursement_service.submit(db, reimb_id, user)
    if not r:
        raise HTTPException(status_code=404, detail="报销单不存在或无权操作")
    await record_service.audit(
        db, user.id, "reimb_submit", "reimbursement", r.id, {"amount": r.amount, "type": r.expense_type}
    )
    return reimbursement_service.to_out(r, user.display_name)
