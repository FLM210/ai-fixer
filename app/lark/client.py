import asyncio
import logging
import threading

import lark_oapi as lark
from lark_oapi.ws import Client as WsClient

logger = logging.getLogger(__name__)


class LarkClient:
    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self._ws_client: WsClient | None = None
        self._thread: threading.Thread | None = None

    async def start(self, event_handler: lark.EventDispatcherHandler) -> None:
        self._ws_client = WsClient(
            self.app_id,
            self.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.DEBUG,
        )
        # WsClient.start() 使用模块级 loop 变量（导入时已固定），
        # 且内部调用 loop.run_until_complete() 会与已有 event loop 冲突。
        # 解决：在独立线程中创建新 loop，并 patch lark_oapi.ws.client.loop。
        def _run_ws():
            import lark_oapi.ws.client as ws_module

            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)

            # 直接替换模块级 loop 变量
            original_loop = ws_module.loop
            ws_module.loop = new_loop

            try:
                self._ws_client.start()
            except Exception:
                logger.exception("Lark WebSocket 异常退出")
            finally:
                ws_module.loop = original_loop
                new_loop.close()

        self._thread = threading.Thread(target=_run_ws, daemon=True)
        self._thread.start()
        logger.info("Lark WebSocket 线程已启动")

    async def stop(self) -> None:
        if self._ws_client:
            self._ws_client.stop()
            logger.info("Lark WebSocket 已停止")
