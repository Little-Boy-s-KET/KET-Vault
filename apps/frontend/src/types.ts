/**
 * KET Board - TypeScript Type Definitions.
 * 
 * Shared types between frontend components.
 * Upgraded for 10-agent MoE (Mixture-of-Experts) architecture.
 */

// =============================================================================
// Enums
// =============================================================================

export type ProposalAction =
  | "FARM_YIELD"
  | "PROVIDE_LIQUIDITY"
  | "LEND"
  | "SWAP"
  | "WITHDRAW";

export type OpportunityType =
  | "YIELD_FARM"
  | "ARBITRAGE"
  | "HEDGE"
  | "REBALANCE"
  | "ECOSYSTEM_FARM";

export type Decision = "PASS" | "REJECT" | "DEFER";

export type PipelineState =
  | "PROPOSAL_RECEIVED"
  | "EXPERT_SELECTION"
  | "YIELD_ANALYSIS"
  | "RISK_ASSESSMENT"
  | "MACRO_TIMING"
  | "PARALLEL_EVALUATION"
  | "CONSENSUS_SYNTHESIS"
  | "FINAL_AUDIT"
  | "CONSENSUS_REACHED"
  | "REJECTED"
  | "DEFERRED"
  | "EXECUTING"
  | "COMPLETED"
  | "FAILED";

export type AgentName =
  | "yield_maxi"
  | "risk_auditor"
  | "macro_strategist"
  | "arbitrage_sniper"
  | "delta_neutral_hedger"
  | "concentrated_lp_manager"
  | "ecosystem_farmer"
  | "sentiment_analyst"
  | "compliance_officer"
  | "portfolio_rebalancer";

export type AgentRole = "core" | "specialist" | "guardian";

// =============================================================================
// Data Models
// =============================================================================

export interface ProposalRequest {
  action: ProposalAction;
  token: string;
  amount: number;
  target_protocol: string;
  opportunity_type: OpportunityType;
  max_impermanent_loss: number;
  min_audit_score: number;
  context: string;
}

export interface AgentDecision {
  agent_name: AgentName;
  decision: Decision;
  confidence: number;
  reason: string;
  data: Record<string, unknown>;
  amended_params?: Record<string, unknown> | null;
  timestamp: string;
}

export interface ConsensusResult {
  proposal_id: string;
  decisions: AgentDecision[];
  selected_experts: string[];
  votes_pass: number;
  votes_reject: number;
  votes_defer: number;
  threshold: number;
  final_decision: Decision;
  synthesis_reasoning: string;
  tx_hash: string | null;
  explorer_url: string | null;
  completed_at: string;
}

// =============================================================================
// WebSocket Events
// =============================================================================

export interface PipelineEvent {
  type:
    | "pipeline_started"
    | "expert_selected"
    | "agent_started"
    | "agent_decided"
    | "consensus_synthesis"
    | "consensus"
    | "pipeline_completed"
    | "pipeline_error"
    | "pong";
  state: PipelineState;
  proposal_id: string;
  timestamp: string;
  // Event-specific fields
  agent?: AgentName;
  decision?: AgentDecision;
  final_decision?: Decision;
  votes_pass?: number;
  votes_reject?: number;
  votes_defer?: number;
  tx_hash?: string | null;
  explorer_url?: string | null;
  result?: ConsensusResult;
  proposal?: Record<string, unknown>;
  error?: string;
  // MoE-specific fields
  selected_experts?: string[];
  synthesis_reasoning?: string;
}

// =============================================================================
// Component Props
// =============================================================================

export type AgentStatus = "waiting" | "analyzing" | "decided" | "skipped";

export interface AgentState {
  name: AgentName;
  displayName: string;
  emoji: string;
  color: string;
  erc8004Id: string;
  trustScore: number;
  role: AgentRole;
  status: AgentStatus;
  decision?: AgentDecision;
  description: string;
}

export const AGENT_CONFIG: Record<AgentName, Omit<AgentState, "status" | "decision">> = {
  yield_maxi: {
    name: "yield_maxi",
    displayName: "Yield Maxi",
    emoji: "Y",
    color: "#10b981",
    erc8004Id: "#1042",
    trustScore: 0.97,
    role: "core",
    description: "Capital Deployer & Alpha Scanner",
  },
  risk_auditor: {
    name: "risk_auditor",
    displayName: "Risk Auditor",
    emoji: "R",
    color: "#ef4444",
    erc8004Id: "#0887",
    trustScore: 0.99,
    role: "core",
    description: "Safety Veto & Security Validator",
  },
  macro_strategist: {
    name: "macro_strategist",
    displayName: "Macro Strategist",
    emoji: "M",
    color: "#3b82f6",
    erc8004Id: "#1201",
    trustScore: 0.94,
    role: "core",
    description: "Execution Timer & Network Analyst",
  },
  arbitrage_sniper: {
    name: "arbitrage_sniper",
    displayName: "Arbitrage Sniper",
    emoji: "A",
    color: "#06b6d4",
    erc8004Id: "#2301",
    trustScore: 0.91,
    role: "specialist",
    description: "Atomic Cross-DEX Flash Trading",
  },
  delta_neutral_hedger: {
    name: "delta_neutral_hedger",
    displayName: "Delta-Neutral Hedger",
    emoji: "D",
    color: "#eab308",
    erc8004Id: "#2302",
    trustScore: 0.89,
    role: "specialist",
    description: "Volatility Shield via Perp Hedging",
  },
  concentrated_lp_manager: {
    name: "concentrated_lp_manager",
    displayName: "Concentrated LP",
    emoji: "C",
    color: "#f97316",
    erc8004Id: "#2303",
    trustScore: 0.86,
    role: "specialist",
    description: "Liquidity Range Optimizer",
  },
  ecosystem_farmer: {
    name: "ecosystem_farmer",
    displayName: "Ecosystem Farmer",
    emoji: "E",
    color: "#84cc16",
    erc8004Id: "#2304",
    trustScore: 0.88,
    role: "specialist",
    description: "Multi-Protocol Yield Stacking",
  },
  sentiment_analyst: {
    name: "sentiment_analyst",
    displayName: "Sentiment Analyst",
    emoji: "S",
    color: "#d946ef",
    erc8004Id: "#2305",
    trustScore: 0.82,
    role: "specialist",
    description: "Market Psychology Evaluator",
  },
  portfolio_rebalancer: {
    name: "portfolio_rebalancer",
    displayName: "Portfolio Rebalancer",
    emoji: "P",
    color: "#a855f7",
    erc8004Id: "#2306",
    trustScore: 0.85,
    role: "specialist",
    description: "Asset Allocation Optimizer",
  },
  compliance_officer: {
    name: "compliance_officer",
    displayName: "Compliance Officer",
    emoji: "G",
    color: "#dc2626",
    erc8004Id: "#9001",
    trustScore: 0.96,
    role: "guardian",
    description: "Regulatory Guardian (Auto >$10k)",
  },
};

// Helper: get agents by role
export const CORE_AGENTS: AgentName[] = ["yield_maxi", "risk_auditor", "macro_strategist"];
export const SPECIALIST_AGENTS: AgentName[] = [
  "arbitrage_sniper",
  "delta_neutral_hedger",
  "concentrated_lp_manager",
  "ecosystem_farmer",
  "sentiment_analyst",
  "portfolio_rebalancer",
];
export const GUARDIAN_AGENTS: AgentName[] = ["compliance_officer"];
export const ALL_AGENTS: AgentName[] = [...CORE_AGENTS, ...SPECIALIST_AGENTS, ...GUARDIAN_AGENTS];

// Opportunity type labels for UI dropdown
export const OPPORTUNITY_LABELS: Record<OpportunityType, string> = {
  YIELD_FARM: "Yield Farming",
  ARBITRAGE: "Arbitrage Trading",
  HEDGE: "Delta-Neutral Hedge",
  REBALANCE: "Portfolio Rebalance",
  ECOSYSTEM_FARM: "Ecosystem Farming",
};
