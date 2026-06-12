"""
KET Board - MoE Gating Network / Smart Router.

Determines which specialist experts should evaluate a proposal
based on opportunity type, USD value, and market context.

Ported from KET_core_CLI router.py with enhancements for
the Web pipeline integration.
"""

from __future__ import annotations

from typing import List

from models import OpportunityType


# =============================================================================
# Expert Routing Logic
# =============================================================================

def select_experts(
    opportunity_type: OpportunityType,
    usd_value: float,
    context: str = "",
) -> List[str]:
    """
    Deterministic routing function to select the necessary experts
    based on the trigger context.

    The Risk Auditor and Macro Strategist are ALWAYS selected as
    core board members. Specialists are added based on conditions.

    Args:
        opportunity_type: Type of DeFi opportunity
        usd_value: Approximate USD value of the transaction
        context: Additional market context string

    Returns:
        List of unique expert names to activate
    """
    # Core board members — always present
    selected_experts = ["yield_maxi", "risk_auditor", "macro_strategist"]

    # --- Opportunity-based routing ---

    if opportunity_type == OpportunityType.ARBITRAGE:
        selected_experts.append("arbitrage_sniper")

    if opportunity_type == OpportunityType.YIELD_FARM:
        # If asset is volatile, add hedger alongside yield maxi
        if "volatile" in context.lower():
            selected_experts.append("delta_neutral_hedger")
        # Always add yield maxi (already in core)

    if opportunity_type == OpportunityType.REBALANCE:
        selected_experts.append("portfolio_rebalancer")

    if opportunity_type == OpportunityType.ECOSYSTEM_FARM:
        selected_experts.append("ecosystem_farmer")

    if opportunity_type == OpportunityType.HEDGE:
        selected_experts.append("delta_neutral_hedger")

    # --- Context-based routing ---

    # Auto-trigger compliance for large transactions
    if usd_value > 10_000:
        selected_experts.append("compliance_officer")

    # Add sentiment analyst if market context mentions sentiment keywords
    sentiment_keywords = ["sentiment", "fear", "greed", "fud", "fomo", "crash", "pump"]
    if any(kw in context.lower() for kw in sentiment_keywords):
        selected_experts.append("sentiment_analyst")

    # Add concentrated LP manager for liquidity provision
    if opportunity_type in (OpportunityType.YIELD_FARM, OpportunityType.ECOSYSTEM_FARM):
        if "concentrated" in context.lower() or "clp" in context.lower():
            selected_experts.append("concentrated_lp_manager")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for name in selected_experts:
        if name not in seen:
            seen.add(name)
            unique.append(name)

    return unique


# =============================================================================
# All Available Experts
# =============================================================================

ALL_EXPERTS = [
    "yield_maxi",
    "risk_auditor",
    "macro_strategist",
    "arbitrage_sniper",
    "delta_neutral_hedger",
    "concentrated_lp_manager",
    "ecosystem_farmer",
    "sentiment_analyst",
    "compliance_officer",
    "portfolio_rebalancer",
]

CORE_EXPERTS = ["yield_maxi", "risk_auditor", "macro_strategist"]

SPECIALIST_EXPERTS = [
    "arbitrage_sniper",
    "delta_neutral_hedger",
    "concentrated_lp_manager",
    "ecosystem_farmer",
    "sentiment_analyst",
    "portfolio_rebalancer",
]

GUARDIAN_EXPERTS = ["compliance_officer"]
