"""记录查询（仅管理员）：全部问答会话 + 审计日志。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models import User
from app.services import chat_service, record_service

router = APIRouter()


@router.get("/records/sessions")
async def all_sessions(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await chat_service.list_sessions(db, None)


@router.get("/records/audit")
async def audit_list(
    limit: int = 200, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    return await record_service.list_audit(db, limit)
