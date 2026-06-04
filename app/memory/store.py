"""基于 pgvector 的 Incident 向量记忆存储。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg
from pgvector.asyncpg import register_vector

from app.memory.embedding import EmbeddingClient


@dataclass
class SimilarIncident:
    incident_id: str
    alert_text: str
    category: str | None
    diagnosis_summary: str | None
    fix_applied: str | None
    outcome: str | None
    similarity: float


class IncidentMemoryStore:
    """存储和检索 incident 向量记忆。"""

    def __init__(self, db_url: str, embedding_client: EmbeddingClient) -> None:
        self._db_url = db_url
        self._embedding = embedding_client

    async def setup(self) -> None:
        """初始化 pgvector 扩展和 incident_memories 表。"""
        conn = await asyncpg.connect(self._db_url)
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await register_vector(conn)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fixer.incident_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    incident_id UUID NOT NULL REFERENCES fixer.incidents(id) ON DELETE CASCADE,
                    embedding vector(%d) NOT NULL,
                    alert_text TEXT NOT NULL,
                    category TEXT,
                    diagnosis_summary TEXT,
                    fix_applied TEXT,
                    outcome TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """ % self._embedding.dimension)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_incident_memories_embedding
                ON fixer.incident_memories USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_incident_memories_incident_id
                ON fixer.incident_memories (incident_id)
            """)
        finally:
            await conn.close()

    async def store(
        self,
        incident_id: str | UUID,
        alert_text: str,
        category: str | None,
        diagnosis_summary: str | None,
        fix_applied: str | None,
        outcome: str | None,
    ) -> None:
        """存储一个 incident 的向量记忆。"""
        # 拼接用于 embedding 的文本
        embed_text = self._build_embed_text(alert_text, category, diagnosis_summary, fix_applied)
        embedding = await self._embedding.embed(embed_text)

        conn = await asyncpg.connect(self._db_url)
        try:
            await register_vector(conn)
            await conn.execute("""
                INSERT INTO fixer.incident_memories
                    (incident_id, embedding, alert_text, category, diagnosis_summary, fix_applied, outcome)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, incident_id, embedding, alert_text, category, diagnosis_summary, fix_applied, outcome)
        finally:
            await conn.close()

    async def search(
        self,
        alert_text: str,
        category: str | None = None,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[SimilarIncident]:
        """语义检索相似的历史 incident。"""
        query_text = self._build_embed_text(alert_text, category, None, None)
        embedding = await self._embedding.embed(query_text)

        conn = await asyncpg.connect(self._db_url)
        try:
            await register_vector(conn)
            rows = await conn.fetch("""
                SELECT
                    incident_id::text,
                    alert_text,
                    category,
                    diagnosis_summary,
                    fix_applied,
                    outcome,
                    1 - (embedding <=> $1) AS similarity
                FROM fixer.incident_memories
                WHERE 1 - (embedding <=> $1) >= $2
                ORDER BY embedding <=> $1
                LIMIT $3
            """, embedding, min_similarity, limit)

            return [
                SimilarIncident(
                    incident_id=r["incident_id"],
                    alert_text=r["alert_text"],
                    category=r["category"],
                    diagnosis_summary=r["diagnosis_summary"],
                    fix_applied=r["fix_applied"],
                    outcome=r["outcome"],
                    similarity=r["similarity"],
                )
                for r in rows
            ]
        finally:
            await conn.close()

    @staticmethod
    def _build_embed_text(
        alert_text: str,
        category: str | None,
        diagnosis_summary: str | None,
        fix_applied: str | None,
    ) -> str:
        """构建用于 embedding 的文本。"""
        parts = [alert_text]
        if category:
            parts.append(f"类别: {category}")
        if diagnosis_summary:
            parts.append(f"诊断: {diagnosis_summary}")
        if fix_applied:
            parts.append(f"修复: {fix_applied}")
        return "\n".join(parts)
