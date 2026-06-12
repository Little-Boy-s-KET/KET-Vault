/**
 * KET Board - Proposal Form Component.
 * Updated for MoE architecture with opportunity type routing.
 */

import { useState } from "react";
import type { ProposalRequest, ProposalAction, OpportunityType } from "../types";
import { OPPORTUNITY_LABELS } from "../types";

interface Props {
  onSubmit: (proposal: ProposalRequest) => void;
  isRunning: boolean;
  isWalletConnected: boolean;
  vaultBalance: number;
}

const ACTIONS: { value: ProposalAction; label: string }[] = [
  { value: "FARM_YIELD", label: "Farm Yield" },
  { value: "PROVIDE_LIQUIDITY", label: "Provide Liquidity" },
  { value: "LEND", label: "Lend" },
  { value: "SWAP", label: "Swap" },
  { value: "WITHDRAW", label: "Withdraw" },
];

const PROTOCOLS = [
  "Agni Finance",
  "FusionX",
  "Lendle",
  "INIT Capital",
  "Merchant Moe",
  "mETH Staking",
];

const OPPORTUNITY_OPTIONS: { value: OpportunityType; label: string }[] = (
  Object.entries(OPPORTUNITY_LABELS) as [OpportunityType, string][]
).map(([value, label]) => ({ value, label }));

export function ProposalForm({ onSubmit, isRunning, isWalletConnected, vaultBalance }: Props) {
  const [action, setAction] = useState<ProposalAction>("FARM_YIELD");
  const [token, setToken] = useState("USDC");
  const [amount, setAmount] = useState("1000");
  const [protocol, setProtocol] = useState("Agni Finance");
  const [opportunityType, setOpportunityType] = useState<OpportunityType>("YIELD_FARM");
  const [context, setContext] = useState("");
  
  // Dynamic AI sliders state
  const [maxIL, setMaxIL] = useState(5.0);
  const [minAudit, setMinAudit] = useState(80.0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      action,
      token: token.toUpperCase(),
      amount: parseFloat(amount) || 1000,
      target_protocol: protocol,
      opportunity_type: opportunityType,
      max_impermanent_loss: maxIL,
      min_audit_score: minAudit,
      context,
    });
  };

  const isLocked = !isWalletConnected || vaultBalance < 10;

  return (
    <form className={`proposal-form ${isLocked ? "locked" : ""}`} onSubmit={handleSubmit}>
      <h2 className="form-title">Submit Treasury Proposal</h2>
      
      {isLocked && (
        <div className="form-lock-overlay">
          <div className="lock-message">
            <span className="lock-icon"></span>
            <p className="lock-title">Proposal Submission Locked</p>
            <p className="lock-desc">
              {!isWalletConnected 
                ? "Please connect your Web3 wallet first to initiate governance votes."
                : `Minimum vault deposit of 10 MNT required. Current: ${vaultBalance} MNT.`
              }
            </p>
          </div>
        </div>
      )}

      <div className="form-grid">
        <div className="form-group">
          <label className="form-label">Action</label>
          <select
            className="form-select"
            value={action}
            onChange={(e) => setAction(e.target.value as ProposalAction)}
            disabled={isRunning || isLocked}
          >
            {ACTIONS.map((a) => (
              <option key={a.value} value={a.value}>
                {a.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Token</label>
          <input
            className="form-input"
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="USDC"
            disabled={isRunning || isLocked}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Amount</label>
          <input
            className="form-input"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="1000"
            min="1"
            disabled={isRunning || isLocked}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Protocol</label>
          <select
            className="form-select"
            value={protocol}
            onChange={(e) => setProtocol(e.target.value)}
            disabled={isRunning || isLocked}
          >
            {PROTOCOLS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">MoE Strategy</label>
          <select
            className="form-select"
            value={opportunityType}
            onChange={(e) => setOpportunityType(e.target.value as OpportunityType)}
            disabled={isRunning || isLocked}
          >
            {OPPORTUNITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group form-group-full">
          <label className="form-label">Context (optional)</label>
          <input
            className="form-input"
            type="text"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="e.g., volatile, sentiment, concentrated"
            disabled={isRunning || isLocked}
          />
        </div>
      </div>

      {/* Dynamic AI Risk Parameters Sliders */}
      <div className="risk-sliders-container">
        <h3 className="risk-sliders-title">AI Board Risk Parameters</h3>
        <div className="risk-sliders-grid">
          <div className="form-group">
            <div className="slider-label-row">
              <label className="form-label">Max Impermanent Loss Tolerance</label>
              <span className="slider-value">{maxIL.toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              step="0.5"
              className="form-slider"
              value={maxIL}
              onChange={(e) => setMaxIL(parseFloat(e.target.value))}
              disabled={isRunning || isLocked}
            />
          </div>

          <div className="form-group">
            <div className="slider-label-row">
              <label className="form-label">Minimum Audit Score Required</label>
              <span className="slider-value">{minAudit.toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              className="form-slider"
              value={minAudit}
              onChange={(e) => setMinAudit(parseFloat(e.target.value))}
              disabled={isRunning || isLocked}
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        className="submit-btn"
        disabled={isRunning || !token || !amount || isLocked}
      >
        {isRunning ? (
          <>
            <span className="spinner" /> Pipeline Running...
          </>
        ) : (
          <>Submit to Board</>
        )}
      </button>
    </form>
  );
}
