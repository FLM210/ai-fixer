"""知识库服务层：CRUD、版本历史、向量检索、过期检查。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge_entry import KnowledgeEntry
from app.db.models.knowledge_revision import KnowledgeRevision

logger = logging.getLogger(__name__)

# 过期天数：超过此天数未使用的条目标记为 review
STALE_DAYS = 90


class KnowledgeService:
    """知识库业务逻辑。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── CRUD ──────────────────────────────────────────────────────

    async def create(
        self,
        title: str,
        content: str,
        category: str | None = None,
        tags: list[str] | None = None,
        source_type: str = "manual",
        source_incident_id: str | UUID | None = None,
        created_by: str | None = None,
        status: str = "published",
    ) -> KnowledgeEntry:
        """创建知识条目，并自动生成第一个 revision。"""
        entry = KnowledgeEntry(
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            source_type=source_type,
            source_incident_id=source_incident_id,
            created_by=created_by,
            status=status,
            current_revision=1,
        )
        self._session.add(entry)
        await self._session.flush()

        # 创建第一个版本
        revision = KnowledgeRevision(
            entry_id=entry.id,
            revision_number=1,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            change_summary="初始版本",
            created_by=created_by,
        )
        self._session.add(revision)
        await self._session.flush()

        return entry

    async def get(self, entry_id: str | UUID) -> KnowledgeEntry | None:
        """获取单个知识条目。"""
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        entry_id: str | UUID,
        *,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        change_summary: str | None = None,
        updated_by: str | None = None,
    ) -> KnowledgeEntry | None:
        """更新知识条目，并自动创建新 revision。"""
        entry = await self.get(entry_id)
        if entry is None:
            return None

        changed = False
        if title is not None and title != entry.title:
            entry.title = title
            changed = True
        if content is not None and content != entry.content:
            entry.content = content
            changed = True
        if category is not None and category != entry.category:
            entry.category = category
            changed = True
        if tags is not None and tags != entry.tags:
            entry.tags = tags
            changed = True
        if status is not None:
            entry.status = status
            changed = True

        if changed:
            new_rev = entry.current_revision + 1
            entry.current_revision = new_rev
            revision = KnowledgeRevision(
                entry_id=entry.id,
                revision_number=new_rev,
                title=entry.title,
                content=entry.content,
                category=entry.category,
                tags=entry.tags,
                change_summary=change_summary or "内容更新",
                created_by=updated_by,
            )
            self._session.add(revision)
            await self._session.flush()
            # 刷新对象以确保所有属性已加载
            await self._session.refresh(entry)

        return entry

    async def delete(self, entry_id: str | UUID) -> bool:
        """删除知识条目（级联删除 revision 和 relation）。"""
        entry = await self.get(entry_id)
        if entry is None:
            return False
        await self._session.delete(entry)
        await self._session.flush()
        return True

    async def list_entries(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        source_type: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[KnowledgeEntry], int]:
        """列表查询知识条目，支持筛选和分页。"""
        stmt = select(KnowledgeEntry)
        count_stmt = select(func.count()).select_from(KnowledgeEntry)

        if status:
            stmt = stmt.where(KnowledgeEntry.status == status)
            count_stmt = count_stmt.where(KnowledgeEntry.status == status)
        if category:
            stmt = stmt.where(KnowledgeEntry.category == category)
            count_stmt = count_stmt.where(KnowledgeEntry.category == category)
        if source_type:
            stmt = stmt.where(KnowledgeEntry.source_type == source_type)
            count_stmt = count_stmt.where(KnowledgeEntry.source_type == source_type)
        if keyword:
            like_pattern = f"%{keyword}%"
            stmt = stmt.where(
                KnowledgeEntry.title.ilike(like_pattern)
                | KnowledgeEntry.content.ilike(like_pattern)
            )
            count_stmt = count_stmt.where(
                KnowledgeEntry.title.ilike(like_pattern)
                | KnowledgeEntry.content.ilike(like_pattern)
            )

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(KnowledgeEntry.updated_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        entries = list(result.scalars().all())

        return entries, total

    # ── 版本历史 ─────────────────────────────────────────────────

    async def get_revisions(self, entry_id: str | UUID) -> list[KnowledgeRevision]:
        """获取条目的所有版本历史，按版本号降序。"""
        stmt = (
            select(KnowledgeRevision)
            .where(KnowledgeRevision.entry_id == entry_id)
            .order_by(KnowledgeRevision.revision_number.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_revision(
        self, entry_id: str | UUID, revision_number: int
    ) -> KnowledgeRevision | None:
        """获取指定版本。"""
        stmt = select(KnowledgeRevision).where(
            KnowledgeRevision.entry_id == entry_id,
            KnowledgeRevision.revision_number == revision_number,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def rollback(
        self, entry_id: str | UUID, revision_number: int, rolled_back_by: str | None = None
    ) -> KnowledgeEntry | None:
        """回滚到指定版本。"""
        revision = await self.get_revision(entry_id, revision_number)
        if revision is None:
            return None
        return await self.update(
            entry_id,
            title=revision.title,
            content=revision.content,
            category=revision.category,
            tags=revision.tags,
            change_summary=f"回滚到版本 {revision_number}",
            updated_by=rolled_back_by,
        )

    # ── 使用追踪 ─────────────────────────────────────────────────

    async def record_usage(self, entry_id: str | UUID) -> None:
        """记录知识条目被使用一次。"""
        stmt = (
            update(KnowledgeEntry)
            .where(KnowledgeEntry.id == entry_id)
            .values(
                use_count=KnowledgeEntry.use_count + 1,
                last_used_at=datetime.now(UTC),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    # ── 过期检查 ─────────────────────────────────────────────────

    async def check_stale_entries(self) -> list[KnowledgeEntry]:
        """将超过 STALE_DAYS 天未使用的 published 条目标记为 review。
        返回被标记的条目列表。
        """
        cutoff = datetime.now(UTC) - timedelta(days=STALE_DAYS)
        stmt = select(KnowledgeEntry).where(
            KnowledgeEntry.status == "published",
            (KnowledgeEntry.last_used_at.is_(None) & (KnowledgeEntry.created_at < cutoff))
            | (KnowledgeEntry.last_used_at < cutoff),
        )
        result = await self._session.execute(stmt)
        stale_entries = list(result.scalars().all())

        for entry in stale_entries:
            entry.status = "review"

        if stale_entries:
            await self._session.flush()
            logger.info("标记 %d 条过期知识条目为 review", len(stale_entries))

        return stale_entries

    # ── 统计 ─────────────────────────────────────────────────────

    async def stats(self) -> dict[str, Any]:
        """返回知识库统计信息。"""
        total_stmt = select(func.count()).select_from(KnowledgeEntry)
        published_stmt = (
            select(func.count())
            .select_from(KnowledgeEntry)
            .where(KnowledgeEntry.status == "published")
        )
        review_stmt = (
            select(func.count())
            .select_from(KnowledgeEntry)
            .where(KnowledgeEntry.status == "review")
        )

        total = (await self._session.execute(total_stmt)).scalar() or 0
        published = (await self._session.execute(published_stmt)).scalar() or 0
        review = (await self._session.execute(review_stmt)).scalar() or 0

        # 按 category 分组统计
        cat_stmt = (
            select(KnowledgeEntry.category, func.count())
            .where(KnowledgeEntry.status == "published")
            .group_by(KnowledgeEntry.category)
        )
        cat_result = await self._session.execute(cat_stmt)
        categories = {row[0] or "未分类": row[1] for row in cat_result.all()}

        return {
            "total": total,
            "published": published,
            "review": review,
            "archived": total - published - review,
            "categories": categories,
        }
