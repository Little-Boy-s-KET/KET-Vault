/**
 * KET Board - ERC-8004 Agent Marketplace.
 */

import { useState } from "react";

interface AgentItem {
  id: string;
  name: string;
  erc8004Id: string;
  trustScore: number;
  description: string;
  specialty: string;
  rentCost: number; // in $MNT
}

const MARKETPLACE_AGENTS: AgentItem[] = [
  {
    id: "degen_farmer",
    name: "Degen Yield Farmer",
    erc8004Id: "#0099",
    trustScore: 88,
    description: "High-risk yield optimization scanning micro-cap liquidity pools on Mantle.",
    specialty: "High-yield Farm Scanning",
    rentCost: 50,
  },
  {
    id: "inst_auditor",
    name: "Institutional Auditor",
    erc8004Id: "#0102",
    trustScore: 99,
    description: "Deep byte-code auditing agent utilizing symbolic execution to detect smart contract exploits.",
    specialty: "Contract Exploits & Byte-code Audit",
    rentCost: 150,
  },
  {
    id: "arb_bot",
    name: "Arbitrage Executioner",
    erc8004Id: "#0188",
    trustScore: 92,
    description: "Mem-pool front-running scanner executing multi-hop arbitrage routes across Mantle DEXs.",
    specialty: "DEX Arbitrage Execution",
    rentCost: 100,
  },
  {
    id: "sentiment_scanner",
    name: "Sentiment Scanner",
    erc8004Id: "#0212",
    trustScore: 95,
    description: "Scans social networks, governance forums and news portals for Mantle protocols sentiment analysis.",
    specialty: "Market Sentiment & Social Scanning",
    rentCost: 40,
  },
];

interface Props {
  isWalletConnected: boolean;
  walletBalance: number;
  hiredAgentIds: string[];
  onHireAgent: (agentId: string, cost: number) => void;
}

export function AgentMarketplace({
  isWalletConnected,
  walletBalance,
  hiredAgentIds,
  onHireAgent,
}: Props) {
  const [hiringId, setHiringId] = useState<string | null>(null);

  const handleHireClick = (agent: AgentItem) => {
    if (!isWalletConnected) return;

    if (walletBalance < agent.rentCost) {
      alert("Insufficient wallet balance to hire this agent");
      return;
    }

    setHiringId(agent.id);
    
    // Simulate smart contract interactions on Mantle (ERC-8004 registry lookup and approval)
    setTimeout(() => {
      onHireAgent(agent.id, agent.rentCost);
      setHiringId(null);
    }, 1500);
  };

  return (
    <div className="marketplace-container">
      <div className="portfolio-header">
        <h2 className="portfolio-title">Agent Marketplace</h2>
        <div className="aum-summary-box">
          <span className="aum-label">ERC-8004 Registry</span>
          <span className="aum-value">Mantle Network</span>
        </div>
      </div>

      <div className="marketplace-grid">
        {MARKETPLACE_AGENTS.map((agent) => {
          const isHired = hiredAgentIds.includes(agent.id);
          const isHiring = hiringId === agent.id;
          const isAffordable = walletBalance >= agent.rentCost;

          return (
            <div 
              key={agent.id} 
              className={`agent-market-card neon-card ${isHired ? "hired" : ""}`}
            >
              <div className="agent-market-header">
                <div className="agent-badge-group">
                  <span className="agent-market-id">ERC-8004: {agent.erc8004Id}</span>
                  <span className="agent-trust-score">Trust: {agent.trustScore}%</span>
                </div>
                <h3 className="agent-market-name">{agent.name}</h3>
              </div>

              <div className="agent-market-body">
                <p className="agent-market-desc">{agent.description}</p>
                <div className="spec-label-row">
                  <span className="spec-lbl">Specialty:</span>
                  <span className="spec-val">{agent.specialty}</span>
                </div>
                <div className="rent-label-row">
                  <span className="rent-lbl">Cost:</span>
                  <span className="rent-val">{agent.rentCost} MNT/mo</span>
                </div>
              </div>

              <div className="agent-market-footer">
                {!isWalletConnected ? (
                  <button className="market-btn disabled" disabled>
                    Connect Wallet to Hire
                  </button>
                ) : isHired ? (
                  <button className="market-btn hired-state-btn" disabled>
                    Hired & Active
                  </button>
                ) : (
                  <button 
                    className={`market-btn ${!isAffordable ? "disabled" : ""}`}
                    disabled={isHiring || !isAffordable}
                    onClick={() => handleHireClick(agent)}
                  >
                    {isHiring ? (
                      <>
                        <span className="blockchain-spinner micro" /> Approving...
                      </>
                    ) : !isAffordable ? (
                      "Insufficient Balance"
                    ) : (
                      "Hire Agent"
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
