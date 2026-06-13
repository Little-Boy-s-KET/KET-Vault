import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add backend to path FIRST so it finds the right main.py
import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parent.parent
_AGENT_CORE = _BACKEND.parent.parent / "packages" / "agent-core"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(1, str(_AGENT_CORE))

from main import app
from models import Proposal, ProposalAction, OpportunityType
from unittest.mock import patch
from core.pipeline_manager import pipeline_manager
from api.routes import _run_pipeline_task

# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_root_health(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detailed_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

# =============================================================================
# Agent Endpoints Tests
# =============================================================================

class TestAgentEndpoints:
    @pytest.mark.asyncio
    async def test_list_agents(self, client):
        resp = await client.get("/api/agents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_agent_yield_maxi(self, client):
        resp = await client.get("/api/agents/yield_maxi")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        resp = await client.get("/api/agents/nonexistent_agent")
        assert resp.status_code == 404

# =============================================================================
# Proposal Endpoint Tests
# =============================================================================

class TestProposalEndpoint:
    @pytest.mark.asyncio
    async def test_submit_valid_proposal(self, client):
        resp = await client.post("/api/proposal", json={
            "action": "FARM_YIELD",
            "token": "USDC",
            "amount": 1000.0,
            "target_protocol": "Agni Finance",
            "opportunity_type": "YIELD_FARM",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_submit_invalid_action(self, client):
        resp = await client.post("/api/proposal", json={
            "action": "INVALID_ACTION",
            "token": "USDC",
            "amount": 1000.0,
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_invalid_opportunity_type(self, client):
        resp = await client.post("/api/proposal", json={
            "action": "FARM_YIELD",
            "token": "USDC",
            "amount": 1000.0,
            "opportunity_type": "INVALID_TYPE",
        })
        assert resp.status_code == 400

class TestPipelineTask:
    @pytest.mark.asyncio
    async def test_run_pipeline_task_success(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )
        with patch('api.routes.KETOrchestrator') as MockOrch:
            mock_instance = MockOrch.return_value
            mock_instance.run_pipeline.return_value = {"final_decision": "PASS"}
            await _run_pipeline_task("test-task-123", proposal)
            mock_instance.run_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_pipeline_task_exception(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )
        pipeline_manager.create_pipeline(proposal.model_dump(mode="json"))
        with patch('api.routes.KETOrchestrator') as MockOrch:
            mock_instance = MockOrch.return_value
            mock_instance.run_pipeline.side_effect = Exception("Orchestrator failed")
            await _run_pipeline_task("test-task-123", proposal)
            events = pipeline_manager.get_events("test-task-123")
            assert any(e["type"] == "pipeline_error" for e in events)

class TestStatusEndpoint:
    @pytest.mark.asyncio
    async def test_get_status_after_submit(self, client):
        submit_resp = await client.post("/api/proposal", json={
            "action": "LEND",
            "token": "USDC",
            "amount": 1000.0,
        })
        pipeline_id = submit_resp.json()["pipeline_id"]
        status_resp = await client.get(f"/api/status/{pipeline_id}")
        assert status_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client):
        resp = await client.get("/api/status/nonexistent")
        assert resp.status_code == 404

class TestHistoryEndpoint:
    @pytest.mark.asyncio
    async def test_get_history(self, client):
        resp = await client.get("/api/history")
        assert resp.status_code == 200
