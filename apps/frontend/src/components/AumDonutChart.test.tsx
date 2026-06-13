import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AumDonutChart } from "./AumDonutChart";

describe("AumDonutChart", () => {
  it("renders correctly with default allocations", () => {
    render(<AumDonutChart />);

    // Check total AUM text
    expect(screen.getByText("Total AUM")).toBeInTheDocument();
    expect(screen.getByText("$250,000")).toBeInTheDocument();

    // Check legend items
    expect(screen.getByText("USDC")).toBeInTheDocument();
    expect(screen.getByText("MNT")).toBeInTheDocument();
    expect(screen.getByText("mETH")).toBeInTheDocument();
  });

  it("handles hover states on segments and legend correctly", () => {
    const { container } = render(<AumDonutChart />);

    // SVG circles representing segments (first is background)
    const segments = container.querySelectorAll(".donut-segment");
    expect(segments).toHaveLength(3);

    // The stroke-width is an attribute in the SVG, not an inline style in standard rendering (unless passed to style={}).
    // Checking the attribute is more robust for SVGs in jsdom.
    expect(segments[0]).toHaveAttribute("stroke-width", "16");

    // Hover first segment
    fireEvent.mouseEnter(segments[0]);
    expect(segments[0]).toHaveAttribute("stroke-width", "19");

    // Leave first segment
    fireEvent.mouseLeave(segments[0]);
    expect(segments[0]).toHaveAttribute("stroke-width", "16");
  });

  it("highlights legend on hover", () => {
    const { container } = render(<AumDonutChart />);

    const legendItems = container.querySelectorAll(".legend-item");
    expect(legendItems).toHaveLength(3);

    // Not highlighted initially
    expect(legendItems[0]).not.toHaveClass("highlighted");

    // Hover
    fireEvent.mouseEnter(legendItems[0]);
    expect(legendItems[0]).toHaveClass("highlighted");

    // Unhover
    fireEvent.mouseLeave(legendItems[0]);
    expect(legendItems[0]).not.toHaveClass("highlighted");
  });
});
