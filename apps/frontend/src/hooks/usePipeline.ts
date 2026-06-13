/**
 * KET Board - Pipeline Hook.
 *
 * Manages the full MoE consensus pipeline lifecycle:
 * - Submits proposals via REST API
 * - Connects to WebSocket for real-time updates
 * - Tracks 10 agent states (waiting/analyzing/decided/skipped)
 * - Handles expert_selected event for MoE routing
 */

import { useState, useCallback, useRef } from "react";
import type {
  AgentState,
  AgentName,
  ConsensusResult,
  PipelineEvent,
  PipelineState,
  ProposalRequest,
  AgentDecision,
} from "../types";
import { AGENT_CONFIG, ALL_AGENTS } from "../types";
import { submitProposal, getWsUrl } from "../utils/api";

// =============================================================================
// Toast helpers
// =============================================================================

interface Toast {
  id: number;
  message: string;
  type: "info" | "success" | "error";
}

let toastId = 0;

// =============================================================================
// Timeline helpers
// =============================================================================

interface TimelineEntry {
  time: string;
  message: string;
  type: "info" | "agent" | "consensus" | "error";
}

// =============================================================================
// Initial agent states (all 10 agents)
// =============================================================================

function createInitialAgents(): AgentState[] {
  return ALL_AGENTS.map((name) => {
    const config = AGENT_CONFIG[name];
    return {
      ...config,
      status: "waiting" as const,
      decision: undefined,
    };
  });
}

// =============================================================================
// Hook
// =============================================================================

export function usePipeline() {
  const [agents, setAgents] = useState<AgentState[]>(createInitialAgents());
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [result, setResult] = useState<ConsensusResult | null>(null);
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const selectedExpertsRef = useRef<string[]>([]);

  // ──────────────────────────────────────────────────────────────────
  // Toast management
  // ──────────────────────────────────────────────────────────────────

  const addToast = useCallback(
    (message: string, type: Toast["type"] = "info") => {
      const id = ++toastId;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    []
  );

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ──────────────────────────────────────────────────────────────────
  // Timeline management
  // ──────────────────────────────────────────────────────────────────

  const addTimeline = useCallback(
    (message: string, type: TimelineEntry["type"] = "info") => {
      const time = new Date().toLocaleTimeString();
      setTimeline((prev) => [...prev, { time, message, type }]);
    },
    []
  );

  // ──────────────────────────────────────────────────────────────────
  // Agent state management
  // ──────────────────────────────────────────────────────────────────

  const updateAgent = useCallback(
    (name: AgentName, update: Partial<AgentState>) => {
      setAgents((prev) =>
        prev.map((a) => (a.name === name ? { ...a, ...update } : a))
      );
    },
    []
  );

  const markUnselectedAsSkipped = useCallback(
    (selectedExperts: string[]) => {
      setAgents((prev) =>
        prev.map((a) => {
          if (selectedExperts.includes(a.name)) {
            return a; // Keep current status
          }
          return { ...a, status: "skipped" as const };
        })
      );
    },
    []
  );

  // ──────────────────────────────────────────────────────────────────
  // WebSocket event handler
  // ──────────────────────────────────────────────────────────────────

  const handleWsEvent = useCallback(
    (event: PipelineEvent) => {
      setPipelineState(event.state);

      switch (event.type) {
        case "pipeline_started":
          addTimeline("Pipeline started — MoE Router selecting experts...", "info");
          addToast("Pipeline started", "info");
          break;

        case "expert_selected":
          if (event.selected_experts) {
            selectedExpertsRef.current = event.selected_experts;
            markUnselectedAsSkipped(event.selected_experts);
            addTimeline(
              `MoE Router selected ${event.selected_experts.length} experts: ${event.selected_experts.join(", ")}`,
              "info"
            );
            addToast(
              `${event.selected_experts.length} experts activated`,
              "info"
            );
          }
          break;

        case "agent_started":
          if (event.agent) {
            updateAgent(event.agent, { status: "analyzing" });
            const config = AGENT_CONFIG[event.agent];
            addTimeline(
              `${config?.displayName || event.agent} analyzing...`,
              "agent"
            );
          }
          break;

        case "agent_decided":
          if (event.agent && event.decision) {
            updateAgent(event.agent, {
              status: "decided",
              decision: event.decision as AgentDecision,
            });
            const config = AGENT_CONFIG[event.agent];
            addTimeline(
              `${config?.displayName || event.agent}: ${event.decision.decision} (${Math.round(event.decision.confidence * 100)}%)`,
              "agent"
            );
            if (event.decision.decision === "REJECT") {
              addToast(
                `${config?.displayName || event.agent} VETOED`,
                "error"
              );
            }
          }
          break;

        case "consensus_synthesis":
          if (event.synthesis_reasoning) {
            addTimeline(
              `Consensus Synthesis: ${event.synthesis_reasoning}`,
              "consensus"
            );
          }
          break;

        case "consensus":
          addTimeline(
            `Consensus: ${event.final_decision} (${event.votes_pass} pass / ${event.votes_reject} reject / ${event.votes_defer} defer)`,
            "consensus"
          );
          break;

        case "pipeline_completed":
          if (event.result) {
            setResult(event.result as ConsensusResult);
          }
          setIsRunning(false);
          addTimeline("Pipeline completed", "info");
          if (event.final_decision === "PASS") {
            addToast("Consensus reached! Transaction executed.", "success");
          } else if (event.final_decision === "REJECT") {
            addToast("Proposal rejected by the board.", "error");
          } else {
            addToast("Execution deferred.", "info");
          }
          break;

        case "pipeline_error":
          setError(event.error || "Unknown error");
          setIsRunning(false);
          addTimeline(`Error: ${event.error}`, "error");
          addToast(`Pipeline error: ${event.error}`, "error");
          break;
      }
    },
    [addTimeline, addToast, updateAgent, markUnselectedAsSkipped]
  );

  // ──────────────────────────────────────────────────────────────────
  // Submit proposal
  // ──────────────────────────────────────────────────────────────────

  const submit = useCallback(
    async (proposal: ProposalRequest) => {
      // Reset state
      setAgents(createInitialAgents());
      setTimeline([]);
      setResult(null);
      setError(null);
      setIsRunning(true);
      selectedExpertsRef.current = [];

      try {
        const response = await submitProposal(proposal);
        const pipelineId = response.pipeline_id;

        addTimeline(`Proposal submitted: ${pipelineId}`, "info");

        // Connect WebSocket
        const wsUrl = getWsUrl(pipelineId);
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (msg) => {
          try {
            const event = JSON.parse(msg.data) as PipelineEvent;
            handleWsEvent(event);
          } catch {
            // Ignore malformed messages
          }
        };

        ws.onerror = () => {
          setError("WebSocket connection error");
          setIsRunning(false);
        };

        ws.onclose = () => {
          wsRef.current = null;
        };

        // Keep-alive ping
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          } else {
            clearInterval(pingInterval);
          }
        }, 15_000);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to submit proposal");
        setIsRunning(false);
        addToast("Failed to connect to server", "error");
      }
    },
    [addTimeline, addToast, handleWsEvent]
  );

  // ──────────────────────────────────────────────────────────────────
  // Reset
  // ──────────────────────────────────────────────────────────────────

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setAgents(createInitialAgents());
    setTimeline([]);
    setResult(null);
    setPipelineState(null);
    setIsRunning(false);
    setError(null);
    selectedExpertsRef.current = [];
  }, []);

  return {
    agents,
    timeline,
    result,
    pipelineState,
    isRunning,
    error,
    toasts,
    submit,
    reset,
    dismissToast,
  };
}
