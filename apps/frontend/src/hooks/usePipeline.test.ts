/**
 * usePipeline Hook Tests.
 *
 * Tests initial state, event handling, and reset logic.
 * Updated for 10-agent MoE architecture with direct WebSocket usage.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePipeline } from "./usePipeline";

// =========================================================================
// Mock WebSocket & API
// =========================================================================

let mockWsInstances: MockWebSocket[] = [];

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState = 0;
  onopen: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: unknown) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  close = vi.fn();
  send = vi.fn();

  constructor(url: string) {
    this.url = url;
    mockWsInstances.push(this);
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

vi.mock("../utils/api", () => ({
  submitProposal: vi.fn().mockResolvedValue({
    pipeline_id: "test-pipeline-001",
    message: "Pipeline started",
  }),
  getWsUrl: vi.fn((id: string) => `ws://localhost:8000/ws/pipeline/${id}`),
}));

// Mock crypto.randomUUID
vi.stubGlobal("crypto", {
  randomUUID: () => `uuid-${Math.random().toString(36).slice(2, 8)}`,
});

const PROPOSAL = {
  action: "FARM_YIELD" as const,
  token: "USDC",
  amount: 1000,
  target_protocol: "Agni Finance",
  opportunity_type: "YIELD_FARM" as const,
  max_impermanent_loss: 5.0,
  min_audit_score: 80.0,
  context: "",
};

// =========================================================================
// Tests
// =========================================================================

describe("usePipeline", () => {
  beforeEach(() => {
    mockWsInstances = [];
  });

  it("initializes with 10 agents in waiting state", () => {
    const { result } = renderHook(() => usePipeline());

    expect(result.current.agents).toHaveLength(10);
    // Core agents first
    expect(result.current.agents[0].name).toBe("yield_maxi");
    expect(result.current.agents[1].name).toBe("risk_auditor");
    expect(result.current.agents[2].name).toBe("macro_strategist");
    // All agents start in waiting
    result.current.agents.forEach((agent) => {
      expect(agent.status).toBe("waiting");
    });
  });

  it("agents have ERC-8004 IDs", () => {
    const { result } = renderHook(() => usePipeline());

    expect(result.current.agents[0].erc8004Id).toBe("#1042");
    expect(result.current.agents[1].erc8004Id).toBe("#0887");
    expect(result.current.agents[2].erc8004Id).toBe("#1201");
  });

  it("agents have role assignments", () => {
    const { result } = renderHook(() => usePipeline());

    const roles = result.current.agents.map((a) => a.role);
    expect(roles.filter((r) => r === "core")).toHaveLength(3);
    expect(roles.filter((r) => r === "specialist")).toHaveLength(6);
    expect(roles.filter((r) => r === "guardian")).toHaveLength(1);
  });

  it("starts with clean state", () => {
    const { result } = renderHook(() => usePipeline());

    expect(result.current.timeline).toHaveLength(0);
    expect(result.current.result).toBeNull();
    expect(result.current.pipelineState).toBeNull();
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.toasts).toHaveLength(0);
  });

  it("submits proposal and connects WebSocket", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    expect(result.current.isRunning).toBe(true);
    expect(mockWsInstances).toHaveLength(1);
    expect(mockWsInstances[0].url).toContain("test-pipeline-001");
  });

  it("handles agent_started event — sets analyzing", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    const ws = mockWsInstances[0];

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "agent_started",
          state: "YIELD_ANALYSIS",
          proposal_id: "p-001",
          timestamp: "2026-06-12T00:00:01Z",
          agent: "yield_maxi",
        }),
      });
    });

    expect(result.current.agents[0].status).toBe("analyzing");
  });

  it("handles agent_decided event — updates agent", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    const ws = mockWsInstances[0];

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "agent_decided",
          state: "YIELD_ANALYSIS",
          proposal_id: "p-001",
          timestamp: "2026-06-12T00:00:02Z",
          agent: "yield_maxi",
          decision: {
            agent_name: "yield_maxi",
            decision: "PASS",
            confidence: 0.85,
            reason: "Good yield",
            data: { apy: 24.5 },
            timestamp: "2026-06-12T00:00:02Z",
          },
        }),
      });
    });

    expect(result.current.agents[0].status).toBe("decided");
    expect(result.current.agents[0].decision?.decision).toBe("PASS");
  });

  it("handles expert_selected — marks unselected as skipped", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    const ws = mockWsInstances[0];

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "expert_selected",
          state: "EXPERT_SELECTION",
          proposal_id: "p-001",
          timestamp: "2026-06-12T00:00:00Z",
          selected_experts: ["yield_maxi", "risk_auditor", "macro_strategist"],
        }),
      });
    });

    // Selected should remain waiting
    expect(result.current.agents[0].status).toBe("waiting"); // yield_maxi
    // Unselected specialists should be skipped
    const arb = result.current.agents.find(
      (a) => a.name === "arbitrage_sniper"
    );
    expect(arb?.status).toBe("skipped");
  });

  it("handles pipeline_completed — sets result and stops running", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    const ws = mockWsInstances[0];

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "pipeline_completed",
          state: "COMPLETED",
          proposal_id: "p-001",
          timestamp: "2026-06-12T00:00:10Z",
          final_decision: "PASS",
          tx_hash: "0xabc123def456",
          result: {
            proposal_id: "p-001",
            decisions: [],
            selected_experts: [
              "yield_maxi",
              "risk_auditor",
              "macro_strategist",
            ],
            votes_pass: 3,
            votes_reject: 0,
            votes_defer: 0,
            threshold: 2,
            final_decision: "PASS",
            synthesis_reasoning: "3 experts APPROVE",
            tx_hash: "0xabc123def456",
            explorer_url:
              "https://explorer.mantle.xyz/tx/0xabc123def456",
            completed_at: "2026-06-12T00:00:10Z",
          },
        }),
      });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.result).not.toBeNull();
    expect(result.current.result!.final_decision).toBe("PASS");
  });

  it("reset clears all state and closes WebSocket", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    act(() => {
      result.current.reset();
    });

    expect(
      result.current.agents.every((a) => a.status === "waiting")
    ).toBe(true);
    expect(result.current.timeline).toHaveLength(0);
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
    expect(mockWsInstances[0].close).toHaveBeenCalled();
  });

  it("handles pipeline_error event", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    const ws = mockWsInstances[0];

    act(() => {
      ws.onmessage?.({
        data: JSON.stringify({
          type: "pipeline_error",
          state: "FAILED",
          proposal_id: "p-001",
          timestamp: "2026-06-12T00:00:05Z",
          error: "Agent timed out",
        }),
      });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBe("Agent timed out");
  });

  it("handles WebSocket error", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit(PROPOSAL);
    });

    const ws = mockWsInstances[0];

    act(() => {
      ws.onerror?.({});
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBe("WebSocket connection error");
  });
});
