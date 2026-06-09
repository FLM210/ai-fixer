"""知识库向量检索服务。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import asyncpg
from pgvector.asyncpg import register_vector

from app.memory.embedding import EmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeSearchResult:
    entry_id: str
    title: str
    content: str
    category: str | None
    tags: list[str]
    source_type: str
    use_count: int
    similarity: float


class KnowledgeSearchService:
    """基于 pgvector 的知识库语义检索。"""

    def __init__(self, db_url: str, embedding_client: EmbeddingClient) -> None:
        self._db_url = db_url
        self._embedding = embedding_client

    async def search(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 5,
        min_similarity: float = 0.6,
    ) -> list[KnowledgeSearchResult]:
        """语义检索知识条目。

        Args:
            query: 查询文本（告警内容或问题描述）
            category: 可选的分类过滤
            limit: 返回条数
            min_similarity: 最低相似度阈值

        Returns:
            按相似度降序排列的结果列表
        """
        embedding = await self._embedding.embed(query)

        conn = await asyncpg.connect(self._db_url)
        try:
            await register_vector(conn)

            if category:
                rows = await conn.fetch(
                    """
                    SELECT
                        id::text,
                        title,
                        content,
                        category,
                        tags,
                        source_type,
                        use_count,
                        1 - (embedding <=> $1) AS similarity
                    FROM fixer.knowledge_entries
                    WHERE status = 'published'
                        AND embedding IS NOT NULL
                        AND category = $2
                        AND 1 - (embedding <=> $1) >= $3
                    ORDER BY
                        CASE WHEN use_count > 0 THEN 0 ELSE 1 END,
                        embedding <=> $1
                    LIMIT $4
                """,
                    embedding,
                    category,
                    min_similarity,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT
                        id::text,
                        title,
                        content,
                        category,
                        tags,
                        source_type,
                        use_count,
                        1 - (embedding <=> $1) AS similarity
                    FROM fixer.knowledge_entries
                    WHERE status = 'published'
                        AND embedding IS NOT NULL
                        AND 1 - (embedding <=> $1) >= $2
                    ORDER BY
                        CASE WHEN use_count > 0 THEN 0 ELSE 1 END,
                        embedding <=> $1
                    LIMIT $3
                """,
                    embedding,
                    min_similarity,
                    limit,
                )

            return [
                KnowledgeSearchResult(
                    entry_id=r["id"],
                    title=r["title"],
                    content=r["content"][:500],
                    category=r["category"],
                    tags=r["tags"] or [],
                    source_type=r["source_type"],
                    use_count=r["use_count"],
                    similarity=round(r["similarity"], 3),
                )
                for r in rows
            ]
        finally:
            await conn.close()
