/**
 * API Utilities Unit Tests.
 *
 * Tests the API client functions and WebSocket connection logic.
 * All network calls are mocked.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { getWsUrl, submitProposal, getPipelineStatus, getAgents } from "./api";

// =========================================================================
// Mock fetch
// =========================================================================

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockClear();
});

// =========================================================================
// getWsUrl Tests
// =========================================================================

describe("getWsUrl", () => {
  it("generates correct WebSocket URL", () => {
    const url = getWsUrl("abc-123");
    expect(url).toBe("ws://localhost:8000/ws/pipeline/abc-123");
  });

  it("handles different pipeline IDs", () => {
    const url = getWsUrl("test-pipeline-001");
    expect(url).toContain("test-pipeline-001");
    expect(url).toMatch(/^ws:\/\/localhost:8000\/ws\/pipeline\//);
  });
});

// =========================================================================
// submitProposal Tests
// =========================================================================

describe("submitProposal", () => {
  it("calls fetch with correct URL and method", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          pipeline_id: "test-001",
          message: "Pipeline started",
        }),
    });

    const result = await submitProposal({
      action: "FARM_YIELD",
      token: "USDC",
      amount: 1000,
      target_protocol: "Agni Finance",
      opportunity_type: "YIELD_FARM",
      max_impermanent_loss: 5.0,
      min_audit_score: 80.0,
      context: "",
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/proposal");
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");

    // Verify body contains the proposal data
    const body = JSON.parse(options.body);
    expect(body.token).toBe("USDC");
    expect(body.amount).toBe(1000);
    expect(body.action).toBe("FARM_YIELD");

    expect(result.pipeline_id).toBe("test-001");
  });

  it("throws on HTTP error with detail", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () =>
        Promise.resolve({
          detail: "Invalid action 'FAKE'",
        }),
    });

    await expect(
      submitProposal({
        action: "FARM_YIELD" as any,
        token: "USDC",
        amount: 100,
        target_protocol: "",
        opportunity_type: "YIELD_FARM",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
        context: "",
      })
    ).rejects.toThrow("Invalid action");
  });

  it("throws generic error when JSON parsing fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("parse error")),
    });

    await expect(
      submitProposal({
        action: "FARM_YIELD",
        token: "USDC",
        amount: 100,
        target_protocol: "",
        opportunity_type: "YIELD_FARM",
        max_impermanent_loss: 5.0,
        min_audit_score: 80.0,
        context: "",
      })
    ).rejects.toThrow();
  });
});

// =========================================================================
// getPipelineStatus Tests
// =========================================================================

describe("getPipelineStatus", () => {
  it("calls correct endpoint", async () => {
    const mockData = { id: "abc-123", status: "running", events: [] };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await getPipelineStatus("abc-123");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/status/abc-123"
    );
    expect(result.id).toBe("abc-123");
  });

  it("throws on 404", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

    await expect(getPipelineStatus("nonexistent")).rejects.toThrow(
      "not found"
    );
  });
});

// =========================================================================
// getAgents Tests
// =========================================================================

describe("getAgents", () => {
  it("calls correct endpoint", async () => {
    const mockAgents = [
      {
        name: "yield_maxi",
        display_name: "Yield Maxi",
        role: "core",
      },
    ];
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockAgents),
    });

    const result = await getAgents();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/agents"
    );
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("yield_maxi");
  });

  it("throws on failure", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

    await expect(getAgents()).rejects.toThrow("Failed to fetch agents");
  });
});

// =========================================================================
// connectPipelineWS Tests
// =========================================================================

describe("connectPipelineWS", () => {
  let mockWsInstances: any[] = [];
  let OriginalWebSocket: typeof WebSocket;

  beforeEach(() => {
    mockWsInstances = [];

    // Mock WebSocket using a class (arrow functions can't be constructors)
    class MockWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;

      url: string;
      readyState = 0;
      onopen: any = null;
      onmessage: any = null;
      onclose: any = null;
      onerror: any = null;
      close = vi.fn().mockImplementation(function (this: any) {
        this.readyState = 3;
      });
      send = vi.fn();

      constructor(url: string) {
        this.url = url;
        // Set to OPEN after construction
        setTimeout(() => {
          this.readyState = 1;
          this.onopen?.({});
        }, 0);
        mockWsInstances.push(this);
      }
    }

    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    // Re-stub fetch since unstubAllGlobals removes it
    vi.stubGlobal("fetch", mockFetch);
  });

  it("creates WebSocket with correct URL", async () => {
    const { connectPipelineWS } = await import("./api");

    const conn = connectPipelineWS("test-123", {
      onEvent: vi.fn(),
    });

    expect(mockWsInstances).toHaveLength(1);
    expect(mockWsInstances[0].url).toBe(
      "ws://localhost:8000/ws/pipeline/test-123"
    );

    conn.close();
  });

  it("close() calls ws.close with code 1000", async () => {
    const { connectPipelineWS } = await import("./api");

    const conn = connectPipelineWS("test-456", {
      onEvent: vi.fn(),
    });

    // Simulate connection open
    mockWsInstances[0].readyState = 1;
    conn.close();

    expect(mockWsInstances[0].close).toHaveBeenCalledWith(
      1000,
      "Client closing"
    );
  });

  it("dispatches parsed events to onEvent callback", async () => {
    const { connectPipelineWS } = await import("./api");
    const onEvent = vi.fn();

    connectPipelineWS("test-789", { onEvent });

    const ws = mockWsInstances[0];
    const mockEvent = {
      type: "agent_decided",
      state: "YIELD_ANALYSIS",
      proposal_id: "p-001",
      timestamp: "2026-01-01T00:00:00Z",
    };

    // Simulate receiving a message
    ws.onmessage?.({ data: JSON.stringify(mockEvent) });

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(mockEvent);
  });

  it("handles malformed JSON gracefully", async () => {
    const { connectPipelineWS } = await import("./api");
    const onEvent = vi.fn();
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    connectPipelineWS("test-bad-json", { onEvent });

    const ws = mockWsInstances[0];
    ws.onmessage?.({ data: "not valid json {{{" });

    expect(onEvent).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });
});
