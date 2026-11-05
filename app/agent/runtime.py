"""运行时单例：LLM / Embedder / Retriever / Orchestrator。"""
from functools import lru_cache

from app.agent.llm.factory import get_embedder, get_llm
from app.agent.rag.retriever import Retriever


@lru_cache(maxsize=1)
def llm():
    return get_llm()


@lru_cache(maxsize=1)
def embedder():
    return get_embedder()


@lru_cache(maxsize=1)
def retriever():
    return Retriever(embedder())


@lru_cache(maxsize=1)
def orchestrator():
    from app.agent.orchestrator import AgentOrchestrator

    return AgentOrchestrator(llm(), retriever())
