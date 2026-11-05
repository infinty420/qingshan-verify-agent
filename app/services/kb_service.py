"""知识库服务：文档入库（分块 + 向量化）、版本管理、启停。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.rag.chunker import chunk_markdown
from app.agent.runtime import embedder
from app.models import KBChunk, KBDocument


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def to_out(d: KBDocument) -> dict:
    return {
        "id": d.id,
        "title": d.title,
        "version": d.version,
        "status": d.status,
        "chunk_count": d.chunk_count,
        "created_at": _iso(d.created_at),
        "updated_at": _iso(d.updated_at),
    }


async def ingest_markdown(
    db: AsyncSession, title: str, content: str, uploaded_by: int | None = None
) -> KBDocument:
    """解析 → 分块 → 向量化 → 入库；同标题旧版本自动归档（版本化发布）。"""
    olds = (
        await db.execute(select(KBDocument).where(KBDocument.title == title))
    ).scalars().all()
    version = max([d.version for d in olds], default=0) + 1
    for d in olds:
        d.status = "archived"

    doc = KBDocument(title=title, status="processing", version=version, uploaded_by=uploaded_by)
    db.add(doc)
    await db.flush()

    chunks = chunk_markdown(content)
    if chunks:
        vectors = await embedder().embed(
            [f"{c['section']}。{c['content']}" for c in chunks]
        )
        for i, c in enumerate(chunks):
            db.add(
                KBChunk(
                    document_id=doc.id,
                    chunk_index=i,
                    section=c["section"],
                    content=c["content"],
                    embedding=vectors[i],
                )
            )
    doc.status = "active"
    doc.chunk_count = len(chunks)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_documents(db: AsyncSession) -> list[dict]:
    docs = (await db.execute(select(KBDocument).order_by(KBDocument.id))).scalars().all()
    return [to_out(d) for d in docs]


async def toggle_status(db: AsyncSession, doc_id: int) -> KBDocument | None:
    doc = await db.get(KBDocument, doc_id)
    if not doc:
        return None
    doc.status = "archived" if doc.status == "active" else "active"
    await db.commit()
    await db.refresh(doc)
    return doc
