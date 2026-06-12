"""
KET Board - Pydantic Data Models.

Defines the strict JSON schemas that all agents MUST conform to.
This is the contract between agents, orchestrator, and API layer.

Upgraded to support 10-agent MoE (Mixture-of-Experts) pipeline
merged from KET_core_CLI architecture.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class ProposalAction(str, Enum):
    """Supported treasury actions."""
    FARM_YIELD = "FARM_YIELD"
    PROVIDE_LIQUIDITY = "PROVIDE_LIQUIDITY"
    LEND = "LEND"
    SWAP = "SWAP"
    WITHDRAW = "WITHDRAW"


class OpportunityType(str, Enum):
    """MoE opportunity types for smart routing."""
    YIELD_FARM = "YIELD_FARM"
    ARBITRAGE = "ARBITRAGE"
    HEDGE = "HEDGE"
    REBALANCE = "REBALANCE"
    ECOSYSTEM_FARM = "ECOSYSTEM_FARM"


class Decision(str, Enum):
    """Agent vote options."""
    PASS = "PASS"
    REJECT = "REJECT"
    DEFER = "DEFER"


class ActionDecision(str, Enum):
    """MoE expert evaluation decisions (from CLI architecture)."""
    APPROVE = "APPROVE"
    AMEND = "AMEND"
    VETO = "VETO"


class AgentRole(str, Enum):
    """Agent classification for UI grouping."""
    CORE = "core"
    SPECIALIST = "specialist"
    GUARDIAN = "guardian"


class PipelineState(str, Enum):
    """State machine states for the consensus pipeline."""
    PROPOSAL_RECEIVED = "PROPOSAL_RECEIVED"
    EXPERT_SELECTION = "EXPERT_SELECTION"
    YIELD_ANALYSIS = "YIELD_ANALYSIS"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    MACRO_TIMING = "MACRO_TIMING"
    PARALLEL_EVALUATION = "PARALLEL_EVALUATION"
    CONSENSUS_SYNTHESIS = "CONSENSUS_SYNTHESIS"
    FINAL_AUDIT = "FINAL_AUDIT"
    CONSENSUS_REACHED = "CONSENSUS_REACHED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# =============================================================================
# Core Models
# =============================================================================

class Proposal(BaseModel):
    """
    Input from user: a treasury action request.

    Example:
        {
            "action": "FARM_YIELD",
            "token": "USDC",
            "amount": 1000.0,
            "target_protocol": "Agni Finance",
            "opportunity_type": "YIELD_FARM"
        }
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: ProposalAction
    token: str = Field(description="Token symbol (e.g., USDC, MNT, WETH)")
    amount: float = Field(gt=0, description="Amount in token units")
    target_protocol: str = Field(
        default="",
        description="Target DeFi protocol (optional, agent can suggest)",
    )
    opportunity_type: OpportunityType = Field(
        default=OpportunityType.YIELD_FARM,
        description="Type of opportunity for MoE routing",
    )
    max_impermanent_loss: float = Field(default=5.0, description="Max IL tolerance percent")
    min_audit_score: float = Field(default=80.0, description="Min security audit score required")
    context: str = Field(default="", description="Additional context for expert routing")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AgentDecision(BaseModel):
    """
    Strict JSON output from each agent.
    Every agent MUST return exactly this structure.
    """
    agent_name: str = Field(description="Name of the agent (e.g., yield_maxi)")
    decision: Decision
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score 0.0 to 1.0",
    )
    reason: str = Field(description="Human-readable justification")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific analysis data (APY, risk score, gas, etc.)",
    )
    amended_params: Optional[dict[str, Any]] = Field(
        default=None,
        description="Amended parameters if agent suggests changes (MoE AMEND)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ConsensusResult(BaseModel):
    """Final output of the consensus pipeline."""
    proposal_id: str
    decisions: list[AgentDecision]
    selected_experts: list[str] = Field(
        default_factory=list,
        description="Experts selected by the MoE Router",
    )
    votes_pass: int = 0
    votes_reject: int = 0
    votes_defer: int = 0
    threshold: int = 2
    final_decision: Decision
    synthesis_reasoning: str = Field(
        default="",
        description="LLM consensus synthesis reasoning",
    )
    tx_hash: str | None = None
    explorer_url: str | None = None
    signature_slots: dict[str, str | None] = Field(
        default_factory=lambda: {
            "yield_maxi": None,
            "risk_auditor": None,
            "macro_strategist": None,
        },
        description="Cryptographic signature placeholders per agent",
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def consensus_reached(self) -> bool:
        return self.votes_pass >= self.threshold


class LogEntry(BaseModel):
    """Structured log entry for pipeline events."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    state: PipelineState
    agent: str = ""
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class PipelineContext(BaseModel):
    """
    Full context of a running pipeline.
    Tracks state, proposal, all decisions, and logs.
    """
    state: PipelineState = PipelineState.PROPOSAL_RECEIVED
    proposal: Proposal
    decisions: list[AgentDecision] = Field(default_factory=list)
    selected_experts: list[str] = Field(
        default_factory=list,
        description="Experts chosen by MoE Router",
    )
    logs: list[LogEntry] = Field(default_factory=list)
    error: str | None = None
    iterations_remaining: int = Field(
        default=3,
        description="Amendment loop budget. Hits 0 -> auto-reject.",
    )

    def add_log(self, message: str, agent: str = "", data: dict | None = None):
        """Append a structured log entry."""
        self.logs.append(
            LogEntry(
                state=self.state,
                agent=agent,
                message=message,
                data=data or {},
            )
        )

    def add_decision(self, decision: AgentDecision):
        """Record an agent's decision."""
        self.decisions.append(decision)
        self.add_log(
            message=f"{decision.agent_name}: {decision.decision.value} "
                    f"({decision.confidence:.0%}) - {decision.reason}",
            agent=decision.agent_name,
            data=decision.data,
        )
