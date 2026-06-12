# KET - AI Board of Directors for DeFi Treasury

> **Treasury-as-a-Service (TaaS)** powered by multi-agent AI consensus on [Mantle Network](https://www.mantle.xyz/).

## The Problem

- **Human Latency**: Traditional multi-sigs suffer from time-zone delays, missing critical DeFi opportunities.
- **Brittle Automation**: Single-threaded bots lack context-awareness to avoid honeypots or respond to exploits.

## The Solution: The KET Board

KET employs a **committee of 3 specialized AI agents** that must reach consensus (2-of-3) before any transaction is signed:

| Agent | Role | Superpower |
|-------|------|------------|
| **Yield Maxi** | Capital Deployer | Scans DEXs/lending for alpha, proposes yield strategies |
| **Risk Auditor** | Safety Veto | Validates contract security, monitors IL risk |
| **Macro Strategist** | Execution Timer | Analyzes gas prices & network health for optimal timing |

## Technical Stack

- **Chain**: Mantle Network (EVM-compatible L2)
- **Framework**: Byreal Skills CLI for modular agentic execution
- **Identity**: ERC-8004 for agent reputation tracking
- **Consensus**: Multi-sig threshold (2-of-3) after verified inter-agent negotiation

## Project Structure

```
ket/
├── apps/
│   ├── frontend/          # React Dashboard (Phase 4)
│   └── backend/           # FastAPI Server (Phase 3)
└── packages/
    └── agent-core/        # AI Consensus Engine (Phase 2) ← YOU ARE HERE
        ├── orchestrator.py    # State Machine
        ├── agents.py          # 3 Agent Personas
        ├── models.py          # Data Schemas
        ├── skills.py          # Byreal CLI Wrappers
        └── main.py            # CLI Entry Point
```

## Quick Start

```bash
# 1. Setup environment
cd packages/agent-core
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Configure
cp ../../.env.example ../../.env
# Edit .env with your API keys

# 3. Run the Board
python main.py
```

## Phases

- [x] **Phase 1**: Monorepo Setup
- [x] **Phase 2**: Agent-Core State Machine
- [ ] **Phase 3**: Backend API (FastAPI)
- [ ] **Phase 4**: Frontend Dashboard (React)

## License

MIT

---

*Built for the Mantle Network Hackathon — Track 6: Agentic Economy*
