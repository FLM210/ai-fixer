"""SSE 实时事件推送 API。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# 事件队列列表（每个 SSE 客户端一个）
_event_queues: list[asyncio.Queue[str]] = []


async def _event_generator(queue: asyncio.Queue[str]) -> AsyncIterator[str]:
    """SSE 事件生成器。"""
    try:
        # 发送初始连接确认
        yield _sse_event("connected", {"time": datetime.now(timezone.utc).isoformat()})

        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30)
                yield data
            except asyncio.TimeoutError:
                # 心跳
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        return


def _sse_event(event: str, data: dict) -> str:
    """格式化 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def broadcast_event(event: str, data: dict) -> None:
    """向所有 SSE 客户端广播事件。"""
    message = _sse_event(event, data)
    dead_queues = []
    for queue in _event_queues:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            dead_queues.append(queue)
    for q in dead_queues:
        _event_queues.remove(q)


@router.get("/events")
async def event_stream() -> StreamingResponse:
    """SSE 事件流端点。"""
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _event_queues.append(queue)

    async def cleanup_generator() -> AsyncIterator[str]:
        try:
            async for event in _event_generator(queue):
                yield event
        finally:
            if queue in _event_queues:
                _event_queues.remove(queue)

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
