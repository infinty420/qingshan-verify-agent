"""全局配置：Demo 默认零外部依赖（SQLite + 本地抽取式 LLM + 本地向量）。

生产切换（OpenAI 兼容协议，供应商可热替换）只需设置环境变量：
  LLM_PROVIDER=openai_compat
  LLM_BASE_URL=https://api.moonshot.cn/v1   （或任意兼容供应商）
  LLM_API_KEY=sk-xxx
  LLM_MODEL=kimi-k2
数据库切换 PostgreSQL + pgvector：
  DATABASE_URL=postgresql+asyncpg://user:pass@host/db
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings:
    app_name: str = os.getenv("APP_NAME", "开店筹备与运营验收 · 业务核对助手")

    data_dir: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{(BASE_DIR / 'data' / 'verify_agent.db').as_posix()}",
    )

    # 鉴权
    secret_key: str = os.getenv("SECRET_KEY", "demo-secret-change-in-prod")
    token_expire_hours: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

    # LLM（OpenAI 兼容协议；local_demo 为离线演示供应商）
    llm_provider: str = os.getenv("LLM_PROVIDER", "local_demo")  # local_demo | openai_compat
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Embedding（可与 LLM 不同供应商）
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local_demo")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # RAG 参数
    top_k: int = int(os.getenv("TOP_K", "5"))
    retrieval_threshold: float = float(os.getenv("RETRIEVAL_THRESHOLD", "0.12"))

    # 种子知识库目录
    knowledge_dir: Path = BASE_DIR / "knowledge_docs"

    port: int = int(os.getenv("PORT", "8790"))


settings = Settings()
