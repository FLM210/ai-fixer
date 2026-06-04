"""Embedding 客户端：使用 OpenAI 兼容 API 生成向量。"""

from __future__ import annotations

import httpx


class EmbeddingClient:
    """OpenAI 兼容的 embedding API 客户端。"""

    def __init__(self, base_url: str, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dimension = 1536  # text-embedding-3-small 默认维度

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """生成单条文本的 embedding。"""
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding。"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": texts, "model": self._model},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        # 按 index 排序确保顺序正确
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]
