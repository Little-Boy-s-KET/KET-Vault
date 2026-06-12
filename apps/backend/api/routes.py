"""
KET Board - REST API Routes.

Endpoints:
    POST /api/proposal       - Submit a new treasury proposal
    GET  /api/status/{id}    - Get pipeline status
    GET  /api/history        - List recent pipelines
    GET  /api/agents         - List all available agents
    GET  /api/agents/{name}  - Get agent details
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# Add agent-core to path
_AGENT_CORE = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "agent-core"
if str(_AGENT_CORE) not in sys.path:
    sys.path.insert(0, str(_AGENT_CORE))

from models import Proposal, ProposalAction, OpportunityType
from orchestrator import KETOrchestrator
from core.pipeline_manager import pipeline_manager
from router import ALL_EXPERTS, CORE_EXPERTS, SPECIALIST_EXPERTS, GUARDIAN_EXPERTS

router = APIRouter(prefix="/api", tags=["pipeline"])


# =============================================================================
# Request / Response Models
# =============================================================================

class ProposalRequest(BaseModel):
    """Input from frontend."""
    action: str = Field(default="FARM_YIELD")
    token: str = Field(default="USDC")
    amount: float = Field(default=1000.0, gt=0)
    target_protocol: str = Field(default="Agni Finance")
    opportunity_type: str = Field(
        default="YIELD_FARM",
        description="MoE opportunity type for expert routing",
    )
    max_impermanent_loss: float = Field(default=5.0)
    min_audit_score: float = Field(default=80.0)
    context: str = Field(
        default="",
        description="Additional context for expert routing (e.g., 'volatile', 'sentiment')",
    )


class ProposalResponse(BaseModel):
    """Response after submitting a proposal."""
    pipeline_id: str
    message: str


class AgentInfo(BaseModel):
    """Agent details response."""
    name: str
    display_name: str
    role: str
    emoji: str
    color: str
    erc8004_id: str
    trust_score: float
    description: str


# =============================================================================
# Agent Metadata Registry
# =============================================================================

AGENT_METADATA = {
    "yield_maxi": {
        "display_name": "Yield Maxi",
        "role": "core",
        "emoji": "Y",
        "color": "#10b981",
        "erc8004_id": "#1042",
        "trust_score": 0.97,
        "description": "Capital Deployer & Alpha Scanner. Maximizes APY across Mantle ecosystem.",
    },
    "risk_auditor": {
        "display_name": "Risk Auditor",
        "role": "core",
        "emoji": "R",
        "color": "#ef4444",
        "erc8004_id": "#0887",
        "trust_score": 0.99,
        "description": "Safety Veto & Security Validator. Has ABSOLUTE VETO POWER.",
    },
    "macro_strategist": {
        "display_name": "Macro Strategist",
        "role": "core",
        "emoji": "M",
        "color": "#3b82f6",
        "erc8004_id": "#1201",
        "trust_score": 0.94,
        "description": "Execution Timer & Network Health Analyst. Optimizes gas and timing.",
    },
    "arbitrage_sniper": {
        "display_name": "Arbitrage Sniper",
        "role": "specialist",
        "emoji": "A",
        "color": "#06b6d4",
        "erc8004_id": "#2301",
        "trust_score": 0.91,
        "description": "Atomic cross-protocol flash trading. Zero-directional risk.",
    },
    "delta_neutral_hedger": {
        "display_name": "Delta-Neutral Hedger",
        "role": "specialist",
        "emoji": "D",
        "color": "#eab308",
        "erc8004_id": "#2302",
        "trust_score": 0.89,
        "description": "Volatility Shield. Hedges spot exposure via perp positions.",
    },
    "concentrated_lp_manager": {
        "display_name": "Concentrated LP",
        "role": "specialist",
        "emoji": "C",
        "color": "#f97316",
        "erc8004_id": "#2303",
        "trust_score": 0.86,
        "description": "Optimizes concentrated liquidity positions for max fee earnings.",
    },
    "ecosystem_farmer": {
        "display_name": "Ecosystem Farmer",
        "role": "specialist",
        "emoji": "E",
        "color": "#84cc16",
        "erc8004_id": "#2304",
        "trust_score": 0.88,
        "description": "Multi-protocol yield stacking and airdrop farming specialist.",
    },
    "sentiment_analyst": {
        "display_name": "Sentiment Analyst",
        "role": "specialist",
        "emoji": "S",
        "color": "#d946ef",
        "erc8004_id": "#2305",
        "trust_score": 0.82,
        "description": "Market psychology evaluation and crowd sentiment analysis.",
    },
    "portfolio_rebalancer": {
        "display_name": "Portfolio Rebalancer",
        "role": "specialist",
        "emoji": "P",
        "color": "#a855f7",
        "erc8004_id": "#2306",
        "trust_score": 0.85,
        "description": "Asset allocation optimizer. Maintains target portfolio weights.",
    },
    "compliance_officer": {
        "display_name": "Compliance Officer",
        "role": "guardian",
        "emoji": "G",
        "color": "#dc2626",
        "erc8004_id": "#9001",
        "trust_score": 0.96,
        "description": "Regulatory guardian. Auto-triggered for transactions > $10,000.",
    },
}


# =============================================================================
# Background Task
# =============================================================================

async def _run_pipeline_task(pipeline_id: str, proposal: Proposal):
    """Run the orchestrator pipeline as a background task."""
    orchestrator = KETOrchestrator()
    callback = pipeline_manager.create_event_callback(pipeline_id)

    try:
        result = await orchestrator.run_pipeline(
            proposal,
            verbose=False,
            on_event=callback,
        )
    except Exception as e:
        await pipeline_manager.broadcast(pipeline_id, {
            "type": "pipeline_error",
            "state": "FAILED",
            "error": str(e),
        })


# =============================================================================
# Routes
# =============================================================================

@router.post("/proposal", response_model=ProposalResponse)
async def submit_proposal(
    request: ProposalRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit a treasury proposal to the KET Board.

    The pipeline runs asynchronously. Connect to the WebSocket
    endpoint to receive real-time updates.
    """
    # Validate action
    try:
        action = ProposalAction(request.action)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{request.action}'. "
                   f"Valid: {[a.value for a in ProposalAction]}",
        )

    # Validate opportunity type
    try:
        opportunity_type = OpportunityType(request.opportunity_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid opportunity_type '{request.opportunity_type}'. "
                   f"Valid: {[o.value for o in OpportunityType]}",
        )

    # Create proposal
    proposal = Proposal(
        action=action,
        token=request.token.upper(),
        amount=request.amount,
        target_protocol=request.target_protocol,
        opportunity_type=opportunity_type,
        max_impermanent_loss=request.max_impermanent_loss,
        min_audit_score=request.min_audit_score,
        context=request.context,
    )

    # Create pipeline
    pipeline_id = pipeline_manager.create_pipeline(
        proposal.model_dump(mode="json")
    )

    # Launch pipeline in background
    background_tasks.add_task(_run_pipeline_task, pipeline_id, proposal)

    return ProposalResponse(
        pipeline_id=pipeline_id,
        message=f"Pipeline {pipeline_id} started. Connect to WS for updates.",
    )


@router.get("/status/{pipeline_id}")
async def get_status(pipeline_id: str):
    """Get current status of a pipeline."""
    pipeline = pipeline_manager.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    events = pipeline_manager.get_events(pipeline_id)
    return {
        **pipeline,
        "events": events,
    }


@router.get("/history")
async def get_history():
    """Get list of recent pipelines."""
    return {"pipelines": pipeline_manager.get_all_pipelines()}


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """List all available agents with their metadata."""
    agents = []
    for name in ALL_EXPERTS:
        meta = AGENT_METADATA.get(name, {})
        agents.append(AgentInfo(
            name=name,
            display_name=meta.get("display_name", name),
            role=meta.get("role", "specialist"),
            emoji=meta.get("emoji", "?"),
            color=meta.get("color", "#888888"),
            erc8004_id=meta.get("erc8004_id", "#0000"),
            trust_score=meta.get("trust_score", 0.5),
            description=meta.get("description", ""),
        ))
    return agents


@router.get("/agents/{name}", response_model=AgentInfo)
async def get_agent_info(name: str):
    """Get detailed information about a specific agent."""
    meta = AGENT_METADATA.get(name)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{name}' not found. Available: {ALL_EXPERTS}",
        )
    return AgentInfo(
        name=name,
        display_name=meta["display_name"],
        role=meta["role"],
        emoji=meta["emoji"],
        color=meta["color"],
        erc8004_id=meta["erc8004_id"],
        trust_score=meta["trust_score"],
        description=meta["description"],
    )
