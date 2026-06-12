/**
 * KET Board - Agent Board Component.
 * 
 * 3-row layout for MoE architecture:
 *   Row 1: The Core Board (3 agents - always active, larger cards)
 *   Row 2: The MoE Specialists (6 agents - dimmed by default, glow when selected)
 *   Row 3: The Guardian (Compliance Officer - bottom strip)
 */

import { AgentCard } from "./AgentCard";
import type { AgentState } from "../types";
import { CORE_AGENTS, SPECIALIST_AGENTS, GUARDIAN_AGENTS } from "../types";

interface Props {
  agents: AgentState[];
}

export function AgentBoard({ agents }: Props) {
  const agentMap = new Map(agents.map((a) => [a.name, a]));

  const coreAgents = CORE_AGENTS
    .map((name) => agentMap.get(name))
    .filter(Boolean) as AgentState[];

  const specialistAgents = SPECIALIST_AGENTS
    .map((name) => agentMap.get(name))
    .filter(Boolean) as AgentState[];

  const guardianAgents = GUARDIAN_AGENTS
    .map((name) => agentMap.get(name))
    .filter(Boolean) as AgentState[];

  return (
    <section className="agent-board">
      {/* Row 1: Core Board */}
      <div className="board-section">
        <h3 className="section-title section-core">
          <span className="section-icon"></span> The Core Board
        </h3>
        <div className="agents-grid agents-core">
          {coreAgents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </div>

      {/* Row 2: MoE Specialists */}
      <div className="board-section">
        <h3 className="section-title section-specialist">
          <span className="section-icon"></span> MoE Specialist Experts
        </h3>
        <div className="agents-grid agents-specialist">
          {specialistAgents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} compact />
          ))}
        </div>
      </div>

      {/* Row 3: Guardian */}
      {guardianAgents.length > 0 && (
        <div className="board-section">
          <h3 className="section-title section-guardian">
            <span className="section-icon"></span> The Guardian
          </h3>
          <div className="agents-grid agents-guardian">
            {guardianAgents.map((agent) => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
