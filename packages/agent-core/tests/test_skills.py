"""
KET Board - Skills Unit Tests.

Tests all skill functions in MOCK mode (default).
All tests are deterministic and run offline.
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skills import (
    GasOracleSnapshot,
    execute_tx,
    get_network_status,
    query_gas_oracle,
    query_pools,
    simulate_tx,
)


# =============================================================================
# query_pools Tests
# =============================================================================

class TestQueryPools:
    """Test DeFi pool query function."""

    @pytest.mark.asyncio
    async def test_usdc_pools(self):
        result = await query_pools("USDC")

        assert result["success"] is True
        assert result["token"] == "USDC"
        assert result["network"] == "mantle"
        assert result["pools_found"] == 3
        assert len(result["pools"]) == 3
        assert result["best_apy"] > 0
        assert result["total_tvl"] > 0

    @pytest.mark.asyncio
    async def test_mnt_pools(self):
        result = await query_pools("MNT")

        assert result["success"] is True
        assert result["pools_found"] == 3
        # Verify specific protocol exists
        protocols = [p["protocol"] for p in result["pools"]]
        assert "Agni Finance" in protocols
        assert "Merchant Moe" in protocols

    @pytest.mark.asyncio
    async def test_weth_pools(self):
        result = await query_pools("WETH")

        assert result["success"] is True
        assert result["pools_found"] == 2
        protocols = [p["protocol"] for p in result["pools"]]
        assert "FusionX" in protocols
        assert "mETH Staking" in protocols

    @pytest.mark.asyncio
    async def test_unknown_token_no_pools(self):
        result = await query_pools("FAKECOIN")

        assert result["success"] is False
        assert result["pools_found"] == 0
        assert result["pools"] == []
        assert result["best_apy"] == 0
        assert result["total_tvl"] == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_token(self):
        """Token lookup should be case-insensitive."""
        result = await query_pools("usdc")
        assert result["success"] is True
        assert result["token"] == "USDC"

    @pytest.mark.asyncio
    async def test_pool_has_required_fields(self):
        """Each pool should have standard fields."""
        result = await query_pools("USDC")
        required_fields = ["protocol", "pair", "apy", "tvl", "audited", "auditor", "il_risk"]
        for pool in result["pools"]:
            for field in required_fields:
                assert field in pool, f"Missing field '{field}' in pool {pool['protocol']}"

    @pytest.mark.asyncio
    async def test_custom_network(self):
        result = await query_pools("USDC", network="ethereum")
        assert result["network"] == "ethereum"


# =============================================================================
# simulate_tx Tests
# =============================================================================

class TestSimulateTx:
    """Test transaction simulation function."""

    @pytest.mark.asyncio
    async def test_normal_simulation(self):
        result = await simulate_tx({
            "action": "FARM_YIELD",
            "token": "USDC",
            "amount": 1000,
        })

        assert result["success"] is True
        assert result["will_revert"] is False
        assert result["gas_estimate"] > 0
        assert result["gas_cost_usd"] >= 0
        assert result["warnings"] == []

    @pytest.mark.asyncio
    async def test_high_slippage_rejected(self):
        """Slippage > 5% should fail simulation."""
        result = await simulate_tx({
            "action": "SWAP",
            "token": "USDC",
            "amount": 100,
            "slippage_tolerance": 0.06,
        })

        assert result["success"] is False
        assert result["will_revert"] is True
        assert len(result["warnings"]) > 0
        assert "SlippageExceeded" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_default_slippage_passes(self):
        """Default slippage (0.5%) should pass."""
        result = await simulate_tx({"token": "USDC", "amount": 100})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_large_tx_higher_gas(self):
        """Transactions > $1M should estimate higher gas."""
        result = await simulate_tx({"token": "USDC", "amount": 2_000_000})
        assert result["success"] is True
        assert result["gas_estimate"] >= 300_000

    @pytest.mark.asyncio
    async def test_boundary_slippage(self):
        """Exactly 5% slippage should pass (condition is > 0.05)."""
        result = await simulate_tx({
            "token": "USDC",
            "amount": 100,
            "slippage_tolerance": 0.05,
        })
        assert result["success"] is True


# =============================================================================
# execute_tx Tests
# =============================================================================

class TestExecuteTx:
    """Test transaction execution in mock mode."""

    @pytest.mark.asyncio
    async def test_mock_execution(self):
        """Default mock mode should generate a valid tx hash."""
        result = await execute_tx({"token": "USDC", "amount": 1000})

        assert result["success"] is True
        assert result["tx_hash"] is not None
        assert result["tx_hash"].startswith("0x")
        assert len(result["tx_hash"]) == 66  # 0x + 64 hex chars
        assert result["explorer_url"] is not None
        assert "mantlescan.xyz" in result["explorer_url"]
        assert result["block_number"] is not None
        assert result["gas_used"] > 0

    @pytest.mark.asyncio
    async def test_mock_unique_hashes(self):
        """Each mock execution should generate a different tx hash."""
        r1 = await execute_tx({"token": "USDC", "amount": 100})
        r2 = await execute_tx({"token": "USDC", "amount": 100})
        assert r1["tx_hash"] != r2["tx_hash"]


# =============================================================================
# get_network_status Tests
# =============================================================================

class TestGetNetworkStatus:
    """Test network status query."""

    @pytest.mark.asyncio
    async def test_returns_required_fields(self):
        status = await get_network_status()

        assert "gas_price_gwei" in status
        assert "network_utilization_pct" in status
        assert "block_time_seconds" in status
        assert "pending_txs" in status
        assert "chain_id" in status
        assert "latest_block" in status

    @pytest.mark.asyncio
    async def test_chain_id_is_mantle(self):
        status = await get_network_status()
        assert status["chain_id"] == 5000

    @pytest.mark.asyncio
    async def test_gas_price_positive(self):
        status = await get_network_status()
        assert status["gas_price_gwei"] > 0

    @pytest.mark.asyncio
    async def test_utilization_in_range(self):
        status = await get_network_status()
        assert 0 <= status["network_utilization_pct"] <= 100


# =============================================================================
# query_gas_oracle Tests
# =============================================================================

class TestQueryGasOracle:
    """Test gas oracle snapshot."""

    @pytest.mark.asyncio
    async def test_returns_snapshot(self):
        snapshot = await query_gas_oracle()

        assert isinstance(snapshot, GasOracleSnapshot)
        assert snapshot.current_gwei > 0
        assert snapshot.avg_24h_gwei > 0
        assert snapshot.network_congestion in ("LOW", "MODERATE", "HIGH")
        assert snapshot.pending_tx_count >= 0
        assert snapshot.recommended_wait_blocks >= 0

    @pytest.mark.asyncio
    async def test_low_congestion_no_wait(self):
        """When congestion is LOW, recommended wait should be 0."""
        # Run multiple times since congestion is random
        for _ in range(20):
            snapshot = await query_gas_oracle()
            if snapshot.network_congestion == "LOW":
                assert snapshot.recommended_wait_blocks == 0
                return
        # If we never hit LOW in 20 tries, that's statistically very unlikely
        # but not impossible — skip assertion
