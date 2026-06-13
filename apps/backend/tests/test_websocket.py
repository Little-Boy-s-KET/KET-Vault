import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parent.parent
_AGENT_CORE = _BACKEND.parent.parent / "packages" / "agent-core"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_AGENT_CORE))

from api.websocket import pipeline_websocket
from core.pipeline_manager import pipeline_manager

@pytest.mark.asyncio
async def test_websocket_endpoint_success():
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.receive_text.side_effect = ["ping", "ping", WebSocketDisconnect()]
    mock_ws.client_state = WebSocketState.CONNECTED

    pipeline_manager.get_pipeline = MagicMock(return_value={"id": "test-pipeline-123"})
    pipeline_manager.connect = AsyncMock()
    pipeline_manager.disconnect = MagicMock()

    await pipeline_websocket(mock_ws, "test-pipeline-123")

    pipeline_manager.connect.assert_called_once_with("test-pipeline-123", mock_ws)
    assert mock_ws.send_json.call_count == 2
    mock_ws.send_json.assert_called_with({"type": "pong"})
    pipeline_manager.disconnect.assert_called_once_with("test-pipeline-123", mock_ws)
    mock_ws.close.assert_called_once_with(code=1000)

@pytest.mark.asyncio
async def test_websocket_endpoint_exception():
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.receive_text.side_effect = Exception("Unknown Error")
    mock_ws.client_state = WebSocketState.CONNECTED

    pipeline_manager.get_pipeline = MagicMock(return_value={"id": "test-pipeline-456"})
    pipeline_manager.connect = AsyncMock()
    pipeline_manager.disconnect = MagicMock()

    await pipeline_websocket(mock_ws, "test-pipeline-456")

    pipeline_manager.connect.assert_called_once_with("test-pipeline-456", mock_ws)
    pipeline_manager.disconnect.assert_called_once_with("test-pipeline-456", mock_ws)
    mock_ws.close.assert_called_once_with(code=1000)

@pytest.mark.asyncio
async def test_websocket_endpoint_not_found():
    mock_ws = AsyncMock(spec=WebSocket)

    pipeline_manager.get_pipeline = MagicMock(return_value=None)

    await pipeline_websocket(mock_ws, "missing-pipeline")

    mock_ws.close.assert_called_once_with(code=4004, reason="Pipeline not found")

@pytest.mark.asyncio
async def test_websocket_endpoint_close_exception():
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.receive_text.side_effect = WebSocketDisconnect()
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.close.side_effect = Exception("Close error")

    pipeline_manager.get_pipeline = MagicMock(return_value={"id": "test-pipeline-789"})
    pipeline_manager.connect = AsyncMock()
    pipeline_manager.disconnect = MagicMock()

    await pipeline_websocket(mock_ws, "test-pipeline-789")

    mock_ws.close.assert_called_once_with(code=1000)
