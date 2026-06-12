/**
 * KET Board - Agent Card Component.
 * 
 * Displays a single agent's status with role badge,
 * analysis state, and decision result.
 * Supports 'skipped' state for MoE unselected agents.
 */

import type { AgentState, Decision } from "../types";

interface Props {
  agent: AgentState;
  compact?: boolean;
}

export function AgentCard({ agent, compact = false }: Props) {
  const isSkipped = agent.status === "skipped";
  const isActive = agent.status === "analyzing" || agent.status === "decided";

  const roleBadgeClass = `role-badge role-${agent.role}`;
  const cardClass = [
    "agent-card",
    `agent-${agent.status}`,
    isSkipped ? "agent-skipped" : "",
    isActive ? "agent-active" : "",
    compact ? "agent-compact" : "",
  ].filter(Boolean).join(" ");

  const decisionClass = (d: Decision) => {
    if (d === "PASS") return "decision-pass";
    if (d === "REJECT") return "decision-reject";
    return "decision-defer";
  };

  return (
    <div
      className={cardClass}
      style={{ "--agent-color": agent.color } as React.CSSProperties}
    >
      <div className="agent-header">
        <div className="agent-identity">
          <span className="agent-emoji">{agent.emoji}</span>
          <div className="agent-info">
            <span className="agent-name">{agent.displayName}</span>
            <span className="agent-erc">{agent.erc8004Id}</span>
          </div>
        </div>
        <span className={roleBadgeClass}>
          {agent.role === "core" ? "Core" : agent.role === "guardian" ? "Guardian" : "Expert"}
        </span>
      </div>

      {!compact && (
        <p className="agent-description">{agent.description}</p>
      )}

      <div className="agent-trust">
        <span className="trust-label">Trust Score</span>
        <div className="trust-bar">
          <div
            className="trust-fill"
            style={{ width: `${agent.trustScore * 100}%` }}
          />
        </div>
        <span className="trust-value">{(agent.trustScore * 100).toFixed(0)}%</span>
      </div>

      {/* Status indicator */}
      <div className="agent-status-bar">
        {agent.status === "waiting" && (
          <span className="status-text status-waiting">Standby</span>
        )}
        {agent.status === "analyzing" && (
          <span className="status-text status-analyzing">
            <span className="pulse-dot" /> Analyzing...
          </span>
        )}
        {agent.status === "skipped" && (
          <span className="status-text status-skipped">Not Selected</span>
        )}
        {agent.status === "decided" && agent.decision && (
          <div className="agent-decision">
            <span className={`decision-badge ${decisionClass(agent.decision.decision)}`}>
              {agent.decision.decision}
            </span>
            <span className="decision-confidence">
              {(agent.decision.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>

      {/* Reasoning (only when decided and not compact) */}
      {!compact && agent.status === "decided" && agent.decision && (
        <p className="agent-reason">{agent.decision.reason}</p>
      )}
    </div>
  );
}
