"""
KET Board - WebSocket Handler.

Real-time WebSocket endpoint for streaming pipeline events
to the frontend dashboard. Handles unexpected disconnects gracefully.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from core.pipeline_manager import pipeline_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/pipeline/{pipeline_id}")
async def pipeline_websocket(websocket: WebSocket, pipeline_id: str):
    """
    WebSocket endpoint for real-time pipeline updates.

    Clients connect after submitting a proposal and receive
    events as each agent analyzes and decides.

    Handles:
        - Client ping/pong keepalive
        - Unexpected disconnects mid-pipeline
        - Graceful cleanup on any error
    """
    # Verify pipeline exists
    pipeline = pipeline_manager.get_pipeline(pipeline_id)
    if not pipeline:
        await websocket.close(code=4004, reason="Pipeline not found")
        return

    # Connect and stream events
    await pipeline_manager.connect(pipeline_id, websocket)
    logger.info("WS client connected to pipeline %s", pipeline_id)

    try:
        # Keep connection alive until client disconnects
        while True:
            data = await websocket.receive_text()
            # Client can send "ping" to keep alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info(
            "WS client disconnected from pipeline %s (clean)",
            pipeline_id,
        )
    except Exception as exc:
        logger.warning(
            "WS client lost from pipeline %s: %s",
            pipeline_id,
            exc,
        )
    finally:
        pipeline_manager.disconnect(pipeline_id, websocket)
        # Attempt graceful close if still open
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close(code=1000)
            except Exception:
                pass
