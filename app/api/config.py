"""配置管理 API。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_dynamic

router = APIRouter()


class ConfigItem(BaseModel):
    value: Any
    type: str
    description: str
    source: str  # "database" | "default"
    is_secret: bool = False


class ConfigGroup(BaseModel):
    name: str
    label: str
    items: dict[str, ConfigItem]


class ConfigResponse(BaseModel):
    groups: list[ConfigGroup]


class ConfigUpdateRequest(BaseModel):
    configs: dict[str, Any]
    updated_by: str = "api"


class ConfigUpdateResponse(BaseModel):
    updated_keys: list[str]
    message: str


# 配置分组定义
_GROUPS = [
    {
        "name": "llm",
        "label": "LLM 模型",
        "keys": [
            "llm_provider",
            "llm_base_url",
            "llm_api_key",
            "llm_model",
            "llm_timeout_seconds",
            "llm_max_turns",
        ],
    },
    {
        "name": "lark",
        "label": "飞书集成",
        "keys": [
            "lark_app_id",
            "lark_app_secret",
            "alert_bot_ids",
            "card_signing_key",
            "lark_mode",
        ],
    },
    {
        "name": "diagnose",
        "label": "诊断配置",
        "keys": [
            "diagnose_confidence_threshold",
        ],
    },
    {
        "name": "safety_fence",
        "label": "安全围栏",
        "keys": [
            "fence_auto_namespaces",
            "fence_max_replica_change",
            "fence_max_auto_fixes_per_hour",
            "fence_max_auto_steps_per_incident",
            "fence_cooldown_seconds",
            "fence_require_approval_verbs",
        ],
    },
    {
        "name": "embedding",
        "label": "向量记忆",
        "keys": [
            "embedding_base_url",
            "embedding_api_key",
            "embedding_model",
            "embedding_enabled",
        ],
    },
    {
        "name": "monitoring_pg",
        "label": "PostgreSQL 监控",
        "keys": ["pg_monitor_dsn", "pg_monitor_enabled"],
    },
    {
        "name": "monitoring_redis",
        "label": "Redis 监控",
        "keys": ["redis_monitor_url", "redis_monitor_enabled"],
    },
    {
        "name": "monitoring_aws",
        "label": "AWS 监控",
        "keys": [
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_region",
            "aws_enabled",
        ],
    },
    {
        "name": "other",
        "label": "其他",
        "keys": ["log_level"],
    },
]


@router.get("/config")
async def get_config() -> ConfigResponse:
    """获取所有可配置项（分组返回）。"""
    dynamic = get_dynamic()
    all_items = dynamic.get_all()

    groups = []
    for group_def in _GROUPS:
        items = {}
        for key in group_def["keys"]:
            if key in all_items:
                items[key] = ConfigItem(**all_items[key])
        groups.append(ConfigGroup(
            name=group_def["name"],
            label=group_def["label"],
            items=items,
        ))

    return ConfigResponse(groups=groups)


@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ConfigUpdateResponse:
    """批量更新配置项。"""
    dynamic = get_dynamic()
    await dynamic.update(session, request.configs, updated_by=request.updated_by)
    return ConfigUpdateResponse(
        updated_keys=list(request.configs.keys()),
        message=f"已更新 {len(request.configs)} 项配置",
    )
