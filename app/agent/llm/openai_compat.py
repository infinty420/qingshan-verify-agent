"""OpenAI 兼容供应商：/chat/completions（流式问答 + JSON 抽取）。

换供应商只改环境变量：LLM_BASE_URL / LLM_API_KEY / LLM_MODEL，零代码改动。
抽取失败自动回退到规则抽取，保证链路可用。
"""
import json
import re
from typing import AsyncIterator

import httpx

from app.agent.llm.base import LLMProvider
from app.agent.prompts import build_extract_messages, build_qa_messages
from app.agent.tools import extract_reimbursement as rules_extract


class OpenAICompatLLM(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        self.name = f"openai-compat:{model}"
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model

    async def answer_stream(
        self, question: str, hits: list[dict], history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": build_qa_messages(question, hits, history),
            "stream": True,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", f"{self._base}/chat/completions", json=payload, headers=self._headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                    except Exception:
                        continue
                    if delta:
                        yield delta

    async def extract_reimbursement(self, text: str, hits: list[dict] | None = None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions",
                    json={
                        "model": self._model,
                        "messages": build_extract_messages(text, hits),
                        "temperature": 0,
                    },
                    headers=self._headers,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", content, re.S)
            if m:
                data = json.loads(m.group(0))
                return {
                    "expense_type": data.get("expense_type") or "日常费用",
                    "amount": float(data.get("amount") or 0),
                    "expense_date": data.get("expense_date") or "",
                    "description": (data.get("description") or text)[:200],
                    "policy_refs": data.get("policy_refs") or [],
                }
        except Exception:
            pass
        return rules_extract(text, hits)
