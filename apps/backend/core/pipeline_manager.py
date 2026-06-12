"""
KET Board - Pipeline Manager.

Manages running pipelines, stores state, and broadcasts
WebSocket events to connected clients.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class PipelineManager:
    """
    Singleton manager for all active consensus pipelines.

    Tracks pipeline state and broadcasts events to connected
    WebSocket clients in real-time.
    """

    def __init__(self):
        # Active pipelines: {pipeline_id: pipeline_data}
        self._pipelines: dict[str, dict[str, Any]] = {}
        # WebSocket connections: {pipeline_id: [websocket, ...]}
        self._connections: dict[str, list[WebSocket]] = {}
        # Event history: {pipeline_id: [event, ...]}
        self._events: dict[str, list[dict]] = {}

    def create_pipeline(self, proposal_data: dict) -> str:
        """Create a new pipeline and return its ID."""
        pipeline_id = str(uuid.uuid4())[:8]
        self._pipelines[pipeline_id] = {
            "id": pipeline_id,
            "status": "pending",
            "proposal": proposal_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
            "result": None,
        }
        self._events[pipeline_id] = []
        self._connections[pipeline_id] = []
        return pipeline_id

    def get_pipeline(self, pipeline_id: str) -> dict | None:
        """Get pipeline data by ID."""
        return self._pipelines.get(pipeline_id)

    def get_events(self, pipeline_id: str) -> list[dict]:
        """Get all events for a pipeline."""
        return self._events.get(pipeline_id, [])

    def get_all_pipelines(self) -> list[dict]:
        """Get all pipelines (most recent first)."""
        pipelines = list(self._pipelines.values())
        pipelines.sort(key=lambda p: p["created_at"], reverse=True)
        return pipelines[:20]  # limit to 20 most recent

    async def connect(self, pipeline_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a pipeline."""
        await websocket.accept()
        if pipeline_id not in self._connections:
            self._connections[pipeline_id] = []
        self._connections[pipeline_id].append(websocket)

        # Send any existing events (replay for late joiners)
        for event in self._events.get(pipeline_id, []):
            try:
                await websocket.send_json(event)
            except Exception:
                break

    def disconnect(self, pipeline_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if pipeline_id in self._connections:
            self._connections[pipeline_id] = [
                ws for ws in self._connections[pipeline_id]
                if ws != websocket
            ]

    async def broadcast(self, pipeline_id: str, event: dict):
        """
        Broadcast an event to all connected WebSocket clients.
        Also stores the event in history for replay.
        """
        # Add timestamp
        event["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Store event
        if pipeline_id not in self._events:
            self._events[pipeline_id] = []
        self._events[pipeline_id].append(event)

        # Update pipeline status
        if pipeline_id in self._pipelines:
            self._pipelines[pipeline_id]["status"] = event.get("state", "running")
            if event.get("type") == "pipeline_completed":
                self._pipelines[pipeline_id]["result"] = event.get("result")

        # Broadcast to all connected clients
        dead_connections = []
        for ws in self._connections.get(pipeline_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(pipeline_id, ws)

    def create_event_callback(self, pipeline_id: str):
        """
        Create an async callback function for the orchestrator.
        This bridges the orchestrator's on_event to WebSocket broadcast.
        """
        async def callback(event: dict):
            await self.broadcast(pipeline_id, event)
        return callback


# Singleton instance
pipeline_manager = PipelineManager()
