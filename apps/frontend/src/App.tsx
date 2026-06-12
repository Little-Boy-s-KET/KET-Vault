/**
 * KET Board - Main Application.
 *
 * AI Board of Directors Dashboard for DeFi Treasury
 * on Mantle Network.
 */

import { useState } from "react";
import { Header } from "./components/Header";
import { ProposalForm } from "./components/ProposalForm";
import { AgentBoard } from "./components/AgentBoard";
import { PipelineTimeline } from "./components/PipelineTimeline";
import { ConsensusResult } from "./components/ConsensusResult";
import { ToastContainer } from "./components/Toast";
import { WalletModal } from "./components/WalletModal";
import { DepositModal } from "./components/DepositModal";
import { TreasuryPortfolio } from "./components/TreasuryPortfolio";
import { AgentMarketplace } from "./components/AgentMarketplace";
import { usePipeline } from "./hooks/usePipeline";

function App() {
  const {
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
  } = usePipeline();

  // Tab State
  const [activeTab, setActiveTab] = useState<"board" | "portfolio" | "marketplace">("board");

  // Web3 Mock States
  const [isWalletConnected, setIsWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState("");
  const [walletBalance, setWalletBalance] = useState(0);
  const [vaultBalance, setVaultBalance] = useState(0);
  const [hiredAgentIds, setHiredAgentIds] = useState<string[]>([]);

  // Modals Visibility
  const [isWalletModalOpen, setIsWalletModalOpen] = useState(false);
  const [isDepositModalOpen, setIsDepositModalOpen] = useState(false);

  const hasStarted = pipelineState !== null;

  const handleWalletConnect = (address: string, balance: number) => {
    setIsWalletConnected(true);
    setWalletAddress(address);
    setWalletBalance(balance);
  };

  const handleVaultDeposit = (amount: number) => {
    setWalletBalance((prev) => prev - amount);
    setVaultBalance((prev) => prev + amount);
  };

  const handleHireAgent = (agentId: string, cost: number) => {
    setWalletBalance((prev) => prev - cost);
    setHiredAgentIds((prev) => [...prev, agentId]);
  };

  return (
    <div className="app-container">
      <Header 
        isWalletConnected={isWalletConnected}
        walletAddress={walletAddress}
        walletBalance={walletBalance}
        vaultBalance={vaultBalance}
        onConnectClick={() => setIsWalletModalOpen(true)}
        onDepositClick={() => setIsDepositModalOpen(true)}
      />

      <nav className="tab-navigation">
        <button
          className={`tab-btn ${activeTab === "board" ? "active" : ""}`}
          onClick={() => setActiveTab("board")}
        >
          Consensus Board
        </button>
        <button
          className={`tab-btn ${activeTab === "portfolio" ? "active" : ""}`}
          onClick={() => setActiveTab("portfolio")}
        >
          Treasury Portfolio
        </button>
        <button
          className={`tab-btn ${activeTab === "marketplace" ? "active" : ""}`}
          onClick={() => setActiveTab("marketplace")}
        >
          Agent Marketplace
        </button>
      </nav>

      {activeTab === "board" && (
        <div className="tab-content">
          <ProposalForm 
            onSubmit={submit} 
            isRunning={isRunning} 
            isWalletConnected={isWalletConnected}
            vaultBalance={vaultBalance}
          />

          {hasStarted && (
            <>
              <AgentBoard agents={agents} />

              <PipelineTimeline entries={timeline} />

              {result && <ConsensusResult result={result} />}

              {error && (
                <div className="consensus-result reject">
                  <div className="consensus-icon"></div>
                  <h2 className="consensus-title reject">Error</h2>
                  <p className="consensus-votes">{error}</p>
                </div>
              )}

              {!isRunning && result && (
                <button
                  className="submit-btn"
                  onClick={reset}
                  style={{ alignSelf: "center", marginTop: "20px" }}
                >
                  New Proposal
                </button>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === "portfolio" && (
        <div className="tab-content">
          <TreasuryPortfolio />
        </div>
      )}

      {activeTab === "marketplace" && (
        <div className="tab-content">
          <AgentMarketplace 
            isWalletConnected={isWalletConnected}
            walletBalance={walletBalance}
            hiredAgentIds={hiredAgentIds}
            onHireAgent={handleHireAgent}
          />
        </div>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <WalletModal 
        isOpen={isWalletModalOpen}
        onClose={() => setIsWalletModalOpen(false)}
        onConnect={handleWalletConnect}
      />

      <DepositModal 
        isOpen={isDepositModalOpen}
        onClose={() => setIsDepositModalOpen(false)}
        walletBalance={walletBalance}
        onDeposit={handleVaultDeposit}
      />
    </div>
  );
}

export default App;
