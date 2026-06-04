import asyncio
from unittest.mock import MagicMock, patch

import lark_oapi as lark
import pytest

from app.lark.client import LarkClient


class TestLarkClient:
    def test_init(self):
        client = LarkClient(app_id="test_app_id", app_secret="test_app_secret")
        assert client.app_id == "test_app_id"
        assert client.app_secret == "test_app_secret"
        assert client._ws_client is None
        assert client._task is None

    @pytest.mark.asyncio
    async def test_start(self):
        client = LarkClient(app_id="test_app_id", app_secret="test_app_secret")
        mock_event_handler = MagicMock()

        with patch('app.lark.client.WsClient') as mock_ws_client_cls:
            mock_ws_client = MagicMock()
            mock_ws_client_cls.return_value = mock_ws_client

            with patch('app.lark.client.asyncio.create_task') as mock_create_task:
                mock_task = MagicMock()
                mock_create_task.return_value = mock_task

                await client.start(mock_event_handler)

                mock_ws_client_cls.assert_called_once_with(
                    "test_app_id",
                    "test_app_secret",
                    event_handler=mock_event_handler,
                    log_level=lark.LogLevel.DEBUG,
                )
                mock_create_task.assert_called_once_with(mock_ws_client.start())
                assert client._ws_client == mock_ws_client
                assert client._task == mock_task

    @pytest.mark.asyncio
    async def test_stop(self):
        client = LarkClient(app_id="test_app_id", app_secret="test_app_secret")

        mock_ws_client = MagicMock()

        async def _dummy_coro():
            await asyncio.sleep(3600)

        real_task = asyncio.create_task(_dummy_coro())

        client._ws_client = mock_ws_client
        client._task = real_task

        await client.stop()

        mock_ws_client.stop.assert_called_once()
        assert real_task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        client = LarkClient(app_id="test_app_id", app_secret="test_app_secret")
        await client.stop()
