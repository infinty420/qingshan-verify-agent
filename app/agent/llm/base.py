"""LLM 供应商抽象接口：问答流式生成 + 报销结构化抽取。实现供应商可热替换。"""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def answer_stream(
        self, question: str, hits: list[dict], history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """基于检索命中（hits）流式生成回答。"""

    @abstractmethod
    async def extract_reimbursement(self, text: str, hits: list[dict] | None = None) -> dict:
        """从用户诉求中抽取报销单结构化字段。"""
