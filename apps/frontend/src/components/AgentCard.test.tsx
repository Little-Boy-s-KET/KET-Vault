/**
 * AgentCard Component Tests.
 *
 * Tests rendering across all 3 states (waiting, analyzing, decided)
 * and verifies ERC-8004 identity badge display.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentCard } from "./AgentCard";
import type { AgentState } from "../types";

// =========================================================================
// Fixtures
// =========================================================================

const baseAgent: AgentState = {
  name: "yield_maxi",
  displayName: "Yield Maxi",
  emoji: "",
  color: "#10b981",
  erc8004Id: "#1042",
  trustScore: 0.97,
  status: "waiting",
};

const decidedAgent: AgentState = {
  ...baseAgent,
  status: "decided",
  decision: {
    agent_name: "yield_maxi",
    decision: "PASS",
    confidence: 0.85,
    reason: "Agni Finance USDC pool looks good",
    data: { apy: 24.5, tvl: 2300000 },
    timestamp: "2026-06-12T00:00:00Z",
  },
};

// =========================================================================
// Tests
// =========================================================================

describe("AgentCard", () => {
  it("renders agent name and ERC-8004 badge", () => {
    render(<AgentCard agent={baseAgent} index={0} />);

    expect(screen.getByText("Yield Maxi")).toBeInTheDocument();
    expect(screen.getByText("ERC-8004 #1042")).toBeInTheDocument();
    expect(screen.getByText("97%")).toBeInTheDocument();
  });

  it("shows Standby badge in waiting state", () => {
    render(<AgentCard agent={baseAgent} index={0} />);

    expect(screen.getByText("Standby")).toBeInTheDocument();
  });

  it("shows spinner in analyzing state", () => {
    const analyzing: AgentState = { ...baseAgent, status: "analyzing" };
    render(<AgentCard agent={analyzing} index={0} />);

    expect(screen.getByText("Analyzing")).toBeInTheDocument();
    expect(screen.getByText("Processing proposal...")).toBeInTheDocument();
  });

  it("shows decision details when decided", () => {
    render(<AgentCard agent={decidedAgent} index={0} />);

    // Decision text - appears in badge and decision value
    expect(screen.getAllByText(/PASS/).length).toBeGreaterThanOrEqual(2);
    // Confidence percentage
    expect(screen.getByText("85%")).toBeInTheDocument();
    // Reason
    expect(
      screen.getByText(/"Agni Finance USDC pool looks good"/)
    ).toBeInTheDocument();
  });

  it("renders confidence bar with correct width", () => {
    const { container } = render(
      <AgentCard agent={decidedAgent} index={0} />
    );

    const fill = container.querySelector(".confidence-bar-fill") as HTMLElement;
    expect(fill).toBeTruthy();
    expect(fill.style.width).toBe("85%");
  });

  it("renders trust bar with correct width", () => {
    const { container } = render(
      <AgentCard agent={baseAgent} index={0} />
    );

    const trustFill = container.querySelector(
      ".trust-bar-fill"
    ) as HTMLElement;
    expect(trustFill).toBeTruthy();
    expect(trustFill.style.width).toBe("97%");
  });

  it("applies reject badge class for REJECT decision", () => {
    const rejectedAgent: AgentState = {
      ...baseAgent,
      status: "decided",
      decision: {
        agent_name: "yield_maxi",
        decision: "REJECT",
        confidence: 0.99,
        reason: "Unaudited contract",
        data: {},
        timestamp: "2026-06-12T00:00:00Z",
      },
    };

    const { container } = render(
      <AgentCard agent={rejectedAgent} index={0} />
    );

    const badge = container.querySelector(".agent-status-badge");
    expect(badge?.classList.contains("reject")).toBe(true);
  });
});
