"""
KET Board - FastAPI Backend Server.

Main application entry point. Configures CORS, mounts API routes
and WebSocket endpoints.

Run with:
    cd apps/backend
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Add agent-core to Python path
_AGENT_CORE = Path(__file__).resolve().parent.parent.parent / "packages" / "agent-core"
if str(_AGENT_CORE) not in sys.path:
    sys.path.insert(0, str(_AGENT_CORE))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.websocket import router as ws_router

# =============================================================================
# App Configuration
# =============================================================================

app = FastAPI(
    title="KET Board of Directors API",
    description="AI Treasury Consensus Engine for Mantle Network — MoE Architecture",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - Allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternative
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(api_router)
app.include_router(ws_router)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "KET Board API",
        "status": "operational",
        "version": "2.0.0",
        "architecture": "MoE (Mixture-of-Experts)",
        "chain": "Mantle Network",
    }


@app.get("/health", tags=["health"])
async def health():
    """Detailed health check."""
    llm_strategy = os.environ.get("LLM_STRATEGY", "HYBRID")
    live_mode = os.environ.get("KET_LIVE_MODE", "false").lower() == "true"

    return {
        "status": "healthy",
        "agents_count": 10,
        "core_agents": ["yield_maxi", "risk_auditor", "macro_strategist"],
        "specialist_agents": [
            "arbitrage_sniper", "delta_neutral_hedger",
            "concentrated_lp_manager", "ecosystem_farmer",
            "sentiment_analyst", "portfolio_rebalancer",
        ],
        "guardian_agents": ["compliance_officer"],
        "consensus_threshold": "dynamic (based on selected experts)",
        "llm_strategy": llm_strategy,
        "live_mode": live_mode,
    }
