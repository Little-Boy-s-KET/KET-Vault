"""
KET Board - Orchestrator Unit Tests.

Tests all state machine transitions and agent consensus scenarios.
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Decision, Proposal, ProposalAction, PipelineState
from orchestrator import KETOrchestrator
from agents import YieldMaxiAgent, RiskAuditorAgent, MacroStrategistAgent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def orchestrator():
    """Create an orchestrator with default settings."""
    return KETOrchestrator(threshold=2)


@pytest.fixture
def usdc_proposal():
    """Standard USDC yield farming proposal."""
    return Proposal(
        action=ProposalAction.FARM_YIELD,
        token="USDC",
        amount=1000.0,
        target_protocol="Agni Finance",
        max_impermanent_loss=10.0,
        min_audit_score=80.0,
    )


@pytest.fixture
def unknown_token_proposal():
    """Proposal with unknown token - should be rejected."""
    return Proposal(
        action=ProposalAction.FARM_YIELD,
        token="FAKECOIN",
        amount=100.0,
    )


@pytest.fixture
def lending_proposal():
    """Low-risk lending proposal."""
    return Proposal(
        action=ProposalAction.LEND,
        token="USDC",
        amount=5000.0,
        target_protocol="Lendle",
    )


# =============================================================================
# Individual Agent Tests
# =============================================================================

class TestYieldMaxiAgent:
    """Test the Yield Maxi agent's analysis logic."""

    @pytest.mark.asyncio
    async def test_pass_valid_token(self, usdc_proposal):
        agent = YieldMaxiAgent()
        decision = await agent.analyze(usdc_proposal)

        assert decision.agent_name == "yield_maxi"
        assert decision.decision == Decision.PASS
        assert 0 < decision.confidence <= 1.0
        assert "Agni" in decision.reason
        assert "apy" in decision.data
        assert "tvl" in decision.data

    @pytest.mark.asyncio
    async def test_reject_unknown_token(self, unknown_token_proposal):
        agent = YieldMaxiAgent()
        decision = await agent.analyze(unknown_token_proposal)

        assert decision.decision == Decision.REJECT
        assert decision.confidence >= 0.9
        assert "No pools" in decision.reason


class TestRiskAuditorAgent:
    """Test the Risk Auditor agent's security validation."""

    @pytest.mark.asyncio
    async def test_pass_audited_protocol(self, usdc_proposal):
        agent = RiskAuditorAgent()
        context = {
            "yield_maxi_data": {
                "recommended_protocol": "Agni Finance",
                "apy": 24.5,
                "tvl": 2_300_000,
            }
        }
        decision = await agent.analyze(usdc_proposal, context=context)

        assert decision.agent_name == "risk_auditor"
        assert decision.decision == Decision.PASS
        assert decision.data["audit_status"] == "AUDITED"
        assert decision.data["auditor"] == "Zellic"

    @pytest.mark.asyncio
    async def test_dynamic_veto_impermanent_loss(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            max_impermanent_loss=5.0,  # Below Agni's 8.2% IL
        )
        agent = RiskAuditorAgent()
        context = {
            "yield_maxi_data": {
                "recommended_protocol": "Agni Finance",
            }
        }
        decision = await agent.analyze(proposal, context=context)
        assert decision.decision == Decision.REJECT
        assert "VETO: IL risk 8.2% exceeds user maximum threshold" in decision.reason

    @pytest.mark.asyncio
    async def test_dynamic_veto_audit_score(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            min_audit_score=98.0,  # Above Agni's Zellic score of 95
        )
        agent = RiskAuditorAgent()
        context = {
            "yield_maxi_data": {
                "recommended_protocol": "Agni Finance",
            }
        }
        decision = await agent.analyze(proposal, context=context)
        assert decision.decision == Decision.REJECT
        assert "VETO: Contract audit score 95 is below user minimum threshold" in decision.reason

    @pytest.mark.asyncio
    async def test_veto_unknown_protocol(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="RugPullSwap",
        )
        agent = RiskAuditorAgent()
        context = {
            "yield_maxi_data": {
                "recommended_protocol": "RugPullSwap",
            }
        }
        decision = await agent.analyze(proposal, context=context)

        assert decision.decision == Decision.REJECT
        assert decision.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_pass_low_il_lending(self, lending_proposal):
        agent = RiskAuditorAgent()
        context = {
            "yield_maxi_data": {
                "recommended_protocol": "Lendle",
            }
        }
        decision = await agent.analyze(lending_proposal, context=context)

        assert decision.decision == Decision.PASS
        assert decision.data["il_risk_pct"] == 0.0
        assert decision.data["risk_score"] == "LOW"


class TestMacroStrategistAgent:
    """Test the Macro Strategist agent's timing logic."""

    @pytest.mark.asyncio
    async def test_returns_pass_or_defer(self, usdc_proposal):
        agent = MacroStrategistAgent()
        decision = await agent.analyze(usdc_proposal)

        assert decision.agent_name == "macro_strategist"
        assert decision.decision in (Decision.PASS, Decision.DEFER)
        assert "gas_price_gwei" in decision.data
        assert "network_utilization_pct" in decision.data


# =============================================================================
# Full Pipeline Tests
# =============================================================================

class TestOrchestrator:
    """Test the full consensus pipeline."""

    @pytest.mark.asyncio
    async def test_happy_path_consensus(self, orchestrator, usdc_proposal):
        """USDC + Agni Finance should reach consensus."""
        result = await orchestrator.run_pipeline(
            usdc_proposal, verbose=False
        )

        assert result.proposal_id == usdc_proposal.id
        assert len(result.decisions) == 3  # all 3 agents ran
        assert result.votes_pass >= 2
        assert result.final_decision == Decision.PASS
        # Should have a (mock) tx hash
        assert result.tx_hash is not None
        assert result.tx_hash.startswith("0x")
        assert result.explorer_url is not None

    @pytest.mark.asyncio
    async def test_reject_unknown_token(self, orchestrator, unknown_token_proposal):
        """Unknown token should be rejected by Yield Maxi early."""
        result = await orchestrator.run_pipeline(
            unknown_token_proposal, verbose=False
        )

        assert result.final_decision == Decision.REJECT
        assert result.votes_reject >= 1
        assert result.tx_hash is None  # no execution

    @pytest.mark.asyncio
    async def test_lending_low_risk(self, orchestrator, lending_proposal):
        """Lending proposals should pass with high confidence."""
        result = await orchestrator.run_pipeline(
            lending_proposal, verbose=False
        )

        # Lending has 0% IL, should pass risk check easily
        risk_decision = next(
            d for d in result.decisions if d.agent_name == "risk_auditor"
        )
        assert risk_decision.decision == Decision.PASS
        assert risk_decision.data["il_risk_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_pipeline_has_three_core_agents(self, orchestrator):
        """Pipeline should always involve at least 3 core agents."""
        from router import CORE_EXPERTS
        assert len(CORE_EXPERTS) == 3
        assert "yield_maxi" in CORE_EXPERTS
        assert "risk_auditor" in CORE_EXPERTS
        assert "macro_strategist" in CORE_EXPERTS

    @pytest.mark.asyncio
    async def test_consensus_threshold(self, orchestrator):
        """Threshold should be 2 out of 3."""
        assert orchestrator.threshold == 2

    @pytest.mark.asyncio
    async def test_result_model_integrity(self, orchestrator, usdc_proposal):
        """Result should have all required fields populated."""
        result = await orchestrator.run_pipeline(
            usdc_proposal, verbose=False
        )

        assert result.proposal_id is not None
        assert len(result.decisions) > 0
        assert result.votes_pass + result.votes_reject + result.votes_defer == len(result.decisions)
        assert result.threshold == 2
        assert result.completed_at is not None
