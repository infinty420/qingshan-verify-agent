"""供应商工厂：由环境变量决定使用哪家 LLM / Embedding。"""
from app.agent.llm.base import LLMProvider
from app.agent.llm.local_demo import LocalDemoLLM
from app.agent.llm.openai_compat import OpenAICompatLLM
from app.agent.rag.embedder import LocalEmbedder, OpenAICompatEmbedder
from app.core.config import settings


def get_llm() -> LLMProvider:
    if settings.llm_provider == "openai_compat" and settings.llm_api_key:
        return OpenAICompatLLM(settings.llm_base_url, settings.llm_api_key, settings.llm_model)
    return LocalDemoLLM()


def get_embedder():
    if settings.embedding_provider == "openai_compat" and settings.llm_api_key:
        return OpenAICompatEmbedder(
            settings.llm_base_url, settings.llm_api_key, settings.embedding_model
        )
    return LocalEmbedder()
