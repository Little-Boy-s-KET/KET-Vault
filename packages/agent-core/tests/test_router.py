"""
KET Board - MoE Router Unit Tests.

Tests the deterministic expert routing logic that selects
which specialists evaluate a given proposal.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import OpportunityType
from router import (
    ALL_EXPERTS,
    CORE_EXPERTS,
    GUARDIAN_EXPERTS,
    SPECIALIST_EXPERTS,
    select_experts,
)


# =============================================================================
# Core Expert Tests
# =============================================================================

class TestCoreExperts:
    """Core board members should always be selected."""

    def test_core_always_present_yield_farm(self):
        selected = select_experts(OpportunityType.YIELD_FARM, 100.0)
        for core in CORE_EXPERTS:
            assert core in selected

    def test_core_always_present_arbitrage(self):
        selected = select_experts(OpportunityType.ARBITRAGE, 100.0)
        for core in CORE_EXPERTS:
            assert core in selected

    def test_core_always_present_hedge(self):
        selected = select_experts(OpportunityType.HEDGE, 100.0)
        for core in CORE_EXPERTS:
            assert core in selected

    def test_core_always_present_rebalance(self):
        selected = select_experts(OpportunityType.REBALANCE, 100.0)
        for core in CORE_EXPERTS:
            assert core in selected

    def test_core_always_present_ecosystem(self):
        selected = select_experts(OpportunityType.ECOSYSTEM_FARM, 100.0)
        for core in CORE_EXPERTS:
            assert core in selected


# =============================================================================
# Opportunity-Based Routing Tests
# =============================================================================

class TestOpportunityRouting:
    """Specialist agents should be added based on opportunity type."""

    def test_arbitrage_adds_sniper(self):
        selected = select_experts(OpportunityType.ARBITRAGE, 100.0)
        assert "arbitrage_sniper" in selected

    def test_rebalance_adds_rebalancer(self):
        selected = select_experts(OpportunityType.REBALANCE, 100.0)
        assert "portfolio_rebalancer" in selected

    def test_hedge_adds_hedger(self):
        selected = select_experts(OpportunityType.HEDGE, 100.0)
        assert "delta_neutral_hedger" in selected

    def test_ecosystem_farm_adds_farmer(self):
        selected = select_experts(OpportunityType.ECOSYSTEM_FARM, 100.0)
        assert "ecosystem_farmer" in selected

    def test_yield_farm_no_extra_specialists_by_default(self):
        """Without context, YIELD_FARM should only have core experts."""
        selected = select_experts(OpportunityType.YIELD_FARM, 100.0)
        # Should only have core experts
        for s in selected:
            assert s in CORE_EXPERTS


# =============================================================================
# Context-Based Routing Tests
# =============================================================================

class TestContextRouting:
    """Routing based on context keywords and USD value."""

    def test_volatile_context_adds_hedger(self):
        selected = select_experts(
            OpportunityType.YIELD_FARM, 100.0, context="volatile market"
        )
        assert "delta_neutral_hedger" in selected

    def test_volatile_case_insensitive(self):
        selected = select_experts(
            OpportunityType.YIELD_FARM, 100.0, context="VOLATILE conditions"
        )
        assert "delta_neutral_hedger" in selected

    def test_sentiment_keywords_add_analyst(self):
        keywords = ["sentiment", "fear", "greed", "fud", "fomo", "crash", "pump"]
        for kw in keywords:
            selected = select_experts(
                OpportunityType.YIELD_FARM, 100.0, context=f"market is {kw}"
            )
            assert "sentiment_analyst" in selected, f"Failed for keyword: {kw}"

    def test_concentrated_context_adds_lp_manager(self):
        selected = select_experts(
            OpportunityType.YIELD_FARM, 100.0, context="concentrated liquidity"
        )
        assert "concentrated_lp_manager" in selected

    def test_clp_context_adds_lp_manager(self):
        selected = select_experts(
            OpportunityType.ECOSYSTEM_FARM, 100.0, context="CLP strategy"
        )
        assert "concentrated_lp_manager" in selected

    def test_no_lp_manager_for_arbitrage_context(self):
        """Concentrated LP only triggers for YIELD_FARM and ECOSYSTEM_FARM."""
        selected = select_experts(
            OpportunityType.ARBITRAGE, 100.0, context="concentrated"
        )
        assert "concentrated_lp_manager" not in selected


# =============================================================================
# Compliance Trigger Tests
# =============================================================================

class TestComplianceTrigger:
    """Compliance officer auto-triggers for large transactions."""

    def test_large_tx_adds_compliance(self):
        selected = select_experts(OpportunityType.YIELD_FARM, 15_000.0)
        assert "compliance_officer" in selected

    def test_small_tx_no_compliance(self):
        selected = select_experts(OpportunityType.YIELD_FARM, 5_000.0)
        assert "compliance_officer" not in selected

    def test_exact_threshold_no_compliance(self):
        """Exactly $10,000 should NOT trigger (condition is > 10_000)."""
        selected = select_experts(OpportunityType.YIELD_FARM, 10_000.0)
        assert "compliance_officer" not in selected

    def test_above_threshold_triggers(self):
        selected = select_experts(OpportunityType.YIELD_FARM, 10_001.0)
        assert "compliance_officer" in selected


# =============================================================================
# Deduplication Tests
# =============================================================================

class TestDeduplication:
    """Ensure no duplicate experts in selection."""

    def test_no_duplicates(self):
        """Even when multiple triggers match, no expert should appear twice."""
        selected = select_experts(
            OpportunityType.YIELD_FARM,
            50_000.0,
            context="volatile concentrated sentiment fear",
        )
        assert len(selected) == len(set(selected))

    def test_order_preserved(self):
        """Core experts should always come first."""
        selected = select_experts(OpportunityType.ARBITRAGE, 50_000.0)
        # Core experts should be at the beginning
        for i, core in enumerate(CORE_EXPERTS):
            assert selected[i] == core


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Verify expert list constants are correct."""

    def test_all_experts_count(self):
        assert len(ALL_EXPERTS) == 10

    def test_core_experts_count(self):
        assert len(CORE_EXPERTS) == 3

    def test_specialist_experts_count(self):
        assert len(SPECIALIST_EXPERTS) == 6

    def test_guardian_experts_count(self):
        assert len(GUARDIAN_EXPERTS) == 1

    def test_all_experts_is_superset(self):
        """ALL_EXPERTS should contain every expert from all categories."""
        for expert in CORE_EXPERTS + SPECIALIST_EXPERTS + GUARDIAN_EXPERTS:
            assert expert in ALL_EXPERTS
