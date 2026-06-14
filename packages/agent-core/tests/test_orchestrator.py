import sys
from pathlib import Path

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock openai globally before imports
sys.modules['openai'] = MagicMock()

from models import Decision, Proposal, ProposalAction, PipelineState, OpportunityType, AgentDecision
from orchestrator import KETOrchestrator
from agents import YieldMaxiAgent, RiskAuditorAgent, MacroStrategistAgent

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def orchestrator():
    return KETOrchestrator(threshold=2)

@pytest.fixture
def usdc_proposal():
    return Proposal(
        action=ProposalAction.FARM_YIELD,
        token="USDC",
        amount=1000.0,
        target_protocol="Agni Finance",
        max_impermanent_loss=10.0,
        min_audit_score=80.0,
        opportunity_type=OpportunityType.YIELD_FARM
    )

@pytest.fixture
def unknown_token_proposal():
    return Proposal(
        action=ProposalAction.FARM_YIELD,
        token="FAKECOIN",
        amount=100.0,
        opportunity_type=OpportunityType.YIELD_FARM
    )

@pytest.fixture
def lending_proposal():
    return Proposal(
        action=ProposalAction.LEND,
        token="USDC",
        amount=5000.0,
        target_protocol="Lendle",
        opportunity_type=OpportunityType.YIELD_FARM
    )

# =============================================================================
# Individual Agent Tests
# =============================================================================

class TestYieldMaxiAgent:
    @pytest.mark.asyncio
    async def test_pass_valid_token(self, usdc_proposal):
        agent = YieldMaxiAgent()
        decision = await agent.analyze(usdc_proposal)
        assert decision.agent_name == "yield_maxi"
        assert decision.decision == Decision.PASS

    @pytest.mark.asyncio
    async def test_reject_unknown_token(self, unknown_token_proposal):
        agent = YieldMaxiAgent()
        decision = await agent.analyze(unknown_token_proposal)
        assert decision.decision == Decision.REJECT

class TestRiskAuditorAgent:
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
        assert decision.decision == Decision.PASS

    @pytest.mark.asyncio
    async def test_dynamic_veto_impermanent_loss(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            max_impermanent_loss=5.0,
            opportunity_type=OpportunityType.YIELD_FARM
        )
        agent = RiskAuditorAgent()
        context = {"yield_maxi_data": {"recommended_protocol": "Agni Finance"}}
        decision = await agent.analyze(proposal, context=context)
        assert decision.decision == Decision.REJECT

    @pytest.mark.asyncio
    async def test_dynamic_veto_audit_score(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            min_audit_score=98.0,
            opportunity_type=OpportunityType.YIELD_FARM
        )
        agent = RiskAuditorAgent()
        context = {"yield_maxi_data": {"recommended_protocol": "Agni Finance"}}
        decision = await agent.analyze(proposal, context=context)
        assert decision.decision == Decision.REJECT

    @pytest.mark.asyncio
    async def test_veto_unknown_protocol(self):
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="RugPullSwap",
            opportunity_type=OpportunityType.YIELD_FARM
        )
        agent = RiskAuditorAgent()
        context = {"yield_maxi_data": {"recommended_protocol": "RugPullSwap"}}
        decision = await agent.analyze(proposal, context=context)
        assert decision.decision == Decision.REJECT

    @pytest.mark.asyncio
    async def test_pass_low_il_lending(self, lending_proposal):
        agent = RiskAuditorAgent()
        context = {"yield_maxi_data": {"recommended_protocol": "Lendle"}}
        decision = await agent.analyze(lending_proposal, context=context)
        assert decision.decision == Decision.PASS

class TestMacroStrategistAgent:
    @pytest.mark.asyncio
    async def test_returns_pass_or_defer(self, usdc_proposal):
        agent = MacroStrategistAgent()
        decision = await agent.analyze(usdc_proposal)
        assert decision.decision in (Decision.PASS, Decision.DEFER)


# =============================================================================
# Full Pipeline Tests
# =============================================================================

class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_happy_path_consensus(self, orchestrator, usdc_proposal):
        result = await orchestrator.run_pipeline(usdc_proposal, verbose=False)
        assert result.proposal_id == usdc_proposal.id
        assert len(result.decisions) > 0

    @pytest.mark.asyncio
    async def test_reject_unknown_token(self, orchestrator, unknown_token_proposal):
        result = await orchestrator.run_pipeline(unknown_token_proposal, verbose=False)
        assert result.final_decision == Decision.REJECT
        assert result.tx_hash is None

    @pytest.mark.asyncio
    async def test_lending_low_risk(self, orchestrator, lending_proposal):
        result = await orchestrator.run_pipeline(lending_proposal, verbose=False)
        risk_decision = next((d for d in result.decisions if d.agent_name == "risk_auditor"), None)
        if risk_decision:
            assert risk_decision.decision == Decision.PASS

    @pytest.mark.asyncio
    async def test_consensus_threshold(self, orchestrator):
        assert orchestrator.threshold == 2

    @pytest.mark.asyncio
    async def test_result_model_integrity(self, orchestrator, usdc_proposal):
        result = await orchestrator.run_pipeline(usdc_proposal, verbose=False)
        assert result.proposal_id is not None
        assert len(result.decisions) > 0
        assert result.votes_pass + result.votes_reject + result.votes_defer == len(result.decisions)
        assert result.completed_at is not None

# =============================================================================
# New Coverage Tests
# =============================================================================

class TestKETOrchestratorCoverage:
    @pytest.mark.asyncio
    async def test_run_pipeline_fail_routing(self):
        orch = KETOrchestrator()
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )

        with patch('orchestrator.select_experts') as mock_select:
            mock_select.return_value = []

            result = await orch.run_pipeline(proposal)
            assert result.final_decision == Decision.REJECT
            assert "No expert evaluations" in result.synthesis_reasoning

    @pytest.mark.asyncio
    async def test_run_pipeline_llm_synthesis(self):
        orch = KETOrchestrator()
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )

        # Override the synthesis function to simulate LLM behavior
        def mock_synthesis(decisions):
            return "llm says ok"

        orch._synthesize_consensus = mock_synthesis

        with patch('orchestrator.select_experts') as mock_select:
            mock_select.return_value = ["yield_maxi"]

            with patch('orchestrator.get_agent') as mock_get_agent:
                mock_agent = AsyncMock()
                mock_agent.name = "yield_maxi"
                mock_agent.role = "core"
                mock_agent.analyze.return_value = AgentDecision(
                    agent_name="yield_maxi", decision=Decision.PASS, confidence=0.8, reason="ok"
                )
                mock_get_agent.return_value = mock_agent

                with patch('orchestrator.simulate_tx', new_callable=AsyncMock) as mock_sim:
                    mock_sim.return_value = {"success": True, "gas_estimate": 100, "gas_cost_usd": 0.1, "will_revert": False, "warnings": []}
                    with patch('orchestrator.execute_tx', new_callable=AsyncMock) as mock_exec:
                        mock_exec.return_value = {"success": True, "tx_hash": "0x123", "explorer_url": "url"}

                        # Mocking threshold to 1 for this test since we only return 1 agent
                        orch.threshold = 1

                        result = await orch.run_pipeline(proposal)
                        assert result.final_decision == Decision.PASS
                        assert "llm says ok" in result.synthesis_reasoning or "1 experts APPROVE" in result.synthesis_reasoning

    @pytest.mark.asyncio
    async def test_run_pipeline_all_defer(self):
        orch = KETOrchestrator()
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )

        with patch('orchestrator.select_experts') as mock_select:
            mock_select.return_value = ["yield_maxi", "risk_auditor"]

            with patch('orchestrator.get_agent') as mock_get_agent:
                mock_agent = AsyncMock()
                mock_agent.name = "mock_agent"
                mock_agent.role = "core"
                mock_agent.analyze.return_value = AgentDecision(
                    agent_name="mock_agent", decision=Decision.DEFER, confidence=0.8, reason="deferring"
                )
                mock_get_agent.return_value = mock_agent

                with patch.dict('os.environ', {'LLM_STRATEGY': 'RULE_BASED'}):
                    result = await orch.run_pipeline(proposal)
                    assert result.final_decision == Decision.DEFER

    @pytest.mark.asyncio
    async def test_execute_sim_fail(self):
        orch = KETOrchestrator()
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )

        with patch('orchestrator.simulate_tx', new_callable=AsyncMock) as mock_sim:
            mock_sim.return_value = {"success": False, "gas_estimate": 0, "gas_cost_usd": 0, "will_revert": True, "warnings": ["Sim fail"]}
            with patch('orchestrator.select_experts') as mock_select:
                mock_select.return_value = ["yield_maxi"]
                with patch('orchestrator.get_agent') as mock_get_agent:
                    mock_agent = AsyncMock()
                    mock_agent.name = "yield_maxi"
                    mock_agent.role = "core"
                    mock_agent.analyze.return_value = AgentDecision(
                        agent_name="yield_maxi", decision=Decision.PASS, confidence=0.8, reason="ok"
                    )
                    mock_get_agent.return_value = mock_agent

                    orch.threshold = 1

                    # We expect the final decision to still be PASS from the consensus,
                    # but the context state should be FAILED due to simulation failure.
                    # Currently, Orchestrator doesn't change `final_decision` on tx failure, it only sets ctx.state = FAILED.
                    result = await orch.run_pipeline(proposal)
                    assert result.final_decision == Decision.PASS

    @pytest.mark.asyncio
    async def test_execute_exec_fail(self):
        orch = KETOrchestrator()
        proposal = Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
            opportunity_type=OpportunityType.YIELD_FARM
        )

        with patch('orchestrator.simulate_tx', new_callable=AsyncMock) as mock_sim:
            mock_sim.return_value = {"success": True, "gas_estimate": 100, "gas_cost_usd": 0.1, "will_revert": False, "warnings": []}
            with patch('orchestrator.execute_tx', new_callable=AsyncMock) as mock_exec:
                # execution returns failure
                mock_exec.return_value = {"success": False, "error": "Exec error"}
                with patch('orchestrator.select_experts') as mock_select:
                    mock_select.return_value = ["yield_maxi"]
                    with patch('orchestrator.get_agent') as mock_get_agent:
                        mock_agent = AsyncMock()
                        mock_agent.name = "yield_maxi"
                        mock_agent.role = "core"
                        mock_agent.analyze.return_value = AgentDecision(
                            agent_name="yield_maxi", decision=Decision.PASS, confidence=0.8, reason="ok"
                        )
                        mock_get_agent.return_value = mock_agent

                        orch.threshold = 1

                        result = await orch.run_pipeline(proposal)
                        assert result.final_decision == Decision.PASS
                        assert result.tx_hash is None
