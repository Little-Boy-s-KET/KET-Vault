"""
KET Board - Models Unit Tests.

Tests all Pydantic data models, their validation rules,
default values, enum constraints, and computed properties.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (
    AgentDecision,
    ConsensusResult,
    Decision,
    LogEntry,
    OpportunityType,
    PipelineContext,
    PipelineState,
    Proposal,
    ProposalAction,
)


# =============================================================================
# Proposal Tests
# =============================================================================

class TestProposal:
    """Test Proposal model creation and validation."""

    def test_minimal_creation(self):
        """Proposal with only required fields should use defaults."""
        p = Proposal(action=ProposalAction.FARM_YIELD, token="USDC", amount=1000.0)

        assert p.action == ProposalAction.FARM_YIELD
        assert p.token == "USDC"
        assert p.amount == 1000.0
        assert p.target_protocol == ""
        assert p.opportunity_type == OpportunityType.YIELD_FARM
        assert p.max_impermanent_loss == 5.0
        assert p.min_audit_score == 80.0
        assert p.context == ""
        assert p.metadata == {}

    def test_id_auto_generated(self):
        """Each proposal should get a unique 8-char ID."""
        p1 = Proposal(action=ProposalAction.LEND, token="USDC", amount=100.0)
        p2 = Proposal(action=ProposalAction.LEND, token="USDC", amount=100.0)

        assert len(p1.id) == 8
        assert len(p2.id) == 8
        assert p1.id != p2.id

    def test_created_at_auto_set(self):
        """Timestamp should be auto-populated."""
        p = Proposal(action=ProposalAction.SWAP, token="MNT", amount=500.0)
        assert p.created_at is not None

    def test_amount_must_be_positive(self):
        """Amount must be > 0."""
        with pytest.raises(ValidationError):
            Proposal(action=ProposalAction.FARM_YIELD, token="USDC", amount=0)

        with pytest.raises(ValidationError):
            Proposal(action=ProposalAction.FARM_YIELD, token="USDC", amount=-100)

    def test_invalid_action_raises(self):
        """Invalid action string should fail validation."""
        with pytest.raises(ValidationError):
            Proposal(action="INVALID_ACTION", token="USDC", amount=100.0)

    def test_all_actions_valid(self):
        """All ProposalAction enum values should be accepted."""
        for action in ProposalAction:
            p = Proposal(action=action, token="USDC", amount=100.0)
            assert p.action == action

    def test_all_opportunity_types_valid(self):
        """All OpportunityType enum values should be accepted."""
        for ot in OpportunityType:
            p = Proposal(
                action=ProposalAction.FARM_YIELD,
                token="USDC",
                amount=100.0,
                opportunity_type=ot,
            )
            assert p.opportunity_type == ot

    def test_full_creation(self):
        """Proposal with all fields explicitly set."""
        p = Proposal(
            action=ProposalAction.PROVIDE_LIQUIDITY,
            token="WETH",
            amount=5000.0,
            target_protocol="FusionX",
            opportunity_type=OpportunityType.HEDGE,
            max_impermanent_loss=10.0,
            min_audit_score=90.0,
            context="volatile market conditions",
            metadata={"source": "api"},
        )

        assert p.target_protocol == "FusionX"
        assert p.opportunity_type == OpportunityType.HEDGE
        assert p.max_impermanent_loss == 10.0
        assert p.min_audit_score == 90.0
        assert p.context == "volatile market conditions"
        assert p.metadata == {"source": "api"}

    def test_json_serialization(self):
        """Proposal should serialize to JSON cleanly."""
        p = Proposal(action=ProposalAction.LEND, token="USDC", amount=1000.0)
        data = p.model_dump(mode="json")

        assert data["action"] == "LEND"
        assert data["token"] == "USDC"
        assert data["amount"] == 1000.0
        assert "id" in data
        assert "created_at" in data


# =============================================================================
# AgentDecision Tests
# =============================================================================

class TestAgentDecision:
    """Test AgentDecision model validation."""

    def test_valid_decision(self):
        d = AgentDecision(
            agent_name="yield_maxi",
            decision=Decision.PASS,
            confidence=0.85,
            reason="Looks good",
        )
        assert d.agent_name == "yield_maxi"
        assert d.decision == Decision.PASS
        assert d.confidence == 0.85
        assert d.data == {}
        assert d.amended_params is None
        assert d.timestamp is not None

    def test_confidence_bounds(self):
        """Confidence must be between 0.0 and 1.0."""
        # Valid boundaries
        AgentDecision(
            agent_name="test", decision=Decision.PASS,
            confidence=0.0, reason="min",
        )
        AgentDecision(
            agent_name="test", decision=Decision.PASS,
            confidence=1.0, reason="max",
        )

        # Out of bounds
        with pytest.raises(ValidationError):
            AgentDecision(
                agent_name="test", decision=Decision.PASS,
                confidence=1.1, reason="too high",
            )

        with pytest.raises(ValidationError):
            AgentDecision(
                agent_name="test", decision=Decision.PASS,
                confidence=-0.1, reason="too low",
            )

    def test_all_decision_types(self):
        """All Decision enum values should be valid."""
        for dec in Decision:
            d = AgentDecision(
                agent_name="test", decision=dec,
                confidence=0.5, reason=f"Testing {dec.value}",
            )
            assert d.decision == dec

    def test_with_data_and_amended_params(self):
        d = AgentDecision(
            agent_name="risk_auditor",
            decision=Decision.REJECT,
            confidence=0.99,
            reason="Unaudited",
            data={"audit_status": "UNAUDITED", "risk_score": "CRITICAL"},
            amended_params={"slippage": 0.01},
        )
        assert d.data["audit_status"] == "UNAUDITED"
        assert d.amended_params["slippage"] == 0.01


# =============================================================================
# ConsensusResult Tests
# =============================================================================

class TestConsensusResult:
    """Test ConsensusResult model and consensus_reached property."""

    def _make_result(self, votes_pass=0, votes_reject=0, votes_defer=0, threshold=2):
        return ConsensusResult(
            proposal_id="test-001",
            decisions=[],
            votes_pass=votes_pass,
            votes_reject=votes_reject,
            votes_defer=votes_defer,
            threshold=threshold,
            final_decision=Decision.PASS if votes_pass >= threshold else Decision.REJECT,
        )

    def test_consensus_reached_true(self):
        result = self._make_result(votes_pass=2, threshold=2)
        assert result.consensus_reached is True

    def test_consensus_reached_false(self):
        result = self._make_result(votes_pass=1, threshold=2)
        assert result.consensus_reached is False

    def test_consensus_reached_exact_threshold(self):
        result = self._make_result(votes_pass=3, threshold=3)
        assert result.consensus_reached is True

    def test_consensus_exceeded_threshold(self):
        result = self._make_result(votes_pass=3, threshold=2)
        assert result.consensus_reached is True

    def test_default_signature_slots(self):
        result = self._make_result(votes_pass=2)
        assert "yield_maxi" in result.signature_slots
        assert "risk_auditor" in result.signature_slots
        assert "macro_strategist" in result.signature_slots
        assert all(v is None for v in result.signature_slots.values())

    def test_tx_hash_optional(self):
        result = self._make_result(votes_pass=0, threshold=2)
        assert result.tx_hash is None
        assert result.explorer_url is None


# =============================================================================
# PipelineContext Tests
# =============================================================================

class TestPipelineContext:
    """Test PipelineContext state tracking methods."""

    def test_initial_state(self):
        p = Proposal(action=ProposalAction.FARM_YIELD, token="USDC", amount=100.0)
        ctx = PipelineContext(proposal=p)

        assert ctx.state == PipelineState.PROPOSAL_RECEIVED
        assert len(ctx.decisions) == 0
        assert len(ctx.logs) == 0
        assert ctx.error is None
        assert ctx.iterations_remaining == 3

    def test_add_log(self):
        p = Proposal(action=ProposalAction.LEND, token="USDC", amount=100.0)
        ctx = PipelineContext(proposal=p)

        ctx.add_log("Pipeline started")
        ctx.add_log("Agent analyzing", agent="yield_maxi", data={"step": 1})

        assert len(ctx.logs) == 2
        assert ctx.logs[0].message == "Pipeline started"
        assert ctx.logs[0].state == PipelineState.PROPOSAL_RECEIVED
        assert ctx.logs[1].agent == "yield_maxi"
        assert ctx.logs[1].data == {"step": 1}

    def test_add_decision(self):
        p = Proposal(action=ProposalAction.FARM_YIELD, token="USDC", amount=100.0)
        ctx = PipelineContext(proposal=p)

        decision = AgentDecision(
            agent_name="yield_maxi",
            decision=Decision.PASS,
            confidence=0.85,
            reason="Good yield",
            data={"apy": 24.5},
        )
        ctx.add_decision(decision)

        assert len(ctx.decisions) == 1
        assert ctx.decisions[0].agent_name == "yield_maxi"
        # add_decision should also create a log entry
        assert len(ctx.logs) == 1
        assert "yield_maxi" in ctx.logs[0].message
        assert "PASS" in ctx.logs[0].message

    def test_state_transitions(self):
        p = Proposal(action=ProposalAction.FARM_YIELD, token="USDC", amount=100.0)
        ctx = PipelineContext(proposal=p)

        ctx.state = PipelineState.EXPERT_SELECTION
        assert ctx.state == PipelineState.EXPERT_SELECTION

        ctx.state = PipelineState.YIELD_ANALYSIS
        assert ctx.state == PipelineState.YIELD_ANALYSIS


# =============================================================================
# LogEntry Tests
# =============================================================================

class TestLogEntry:
    """Test LogEntry model."""

    def test_auto_timestamp(self):
        log = LogEntry(state=PipelineState.PROPOSAL_RECEIVED, message="Test")
        assert log.timestamp is not None

    def test_defaults(self):
        log = LogEntry(state=PipelineState.EXECUTING)
        assert log.agent == ""
        assert log.message == ""
        assert log.data == {}


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Test enum values are correct and complete."""

    def test_proposal_actions(self):
        actions = [a.value for a in ProposalAction]
        assert "FARM_YIELD" in actions
        assert "PROVIDE_LIQUIDITY" in actions
        assert "LEND" in actions
        assert "SWAP" in actions
        assert "WITHDRAW" in actions
        assert len(actions) == 5

    def test_opportunity_types(self):
        types = [t.value for t in OpportunityType]
        assert "YIELD_FARM" in types
        assert "ARBITRAGE" in types
        assert "HEDGE" in types
        assert "REBALANCE" in types
        assert "ECOSYSTEM_FARM" in types
        assert len(types) == 5

    def test_decisions(self):
        assert len(Decision) == 3
        assert Decision.PASS.value == "PASS"
        assert Decision.REJECT.value == "REJECT"
        assert Decision.DEFER.value == "DEFER"

    def test_pipeline_states_count(self):
        """Pipeline should have 14 distinct states."""
        assert len(PipelineState) == 14
