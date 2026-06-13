import pytest
import os
import sys
from fastapi.testclient import TestClient

# Mock environment variables before importing main
os.environ["LLM_STRATEGY"] = "MOCK"
os.environ["KET_LIVE_MODE"] = "true"

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parent.parent
_AGENT_CORE = _BACKEND.parent.parent / "packages" / "agent-core"
sys.path.insert(0, str(_BACKEND))
sys.path.insert(1, str(_AGENT_CORE))

from main import app

client = TestClient(app)

def test_health_mock_env():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["llm_strategy"] == "MOCK"
    assert data["live_mode"] is True

def test_win32_encoding(monkeypatch):
    import main
    monkeypatch.setattr(sys, "platform", "win32")
    # Simulate a reload of the module in win32 mode (this is just for coverage)
    import importlib
    importlib.reload(main)
    assert os.environ.get("PYTHONIOENCODING") == "utf-8"
