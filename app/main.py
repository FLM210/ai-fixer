from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import api_router
from app.config import get_dynamic_config, get_settings
from app.db import dispose_engine, session_scope
from app.lark.webhook import router as lark_router
from app.llm import build_llm_client
from app.observability import configure_logging
from app.plugins import global_registry
from app.telemetry import setup_tracing
from app.telemetry.metrics import setup_metrics

logger = structlog.get_logger(__name__)


def _load_disabled_plugins() -> list[str]:
    """从数据库加载已禁用的插件列表。"""
    import json as _json

    try:

        # 直接从 DynamicConfig 缓存读取
        dc = get_dynamic_config()
        val = dc.get("disabled_plugins", "[]")
        if isinstance(val, str):
            return _json.loads(val)
        return val if isinstance(val, list) else []
    except Exception:
        return []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    setup_tracing(
        service_name="ai-fixer",
        endpoint=settings.otel_exporter_endpoint
        if hasattr(settings, "otel_exporter_endpoint")
        else None,
    )

    # 检查数据库连接
    logger.info("检查数据库连接...")
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        logger.info("数据库连接成功")
    except Exception as e:
        logger.critical("数据库连接失败，无法启动", error=str(e))
        raise SystemExit(f"数据库连接失败: {e}")

    # 检查 Redis 连接
    logger.info("检查 Redis 连接...")
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        logger.info("Redis 连接成功")
    except Exception as e:
        logger.critical("Redis 连接失败，无法启动", error=str(e))
        raise SystemExit(f"Redis 连接失败: {e}")

    # 从数据库加载动态配置
    try:
        dynamic_cfg = get_dynamic_config()
        async with session_scope() as session:
            await dynamic_cfg.load(session)
        dynamic_cfg.apply_to_settings(settings)
        logger.info("dynamic_config_applied")
    except Exception:
        logger.warning("dynamic_config_load_failed", exc_info=True)

    # 加载插件（从数据库恢复禁用状态）
    disabled_plugins = _load_disabled_plugins()
    global_registry.reload(disabled_names=disabled_plugins)
    logger.info(
        "startup",
        plugins=[s.name for s in global_registry.list_specs(include_disabled=True)],
        disabled=disabled_plugins,
    )

    # 启动飞书连接
    lark_client = None
    if settings.lark_app_id and settings.lark_app_secret:
        # 获取连接模式：websocket（默认）或 callback
        lark_mode = dynamic_cfg.get("lark_mode", "websocket") if dynamic_cfg else "websocket"

        if lark_mode == "websocket":
            # WebSocket 模式：机器人主动连接飞书
            import asyncio

            from app.lark.client import LarkClient
            from app.lark.detector import AlertDetector
            from app.lark.handler import create_event_handler

            detector = AlertDetector(alert_bot_ids=settings.alert_bot_ids)
            handler = create_event_handler(detector, main_loop=asyncio.get_running_loop())
            lark_client = LarkClient(settings.lark_app_id, settings.lark_app_secret)
            await lark_client.start(handler)
            logger.info("lark_ws_started", app_id=settings.lark_app_id)
        else:
            # HTTP 回调模式：飞书推送事件到 /lark/event
            import asyncio

            from app.lark.detector import AlertDetector
            from app.lark.handler import create_event_handler
            from app.lark.webhook import set_event_handler

            detector = AlertDetector(alert_bot_ids=settings.alert_bot_ids)
            handler = create_event_handler(detector, main_loop=asyncio.get_running_loop())
            set_event_handler(handler)
            logger.info("lark_callback_mode", app_id=settings.lark_app_id)
    else:
        logger.info("lark_skipped", reason="lark_app_id or lark_app_secret not configured")

    try:
        yield
    finally:
        if lark_client:
            await lark_client.stop()
        await dispose_engine()
        logger.info("shutdown")


app = FastAPI(title="ai-fixer", version="0.1.0", lifespan=lifespan)

# CORS 中间件（前端开发服务器跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 显式路由（必须在 StaticFiles mount 之前注册）──


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "ai-fixer", "version": "0.1.0"}


@app.get("/healthz")
async def healthz() -> Response:
    settings = get_settings()
    checks: dict[str, dict[str, str]] = {}

    # DB
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        checks["db"] = {"status": "ok"}
    except Exception as e:
        checks["db"] = {"status": "fail", "error": str(e)[:200]}

    # LLM(只验证能构造 client,不实际调用模型)
    if not settings.llm_base_url or not settings.llm_api_key:
        checks["llm"] = {"status": "not_configured", "hint": "请通过前端配置 LLM 参数"}
    else:
        try:
            client = build_llm_client(settings)
            checks["llm"] = {"status": "ok", "provider": client.provider, "model": client.model}
        except Exception as e:
            checks["llm"] = {"status": "fail", "error": str(e)[:200]}

    overall = (
        "ok" if all(c["status"] in ("ok", "not_configured") for c in checks.values()) else "fail"
    )
    body = {"status": overall, "checks": checks}
    status_code = 200 if overall == "ok" else 503
    return Response(
        content=__import__("json").dumps(body),
        status_code=status_code,
        media_type="application/json",
    )


# ── 路由注册 ──
app.include_router(lark_router)
app.include_router(api_router, prefix="/api")
setup_metrics(app)

# ── 生产环境：挂载前端静态文件 ──
# 注意：mount("/", StaticFiles) 会拦截所有请求，包括 /healthz 等显式路由
# 因此只在显式设置 SERVE_STATIC=1 时才启用（生产部署使用）
import os

if os.environ.get("SERVE_STATIC") == "1":
    from fastapi.staticfiles import StaticFiles

    _static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.isdir(_static_dir):
        app.mount("/app", StaticFiles(directory=_static_dir, html=True), name="static")
