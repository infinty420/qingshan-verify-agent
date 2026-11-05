"""向量化：本地 bigram 哈希向量（离线 Demo）+ OpenAI 兼容 Embedding（生产可替换）。

注意：切换 embedding 供应商会改变向量维度与语义空间，需全量重嵌入知识库
（生产环境提供 scripts/reindex.py，见 README）。
"""
import hashlib
import math
import re

DIM = 256
_CJK = re.compile(r"[\u4e00-\u9fff]")
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    text = text.lower()
    grams = _WORD.findall(text)
    cjk = _CJK.findall(text)
    grams.extend("".join(cjk[i : i + 2]) for i in range(len(cjk) - 1))
    if len(cjk) == 1:
        grams.append(cjk[0])
    return grams


def _hash(g: str) -> int:
    return int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)


class LocalEmbedder:
    """字符 bigram + 英文词 哈希 TF 向量，L2 归一化。零依赖、确定性，适合 Demo。"""

    name = "local-bigram-256"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        v = [0.0] * DIM
        for g in _tokens(text):
            v[_hash(g) % DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


class OpenAICompatEmbedder:
    """OpenAI 兼容 /embeddings 接口，切换供应商只改 base_url / model / api_key。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        import httpx

        self.name = f"openai-compat:{model}"
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base}/embeddings",
                json={"model": self._model, "input": texts},
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()["data"]
        return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]
