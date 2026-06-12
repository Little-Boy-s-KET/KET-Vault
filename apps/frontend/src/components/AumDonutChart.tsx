/**
 * KET Board - SVG Donut Chart for AUM Allocation.
 */

import { useState } from "react";

interface Allocation {
  name: string;
  percentage: number;
  value: number;
  color: string;
}

const ALLOCATIONS: Allocation[] = [
  { name: "USDC", percentage: 40, value: 100000, color: "#10b981" },
  { name: "MNT", percentage: 30, value: 75000, color: "#3b82f6" },
  { name: "mETH", percentage: 30, value: 75000, color: "#a855f7" },
];

export function AumDonutChart() {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // SVG parameters
  const radius = 50;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * radius; // ~314.16

  let currentOffset = 0;

  return (
    <div className="aum-chart-container">
      <div className="chart-wrapper">
        <svg 
          viewBox="0 0 140 140" 
          width="100%" 
          height="100%"
          className="donut-svg"
        >
          {/* Background circle */}
          <circle
            cx="70"
            cy="70"
            r={radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth={strokeWidth}
          />
          {ALLOCATIONS.map((alloc, idx) => {
            const strokeDasharray = `${(alloc.percentage / 100) * circumference} ${circumference}`;
            const strokeDashoffset = -currentOffset;
            currentOffset += (alloc.percentage / 100) * circumference;

            const isHovered = hoveredIdx === idx;

            return (
              <circle
                key={alloc.name}
                cx="70"
                cy="70"
                r={radius}
                fill="transparent"
                stroke={alloc.color}
                strokeWidth={isHovered ? strokeWidth + 3 : strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                transform="rotate(-90 70 70)"
                className="donut-segment"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
                style={{
                  transition: "stroke-width 0.2s ease, filter 0.2s ease",
                  cursor: "pointer",
                  filter: isHovered ? "drop-shadow(0 0 6px rgba(255, 255, 255, 0.2))" : "none",
                }}
              />
            );
          })}
        </svg>

        <div className="chart-center-text">
          <span className="center-title">Total AUM</span>
          <span className="center-value">$250,000</span>
        </div>
      </div>

      <div className="chart-legend-container">
        {ALLOCATIONS.map((alloc, idx) => (
          <div 
            key={alloc.name} 
            className={`legend-item ${hoveredIdx === idx ? "highlighted" : ""}`}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <span 
              className="legend-dot" 
              style={{ backgroundColor: alloc.color }}
            />
            <span className="legend-name">{alloc.name}</span>
            <span className="legend-percentage">{alloc.percentage}%</span>
            <span className="legend-value">${alloc.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
