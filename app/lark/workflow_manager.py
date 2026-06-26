"""工作流运行管理器: 跟踪进行中的 LangGraph 工作流, 支持 interrupt/resume。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from langgraph.types import Command

logger = logging.getLogger(__name__)

# pending run 超时时间 (秒)
PENDING_TIMEOUT_SECONDS = 3600  # 1 小时


@dataclass
class PendingRun:
    """一个被 interrupt 暂停的工作流运行。"""

    thread_id: str
    incident_id: str
    chat_id: str
    interrupt_type: str  # "diagnosis_approval" | "proposal_approval"
    app: Any  # CompiledStateGraph 实例
    config: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)


class WorkflowRunManager:
    """管理进行中的工作流运行, 支持 interrupt -> 卡片回调 -> resume 模式。"""

    def __init__(self) -> None:
        self._pending: dict[str, PendingRun] = {}
        self._incident_to_thread: dict[str, str] = {}
        self._chat_to_thread: dict[str, str] = {}
        self._cleanup_task: asyncio.Task[None] | None = None

    def register_pending(
        self,
        thread_id: str,
        incident_id: str,
        chat_id: str,
        interrupt_type: str,
        app: Any,
        config: dict[str, Any],
    ) -> None:
        """注册一个被 interrupt 暂停的工作流。"""
        run = PendingRun(
            thread_id=thread_id,
            incident_id=incident_id,
            chat_id=chat_id,
            interrupt_type=interrupt_type,
            app=app,
            config=config,
        )
        self._pending[thread_id] = run
        self._incident_to_thread[incident_id] = thread_id
        self._chat_to_thread[chat_id] = thread_id
        logger.info(
            "注册待恢复工作流: thread=%s incident=%s type=%s",
            thread_id,
            incident_id,
            interrupt_type,
        )
        # 确保清理任务在运行
        self._ensure_cleanup_task()

    def get_by_thread(self, thread_id: str) -> PendingRun | None:
        """通过 thread_id 获取待恢复的工作流。"""
        return self._pending.get(thread_id)

    def get_by_incident(self, incident_id: str) -> PendingRun | None:
        """通过 incident_id 获取待恢复的工作流。"""
        thread_id = self._incident_to_thread.get(incident_id)
        if thread_id:
            return self._pending.get(thread_id)
        return None

    def get_by_chat(self, chat_id: str) -> PendingRun | None:
        """通过 chat_id 获取最新的待恢复工作流。"""
        thread_id = self._chat_to_thread.get(chat_id)
        if thread_id:
            return self._pending.get(thread_id)
        return None

    async def resume_by_thread(self, thread_id: str, action: str) -> dict[str, Any] | None:
        """通过 thread_id 直接恢复工作流（跳过 incident_id 查找）。"""
        run = self._pending.get(thread_id)
        if not run:
            logger.warning("未找到待恢复的工作流: thread=%s", thread_id)
            return None

        logger.info(
            "恢复工作流: thread=%s incident=%s action=%s type=%s",
            run.thread_id, run.incident_id, action, run.interrupt_type,
        )

        chat_id = run.chat_id
        app = run.app
        config = run.config
        self.remove(thread_id)

        try:
            from langgraph.errors import GraphInterrupt

            result = await app.ainvoke(
                Command(resume={"action": action, "_resumed": True}),
                config=config,
            )

            # 检查是否有新的 interrupt（LangGraph 可能通过 __interrupt__ 字段返回）
            if isinstance(result, dict) and "__interrupt__" in result:
                interrupt_type = "unknown"
                interrupts = result.get("__interrupt__", [])
                if interrupts and hasattr(interrupts[0], "value"):
                    interrupt_data = interrupts[0].value
                    if isinstance(interrupt_data, dict):
                        interrupt_type = interrupt_data.get("type", "unknown")

                logger.info(
                    "工作流再次暂停: thread=%s type=%s",
                    thread_id, interrupt_type,
                )
                self.register_pending(
                    thread_id=thread_id,
                    incident_id=run.incident_id,
                    chat_id=chat_id,
                    interrupt_type=interrupt_type,
                    app=app,
                    config=config,
                )
                return None

            logger.info("工作流恢复完成: thread=%s", thread_id)
            return result

        except GraphInterrupt as e:
            interrupt_type = "unknown"
            if e.interrupts:
                interrupt_data = e.interrupts[0].value
                if isinstance(interrupt_data, dict):
                    interrupt_type = interrupt_data.get("type", "unknown")

            logger.info(
                "工作流再次暂停: thread=%s incident=%s type=%s",
                thread_id, run.incident_id, interrupt_type,
            )
            self.register_pending(
                thread_id=thread_id,
                incident_id=run.incident_id,
                chat_id=chat_id,
                interrupt_type=interrupt_type,
                app=app,
                config=config,
            )
            return None

        except Exception:
            logger.exception("工作流恢复失败: thread=%s", thread_id)
            return None

    def remove(self, thread_id: str) -> PendingRun | None:
        """移除并返回已完成的工作流。"""
        run = self._pending.pop(thread_id, None)
        if run:
            self._incident_to_thread.pop(run.incident_id, None)
            self._chat_to_thread.pop(run.chat_id, None)
        return run

    async def resume(self, incident_id: str, action: str) -> dict[str, Any] | None:
        """恢复一个被 interrupt 暂停的工作流。

        如果工作流在恢复后再次 interrupt (例如诊断确认后进入方案确认),
        会自动重新注册 pending run 并返回 None。

        Args:
            incident_id: 事件 ID
            action: "approve" 或 "reject"

        Returns:
            工作流最终结果, 或 None (如果再次 interrupt 或未找到待恢复的工作流)
        """
        run = self.get_by_incident(incident_id)
        if not run:
            logger.warning("未找到待恢复的工作流: incident=%s", incident_id)
            return None

        logger.info(
            "恢复工作流: thread=%s incident=%s action=%s type=%s",
            run.thread_id,
            incident_id,
            action,
            run.interrupt_type,
        )

        # 先移除旧的 pending run (如果再次 interrupt 会重新注册)
        thread_id = run.thread_id
        chat_id = run.chat_id
        app = run.app
        config = run.config
        self.remove(thread_id)

        try:
            from langgraph.errors import GraphInterrupt

            result = await app.ainvoke(
                Command(resume={"action": action, "_resumed": True}),
                config=config,
            )
            logger.info(
                "工作流恢复完成: thread=%s incident=%s",
                thread_id,
                incident_id,
            )
            return result

        except GraphInterrupt as e:
            # 工作流在下一个 interrupt 节点暂停 (例如方案确认)
            interrupt_type = "unknown"
            if e.interrupts:
                interrupt_data = e.interrupts[0].value
                if isinstance(interrupt_data, dict):
                    interrupt_type = interrupt_data.get("type", "unknown")

            logger.info(
                "工作流再次暂停: thread=%s incident=%s type=%s",
                thread_id,
                incident_id,
                interrupt_type,
            )

            # 重新注册 pending run
            self.register_pending(
                thread_id=thread_id,
                incident_id=incident_id,
                chat_id=chat_id,
                interrupt_type=interrupt_type,
                app=app,
                config=config,
            )
            return None

        except Exception:
            logger.exception(
                "工作流恢复失败: thread=%s incident=%s",
                thread_id,
                incident_id,
            )
            return None

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def _ensure_cleanup_task(self) -> None:
        """确保后台清理任务在运行。"""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_loop())
            except RuntimeError:
                # 没有运行中的事件循环, 跳过
                pass

    async def _cleanup_loop(self) -> None:
        """定期清理超时的 pending run。"""
        while True:
            await asyncio.sleep(300)  # 每 5 分钟检查一次
            await self._cleanup_expired()

    async def _cleanup_expired(self) -> None:
        """清理超时的 pending run 并发送超时通知。"""
        now = time.monotonic()
        expired: list[PendingRun] = []

        for run in list(self._pending.values()):
            if now - run.created_at > PENDING_TIMEOUT_SECONDS:
                expired.append(run)

        for run in expired:
            logger.warning(
                "工作流超时清理: thread=%s incident=%s type=%s age=%.0fs",
                run.thread_id,
                run.incident_id,
                run.interrupt_type,
                now - run.created_at,
            )
            self.remove(run.thread_id)

            # 发送超时通知到飞书群
            try:
                from app.lark.card_sender import send_text_message

                label = (
                    "诊断确认"
                    if run.interrupt_type == "diagnosis_approval"
                    else "修复方案"
                )
                await send_text_message(
                    chat_id=run.chat_id,
                    text=(
                        f"⏰ {label}等待超时 (已超过 1 小时)\n"
                        f"incident: {run.incident_id}\n"
                        f"请重新触发告警处理。"
                    ),
                )
            except Exception:
                logger.warning(
                    "发送超时通知失败: incident=%s", run.incident_id, exc_info=True
                )


# 全局单例
workflow_manager = WorkflowRunManager()
