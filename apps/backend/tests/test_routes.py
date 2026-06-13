"""
KET Board - REST API Routes Unit Tests.

Tests all API endpoints using httpx AsyncClient.
Pipeline execution is NOT awaited — only request/response validation.
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add backend and agent-core to path
# IMPORTANT: Backend must be FIRST so its main.py takes precedence
# over agent-core's main.py
_BACKEND = Path(__file__).resolve().parent.parent
_AGENT_CORE = _BACKEND.parent.parent / "packages" / "agent-core"
if str(_AGENT_CORE) not in sys.path:
    sys.path.insert(0, str(_AGENT_CORE))
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from main import app


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_health(self, client):
        resp = await client.get("/")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "operational"
        assert data["service"] == "KET Board API"
        assert data["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_detailed_health(self, client):
        resp = await client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["agents_count"] == 10
        assert "yield_maxi" in data["core_agents"]
        assert "risk_auditor" in data["core_agents"]
        assert "macro_strategist" in data["core_agents"]
        assert len(data["specialist_agents"]) == 6
        assert len(data["guardian_agents"]) == 1


# =============================================================================
# Agent Endpoints Tests
# =============================================================================

class TestAgentEndpoints:
    """Test agent listing and detail endpoints."""

    @pytest.mark.asyncio
    async def test_list_agents(self, client):
        resp = await client.get("/api/agents")

        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) == 10

        # Verify structure of first agent
        agent = agents[0]
        assert "name" in agent
        assert "display_name" in agent
        assert "role" in agent
        assert "emoji" in agent
        assert "color" in agent
        assert "erc8004_id" in agent
        assert "trust_score" in agent
        assert "description" in agent

    @pytest.mark.asyncio
    async def test_list_agents_roles(self, client):
        resp = await client.get("/api/agents")
        agents = resp.json()

        roles = [a["role"] for a in agents]
        assert roles.count("core") == 3
        assert roles.count("specialist") == 6
        assert roles.count("guardian") == 1

    @pytest.mark.asyncio
    async def test_get_agent_yield_maxi(self, client):
        resp = await client.get("/api/agents/yield_maxi")

        assert resp.status_code == 200
        agent = resp.json()
        assert agent["name"] == "yield_maxi"
        assert agent["display_name"] == "Yield Maxi"
        assert agent["role"] == "core"
        assert agent["erc8004_id"] == "#1042"
        assert agent["trust_score"] == 0.97

    @pytest.mark.asyncio
    async def test_get_agent_compliance_officer(self, client):
        resp = await client.get("/api/agents/compliance_officer")

        assert resp.status_code == 200
        assert resp.json()["role"] == "guardian"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        resp = await client.get("/api/agents/nonexistent_agent")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# =============================================================================
# Proposal Endpoint Tests
# =============================================================================

class TestProposalEndpoint:
    """Test proposal submission endpoint."""

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
        data = resp.json()
        assert "pipeline_id" in data
        assert len(data["pipeline_id"]) == 8
        assert "message" in data

    @pytest.mark.asyncio
    async def test_submit_minimal_proposal(self, client):
        """Default values should apply for optional fields."""
        resp = await client.post("/api/proposal", json={
            "action": "FARM_YIELD",
            "token": "USDC",
            "amount": 500.0,
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
        assert "Invalid action" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_invalid_opportunity_type(self, client):
        resp = await client.post("/api/proposal", json={
            "action": "FARM_YIELD",
            "token": "USDC",
            "amount": 1000.0,
            "opportunity_type": "INVALID_TYPE",
        })

        assert resp.status_code == 400
        assert "Invalid opportunity_type" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_all_actions(self, client):
        """All valid actions should be accepted."""
        actions = ["FARM_YIELD", "PROVIDE_LIQUIDITY", "LEND", "SWAP", "WITHDRAW"]
        for action in actions:
            resp = await client.post("/api/proposal", json={
                "action": action,
                "token": "USDC",
                "amount": 100.0,
            })
            assert resp.status_code == 200, f"Failed for action: {action}"

    @pytest.mark.asyncio
    async def test_submit_all_opportunity_types(self, client):
        """All valid opportunity types should be accepted."""
        types = ["YIELD_FARM", "ARBITRAGE", "HEDGE", "REBALANCE", "ECOSYSTEM_FARM"]
        for ot in types:
            resp = await client.post("/api/proposal", json={
                "action": "FARM_YIELD",
                "token": "USDC",
                "amount": 100.0,
                "opportunity_type": ot,
            })
            assert resp.status_code == 200, f"Failed for type: {ot}"

    @pytest.mark.asyncio
    async def test_submit_with_context(self, client):
        resp = await client.post("/api/proposal", json={
            "action": "FARM_YIELD",
            "token": "MNT",
            "amount": 50_000.0,
            "target_protocol": "Merchant Moe",
            "opportunity_type": "ECOSYSTEM_FARM",
            "max_impermanent_loss": 15.0,
            "min_audit_score": 85.0,
            "context": "volatile market with fomo sentiment",
        })
        assert resp.status_code == 200


# =============================================================================
# Status Endpoint Tests
# =============================================================================

class TestStatusEndpoint:
    """Test pipeline status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_after_submit(self, client):
        """A just-submitted pipeline should be retrievable."""
        submit_resp = await client.post("/api/proposal", json={
            "action": "LEND",
            "token": "USDC",
            "amount": 1000.0,
        })
        pipeline_id = submit_resp.json()["pipeline_id"]

        status_resp = await client.get(f"/api/status/{pipeline_id}")
        assert status_resp.status_code == 200

        data = status_resp.json()
        assert data["id"] == pipeline_id
        assert "proposal" in data
        assert "events" in data

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, client):
        resp = await client.get("/api/status/nonexistent")
        assert resp.status_code == 404


# =============================================================================
# History Endpoint Tests
# =============================================================================

class TestHistoryEndpoint:
    """Test pipeline history endpoint."""

    @pytest.mark.asyncio
    async def test_get_history(self, client):
        resp = await client.get("/api/history")

        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data
        assert isinstance(data["pipelines"], list)
