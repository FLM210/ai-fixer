"""知识库 API 路由。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.knowledge.service import KnowledgeService

router = APIRouter(prefix="/knowledge")


# ── Pydantic 模型 ─────────────────────────────────────────────


class KnowledgeCreateRequest(BaseModel):
    title: str = Field(..., max_length=256)
    content: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_type: str = "manual"
    source_incident_id: str | None = None
    status: str = "published"


class KnowledgeUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    change_summary: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    category: str | None = None
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.6, ge=0.0, le=1.0)


class ImportIncidentRequest(BaseModel):
    title: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class KnowledgeEntryResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str | None
    tags: list[str]
    source_type: str
    source_incident_id: str | None
    status: str
    created_by: str | None
    current_revision: int
    use_count: int
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeRevisionResponse(BaseModel):
    id: str
    entry_id: str
    revision_number: int
    title: str
    content: str
    category: str | None
    tags: list[str]
    change_summary: str | None
    created_by: str | None
    created_at: datetime


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeEntryResponse]
    total: int
    page: int
    page_size: int


class KnowledgeStatsResponse(BaseModel):
    total: int
    published: int
    review: int
    archived: int
    categories: dict[str, int]


# ── 辅助函数 ──────────────────────────────────────────────────


def _entry_to_response(entry: Any) -> KnowledgeEntryResponse:
    return KnowledgeEntryResponse(
        id=str(entry.id),
        title=entry.title,
        content=entry.content,
        category=entry.category,
        tags=entry.tags or [],
        source_type=entry.source_type,
        source_incident_id=str(entry.source_incident_id) if entry.source_incident_id else None,
        status=entry.status,
        created_by=entry.created_by,
        current_revision=entry.current_revision,
        use_count=entry.use_count,
        last_used_at=entry.last_used_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _revision_to_response(rev: Any) -> KnowledgeRevisionResponse:
    return KnowledgeRevisionResponse(
        id=str(rev.id),
        entry_id=str(rev.entry_id),
        revision_number=rev.revision_number,
        title=rev.title,
        content=rev.content,
        category=rev.category,
        tags=rev.tags or [],
        change_summary=rev.change_summary,
        created_by=rev.created_by,
        created_at=rev.created_at,
    )


# ── 路由 ─────────────────────────────────────────────────────


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    status: str | None = None,
    category: str | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeListResponse:
    """获取知识库列表。"""
    svc = KnowledgeService(session)
    entries, total = await svc.list_entries(
        status=status,
        category=category,
        source_type=source_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return KnowledgeListResponse(
        items=[_entry_to_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=KnowledgeEntryResponse, status_code=201)
async def create_knowledge(
    req: KnowledgeCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeEntryResponse:
    """创建知识条目。"""
    svc = KnowledgeService(session)
    entry = await svc.create(
        title=req.title,
        content=req.content,
        category=req.category,
        tags=req.tags,
        source_type=req.source_type,
        source_incident_id=req.source_incident_id,
        status=req.status,
    )
    return _entry_to_response(entry)


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeStatsResponse:
    """获取知识库统计信息。"""
    svc = KnowledgeService(session)
    stats = await svc.stats()
    return KnowledgeStatsResponse(**stats)


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge(
    entry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeEntryResponse:
    """获取知识条目详情。"""
    svc = KnowledgeService(session)
    entry = await svc.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return _entry_to_response(entry)


@router.put("/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_knowledge(
    entry_id: UUID,
    req: KnowledgeUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeEntryResponse:
    """更新知识条目（自动创建新版本）。"""
    svc = KnowledgeService(session)
    entry = await svc.update(
        entry_id,
        title=req.title,
        content=req.content,
        category=req.category,
        tags=req.tags,
        status=req.status,
        change_summary=req.change_summary,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return _entry_to_response(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_knowledge(
    entry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """删除知识条目。"""
    svc = KnowledgeService(session)
    deleted = await svc.delete(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="知识条目不存在")


@router.get("/{entry_id}/revisions", response_model=list[KnowledgeRevisionResponse])
async def get_revisions(
    entry_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeRevisionResponse]:
    """获取知识条目的版本历史。"""
    svc = KnowledgeService(session)
    revisions = await svc.get_revisions(entry_id)
    return [_revision_to_response(r) for r in revisions]


@router.get("/{entry_id}/revisions/{revision_number}", response_model=KnowledgeRevisionResponse)
async def get_revision(
    entry_id: UUID,
    revision_number: int,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRevisionResponse:
    """获取指定版本详情。"""
    svc = KnowledgeService(session)
    rev = await svc.get_revision(entry_id, revision_number)
    if rev is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    return _revision_to_response(rev)


@router.post("/{entry_id}/rollback/{revision_number}", response_model=KnowledgeEntryResponse)
async def rollback_to_revision(
    entry_id: UUID,
    revision_number: int,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeEntryResponse:
    """回滚到指定版本。"""
    svc = KnowledgeService(session)
    entry = await svc.rollback(entry_id, revision_number)
    if entry is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    return _entry_to_response(entry)


@router.post("/check-stale")
async def check_stale_entries(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """检查并标记过期的知识条目。"""
    svc = KnowledgeService(session)
    stale = await svc.check_stale_entries()
    return {
        "marked_count": len(stale),
        "marked_ids": [str(e.id) for e in stale],
    }
