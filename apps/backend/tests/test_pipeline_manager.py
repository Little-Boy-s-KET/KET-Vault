"""
KET Board - PipelineManager Unit Tests.

Tests the in-memory pipeline manager including CRUD operations,
event storage, and broadcast callback creation.
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

# Add backend and agent-core to path
_BACKEND = Path(__file__).resolve().parent.parent
_AGENT_CORE = _BACKEND.parent.parent / "packages" / "agent-core"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_AGENT_CORE))

from core.pipeline_manager import PipelineManager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager():
    """Fresh PipelineManager instance for each test."""
    return PipelineManager()


@pytest.fixture
def sample_proposal():
    return {
        "action": "FARM_YIELD",
        "token": "USDC",
        "amount": 1000.0,
        "target_protocol": "Agni Finance",
    }


# =============================================================================
# create_pipeline Tests
# =============================================================================

class TestCreatePipeline:
    """Test pipeline creation."""

    def test_returns_8_char_id(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        assert isinstance(pid, str)
        assert len(pid) == 8

    def test_pipeline_stored(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        pipeline = manager.get_pipeline(pid)

        assert pipeline is not None
        assert pipeline["id"] == pid
        assert pipeline["status"] == "pending"
        assert pipeline["proposal"] == sample_proposal
        assert pipeline["result"] is None
        assert "created_at" in pipeline

    def test_unique_ids(self, manager, sample_proposal):
        ids = set()
        for _ in range(50):
            pid = manager.create_pipeline(sample_proposal)
            ids.add(pid)
        assert len(ids) == 50

    def test_events_initialized_empty(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        events = manager.get_events(pid)
        assert events == []


# =============================================================================
# get_pipeline Tests
# =============================================================================

class TestGetPipeline:
    """Test pipeline retrieval."""

    def test_returns_data_for_known_id(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        pipeline = manager.get_pipeline(pid)
        assert pipeline is not None
        assert pipeline["id"] == pid

    def test_returns_none_for_unknown_id(self, manager):
        result = manager.get_pipeline("nonexistent")
        assert result is None


# =============================================================================
# get_events Tests
# =============================================================================

class TestGetEvents:
    """Test event retrieval."""

    def test_empty_initially(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        assert manager.get_events(pid) == []

    def test_returns_empty_for_unknown_pipeline(self, manager):
        assert manager.get_events("unknown-id") == []


# =============================================================================
# get_all_pipelines Tests
# =============================================================================

class TestGetAllPipelines:
    """Test pipeline listing."""

    def test_empty_initially(self, manager):
        assert manager.get_all_pipelines() == []

    def test_returns_all_pipelines(self, manager, sample_proposal):
        for _ in range(5):
            manager.create_pipeline(sample_proposal)
        assert len(manager.get_all_pipelines()) == 5

    def test_max_20_pipelines(self, manager, sample_proposal):
        for _ in range(25):
            manager.create_pipeline(sample_proposal)
        assert len(manager.get_all_pipelines()) == 20

    def test_sorted_by_created_at(self, manager, sample_proposal):
        for _ in range(3):
            manager.create_pipeline(sample_proposal)
        pipelines = manager.get_all_pipelines()
        dates = [p["created_at"] for p in pipelines]
        assert dates == sorted(dates, reverse=True)


# =============================================================================
# broadcast Tests
# =============================================================================

class TestBroadcast:
    """Test event broadcasting."""

    @pytest.mark.asyncio
    async def test_stores_event(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        await manager.broadcast(pid, {"type": "test_event", "data": "hello"})

        events = manager.get_events(pid)
        assert len(events) == 1
        assert events[0]["type"] == "test_event"
        assert events[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_adds_timestamp(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        await manager.broadcast(pid, {"type": "test"})

        events = manager.get_events(pid)
        assert "timestamp" in events[0]

    @pytest.mark.asyncio
    async def test_updates_pipeline_status(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        await manager.broadcast(pid, {"type": "agent_started", "state": "YIELD_ANALYSIS"})

        pipeline = manager.get_pipeline(pid)
        assert pipeline["status"] == "YIELD_ANALYSIS"

    @pytest.mark.asyncio
    async def test_stores_result_on_completion(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        result_data = {"final_decision": "PASS", "votes_pass": 3}

        await manager.broadcast(pid, {
            "type": "pipeline_completed",
            "state": "COMPLETED",
            "result": result_data,
        })

        pipeline = manager.get_pipeline(pid)
        assert pipeline["result"] == result_data

    @pytest.mark.asyncio
    async def test_multiple_events_stored_in_order(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)

        await manager.broadcast(pid, {"type": "event_1"})
        await manager.broadcast(pid, {"type": "event_2"})
        await manager.broadcast(pid, {"type": "event_3"})

        events = manager.get_events(pid)
        assert len(events) == 3
        assert events[0]["type"] == "event_1"
        assert events[1]["type"] == "event_2"
        assert events[2]["type"] == "event_3"

    @pytest.mark.asyncio
    async def test_broadcast_handles_unknown_pipeline(self, manager):
        """Broadcasting to unknown pipeline should not crash."""
        await manager.broadcast("unknown", {"type": "test"})
        # Event is still stored
        events = manager.get_events("unknown")
        assert len(events) == 1


# =============================================================================
# create_event_callback Tests
# =============================================================================

class TestCreateEventCallback:
    """Test event callback factory."""

    @pytest.mark.asyncio
    async def test_creates_callable(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        callback = manager.create_event_callback(pid)

        assert callable(callback)

    @pytest.mark.asyncio
    async def test_callback_broadcasts_events(self, manager, sample_proposal):
        pid = manager.create_pipeline(sample_proposal)
        callback = manager.create_event_callback(pid)

        await callback({"type": "test_from_callback", "state": "EXECUTING"})

        events = manager.get_events(pid)
        assert len(events) == 1
        assert events[0]["type"] == "test_from_callback"

        pipeline = manager.get_pipeline(pid)
        assert pipeline["status"] == "EXECUTING"


# =============================================================================
# disconnect Tests
# =============================================================================

class TestDisconnect:
    """Test WebSocket disconnection cleanup."""

    def test_disconnect_unknown_pipeline(self, manager):
        """Disconnecting from unknown pipeline should not crash."""
        mock_ws = MagicMock()
        manager.disconnect("unknown-pipeline", mock_ws)
        # No exception raised

    def test_disconnect_removes_websocket(self, manager, sample_proposal):
        """After disconnect, the websocket should be removed."""
        pid = manager.create_pipeline(sample_proposal)
        mock_ws = MagicMock()
        # Manually add websocket
        manager._connections[pid] = [mock_ws]

        manager.disconnect(pid, mock_ws)
        assert mock_ws not in manager._connections[pid]

class TestConnectMissingBranch:
    @pytest.mark.asyncio
    async def test_connect_unseen_pipeline(self, manager):
        from fastapi import WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        await manager.connect("not-yet-created-pipeline", mock_ws)
        assert mock_ws in manager._connections["not-yet-created-pipeline"]

class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_accepts_and_adds(self, manager, sample_proposal):
        from fastapi import WebSocket
        pid = manager.create_pipeline(sample_proposal)
        mock_ws = AsyncMock(spec=WebSocket)

        await manager.connect(pid, mock_ws)

        mock_ws.accept.assert_called_once()
        assert mock_ws in manager._connections[pid]

    @pytest.mark.asyncio
    async def test_connect_replays_events(self, manager, sample_proposal):
        from fastapi import WebSocket
        pid = manager.create_pipeline(sample_proposal)
        await manager.broadcast(pid, {"type": "event1"})

        mock_ws = AsyncMock(spec=WebSocket)
        await manager.connect(pid, mock_ws)

        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_handles_send_error(self, manager, sample_proposal):
        from fastapi import WebSocket
        pid = manager.create_pipeline(sample_proposal)
        await manager.broadcast(pid, {"type": "event1"})

        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json.side_effect = Exception("Send failed")

        await manager.connect(pid, mock_ws)
        assert mock_ws in manager._connections[pid]

class TestBroadcastDeadConnections:
    @pytest.mark.asyncio
    async def test_broadcast_cleans_dead_connections(self, manager, sample_proposal):
        from fastapi import WebSocket
        pid = manager.create_pipeline(sample_proposal)
        mock_ws_good = AsyncMock(spec=WebSocket)
        mock_ws_bad = AsyncMock(spec=WebSocket)
        mock_ws_bad.send_json.side_effect = Exception("Disconnected")

        await manager.connect(pid, mock_ws_good)
        await manager.connect(pid, mock_ws_bad)

        await manager.broadcast(pid, {"type": "test"})

        assert mock_ws_good in manager._connections[pid]
        assert mock_ws_bad not in manager._connections[pid]
