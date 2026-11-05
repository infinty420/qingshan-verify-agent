"""智能体编排主流程：意图路由 → RAG 检索 → 生成 / 结构化抽取 → 动作与留痕。

产出事件流（dict），由 API 层转换为 SSE：
  {"type": "citations", "items": [...]}     引用出处
  {"type": "delta", "text": "..."}          流式回答片段
  {"type": "draft", "draft": {...}}         报销草稿（reimbursement 意图）
  {"type": "done", "intent": "..."}         结束
"""
import asyncio

from app.agent.intent import detect_intent
from app.core.config import settings
from app.services import chat_service, reimbursement_service


def _draft_out(r) -> dict:
    return {
        "id": r.id,
        "session_id": r.session_id,
        "expense_type": r.expense_type,
        "amount": r.amount,
        "expense_date": r.expense_date,
        "description": r.description,
        "policy_refs": r.policy_refs or [],
        "status": r.status,
    }


class AgentOrchestrator:
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever

    async def _stream_text(self, text: str):
        for i in range(0, len(text), 16):
            await asyncio.sleep(0.015)
            yield text[i : i + 16]

    @staticmethod
    def _cite(hit: dict) -> dict:
        return {
            "doc_title": hit["doc_title"],
            "section": hit["section"],
            "excerpt": hit["excerpt"][:160],
            "score": hit["score"],
        }

    async def handle(self, db, user, session, content):
        # 1) 意图路由
        intent = detect_intent(content)

        # 2) 落库用户消息 + 自动会话标题
        await chat_service.add_message(db, session.id, "user", content)
        if not session.title or session.title == "新会话":
            session.title = content[:20]
            await db.commit()

        # 3) RAG 检索
        hits = await self.retriever.retrieve(db, content, top_k=settings.top_k)

        if intent == "reimbursement":
            # 4a) 结构化抽取 → 报销草稿
            data = await self.llm.extract_reimbursement(content, hits)
            draft = await reimbursement_service.create_draft(
                db,
                user_id=user.id,
                session_id=session.id,
                expense_type=data["expense_type"],
                amount=data["amount"],
                expense_date=data["expense_date"],
                description=data["description"],
                policy_refs=data["policy_refs"],
            )
            citations = data.get("policy_refs") or []
            yield {"type": "citations", "items": citations}
            text = (
                f"已为您生成报销草稿：{data['expense_type']} · ¥{data['amount']:,.2f}。\n\n"
                "请核对下方草稿卡片中的信息（费用类型 / 金额 / 日期 / 制度依据），"
                "确认无误后点击「提交报销」；如需调整，直接告诉我即可。"
            )
            async for seg in self._stream_text(text):
                yield {"type": "delta", "text": seg}
            yield {"type": "draft", "draft": _draft_out(draft)}
            await chat_service.add_message(
                db,
                session.id,
                "assistant",
                text,
                intent="reimbursement",
                citations=citations,
                llm_model=self.llm.name,
            )
            yield {"type": "done", "intent": intent, "draft_id": draft.id}
        else:
            # 4b) RAG 问答（无引用即拒绝回答的护栏在 LLM 供应商内实现）
            citations = [
                self._cite(h) for h in hits[:3] if h["score"] >= settings.retrieval_threshold
            ]
            yield {"type": "citations", "items": citations}
            parts: list[str] = []
            async for seg in self.llm.answer_stream(content, hits):
                parts.append(seg)
                yield {"type": "delta", "text": seg}
            answer = "".join(parts)
            await chat_service.add_message(
                db,
                session.id,
                "assistant",
                answer,
                intent="qa",
                citations=citations or None,
                llm_model=self.llm.name,
            )
            yield {"type": "done", "intent": intent}
