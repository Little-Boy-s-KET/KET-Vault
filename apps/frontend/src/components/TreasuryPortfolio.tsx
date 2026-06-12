/**
 * KET Board - Treasury Portfolio Component.
 */

import { useState } from "react";
import { AumDonutChart } from "./AumDonutChart";

interface PnLPoint {
  date: string;
  value: number;
}

const HISTORICAL_DATA: PnLPoint[] = [
  { date: "May 1", value: 200000 },
  { date: "May 8", value: 215000 },
  { date: "May 15", value: 210000 },
  { date: "May 22", value: 228000 },
  { date: "May 29", value: 235000 },
  { date: "Jun 5", value: 242000 },
  { date: "Jun 12", value: 250000 },
];

const FARMS = [
  {
    protocol: "Agni Finance",
    pair: "USDC/MNT LP",
    apy: 24.5,
    tvl: 2300000,
    allocated: 75000,
    earned: 1420.5,
    status: "Active",
  },
  {
    protocol: "FusionX",
    pair: "USDC/WETH LP",
    apy: 18.7,
    tvl: 5100000,
    allocated: 100000,
    earned: 895.2,
    status: "Active",
  },
  {
    protocol: "Lendle",
    pair: "USDC Lending",
    apy: 8.3,
    tvl: 12000000,
    allocated: 75000,
    earned: 382.1,
    status: "Active",
  },
];

export function TreasuryPortfolio() {
  const [hoveredPointIdx, setHoveredPointIdx] = useState<number | null>(null);

  // SVG Line Chart dimensions
  const width = 600;
  const height = 180;
  const padding = 20;

  // Find min/max values for scaling
  const values = HISTORICAL_DATA.map((d) => d.value);
  const minVal = Math.min(...values) * 0.95;
  const maxVal = Math.max(...values) * 1.05;

  // Convert points to SVG coordinates
  const getCoordinates = () => {
    const pointsCount = HISTORICAL_DATA.length;
    return HISTORICAL_DATA.map((d, idx) => {
      const x = padding + (idx * (width - 2 * padding)) / (pointsCount - 1);
      const y =
        height -
        padding -
        ((d.value - minVal) * (height - 2 * padding)) / (maxVal - minVal);
      return { x, y };
    });
  };

  const coords = getCoordinates();
  
  // Construct path definitions
  const pathD = coords.reduce((acc, c, idx) => {
    return acc + `${idx === 0 ? "M" : "L"} ${c.x} ${c.y} `;
  }, "");

  const areaD =
    pathD +
    `L ${coords[coords.length - 1].x} ${height - padding} ` +
    `L ${coords[0].x} ${height - padding} Z`;

  return (
    <div className="portfolio-container">
      <div className="portfolio-header">
        <h2 className="portfolio-title">Treasury Portfolio</h2>
        <div className="aum-summary-box">
          <span className="aum-label">Total Assets Under Management</span>
          <span className="aum-value">$250,000.00</span>
        </div>
      </div>

      <div className="portfolio-grid">
        {/* Left column - Allocations */}
        <div className="portfolio-card neon-card">
          <h3 className="card-title">Asset Allocations</h3>
          <AumDonutChart />
        </div>

        {/* Right column - P&L Chart */}
        <div className="portfolio-card neon-card">
          <div className="card-header-flex">
            <h3 className="card-title">Performance Trend (P&L)</h3>
            {hoveredPointIdx !== null && (
              <div className="trend-tooltip">
                <span className="tooltip-date">
                  {HISTORICAL_DATA[hoveredPointIdx].date}:
                </span>
                <span className="tooltip-value">
                  ${HISTORICAL_DATA[hoveredPointIdx].value.toLocaleString()}
                </span>
              </div>
            )}
          </div>
          
          <div className="chart-container">
            <svg 
              viewBox={`0 0 ${width} ${height}`} 
              width="100%" 
              height="100%"
              className="line-chart-svg"
            >
              <defs>
                <linearGradient id="chart-glow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid lines */}
              <line
                x1={padding}
                y1={height - padding}
                x2={width - padding}
                y2={height - padding}
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth="1"
              />
              <line
                x1={padding}
                y1={padding}
                x2={width - padding}
                y2={padding}
                stroke="rgba(255, 255, 255, 0.05)"
                strokeWidth="1"
              />

              {/* Area path with gradient */}
              <path d={areaD} fill="url(#chart-glow)" />

              {/* Line path */}
              <path
                d={pathD}
                fill="none"
                stroke="#3b82f6"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Interaction points */}
              {coords.map((c, idx) => (
                <g key={idx}>
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r={hoveredPointIdx === idx ? 6 : 4}
                    fill="#3b82f6"
                    stroke="rgba(255, 255, 255, 0.8)"
                    strokeWidth="1.5"
                    className="chart-dot"
                    style={{ transition: "r 0.1s ease" }}
                  />
                  {/* Invisible larger hover circle */}
                  <circle
                    cx={c.x}
                    cy={c.y}
                    r="15"
                    fill="transparent"
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() => setHoveredPointIdx(idx)}
                    onMouseLeave={() => setHoveredPointIdx(null)}
                  />
                </g>
              ))}
            </svg>
          </div>
          
          <div className="chart-x-axis">
            {HISTORICAL_DATA.map((d, idx) => (
              <span key={idx} className="axis-label">
                {d.date}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Yield Farming Positions */}
      <div className="portfolio-card neon-card table-card">
        <h3 className="card-title">Active Yield Farms & Pools</h3>
        <div className="table-responsive">
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Protocol</th>
                <th>Pool Pair</th>
                <th>APY</th>
                <th>TVL</th>
                <th>Treasury Invested</th>
                <th>Yield Earned</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {FARMS.map((farm, index) => (
                <tr key={index}>
                  <td className="bold-cell">{farm.protocol}</td>
                  <td>{farm.pair}</td>
                  <td className="color-apy">{farm.apy}%</td>
                  <td>${farm.tvl.toLocaleString()}</td>
                  <td className="bold-cell">${farm.allocated.toLocaleString()}</td>
                  <td className="color-earned">${farm.earned.toLocaleString()} MNT</td>
                  <td>
                    <span className="badge badge-active">{farm.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
