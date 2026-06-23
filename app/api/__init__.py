from fastapi import APIRouter

from app.api.alert import router as alert_router
from app.api.config import router as config_router
from app.api.environment_context import router as env_ctx_router
from app.api.events import router as events_router
from app.api.incidents import router as incidents_router
from app.api.knowledge import router as knowledge_router
from app.api.plugins import router as plugins_router
from app.api.status import router as status_router

api_router = APIRouter()
api_router.include_router(status_router, tags=["status"])
api_router.include_router(config_router, tags=["config"])
api_router.include_router(incidents_router, tags=["incidents"])
api_router.include_router(knowledge_router, tags=["knowledge"])
api_router.include_router(plugins_router, tags=["plugins"])
api_router.include_router(events_router, tags=["events"])
api_router.include_router(alert_router, tags=["alert"])
api_router.include_router(env_ctx_router, tags=["environment-context"])

__all__ = ["api_router"]
