import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConsensusResult } from "./ConsensusResult";
import type { ConsensusResult as ConsensusResultType } from "../types";

// =========================================================================
// Fixtures
// =========================================================================

const mockResult: ConsensusResultType = {
  proposal_id: "test-prop-001",
  decisions: [
    {
      agent_name: "yield_maxi",
      decision: "PASS",
      confidence: 0.9,
      reason: "Looks great",
      data: { apy: 20 },
      timestamp: "2026-06-13T00:00:00Z"
    }
  ],
  selected_experts: ["yield_maxi", "risk_auditor"],
  votes_pass: 2,
  votes_reject: 0,
  votes_defer: 0,
  threshold: 2,
  final_decision: "PASS",
  synthesis_reasoning: "2 experts voted PASS",
  tx_hash: "0x123",
  explorer_url: "https://explorer.mantle.xyz/tx/0x123",
  completed_at: "2026-06-13T00:00:00Z"
};

// =========================================================================
// Tests
// =========================================================================

describe("ConsensusResult", () => {
  it("renders PASS state correctly", () => {
    render(<ConsensusResult result={mockResult} />);
    expect(screen.getByText("CONSENSUS REACHED")).toBeInTheDocument();
    expect(screen.getByText("2 experts voted PASS")).toBeInTheDocument();
    expect(screen.getByText("2 Pass / 0 Reject / 0 Defer (Threshold: 2/2)")).toBeInTheDocument();
    expect(screen.getByText("yield maxi")).toBeInTheDocument();
    expect(screen.getByText("risk auditor")).toBeInTheDocument();

    const txLink = screen.getByText("View on Mantle Explorer");
    expect(txLink).toHaveAttribute("href", "https://explorer.mantle.xyz/tx/0x123");
  });

  it("renders REJECT state correctly", () => {
    render(<ConsensusResult result={{ ...mockResult, final_decision: "REJECT", votes_pass: 0, votes_reject: 2, threshold: 2 }} />);
    expect(screen.getByText("PROPOSAL REJECTED")).toBeInTheDocument();
    expect(screen.getByText("0 Pass / 2 Reject / 0 Defer (Threshold: 2/2)")).toBeInTheDocument();
  });

  it("renders DEFER state correctly", () => {
    render(<ConsensusResult result={{ ...mockResult, final_decision: "DEFER", votes_pass: 1, votes_reject: 0, votes_defer: 1, threshold: 2 }} />);
    expect(screen.getByText("EXECUTION DEFERRED")).toBeInTheDocument();
    expect(screen.getByText("1 Pass / 0 Reject / 1 Defer (Threshold: 2/2)")).toBeInTheDocument();
  });

  it("handles missing optional properties gracefully", () => {
    const resultWithoutOptionals = { ...mockResult, tx_hash: null, explorer_url: null, selected_experts: [], synthesis_reasoning: "" };
    render(<ConsensusResult result={resultWithoutOptionals} />);

    // Ensure tx link is not there
    expect(screen.queryByText("View on Mantle Explorer")).not.toBeInTheDocument();

    // Ensure synthesis is not rendered
    expect(screen.queryByText("2 experts voted PASS")).not.toBeInTheDocument();
  });

  it("triggers download when clicking download report", () => {
    // Cannot easily mock document.createElement for internal react usage if we just return an empty object
    // because React relies on DOM nodes. Instead, spy on the real anchor element created during the click handler.

    const originalCreateElement = document.createElement.bind(document);
    const mockAnchor = originalCreateElement('a');
    const clickSpy = vi.spyOn(mockAnchor, 'click');
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
        if (tagName === 'a') return mockAnchor;
        return originalCreateElement(tagName);
    });

    global.URL.createObjectURL = vi.fn(() => "blob:fake-url");
    global.URL.revokeObjectURL = vi.fn();

    render(<ConsensusResult result={mockResult} />);

    const downloadBtn = screen.getByText("Download Audit Report");
    fireEvent.click(downloadBtn);

    expect(createElementSpy).toHaveBeenCalledWith("a");
    expect(mockAnchor.download).toBe(`KET-Audit-Report-${mockResult.proposal_id}.txt`);
    expect(mockAnchor.href).toBe("blob:fake-url");
    expect(clickSpy).toHaveBeenCalled();

    createElementSpy.mockRestore();
  });
});
