"""离线演示供应商：基于检索结果的抽取式回答，无外部 API 依赖。

护栏规则：检索得分不足时拒绝回答（无出处即不回答），与真实 LLM 的提示词约束一致。
"""
import asyncio
import re
from typing import AsyncIterator

from app.agent.llm.base import LLMProvider
from app.agent.rag.embedder import _tokens
from app.agent.tools import extract_reimbursement as rules_extract

NO_REFUSAL = (
    "抱歉，我在现行制度库中没有找到与这个问题直接相关的条款。"
    "为避免无出处的误导，我不做推测性回答——建议换一个问法，或联系管理员补充对应制度文档。"
)

_SENT_SPLIT = re.compile(r"(?<=[。！？；;])")


class LocalDemoLLM(LLMProvider):
    name = "local-demo-extractive-v1"

    async def answer_stream(
        self, question: str, hits: list[dict], history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        parts = self._compose(question, hits)
        if not parts:
            yield NO_REFUSAL
            return
        text = "根据现行制度库，检索到以下依据：\n\n"
        for i, (hit, sent) in enumerate(parts, 1):
            text += f"{i}. 《{hit['doc_title']}》· {hit['section']}\n{sent}\n\n"
        text += "以上均为制度原文摘录，可点击消息下方出处核对完整条款；如需人工确认，请联系财务制度管理员。"
        for i in range(0, len(text), 16):
            await asyncio.sleep(0.015)
            yield text[i : i + 16]

    async def extract_reimbursement(self, text: str, hits: list[dict] | None = None) -> dict:
        return rules_extract(text, hits)

    def _compose(self, question: str, hits: list[dict]) -> list[tuple[dict, str]]:
        """从命中分块中挑选与问题最相关的句子，拼装带出处的回答。"""
        if not hits or hits[0]["score"] < 0.18:
            return []
        qgrams = set(_tokens(question))
        parts: list[tuple[dict, str]] = []
        for hit in hits[:3]:
            if hit["score"] < 0.14:
                continue
            sents = [s for s in _SENT_SPLIT.split(hit["excerpt"]) if len(s.strip()) >= 8]
            scored = sorted(sents, key=lambda s: -len(qgrams & set(_tokens(s))))
            best = "".join(scored[:2])[:260].strip()
            if best:
                parts.append((hit, best))
        return parts
