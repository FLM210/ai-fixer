"""插件管理 API：列表、启用/禁用、热重载、自定义插件上传/删除。"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_dynamic
from app.config.dynamic import DynamicConfig
from app.plugins import global_registry
from app.plugins.registry import CUSTOM_PLUGINS_DIR

router = APIRouter()


class PluginInfo(BaseModel):
    name: str
    category: str
    resource_type: str
    risk_level: str
    timeout_seconds: float
    description: str
    enabled: bool
    source: str  # "builtin" | "custom"
    input_schema: dict[str, Any]


class PluginToggleRequest(BaseModel):
    enabled: bool


class PluginReloadResponse(BaseModel):
    plugins: list[str]
    count: int
    message: str


async def _persist_disabled(session: AsyncSession, dynamic: DynamicConfig) -> None:
    """将当前禁用列表持久化到数据库。"""
    disabled = global_registry.get_disabled_list()
    await dynamic.update(session, {"disabled_plugins": json.dumps(disabled)}, updated_by="plugin_manager")


@router.get("/plugins")
async def list_plugins() -> list[PluginInfo]:
    """获取所有已注册插件的信息。"""
    specs = global_registry.list_specs(include_disabled=True)
    return [
        PluginInfo(
            name=s.name,
            category=s.category,
            resource_type=s.resource_type,
            risk_level=s.risk_level,
            timeout_seconds=s.timeout_seconds,
            description=s.description,
            enabled=not global_registry.is_disabled(s.name),
            source=global_registry.get_plugin_source(s.name),
            input_schema=s.input_schema,
        )
        for s in specs
    ]


@router.put("/plugins/{plugin_name}/toggle")
async def toggle_plugin(
    plugin_name: str,
    request: PluginToggleRequest,
    session: AsyncSession = Depends(get_db_session),
    dynamic: DynamicConfig = Depends(get_dynamic),
) -> dict[str, Any]:
    """启用或禁用指定插件（持久化到数据库）。"""
    if request.enabled:
        ok = global_registry.enable(plugin_name)
        action = "启用"
    else:
        ok = global_registry.disable(plugin_name)
        action = "禁用"

    if not ok:
        raise HTTPException(status_code=404, detail=f"插件 {plugin_name} 不存在")

    # 持久化到数据库
    await _persist_disabled(session, dynamic)

    return {"ok": True, "message": f"插件 {plugin_name} 已{action}"}


@router.post("/plugins/reload")
async def reload_plugins(
    session: AsyncSession = Depends(get_db_session),
    dynamic: DynamicConfig = Depends(get_dynamic),
) -> PluginReloadResponse:
    """热重载所有插件。"""
    disabled = global_registry.get_disabled_list()
    plugins = global_registry.reload(disabled_names=disabled)
    return PluginReloadResponse(
        plugins=plugins,
        count=len(plugins),
        message=f"已重载 {len(plugins)} 个插件",
    )


@router.post("/plugins/upload")
async def upload_plugin(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    dynamic: DynamicConfig = Depends(get_dynamic),
) -> dict[str, Any]:
    """上传自定义插件文件。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="只支持 .py 文件")

    # 安全检查：读取文件内容
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码必须是 UTF-8")

    # 基本安全检查
    dangerous_patterns = ["os.system", "subprocess.call", "exec(", "eval(", "__import__"]
    for pattern in dangerous_patterns:
        if pattern in text:
            raise HTTPException(
                status_code=400,
                detail=f"文件包含危险代码: {pattern}，出于安全考虑被拒绝",
            )

    # 保存到自定义插件目录
    custom_dir = Path(CUSTOM_PLUGINS_DIR)
    custom_dir.mkdir(parents=True, exist_ok=True)
    dest = custom_dir / file.filename

    dest.write_text(text, encoding="utf-8")

    # 热重载
    disabled = global_registry.get_disabled_list()
    plugins = global_registry.reload(disabled_names=disabled)

    return {
        "ok": True,
        "message": f"插件 {file.filename} 已上传",
        "path": str(dest),
        "total_plugins": len(plugins),
    }


@router.delete("/plugins/custom/{plugin_name}")
async def delete_custom_plugin(
    plugin_name: str,
    session: AsyncSession = Depends(get_db_session),
    dynamic: DynamicConfig = Depends(get_dynamic),
) -> dict[str, Any]:
    """删除自定义插件。"""
    # 验证是自定义插件
    source = global_registry.get_plugin_source(plugin_name)
    if source != "custom":
        raise HTTPException(status_code=400, detail=f"插件 {plugin_name} 不是自定义插件，无法删除")

    # 从 registry 获取实际文件路径
    file_path = global_registry.get_plugin_file(plugin_name)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"无法找到插件文件: {plugin_name}")

    plugin_file = Path(file_path)
    if not plugin_file.exists():
        raise HTTPException(status_code=404, detail=f"插件文件不存在: {plugin_file}")

    # 如果是包（目录），删除整个目录；否则删除单个文件
    if plugin_file.is_dir():
        shutil.rmtree(plugin_file)
    else:
        plugin_file.unlink()

    # 从禁用列表中移除
    global_registry.enable(plugin_name)

    # 热重载
    disabled = global_registry.get_disabled_list()
    await _persist_disabled(session, dynamic)
    plugins = global_registry.reload(disabled_names=disabled)

    return {
        "ok": True,
        "message": f"插件 {plugin_name} 已删除",
        "total_plugins": len(plugins),
    }


@router.get("/plugins/custom/list")
async def list_custom_plugins() -> list[dict[str, str]]:
    """列出自定义插件文件。"""
    custom_dir = Path(CUSTOM_PLUGINS_DIR)
    if not custom_dir.exists():
        return []

    result = []
    for item in sorted(custom_dir.iterdir()):
        if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
            result.append({
                "filename": item.name,
                "path": str(item),
                "size": item.stat().st_size,
            })
        elif item.is_dir() and not item.name.startswith("_"):
            init_file = item / "__init__.py"
            if init_file.exists():
                result.append({
                    "filename": item.name,
                    "path": str(item),
                    "size": sum(f.stat().st_size for f in item.rglob("*.py")),
                })

    return result
