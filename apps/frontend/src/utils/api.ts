/**
 * KET Board - API & WebSocket Client.
 *
 * Includes auto-reconnect with exponential backoff
 * for resilient real-time streaming.
 */

import type { ProposalRequest, PipelineEvent } from "../types";

const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";

/**
 * Get WebSocket URL for a pipeline.
 */
export function getWsUrl(pipelineId: string): string {
  return `${WS_BASE}/ws/pipeline/${pipelineId}`;
}

/**
 * Submit a proposal to the KET Board.
 */
export async function submitProposal(
  proposal: ProposalRequest
): Promise<{ pipeline_id: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/proposal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(proposal),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Get pipeline status (polling fallback).
 */
export async function getPipelineStatus(pipelineId: string) {
  const res = await fetch(`${API_BASE}/api/status/${pipelineId}`);
  if (!res.ok) throw new Error(`Pipeline ${pipelineId} not found`);
  return res.json();
}

/**
 * Get list of all available agents.
 */
export async function getAgents() {
  const res = await fetch(`${API_BASE}/api/agents`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

// =========================================================================
// WebSocket with Auto-Reconnect
// =========================================================================

export interface WSCallbacks {
  onEvent: (event: PipelineEvent) => void;
  onClose?: () => void;
  onReconnecting?: (attempt: number) => void;
  onReconnected?: () => void;
  onReconnectFailed?: () => void;
}

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

/**
 * Connect to pipeline WebSocket with auto-reconnect.
 *
 * On unexpected disconnect (not clean close), retries up to 3 times
 * with exponential backoff (1s, 2s, 4s).
 *
 * Returns a cleanup function to close the connection.
 */
export function connectPipelineWS(
  pipelineId: string,
  callbacks: WSCallbacks
): { close: () => void } {
  let ws: WebSocket | null = null;
  let retryCount = 0;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let intentionalClose = false;

  function connect() {
    ws = new WebSocket(`${WS_BASE}/ws/pipeline/${pipelineId}`);

    ws.onopen = () => {
      // If this is a reconnection, notify UI
      if (retryCount > 0) {
        callbacks.onReconnected?.();
      }
      retryCount = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PipelineEvent;
        callbacks.onEvent(data);
      } catch {
        console.warn("Failed to parse WS event:", event.data);
      }
    };

    ws.onclose = (event) => {
      // Clean close (code 1000) or intentional = no reconnect
      if (intentionalClose || event.code === 1000) {
        callbacks.onClose?.();
        return;
      }

      // Pipeline not found (custom code 4004) = no reconnect
      if (event.code === 4004) {
        callbacks.onClose?.();
        return;
      }

      // Unexpected disconnect: attempt reconnect
      if (retryCount < MAX_RETRIES) {
        retryCount++;
        const delay = BASE_DELAY_MS * Math.pow(2, retryCount - 1);
        callbacks.onReconnecting?.(retryCount);
        retryTimer = setTimeout(connect, delay);
      } else {
        callbacks.onReconnectFailed?.();
        callbacks.onClose?.();
      }
    };

    ws.onerror = () => {
      // Error will trigger onclose, so we handle reconnect there
    };
  }

  connect();

  return {
    close() {
      intentionalClose = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close(1000, "Client closing");
      }
    },
  };
}
