/**
 * KET Board - Consensus Result Component.
 *
 * Displays final consensus with vote count,
 * TX hash, and Mantle Explorer link.
 */

import type { ConsensusResult as ConsensusResultType } from "../types";

interface Props {
  result: ConsensusResultType;
}

export function ConsensusResult({ result }: Props) {
  const decision = result.final_decision;
  const decisionClass = decision.toLowerCase();

  const titleMap = {
    PASS: "CONSENSUS REACHED",
    REJECT: "PROPOSAL REJECTED",
    DEFER: "EXECUTION DEFERRED",
  };

  const totalVotes =
    result.votes_pass + result.votes_reject + result.votes_defer;

  const downloadReport = () => {
    const yieldMaxi = result.decisions.find((d) => d.agent_name === "yield_maxi");
    const riskAuditor = result.decisions.find((d) => d.agent_name === "risk_auditor");
    let text = `==================================================\n`;
    text += `              KET BOARD AUDIT REPORT (MoE)\n`;
    text += `==================================================\n`;
    text += `Proposal ID: ${result.proposal_id}\n`;
    text += `Generated At: ${new Date().toLocaleString()}\n`;
    text += `Final Decision: ${result.final_decision} (${result.votes_pass}/${totalVotes} PASS)\n`;
    text += `Selected Experts: ${result.selected_experts?.join(", ") || "N/A"}\n`;
    if (result.synthesis_reasoning) {
      text += `Synthesis: ${result.synthesis_reasoning}\n`;
    }
    text += `--------------------------------------------------\n\n`;

    result.decisions.forEach((d, i) => {
      text += `${i + 1}. ${d.agent_name.toUpperCase().replace(/_/g, " ")} DECISION:\n`;
      text += `   - Vote: ${d.decision}\n`;
      text += `   - Confidence: ${Math.round(d.confidence * 100)}%\n`;
      text += `   - Reason: ${d.reason}\n`;
      if (d.data) {
        Object.entries(d.data).forEach(([key, value]) => {
          if (key !== "all_pools") {
            text += `   - ${key}: ${value}\n`;
          }
        });
      }
      text += `\n`;
    });

    text += `--------------------------------------------------\n`;
    text += `EXECUTION DETAILS:\n`;
    text += `- Transaction Hash: ${result.tx_hash || "N/A (Not executed)"}\n`;
    text += `- Explorer Link: ${result.explorer_url || "N/A"}\n`;
    text += `==================================================\n`;

    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `KET-Audit-Report-${result.proposal_id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`consensus-result ${decisionClass}`}>
      <h2 className={`consensus-title ${decisionClass}`}>
        {titleMap[decision]}
      </h2>
      <p className="consensus-votes">
        {result.votes_pass} Pass / {result.votes_reject} Reject / {result.votes_defer} Defer
        {" "}(Threshold: {result.threshold}/{totalVotes})
      </p>

      {/* Selected Experts */}
      {result.selected_experts && result.selected_experts.length > 0 && (
        <div className="consensus-experts">
          <span className="experts-label">Selected Experts:</span>
          <div className="experts-tags">
            {result.selected_experts.map((name) => (
              <span key={name} className="expert-tag">
                {name.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Synthesis Reasoning */}
      {result.synthesis_reasoning && (
        <p className="synthesis-reasoning">
          {result.synthesis_reasoning}
        </p>
      )}

      <div className="consensus-actions-row">
        {result.tx_hash && result.explorer_url && (
          <a
            href={result.explorer_url}
            target="_blank"
            rel="noopener noreferrer"
            className="tx-link"
          >
            View on Mantle Explorer
          </a>
        )}
        <button className="download-report-btn" onClick={downloadReport}>
          Download Audit Report
        </button>
      </div>
    </div>
  );
}
