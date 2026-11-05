"""检索 + 重排：Demo 内存余弦 + 关键词加权；生产切换 pgvector 后走 SQL 检索。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.rag.embedder import _tokens
from app.models import KBChunk, KBDocument


class Retriever:
    def __init__(self, embedder):
        self.embedder = embedder

    async def retrieve(self, db: AsyncSession, query: str, top_k: int = 5) -> list[dict]:
        rows = (
            await db.execute(
                select(KBChunk, KBDocument)
                .join(KBDocument, KBChunk.document_id == KBDocument.id)
                .where(KBDocument.status == "active")
            )
        ).all()
        if not rows:
            return []
        qvec = (await self.embedder.embed([query]))[0]
        qgrams = set(_tokens(query))
        hits = []
        for chunk, doc in rows:
            vec = chunk.embedding or []
            cos = sum(a * b for a, b in zip(qvec, vec))
            cgrams = set(_tokens(chunk.content))
            overlap = len(qgrams & cgrams) / max(len(qgrams), 1)
            score = 0.6 * cos + 0.4 * overlap
            hits.append(
                {
                    "chunk_id": chunk.id,
                    "doc_id": doc.id,
                    "doc_title": doc.title,
                    "section": chunk.section,
                    "excerpt": chunk.content,
                    "score": round(score, 4),
                }
            )
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:top_k]
