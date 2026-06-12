"""
KET Board - MoE Orchestrator State Machine.

The brain of the KET system. Receives a Proposal, uses the MoE Router
to select experts, runs them in parallel, synthesizes consensus,
and performs a final Risk Audit before execution.

Pipeline flow:
    PROPOSAL_RECEIVED -> EXPERT_SELECTION -> PARALLEL_EVALUATION
        -> CONSENSUS_SYNTHESIS -> FINAL_AUDIT
        -> CONSENSUS_REACHED -> EXECUTING -> COMPLETED
        -> REJECTED (veto)
        -> DEFERRED (macro suggests waiting)
        -> FAILED (execution error)

Merged from KET_core_CLI MoE architecture + KET-Vault Web event system.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from typing import Callable, Awaitable

from agents import get_agent
from config import settings
from models import (
    AgentDecision,
    ConsensusResult,
    Decision,
    PipelineContext,
    PipelineState,
    Proposal,
)
from router import select_experts, CORE_EXPERTS
from skills import execute_tx, simulate_tx

# Type alias for event callback
EventCallback = Callable[[dict], Awaitable[None]] | None

console = Console()

# Distinctive colors for all 10 experts in Rich terminal
EXPERT_COLORS = {
    "yield_maxi": "green",
    "risk_auditor": "red",
    "macro_strategist": "blue",
    "arbitrage_sniper": "cyan",
    "delta_neutral_hedger": "yellow",
    "concentrated_lp_manager": "orange3",
    "ecosystem_farmer": "green_yellow",
    "sentiment_analyst": "bright_magenta",
    "compliance_officer": "bold red",
    "portfolio_rebalancer": "magenta",
}

EXPERT_EMOJIS = {
    "yield_maxi": "[Y]",
    "risk_auditor": "[R]",
    "macro_strategist": "[M]",
    "arbitrage_sniper": "[A]",
    "delta_neutral_hedger": "[D]",
    "concentrated_lp_manager": "[C]",
    "ecosystem_farmer": "[E]",
    "sentiment_analyst": "[S]",
    "compliance_officer": "[G]",
    "portfolio_rebalancer": "[P]",
}


# =============================================================================
# Rich Terminal UI Helpers
# =============================================================================

def _print_header():
    """Print the KET Board header banner."""
    header = Text()
    header.append("KET Board of Directors", style="bold white")
    header.append(" - ", style="dim")
    header.append("MoE Consensus Pipeline", style="bold cyan")
    console.print(Panel(header, border_style="bright_blue", padding=(1, 2)))


def _print_proposal(proposal: Proposal):
    """Print proposal details."""
    table = Table(
        title="Proposal Received",
        border_style="dim",
        show_header=False,
        padding=(0, 2),
    )
    table.add_column("Field", style="dim")
    table.add_column("Value", style="bold white")
    table.add_row("ID", proposal.id)
    table.add_row("Action", proposal.action.value)
    table.add_row("Token", proposal.token)
    table.add_row("Amount", f"${proposal.amount:,.2f}")
    table.add_row("Opportunity", proposal.opportunity_type.value)
    if proposal.target_protocol:
        table.add_row("Target", proposal.target_protocol)
    if proposal.context:
        table.add_row("Context", proposal.context)
    console.print(table)
    console.print()


def _print_selected_experts(selected: list[str]):
    """Print which experts were selected by the router."""
    console.print(
        f"  [bold cyan]MoE Router:[/bold cyan] Selected {len(selected)} experts: "
        + ", ".join(
            f"[{EXPERT_COLORS.get(n, 'white')}]{n}[/]"
            for n in selected
        )
    )
    console.print()


def _print_agent_decision(
    step: int,
    total: int,
    agent_name: str,
    decision: AgentDecision,
):
    """Print a single agent's decision with rich formatting."""
    color_map = {
        Decision.PASS: "green",
        Decision.REJECT: "red",
        Decision.DEFER: "yellow",
    }
    icon_map = {
        Decision.PASS: "[PASS]",
        Decision.REJECT: "[REJECT]",
        Decision.DEFER: "[DEFER]",
    }
    color = color_map.get(decision.decision, "white")
    icon = icon_map.get(decision.decision, "[?]")
    emoji = EXPERT_EMOJIS.get(agent_name, "")
    agent_color = EXPERT_COLORS.get(agent_name, "white")

    console.print(
        f"  {emoji} [{step}/{total}] "
        f"[{agent_color} bold]{agent_name.replace('_', ' ').title()}[/] "
        f"analyzing...",
        style="dim",
    )
    console.print(f"     +-- Decision: [{color} bold]{decision.decision.value} {icon}[/]")
    console.print(f"     +-- Confidence: [bold]{decision.confidence:.0%}[/bold]")
    console.print(f"     +-- Reason: [italic]\"{decision.reason}\"[/italic]")

    if decision.data:
        for key, value in decision.data.items():
            if key not in ("all_pools",):
                formatted_value = (
                    f"${value:,.0f}" if isinstance(value, (int, float))
                    and "tvl" in key
                    else str(value)
                )
                console.print(f"        * {key}: {formatted_value}", style="dim")
    console.print()


def _print_consensus(result: ConsensusResult):
    """Print final consensus result."""
    if result.consensus_reached:
        style = "bold green"
        title = "CONSENSUS REACHED"
    elif result.final_decision == Decision.DEFER:
        style = "bold yellow"
        title = "EXECUTION DEFERRED"
    else:
        style = "bold red"
        title = "PROPOSAL REJECTED"

    console.print()
    console.rule(style=style)
    console.print(
        f"  {title}: "
        f"{result.votes_pass}/{len(result.decisions)} PASS "
        f"(Threshold: {result.threshold}/{len(result.decisions)})",
        style=style,
    )

    if result.selected_experts:
        console.print(
            f"  Selected Experts: {', '.join(result.selected_experts)}",
            style="dim cyan",
        )

    if result.synthesis_reasoning:
        console.print(
            f"  Synthesis: {result.synthesis_reasoning}",
            style="dim",
        )

    if result.tx_hash:
        console.print(
            f"  TX Hash: [link={result.explorer_url}]{result.tx_hash[:18]}...{result.tx_hash[-6:]}[/link]",
        )
        console.print(f"  Explorer: {result.explorer_url}", style="dim cyan")

    console.rule(style=style)
    console.print()


# =============================================================================
# Orchestrator
# =============================================================================

class KETOrchestrator:
    """
    The KET Board MoE Orchestrator.

    Manages the MoE consensus pipeline:
        1. Router selects experts
        2. Core agents run sequentially (Yield -> Risk -> Macro)
        3. Specialist agents run in PARALLEL
        4. Consensus synthesis
        5. Final Risk Audit
        6. Execute if approved

    Requires `consensus_threshold` out of selected agents to PASS.
    """

    def __init__(self, threshold: int | None = None):
        self.threshold = threshold or settings.consensus_threshold
        self.timeout = settings.agent_timeout_seconds

    async def run_pipeline(
        self,
        proposal: Proposal,
        verbose: bool = True,
        on_event: EventCallback = None,
    ) -> ConsensusResult:
        """
        Run the full MoE consensus pipeline for a proposal.

        Args:
            proposal: The treasury action proposal
            verbose: Whether to print rich terminal output
            on_event: Async callback for real-time events (WebSocket)

        Returns:
            ConsensusResult with all agent votes and final decision
        """
        # Initialize pipeline context
        ctx = PipelineContext(proposal=proposal)
        ctx.add_log("Pipeline started")

        async def _emit(event_type: str, data: dict | None = None):
            """Emit event to callback if registered."""
            if on_event:
                await on_event({
                    "type": event_type,
                    "state": ctx.state.value,
                    "proposal_id": proposal.id,
                    **(data or {}),
                })

        await _emit("pipeline_started", {
            "proposal": proposal.model_dump(mode="json"),
        })

        if verbose:
            _print_header()
            _print_proposal(proposal)

        # =====================================================================
        # Step 1: MoE Router — Select Experts
        # =====================================================================
        ctx.state = PipelineState.EXPERT_SELECTION
        ctx.add_log("MoE Router selecting experts")

        selected = select_experts(
            proposal.opportunity_type,
            proposal.amount,
            proposal.context,
        )
        ctx.selected_experts = selected

        await _emit("expert_selected", {
            "selected_experts": selected,
        })

        if verbose:
            _print_selected_experts(selected)

        # =====================================================================
        # Step 2: Separate core vs specialist agents
        # =====================================================================
        # Core agents run SEQUENTIALLY (they depend on each other's context)
        core_agents = [n for n in selected if n in CORE_EXPERTS]
        # Specialist agents run in PARALLEL (independent evaluations)
        specialist_agents = [n for n in selected if n not in CORE_EXPERTS]

        # Remove risk_auditor from sequential — it runs last as Final Audit
        if "risk_auditor" in core_agents:
            core_agents.remove("risk_auditor")

        all_agents_ordered = core_agents + specialist_agents
        total_agents = len(all_agents_ordered) + 1  # +1 for final risk audit

        # Track votes and context
        votes_pass = 0
        votes_reject = 0
        votes_defer = 0
        agent_context: dict[str, Any] = {}
        step = 0

        # =====================================================================
        # Step 3: Run core agents SEQUENTIALLY
        # =====================================================================
        ctx.state = PipelineState.YIELD_ANALYSIS

        for agent_name in core_agents:
            step += 1
            agent = get_agent(agent_name)

            state_map = {
                "yield_maxi": PipelineState.YIELD_ANALYSIS,
                "macro_strategist": PipelineState.MACRO_TIMING,
            }
            ctx.state = state_map.get(agent_name, PipelineState.PARALLEL_EVALUATION)
            ctx.add_log(f"Agent {agent_name} started analysis", agent=agent_name)
            await _emit("agent_started", {"agent": agent_name})

            try:
                decision = await asyncio.wait_for(
                    agent.analyze(proposal, context=agent_context),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                decision = AgentDecision(
                    agent_name=agent_name,
                    decision=Decision.REJECT,
                    confidence=0.0,
                    reason=f"Agent timed out after {self.timeout}s",
                )
            except Exception as e:
                decision = AgentDecision(
                    agent_name=agent_name,
                    decision=Decision.REJECT,
                    confidence=0.0,
                    reason=f"Agent error: {str(e)}",
                )

            ctx.add_decision(decision)
            await _emit("agent_decided", {
                "agent": agent_name,
                "decision": decision.model_dump(mode="json"),
            })

            agent_context[f"{agent_name}_data"] = decision.data
            agent_context[f"{agent_name}_decision"] = decision.decision.value

            if decision.decision == Decision.PASS:
                votes_pass += 1
            elif decision.decision == Decision.REJECT:
                votes_reject += 1
            elif decision.decision == Decision.DEFER:
                votes_defer += 1

            if verbose:
                _print_agent_decision(step, total_agents, agent_name, decision)

        # =====================================================================
        # Step 4: Run specialist agents in PARALLEL
        # =====================================================================
        if specialist_agents:
            ctx.state = PipelineState.PARALLEL_EVALUATION
            ctx.add_log(f"Running {len(specialist_agents)} specialists in parallel")

            # Notify all specialists starting
            for name in specialist_agents:
                await _emit("agent_started", {"agent": name})

            async def _run_specialist(name: str) -> AgentDecision:
                agent = get_agent(name)
                try:
                    return await asyncio.wait_for(
                        agent.analyze(proposal, context=agent_context),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError:
                    return AgentDecision(
                        agent_name=name, decision=Decision.REJECT,
                        confidence=0.0, reason=f"Agent timed out after {self.timeout}s",
                    )
                except Exception as e:
                    return AgentDecision(
                        agent_name=name, decision=Decision.REJECT,
                        confidence=0.0, reason=f"Agent error: {str(e)}",
                    )

            specialist_decisions = await asyncio.gather(
                *[_run_specialist(n) for n in specialist_agents]
            )

            # Emit decisions with 200ms delay to prevent WebSocket race condition
            for decision in specialist_decisions:
                step += 1
                ctx.add_decision(decision)

                # Race condition fix: stagger WS events so React can breathe
                await asyncio.sleep(0.2)

                await _emit("agent_decided", {
                    "agent": decision.agent_name,
                    "decision": decision.model_dump(mode="json"),
                })

                agent_context[f"{decision.agent_name}_data"] = decision.data
                agent_context[f"{decision.agent_name}_decision"] = decision.decision.value

                if decision.decision == Decision.PASS:
                    votes_pass += 1
                elif decision.decision == Decision.REJECT:
                    votes_reject += 1
                elif decision.decision == Decision.DEFER:
                    votes_defer += 1

                if verbose:
                    _print_agent_decision(step, total_agents, decision.agent_name, decision)

        # =====================================================================
        # Step 5: Consensus Synthesis
        # =====================================================================
        ctx.state = PipelineState.CONSENSUS_SYNTHESIS
        ctx.add_log("Synthesizing consensus from expert evaluations")

        synthesis_reasoning = self._synthesize_consensus(ctx.decisions)

        await _emit("consensus_synthesis", {
            "reasoning": synthesis_reasoning,
            "votes_pass": votes_pass,
            "votes_reject": votes_reject,
            "votes_defer": votes_defer,
        })

        # =====================================================================
        # Step 6: Final Risk Audit (Risk Auditor always runs last)
        # =====================================================================
        ctx.state = PipelineState.FINAL_AUDIT
        ctx.add_log("Running Final Risk Audit", agent="risk_auditor")

        step += 1
        risk_agent = get_agent("risk_auditor")
        await _emit("agent_started", {"agent": "risk_auditor"})

        try:
            risk_decision = await asyncio.wait_for(
                risk_agent.analyze(proposal, context=agent_context),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            risk_decision = AgentDecision(
                agent_name="risk_auditor",
                decision=Decision.REJECT,
                confidence=0.0,
                reason=f"Final Risk Audit timed out after {self.timeout}s",
            )
        except Exception as e:
            risk_decision = AgentDecision(
                agent_name="risk_auditor",
                decision=Decision.REJECT,
                confidence=0.0,
                reason=f"Final Risk Audit error: {str(e)}",
            )

        ctx.add_decision(risk_decision)
        await _emit("agent_decided", {
            "agent": "risk_auditor",
            "decision": risk_decision.model_dump(mode="json"),
        })

        if risk_decision.decision == Decision.PASS:
            votes_pass += 1
        elif risk_decision.decision == Decision.REJECT:
            votes_reject += 1

        if verbose:
            _print_agent_decision(step, total_agents, "risk_auditor", risk_decision)

        # Early termination: Risk Auditor VETO kills everything
        if risk_decision.decision == Decision.REJECT:
            ctx.state = PipelineState.REJECTED
            ctx.add_log("Risk Auditor VETO - pipeline terminated", agent="risk_auditor")

        # =====================================================================
        # Step 7: Final Consensus Decision
        # =====================================================================
        if ctx.state != PipelineState.REJECTED:
            if votes_pass >= self.threshold:
                final_decision = Decision.PASS
                ctx.state = PipelineState.CONSENSUS_REACHED
            elif votes_defer > 0 and votes_reject == 0:
                final_decision = Decision.DEFER
                ctx.state = PipelineState.DEFERRED
            else:
                final_decision = Decision.REJECT
                ctx.state = PipelineState.REJECTED
        else:
            final_decision = Decision.REJECT

        # Build result
        result = ConsensusResult(
            proposal_id=proposal.id,
            decisions=ctx.decisions,
            selected_experts=selected,
            votes_pass=votes_pass,
            votes_reject=votes_reject,
            votes_defer=votes_defer,
            threshold=self.threshold,
            final_decision=final_decision,
            synthesis_reasoning=synthesis_reasoning,
        )

        # Emit consensus event
        await _emit("consensus", {
            "final_decision": final_decision.value,
            "votes_pass": votes_pass,
            "votes_reject": votes_reject,
            "votes_defer": votes_defer,
            "selected_experts": selected,
            "synthesis_reasoning": synthesis_reasoning,
        })

        # =====================================================================
        # Step 8: Execute if consensus reached
        # =====================================================================
        if result.consensus_reached:
            ctx.state = PipelineState.EXECUTING
            ctx.add_log("Consensus reached - executing transaction")

            try:
                sim_result = await simulate_tx({
                    "action": proposal.action.value,
                    "token": proposal.token,
                    "amount": proposal.amount,
                    "protocol": agent_context.get(
                        "yield_maxi_data", {}
                    ).get("recommended_protocol", ""),
                })

                if sim_result["success"] and not sim_result["will_revert"]:
                    tx_result = await execute_tx(sim_result["tx_params"])
                    result.tx_hash = tx_result["tx_hash"]
                    result.explorer_url = tx_result["explorer_url"]
                    ctx.state = PipelineState.COMPLETED
                    ctx.add_log(f"TX executed: {tx_result['tx_hash']}", data=tx_result)
                else:
                    ctx.state = PipelineState.FAILED
                    ctx.error = "Transaction simulation failed - would revert"
                    ctx.add_log("TX simulation failed", data=sim_result)
            except Exception as e:
                ctx.state = PipelineState.FAILED
                ctx.error = str(e)
                ctx.add_log(f"TX execution failed: {e}")

        # Emit final result
        await _emit("pipeline_completed", {
            "final_decision": result.final_decision.value,
            "tx_hash": result.tx_hash,
            "explorer_url": result.explorer_url,
            "selected_experts": result.selected_experts,
            "result": result.model_dump(mode="json"),
        })

        if verbose:
            _print_consensus(result)

        return result

    def _synthesize_consensus(self, decisions: list[AgentDecision]) -> str:
        """
        Synthesize reasoning from all expert decisions.
        In rule-based mode, provides a summary. With LLM, would merge conflicts.
        """
        if not decisions:
            return "No expert evaluations to synthesize."

        passes = [d for d in decisions if d.decision == Decision.PASS]
        rejects = [d for d in decisions if d.decision == Decision.REJECT]
        defers = [d for d in decisions if d.decision == Decision.DEFER]

        parts = []
        if passes:
            parts.append(f"{len(passes)} experts APPROVE")
        if rejects:
            reasons = "; ".join(d.reason[:60] for d in rejects)
            parts.append(f"{len(rejects)} experts VETO ({reasons})")
        if defers:
            parts.append(f"{len(defers)} experts suggest DEFER")

        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
        parts.append(f"Avg confidence: {avg_confidence:.0%}")

        return ". ".join(parts) + "."
