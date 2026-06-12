/**
 * usePipeline Hook Tests.
 *
 * Tests initial state, event handling, and reset logic.
 * WebSocket is mocked to test the hook in isolation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePipeline } from "./usePipeline";
import type { PipelineEvent } from "../types";

// =========================================================================
// Mock WebSocket & API
// =========================================================================

// Capture the last callbacks passed to connectPipelineWS
let lastWSCallbacks: {
  onEvent: (event: PipelineEvent) => void;
  onClose?: () => void;
  onReconnecting?: (attempt: number) => void;
  onReconnected?: () => void;
  onReconnectFailed?: () => void;
} | null = null;

const mockClose = vi.fn();

vi.mock("../utils/api", () => ({
  submitProposal: vi.fn().mockResolvedValue({
    pipeline_id: "test-pipeline-001",
    message: "Pipeline started",
  }),
  connectPipelineWS: vi.fn((_id: string, callbacks: typeof lastWSCallbacks) => {
    lastWSCallbacks = callbacks;
    return { close: mockClose };
  }),
}));

// Mock crypto.randomUUID
vi.stubGlobal("crypto", {
  randomUUID: () => `uuid-${Math.random().toString(36).slice(2, 8)}`,
});

// =========================================================================
// Tests
// =========================================================================

describe("usePipeline", () => {
  beforeEach(() => {
    lastWSCallbacks = null;
    mockClose.mockClear();
  });

  it("initializes with 3 agents in waiting state", () => {
    const { result } = renderHook(() => usePipeline());

    expect(result.current.agents).toHaveLength(3);
    expect(result.current.agents[0].name).toBe("yield_maxi");
    expect(result.current.agents[1].name).toBe("risk_auditor");
    expect(result.current.agents[2].name).toBe("macro_strategist");
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
      await result.current.submit({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 1000,
        target_protocol: "Agni Finance",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
      });
    });

    expect(result.current.isRunning).toBe(true);
    expect(result.current.pipelineState).toBe("PROPOSAL_RECEIVED");
    expect(lastWSCallbacks).not.toBeNull();
  });

  it("handles pipeline_started event", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 1000,
        target_protocol: "Agni Finance",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
      });
    });

    act(() => {
      lastWSCallbacks!.onEvent({
        type: "pipeline_started",
        state: "PROPOSAL_RECEIVED",
        proposal_id: "p-001",
        timestamp: "2026-06-12T00:00:00Z",
      });
    });

    expect(result.current.timeline).toHaveLength(1);
    expect(result.current.timeline[0].text).toContain("Proposal received");
  });

  it("handles agent_decided event - updates agent state", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 1000,
        target_protocol: "Agni Finance",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
      });
    });

    // Start agent
    act(() => {
      lastWSCallbacks!.onEvent({
        type: "agent_started",
        state: "YIELD_ANALYSIS",
        proposal_id: "p-001",
        timestamp: "2026-06-12T00:00:01Z",
        agent: "yield_maxi",
      });
    });

    expect(result.current.agents[0].status).toBe("analyzing");

    // Decide agent
    act(() => {
      lastWSCallbacks!.onEvent({
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
      });
    });

    expect(result.current.agents[0].status).toBe("decided");
    expect(result.current.agents[0].decision?.decision).toBe("PASS");
  });

  it("handles pipeline_completed - sets result and stops running", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 1000,
        target_protocol: "Agni Finance",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
      });
    });

    act(() => {
      lastWSCallbacks!.onEvent({
        type: "pipeline_completed",
        state: "COMPLETED",
        proposal_id: "p-001",
        timestamp: "2026-06-12T00:00:10Z",
        tx_hash: "0xabc123def456",
        result: {
          proposal_id: "p-001",
          decisions: [],
          votes_pass: 3,
          votes_reject: 0,
          votes_defer: 0,
          threshold: 2,
          final_decision: "PASS",
          tx_hash: "0xabc123def456",
          explorer_url: "https://explorer.mantle.xyz/tx/0xabc123def456",
          completed_at: "2026-06-12T00:00:10Z",
        },
      });
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.result).not.toBeNull();
    expect(result.current.result!.final_decision).toBe("PASS");
  });

  it("reset clears all state", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 1000,
        target_protocol: "Agni Finance",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
      });
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.agents.every((a) => a.status === "waiting")).toBe(
      true
    );
    expect(result.current.timeline).toHaveLength(0);
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.toasts).toHaveLength(0);
    expect(mockClose).toHaveBeenCalled();
  });

  it("adds toast on reconnecting event", async () => {
    const { result } = renderHook(() => usePipeline());

    await act(async () => {
      await result.current.submit({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 1000,
        target_protocol: "Agni Finance",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
      });
    });

    act(() => {
      lastWSCallbacks!.onReconnecting?.(1);
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe("info");
    expect(result.current.toasts[0].message).toContain("Reconnecting");
  });
});
