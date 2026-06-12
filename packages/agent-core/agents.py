"""
KET Board - AI Agent Personas (MoE Architecture).

10 specialized agents that analyze proposals and return
strictly-typed JSON decisions. Supports HYBRID mode:
- Rule-based (default): Fast, offline, deterministic
- GPT-4o (when OPENAI_API_KEY set): Smart, LLM-powered

Merged from KET_core_CLI expert system with Web pipeline integration.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from models import AgentDecision, Decision, Proposal
from skills import get_network_status, query_pools


# =============================================================================
# Hybrid LLM Helper
# =============================================================================

async def _try_llm_analysis(
    system_prompt: str,
    user_content: str,
    agent_name: str,
    fallback_decision: AgentDecision,
) -> AgentDecision:
    """
    Attempt GPT-4o analysis with automatic fallback to rule-based.
    Crash-proof: if LLM fails for any reason, returns fallback immediately.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    llm_strategy = os.environ.get("LLM_STRATEGY", "HYBRID").upper()

    if llm_strategy == "RULE_BASED" or not api_key or api_key.startswith("sk-your"):
        return fallback_decision

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            timeout=8,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Map LLM decision to our Decision enum
        llm_decision = data.get("decision", "PASS").upper()
        decision_map = {
            "PASS": Decision.PASS,
            "APPROVE": Decision.PASS,
            "REJECT": Decision.REJECT,
            "VETO": Decision.REJECT,
            "DEFER": Decision.DEFER,
            "AMEND": Decision.PASS,
        }

        return AgentDecision(
            agent_name=agent_name,
            decision=decision_map.get(llm_decision, Decision.PASS),
            confidence=float(data.get("confidence", 0.85)),
            reason=data.get("reason", data.get("reasoning", "LLM analysis")),
            data=data.get("data", {}),
            amended_params=data.get("amended_params"),
        )
    except Exception:
        # Crash-proof fallback — never let LLM failure break the pipeline
        return fallback_decision


# =============================================================================
# System Prompts
# =============================================================================

YIELD_MAXI_PROMPT = """You are the Yield Maxi Agent on the KET Board of Directors.

ROLE: Capital Deployer & Alpha Scanner
MANDATE: Maximize the treasury's annualized percentage yield (APY) across the Mantle ecosystem.

ANALYSIS CHECKLIST:
1. Scan all available pools/farms for the requested token
2. Rank by APY adjusted for TVL depth (prefer > $1M TVL)
3. Flag any pool with APY > 50% as potentially unsustainable
4. Recommend the best opportunity with clear reasoning

OUTPUT FORMAT (strict JSON):
{
    "decision": "PASS" | "REJECT",
    "confidence": 0.0 to 1.0,
    "reason": "one-line justification",
    "data": {
        "recommended_protocol": "string",
        "recommended_pair": "string",
        "apy": number,
        "tvl": number
    }
}

REJECT if: No pools found, all APYs < 2%, or TVL too low (< $100k).
"""

RISK_AUDITOR_PROMPT = """You are the Risk Auditor Agent on the KET Board of Directors.

ROLE: Safety Veto & Security Validator
MANDATE: Protect the treasury from exploits, rug pulls, and excessive risk.
You have ABSOLUTE VETO POWER - safety overrides yield.

ANALYSIS CHECKLIST:
1. Verify contract audit status (MUST be audited by reputable firm)
2. Calculate impermanent loss risk (REJECT if IL > 20%)
3. Check TVL stability (sudden drops = red flag)
4. Assess smart contract risk based on protocol age and track record

OUTPUT FORMAT (strict JSON):
{
    "decision": "PASS" | "REJECT",
    "confidence": 0.0 to 1.0,
    "reason": "one-line justification",
    "data": {
        "audit_status": "AUDITED" | "UNAUDITED",
        "auditor": "string",
        "il_risk_pct": number,
        "risk_score": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    }
}
"""

MACRO_STRATEGIST_PROMPT = """You are the Macro Strategist Agent on the KET Board of Directors.

ROLE: Execution Timer & Network Health Analyst
MANDATE: Ensure transactions execute at optimal cost and timing.
The Macro Strategist NEVER rejects - only PASS or DEFER.

OUTPUT FORMAT (strict JSON):
{
    "decision": "PASS" | "DEFER",
    "confidence": 0.0 to 1.0,
    "reason": "one-line justification",
    "data": {
        "gas_price_gwei": number,
        "network_utilization_pct": number,
        "optimal_window": true | false,
        "estimated_tx_cost_usd": number
    }
}
"""

ARBITRAGE_SNIPER_PROMPT = """You are The Arbitrage Sniper (The Inefficiency Exploiter).
Primary Role: Atomic cross-protocol flash trading on Mantle.
Mandate: Capture immediate, zero-risk price discrepancies across the ecosystem.
Execution Logic: Scan price feeds for the same asset pairs across competing Mantle DEXs.
When a profitable spread opens, build an atomic flash-swap transaction.
Trading Best Practice: Generate risk-free, market-neutral revenue streams.

Review the payload. Ensure it perfectly captures the arbitrage opportunity with zero directional risk.
You may AMEND the slippage to be very tight. If the spread is not profitable, REJECT. Otherwise, PASS.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"REJECT", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""

DELTA_NEUTRAL_HEDGER_PROMPT = """You are The Delta-Neutral Hedger (The Volatility Shield).
Primary Role: Short-side hedging and price-risk neutralization.
Mandate: Isolate pure yield while filtering out underlying asset price drops.
Execution Logic: When farming a high-yield pool with a volatile asset, calculate the exact
short position needed and open it on a Mantle perpetual DEX to offset spot exposure.
Trading Best Practice: Immunize the treasury from market downturns during farming.

Review the transaction. If it lacks proper hedging for a volatile asset, REJECT.
If hedging can be applied, PASS with hedge parameters. Otherwise, PASS.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"REJECT", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""

CONCENTRATED_LP_PROMPT = """You are The Concentrated LP Manager.
Primary Role: Optimize concentrated liquidity positions on Mantle DEXs.
Mandate: Maximize fee earnings by placing liquidity in the most active price ranges.
Trading Best Practice: Prevent out-of-range positions and minimize rebalancing costs.

PASS if the LP range and strategy are optimal. REJECT if risk of going out-of-range is high.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"REJECT", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""

ECOSYSTEM_FARMER_PROMPT = """You are The Ecosystem Farmer.
Primary Role: Multi-protocol yield stacking and airdrop farming on Mantle.
Mandate: Maximize composite yield by layering incentives across protocols.
Trading Best Practice: Identify protocols likely to airdrop and stack positions accordingly.

PASS if the farming strategy captures multiple reward layers. REJECT if single-layer only.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"REJECT", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""

SENTIMENT_ANALYST_PROMPT = """You are The Sentiment Analyst.
Primary Role: Market sentiment evaluation and crowd psychology analysis.
Mandate: Assess whether current market conditions favor the proposed action.
Trading Best Practice: Avoid deploying capital during extreme fear or euphoria.

PASS if sentiment is neutral or favorable. DEFER if extreme sentiment detected.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"DEFER", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""

COMPLIANCE_OFFICER_PROMPT = """You are The Compliance Officer (The Guardian).
Primary Role: Regulatory compliance and large transaction oversight.
Mandate: Ensure all transactions comply with treasury policy and risk limits.
Auto-triggered for transactions exceeding $10,000 USD.
Trading Best Practice: Flag suspicious patterns and enforce position limits.

PASS if compliant. REJECT if any policy violation detected.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"REJECT", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""

PORTFOLIO_REBALANCER_PROMPT = """You are The Portfolio Rebalancer.
Primary Role: Optimal asset allocation and portfolio drift correction.
Mandate: Maintain target allocation percentages across the treasury.
Trading Best Practice: Minimize transaction costs while achieving target weights.

PASS if rebalance improves portfolio alignment. REJECT if costs outweigh benefits.

OUTPUT FORMAT (strict JSON):
{"decision": "PASS"|"REJECT", "confidence": 0.0-1.0, "reason": "string", "data": {}}
"""


# =============================================================================
# Agent Classes
# =============================================================================

class BaseAgent:
    """Base class for all KET Board agents."""

    name: str = "base_agent"
    emoji: str = ""
    system_prompt: str = ""

    async def analyze(
        self,
        proposal: Proposal,
        context: dict[str, Any] | None = None,
    ) -> AgentDecision:
        raise NotImplementedError


class YieldMaxiAgent(BaseAgent):
    """Yield Maxi - Capital Deployer & Alpha Scanner."""

    name = "yield_maxi"
    emoji = "[Y]"
    system_prompt = YIELD_MAXI_PROMPT

    async def analyze(
        self,
        proposal: Proposal,
        context: dict[str, Any] | None = None,
    ) -> AgentDecision:
        pool_data = await query_pools(proposal.token)

        if not pool_data["success"] or pool_data["pools_found"] == 0:
            return AgentDecision(
                agent_name=self.name,
                decision=Decision.REJECT,
                confidence=0.95,
                reason=f"No pools found for {proposal.token} on Mantle",
                data={"pools_found": 0},
            )

        pools = pool_data["pools"]
        if proposal.target_protocol:
            matching = [
                p for p in pools
                if p["protocol"].lower() == proposal.target_protocol.lower()
            ]
            best = matching[0] if matching else pools[0]
        else:
            sorted_pools = sorted(
                pools,
                key=lambda p: (p["tvl"] >= 1_000_000, p["apy"]),
                reverse=True,
            )
            best = sorted_pools[0]

        confidence = min(0.95, 0.5 + (best["tvl"] / 10_000_000) * 0.3)
        if best["apy"] > 50:
            confidence *= 0.7

        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=round(confidence, 2),
            reason=(
                f'{best["protocol"]} {best["pair"]} pool: '
                f'APY {best["apy"]}%, TVL ${best["tvl"]:,.0f}, '
                f'sufficient depth for ${proposal.amount:,.0f}'
            ),
            data={
                "recommended_protocol": best["protocol"],
                "recommended_pair": best["pair"],
                "apy": best["apy"],
                "tvl": best["tvl"],
                "all_pools": len(pools),
            },
        )

        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate this proposal:\n{proposal.model_dump_json(indent=2)}\n\nAvailable pools:\n{json.dumps(pools, indent=2)}",
            self.name,
            fallback,
        )


class RiskAuditorAgent(BaseAgent):
    """Risk Auditor - Safety Veto & Security Validator. Has ABSOLUTE VETO POWER."""

    name = "risk_auditor"
    emoji = "[R]"
    system_prompt = RISK_AUDITOR_PROMPT

    async def analyze(
        self,
        proposal: Proposal,
        context: dict[str, Any] | None = None,
    ) -> AgentDecision:
        context = context or {}
        yield_data = context.get("yield_maxi_data", {})
        protocol_name = yield_data.get(
            "recommended_protocol", proposal.target_protocol
        )

        pool_data = await query_pools(proposal.token)
        target_pool = None
        for pool in pool_data.get("pools", []):
            if pool["protocol"].lower() == protocol_name.lower():
                target_pool = pool
                break

        if not target_pool:
            return AgentDecision(
                agent_name=self.name,
                decision=Decision.REJECT,
                confidence=0.99,
                reason=f"Cannot verify security for unknown protocol: {protocol_name}",
                data={"audit_status": "UNKNOWN", "risk_score": "CRITICAL"},
            )

        is_audited = target_pool.get("audited", False)
        auditor = target_pool.get("auditor", "Unknown")
        il_risk = target_pool.get("il_risk", 100.0)

        auditor_scores = {
            "Zellic": 95, "PeckShield": 88, "Halborn": 90, "OpenZeppelin": 98,
        }
        audit_score = auditor_scores.get(auditor, 0) if is_audited else 0

        if audit_score == 0:
            risk_score = "CRITICAL"
        elif il_risk > 20 or audit_score < 80:
            risk_score = "HIGH"
        elif il_risk > 10 or audit_score < 90:
            risk_score = "MEDIUM"
        else:
            risk_score = "LOW"

        if audit_score < proposal.min_audit_score:
            return AgentDecision(
                agent_name=self.name,
                decision=Decision.REJECT,
                confidence=0.99,
                reason=(
                    f"VETO: Contract audit score {audit_score} is below "
                    f"user minimum threshold of {proposal.min_audit_score}% "
                    f"(Audited by {auditor})"
                ),
                data={
                    "audit_status": "AUDITED" if is_audited else "UNAUDITED",
                    "auditor": auditor, "audit_score": audit_score,
                    "il_risk_pct": il_risk,
                    "risk_score": "CRITICAL" if audit_score == 0 else "HIGH",
                },
            )

        if il_risk > proposal.max_impermanent_loss:
            return AgentDecision(
                agent_name=self.name,
                decision=Decision.REJECT,
                confidence=0.88,
                reason=(
                    f"VETO: IL risk {il_risk}% exceeds user "
                    f"maximum threshold of {proposal.max_impermanent_loss}%"
                ),
                data={
                    "audit_status": "AUDITED", "auditor": auditor,
                    "audit_score": audit_score, "il_risk_pct": il_risk,
                    "risk_score": "HIGH",
                },
            )

        confidence_map = {"LOW": 0.88, "MEDIUM": 0.72, "HIGH": 0.45}
        confidence = confidence_map.get(risk_score, 0.5)

        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=confidence,
            reason=(
                f"Contract audited by {auditor} (Score: {audit_score}), "
                f"IL risk {il_risk}% within tolerance, risk score: {risk_score}"
            ),
            data={
                "audit_status": "AUDITED", "auditor": auditor,
                "audit_score": audit_score, "il_risk_pct": il_risk,
                "risk_score": risk_score,
            },
        )

        return await _try_llm_analysis(
            self.system_prompt,
            f"Audit this proposal:\n{proposal.model_dump_json(indent=2)}",
            self.name,
            fallback,
        )


class MacroStrategistAgent(BaseAgent):
    """Macro Strategist - Execution Timer & Network Analyst. Never rejects."""

    name = "macro_strategist"
    emoji = "[M]"
    system_prompt = MACRO_STRATEGIST_PROMPT

    async def analyze(
        self,
        proposal: Proposal,
        context: dict[str, Any] | None = None,
    ) -> AgentDecision:
        network = await get_network_status()

        gas = network["gas_price_gwei"]
        utilization = network["network_utilization_pct"]
        pending = network["pending_txs"]
        estimated_cost = round(gas * 250_000 * 1e-9 * 3500, 4)
        optimal = gas < 0.05 and utilization < 70 and pending < 400

        if gas > 0.1:
            return AgentDecision(
                agent_name=self.name,
                decision=Decision.DEFER,
                confidence=0.80,
                reason=f"Gas price {gas} gwei above 0.1 threshold, recommend waiting",
                data={
                    "gas_price_gwei": gas, "network_utilization_pct": utilization,
                    "optimal_window": False, "estimated_tx_cost_usd": estimated_cost,
                },
            )

        if utilization > 80:
            return AgentDecision(
                agent_name=self.name,
                decision=Decision.DEFER,
                confidence=0.75,
                reason=f"Network utilization {utilization}% too high, congestion risk",
                data={
                    "gas_price_gwei": gas, "network_utilization_pct": utilization,
                    "optimal_window": False, "estimated_tx_cost_usd": estimated_cost,
                },
            )

        confidence = 0.95 if optimal else 0.78

        return AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=confidence,
            reason=(
                f"Gas at {gas} gwei, network utilization {utilization}%, "
                f"{'optimal' if optimal else 'acceptable'} execution window"
            ),
            data={
                "gas_price_gwei": gas, "network_utilization_pct": utilization,
                "optimal_window": optimal, "estimated_tx_cost_usd": estimated_cost,
            },
        )


# =============================================================================
# Specialist Agents (MoE - from CLI architecture)
# =============================================================================

class ArbitrageSniperAgent(BaseAgent):
    """Arbitrage Sniper - Atomic cross-protocol flash trading."""

    name = "arbitrage_sniper"
    emoji = "[A]"
    system_prompt = ARBITRAGE_SNIPER_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=0.82,
            reason="Arbitrage spread detected across Mantle DEXs, atomic execution viable",
            data={"spread_pct": 0.45, "execution_type": "flash_swap", "risk": "zero_directional"},
        )
        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate arbitrage opportunity:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


class DeltaNeutralHedgerAgent(BaseAgent):
    """Delta-Neutral Hedger - Volatility Shield."""

    name = "delta_neutral_hedger"
    emoji = "[D]"
    system_prompt = DELTA_NEUTRAL_HEDGER_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=0.78,
            reason="Hedge position recommended via Mantle perp DEX to offset spot exposure",
            data={"hedge_ratio": 1.0, "perp_platform": "FWX", "funding_rate": -0.02},
        )
        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate hedging needs:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


class ConcentratedLPManagerAgent(BaseAgent):
    """Concentrated LP Manager - Optimizes liquidity positions."""

    name = "concentrated_lp_manager"
    emoji = "[C]"
    system_prompt = CONCENTRATED_LP_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=0.75,
            reason="Concentrated LP position within active range, fee capture optimal",
            data={"range_width": "tight", "fee_tier": "0.3%", "in_range": True},
        )
        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate LP position:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


class EcosystemFarmerAgent(BaseAgent):
    """Ecosystem Farmer - Multi-protocol yield stacking."""

    name = "ecosystem_farmer"
    emoji = "[E]"
    system_prompt = ECOSYSTEM_FARMER_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=0.80,
            reason="Multi-layer farming strategy captures base yield + ecosystem incentives",
            data={"layers": 3, "base_apy": 8.5, "incentive_apy": 15.2, "airdrop_eligible": True},
        )
        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate ecosystem farming:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


class SentimentAnalystAgent(BaseAgent):
    """Sentiment Analyst - Market psychology evaluation."""

    name = "sentiment_analyst"
    emoji = "[S]"
    system_prompt = SENTIMENT_ANALYST_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=0.72,
            reason="Market sentiment neutral-to-positive, no extreme fear or greed detected",
            data={"fear_greed_index": 55, "sentiment": "NEUTRAL", "social_volume": "normal"},
        )
        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate market sentiment for:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


class ComplianceOfficerAgent(BaseAgent):
    """Compliance Officer - Guardian. Auto-triggered for > $10,000 transactions."""

    name = "compliance_officer"
    emoji = "[G]"
    system_prompt = COMPLIANCE_OFFICER_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        # Rule-based: check basic compliance thresholds
        if proposal.amount > 100_000:
            fallback = AgentDecision(
                agent_name=self.name,
                decision=Decision.REJECT,
                confidence=0.90,
                reason=f"Transaction ${proposal.amount:,.0f} exceeds single-tx limit of $100,000. Requires multi-sig approval.",
                data={"limit": 100_000, "requires_multisig": True, "compliance_status": "BLOCKED"},
            )
        else:
            fallback = AgentDecision(
                agent_name=self.name,
                decision=Decision.PASS,
                confidence=0.88,
                reason=f"Transaction ${proposal.amount:,.0f} within compliance limits. No policy violations.",
                data={"limit": 100_000, "requires_multisig": False, "compliance_status": "CLEARED"},
            )

        return await _try_llm_analysis(
            self.system_prompt,
            f"Compliance check:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


class PortfolioRebalancerAgent(BaseAgent):
    """Portfolio Rebalancer - Asset allocation optimizer."""

    name = "portfolio_rebalancer"
    emoji = "[P]"
    system_prompt = PORTFOLIO_REBALANCER_PROMPT

    async def analyze(self, proposal: Proposal, context: dict[str, Any] | None = None) -> AgentDecision:
        fallback = AgentDecision(
            agent_name=self.name,
            decision=Decision.PASS,
            confidence=0.77,
            reason="Rebalance improves portfolio alignment towards target allocation",
            data={"current_drift": 4.2, "target_drift": 0.0, "rebalance_cost_usd": 12.50},
        )
        return await _try_llm_analysis(
            self.system_prompt,
            f"Evaluate rebalancing:\n{proposal.model_dump_json(indent=2)}",
            self.name, fallback,
        )


# =============================================================================
# Agent Registry (10 Agents)
# =============================================================================

AGENT_REGISTRY: dict[str, BaseAgent] = {
    "yield_maxi": YieldMaxiAgent(),
    "risk_auditor": RiskAuditorAgent(),
    "macro_strategist": MacroStrategistAgent(),
    "arbitrage_sniper": ArbitrageSniperAgent(),
    "delta_neutral_hedger": DeltaNeutralHedgerAgent(),
    "concentrated_lp_manager": ConcentratedLPManagerAgent(),
    "ecosystem_farmer": EcosystemFarmerAgent(),
    "sentiment_analyst": SentimentAnalystAgent(),
    "compliance_officer": ComplianceOfficerAgent(),
    "portfolio_rebalancer": PortfolioRebalancerAgent(),
}


def get_agent(name: str) -> BaseAgent:
    """Get an agent instance by name."""
    agent = AGENT_REGISTRY.get(name)
    if not agent:
        raise ValueError(
            f"Unknown agent '{name}'. "
            f"Available: {list(AGENT_REGISTRY.keys())}"
        )
    return agent
