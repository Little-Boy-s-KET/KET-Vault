/**
 * AgentCard Component Tests.
 *
 * Tests rendering across all 4 states (waiting, analyzing, decided, skipped)
 * and verifies role badge and trust score display.
 *
 * Updated for the refactored AgentCard with role badges, description,
 * and new class naming convention.
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
  emoji: "Y",
  color: "#10b981",
  erc8004Id: "#1042",
  trustScore: 0.97,
  role: "core",
  status: "waiting",
  description: "Capital Deployer & Alpha Scanner",
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
    render(<AgentCard agent={baseAgent} />);

    expect(screen.getByText("Yield Maxi")).toBeInTheDocument();
    expect(screen.getByText("#1042")).toBeInTheDocument();
    expect(screen.getByText("97%")).toBeInTheDocument();
  });

  it("shows Core role badge for core agent", () => {
    render(<AgentCard agent={baseAgent} />);
    expect(screen.getByText("Core")).toBeInTheDocument();
  });

  it("shows Expert role badge for specialist agent", () => {
    const specialist: AgentState = {
      ...baseAgent,
      name: "arbitrage_sniper",
      role: "specialist",
    };
    render(<AgentCard agent={specialist} />);
    expect(screen.getByText("Expert")).toBeInTheDocument();
  });

  it("shows Guardian role badge for guardian agent", () => {
    const guardian: AgentState = {
      ...baseAgent,
      name: "compliance_officer",
      role: "guardian",
    };
    render(<AgentCard agent={guardian} />);
    expect(screen.getByText("Guardian")).toBeInTheDocument();
  });

  it("shows Standby in waiting state", () => {
    render(<AgentCard agent={baseAgent} />);
    expect(screen.getByText("Standby")).toBeInTheDocument();
  });

  it("shows Analyzing in analyzing state", () => {
    const analyzing: AgentState = { ...baseAgent, status: "analyzing" };
    render(<AgentCard agent={analyzing} />);
    expect(screen.getByText(/Analyzing/)).toBeInTheDocument();
  });

  it("shows Not Selected in skipped state", () => {
    const skipped: AgentState = { ...baseAgent, status: "skipped" };
    render(<AgentCard agent={skipped} />);
    expect(screen.getByText("Not Selected")).toBeInTheDocument();
  });

  it("shows decision badge when decided", () => {
    render(<AgentCard agent={decidedAgent} />);
    // Decision text in badge
    expect(screen.getByText("PASS")).toBeInTheDocument();
    // Confidence percentage
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("renders trust bar with correct width", () => {
    const { container } = render(<AgentCard agent={baseAgent} />);
    const trustFill = container.querySelector(".trust-fill") as HTMLElement;
    expect(trustFill).toBeTruthy();
    expect(trustFill.style.width).toBe("97%");
  });

  it("renders agent description when not compact", () => {
    render(<AgentCard agent={baseAgent} />);
    expect(
      screen.getByText("Capital Deployer & Alpha Scanner")
    ).toBeInTheDocument();
  });

  it("hides description in compact mode", () => {
    render(<AgentCard agent={baseAgent} compact />);
    expect(
      screen.queryByText("Capital Deployer & Alpha Scanner")
    ).not.toBeInTheDocument();
  });

  it("applies REJECT decision class", () => {
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

    const { container } = render(<AgentCard agent={rejectedAgent} />);
    const badge = container.querySelector(".decision-badge");
    expect(badge?.classList.contains("decision-reject")).toBe(true);
  });

  it("applies skipped class on card", () => {
    const skipped: AgentState = { ...baseAgent, status: "skipped" };
    const { container } = render(<AgentCard agent={skipped} />);
    const card = container.querySelector(".agent-card");
    expect(card?.classList.contains("agent-skipped")).toBe(true);
  });
});
