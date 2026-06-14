"""
KET Board - Specialist Agents & Registry Unit Tests.

Tests all 7 specialist agents (rule-based fallback mode)
and the AGENT_REGISTRY / get_agent() factory.

Environment: LLM_STRATEGY=RULE_BASED to ensure deterministic behavior.
"""

import os
import sys
from pathlib import Path

import pytest

# Force rule-based mode before importing agents
os.environ["LLM_STRATEGY"] = "RULE_BASED"

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Decision, Proposal, ProposalAction
from agents import (
    AGENT_REGISTRY,
    ArbitrageSniperAgent,
    ComplianceOfficerAgent,
    ConcentratedLPManagerAgent,
    DeltaNeutralHedgerAgent,
    EcosystemFarmerAgent,
    PortfolioRebalancerAgent,
    SentimentAnalystAgent,
    get_agent,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def standard_proposal():
    """A standard FARM_YIELD proposal."""
    return Proposal(
        action=ProposalAction.FARM_YIELD,
        token="USDC",
        amount=1000.0,
        target_protocol="Agni Finance",
    )


@pytest.fixture
def large_proposal():
    """A large transaction that should trigger compliance."""
    return Proposal(
        action=ProposalAction.FARM_YIELD,
        token="USDC",
        amount=150_000.0,
    )


@pytest.fixture
def small_proposal():
    """A small compliant transaction."""
    return Proposal(
        action=ProposalAction.LEND,
        token="USDC",
        amount=5_000.0,
    )


# =============================================================================
# ArbitrageSniperAgent Tests
# =============================================================================

class TestArbitrageSniperAgent:
    """Test the Arbitrage Sniper agent."""

    @pytest.mark.asyncio
    async def test_returns_pass(self, standard_proposal):
        agent = ArbitrageSniperAgent()
        decision = await agent.analyze(standard_proposal)

        assert decision.agent_name == "arbitrage_sniper"
        assert decision.decision == Decision.PASS
        assert 0 < decision.confidence <= 1.0
        assert "spread_pct" in decision.data
        assert "execution_type" in decision.data

    @pytest.mark.asyncio
    async def test_agent_name_correct(self):
        agent = ArbitrageSniperAgent()
        assert agent.name == "arbitrage_sniper"
        assert agent.emoji == "[A]"


# =============================================================================
# DeltaNeutralHedgerAgent Tests
# =============================================================================

class TestDeltaNeutralHedgerAgent:
    """Test the Delta-Neutral Hedger agent."""

    @pytest.mark.asyncio
    async def test_returns_pass_with_hedge_data(self, standard_proposal):
        agent = DeltaNeutralHedgerAgent()
        decision = await agent.analyze(standard_proposal)

        assert decision.agent_name == "delta_neutral_hedger"
        assert decision.decision == Decision.PASS
        assert "hedge_ratio" in decision.data
        assert "perp_platform" in decision.data
        assert "funding_rate" in decision.data


# =============================================================================
# ConcentratedLPManagerAgent Tests
# =============================================================================

class TestConcentratedLPManagerAgent:
    """Test the Concentrated LP Manager agent."""

    @pytest.mark.asyncio
    async def test_returns_pass_with_range_data(self, standard_proposal):
        agent = ConcentratedLPManagerAgent()
        decision = await agent.analyze(standard_proposal)

        assert decision.agent_name == "concentrated_lp_manager"
        assert decision.decision == Decision.PASS
        assert "range_width" in decision.data
        assert "fee_tier" in decision.data
        assert "in_range" in decision.data


# =============================================================================
# EcosystemFarmerAgent Tests
# =============================================================================

class TestEcosystemFarmerAgent:
    """Test the Ecosystem Farmer agent."""

    @pytest.mark.asyncio
    async def test_returns_pass_with_multi_layer_data(self, standard_proposal):
        agent = EcosystemFarmerAgent()
        decision = await agent.analyze(standard_proposal)

        assert decision.agent_name == "ecosystem_farmer"
        assert decision.decision == Decision.PASS
        assert "layers" in decision.data
        assert decision.data["layers"] > 1  # Multi-layer
        assert "base_apy" in decision.data
        assert "incentive_apy" in decision.data
        assert "airdrop_eligible" in decision.data


# =============================================================================
# SentimentAnalystAgent Tests
# =============================================================================

class TestSentimentAnalystAgent:
    """Test the Sentiment Analyst agent."""

    @pytest.mark.asyncio
    async def test_returns_pass_with_sentiment_data(self, standard_proposal):
        agent = SentimentAnalystAgent()
        decision = await agent.analyze(standard_proposal)

        assert decision.agent_name == "sentiment_analyst"
        assert decision.decision == Decision.PASS
        assert "fear_greed_index" in decision.data
        assert "sentiment" in decision.data
        assert "social_volume" in decision.data


# =============================================================================
# ComplianceOfficerAgent Tests
# =============================================================================

class TestComplianceOfficerAgent:
    """Test the Compliance Officer agent."""

    @pytest.mark.asyncio
    async def test_pass_below_limit(self, small_proposal):
        """Transactions under $100k should PASS."""
        agent = ComplianceOfficerAgent()
        decision = await agent.analyze(small_proposal)

        assert decision.agent_name == "compliance_officer"
        assert decision.decision == Decision.PASS
        assert decision.data["compliance_status"] == "CLEARED"
        assert decision.data["requires_multisig"] is False

    @pytest.mark.asyncio
    async def test_reject_above_limit(self, large_proposal):
        """Transactions over $100k should REJECT."""
        agent = ComplianceOfficerAgent()
        decision = await agent.analyze(large_proposal)

        assert decision.decision == Decision.REJECT
        assert decision.data["compliance_status"] == "BLOCKED"
        assert decision.data["requires_multisig"] is True
        assert "multi-sig" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_boundary_exact_100k(self):
        """Exactly $100k should PASS (condition is > 100_000)."""
        proposal = Proposal(
            action=ProposalAction.SWAP,
            token="USDC",
            amount=100_000.0,
        )
        agent = ComplianceOfficerAgent()
        decision = await agent.analyze(proposal)
        assert decision.decision == Decision.PASS


# =============================================================================
# PortfolioRebalancerAgent Tests
# =============================================================================

class TestPortfolioRebalancerAgent:
    """Test the Portfolio Rebalancer agent."""

    @pytest.mark.asyncio
    async def test_returns_pass_with_drift_data(self, standard_proposal):
        agent = PortfolioRebalancerAgent()
        decision = await agent.analyze(standard_proposal)

        assert decision.agent_name == "portfolio_rebalancer"
        assert decision.decision == Decision.PASS
        assert "current_drift" in decision.data
        assert "target_drift" in decision.data
        assert "rebalance_cost_usd" in decision.data


# =============================================================================
# Agent Registry Tests
# =============================================================================

class TestAgentRegistry:
    """Test the central AGENT_REGISTRY and get_agent() factory."""

    def test_registry_has_10_agents(self):
        assert len(AGENT_REGISTRY) == 10

    def test_all_expected_agents_registered(self):
        expected = [
            "yield_maxi", "risk_auditor", "macro_strategist",
            "arbitrage_sniper", "delta_neutral_hedger",
            "concentrated_lp_manager", "ecosystem_farmer",
            "sentiment_analyst", "compliance_officer",
            "portfolio_rebalancer",
        ]
        for name in expected:
            assert name in AGENT_REGISTRY, f"Agent '{name}' missing from registry"

    def test_get_agent_valid(self):
        agent = get_agent("yield_maxi")
        assert agent.name == "yield_maxi"

    def test_get_agent_all_names(self):
        for name in AGENT_REGISTRY:
            agent = get_agent(name)
            assert agent.name == name

    def test_get_agent_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent("nonexistent_agent")

    def test_each_agent_has_name_and_emoji(self):
        for name, agent in AGENT_REGISTRY.items():
            assert agent.name == name
            assert len(agent.emoji) > 0
            assert len(agent.system_prompt) > 0
