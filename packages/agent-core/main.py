"""
KET Board - CLI Entry Point.

Run the KET Board consensus pipeline from the terminal.
Supports both interactive mode and JSON file input.

Usage:
    python main.py                    # Run with default demo proposal
    python main.py --token MNT        # Custom token
    python main.py --amount 5000      # Custom amount
    python main.py --all-scenarios    # Run all test scenarios
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console

from models import Proposal, ProposalAction
from orchestrator import KETOrchestrator

console = Console()


# =============================================================================
# Demo Scenarios
# =============================================================================

DEMO_PROPOSALS = [
    {
        "name": "Happy Path - USDC Yield Farm",
        "proposal": Proposal(
            action=ProposalAction.FARM_YIELD,
            token="USDC",
            amount=1000.0,
            target_protocol="Agni Finance",
        ),
    },
    {
        "name": "Lending - Low Risk",
        "proposal": Proposal(
            action=ProposalAction.LEND,
            token="USDC",
            amount=5000.0,
            target_protocol="Lendle",
        ),
    },
    {
        "name": "High IL Risk - MNT Pool",
        "proposal": Proposal(
            action=ProposalAction.PROVIDE_LIQUIDITY,
            token="MNT",
            amount=2000.0,
            target_protocol="Agni Finance",
        ),
    },
    {
        "name": "Unknown Token - Should Reject",
        "proposal": Proposal(
            action=ProposalAction.FARM_YIELD,
            token="SHITCOIN",
            amount=100.0,
        ),
    },
]


async def run_demo(proposal: Proposal):
    """Run a single proposal through the pipeline."""
    orchestrator = KETOrchestrator()
    result = await orchestrator.run_pipeline(proposal, verbose=True)
    return result


async def run_all_scenarios():
    """Run all demo scenarios to showcase different outcomes."""
    orchestrator = KETOrchestrator()

    for i, scenario in enumerate(DEMO_PROPOSALS, 1):
        console.print()
        console.rule(
            f"[bold magenta]Scenario {i}/{len(DEMO_PROPOSALS)}: "
            f"{scenario['name']}[/]"
        )
        console.print()

        result = await orchestrator.run_pipeline(
            scenario["proposal"], verbose=True
        )

        # Summary line
        status_emoji = {
            "PASS": "[PASS]",
            "REJECT": "[REJECT]",
            "DEFER": "[DEFER]",
        }
        emoji = status_emoji.get(result.final_decision.value, "[?]")
        console.print(
            f"  {emoji} Result: [bold]{result.final_decision.value}[/bold] "
            f"({result.votes_pass} pass, {result.votes_reject} reject, "
            f"{result.votes_defer} defer)"
        )

        if i < len(DEMO_PROPOSALS):
            console.print()
            console.print("  [dim]Press Enter for next scenario...[/dim]")
            # In non-interactive mode, just continue
            await asyncio.sleep(0.5)


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="KET Board of Directors - AI Treasury Consensus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Default demo (USDC farm)
  python main.py --token MNT --amount 5000
  python main.py --action LEND --target "Lendle"
  python main.py --all-scenarios          # Run all test cases
        """,
    )
    parser.add_argument(
        "--token",
        default="USDC",
        help="Token symbol (default: USDC)",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=1000.0,
        help="Amount in token units (default: 1000)",
    )
    parser.add_argument(
        "--action",
        default="FARM_YIELD",
        choices=[a.value for a in ProposalAction],
        help="Treasury action (default: FARM_YIELD)",
    )
    parser.add_argument(
        "--target",
        default="Agni Finance",
        help="Target protocol (default: Agni Finance)",
    )
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Run all demo scenarios",
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    if args.all_scenarios:
        await run_all_scenarios()
    else:
        proposal = Proposal(
            action=ProposalAction(args.action),
            token=args.token,
            amount=args.amount,
            target_protocol=args.target,
        )
        await run_demo(proposal)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[dim]Pipeline interrupted by user.[/dim]")
        sys.exit(0)
