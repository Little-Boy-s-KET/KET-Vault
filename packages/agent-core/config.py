"""
KET Board - Configuration & Environment Settings.

Loads environment variables and provides typed configuration
for the entire agent-core pipeline. Supports HYBRID LLM strategy
and LIVE_MODE toggle.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# Find .env file - walk up from agent-core to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Global configuration for the KET Board system."""

    # --- Mantle Network ---
    mantle_rpc_url: str = Field(
        default="https://rpc.mantle.xyz",
        description="Mantle Network RPC endpoint",
    )
    mantle_chain_id: int = Field(default=5000)

    # --- LLM Provider ---
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for agent LLM calls",
    )
    llm_strategy: str = Field(
        default="HYBRID",
        description="LLM strategy: HYBRID (auto-detect), GPT4O (force LLM), RULE_BASED (no LLM)",
    )

    # --- Byreal Skills CLI ---
    byreal_api_key: str = Field(
        default="",
        description="Byreal Skills CLI API key",
    )
    byreal_cli_path: str = Field(
        default="byreal-cli",
        description="Path to byreal-cli binary",
    )

    # --- Execution Mode ---
    live_mode: bool = Field(
        default=False,
        description="Enable live on-chain execution (default: mock)",
        alias="KET_LIVE_MODE",
    )

    # --- Wallet ---
    private_key: str = Field(
        default="0x" + "0" * 64,
        description="Hot wallet private key (NEVER use mainnet funds for testing)",
    )

    # --- Agent Consensus ---
    consensus_threshold: int = Field(
        default=2,
        description="Minimum votes required for consensus",
    )
    agent_timeout_seconds: int = Field(
        default=30,
        description="Max seconds to wait for each agent response",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO")

    model_config = {
        "env_file": str(_ENV_FILE) if _ENV_FILE.exists() else None,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
    }


# Singleton instance
settings = Settings()
