"""知识库管理（仅管理员）：上传入库、列表、启停。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models import User
from app.schemas import KBUploadIn
from app.services import kb_service, record_service

router = APIRouter()


@router.get("/kb/documents")
async def list_documents(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await kb_service.list_documents(db)


@router.post("/kb/documents")
async def upload(
    body: KBUploadIn, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    doc = await kb_service.ingest_markdown(db, body.title, body.content, uploaded_by=admin.id)
    await record_service.audit(
        db, admin.id, "kb_upload", "kb_document", doc.id, {"title": doc.title, "version": doc.version, "chunks": doc.chunk_count}
    )
    return kb_service.to_out(doc)


@router.post("/kb/documents/{doc_id}/toggle")
async def toggle(
    doc_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    doc = await kb_service.toggle_status(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    await record_service.audit(
        db, admin.id, "kb_toggle", "kb_document", doc.id, {"title": doc.title, "status": doc.status}
    )
    return kb_service.to_out(doc)
