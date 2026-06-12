/**
 * KET Board - Deposit to Vault Modal.
 */

import { useState } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  walletBalance: number;
  onDeposit: (amount: number) => void;
}

type DepositStep = "input" | "simulating" | "mining" | "success";

export function DepositModal({ isOpen, onClose, walletBalance, onDeposit }: Props) {
  const [amount, setAmount] = useState("100.0");
  const [step, setStep] = useState<DepositStep>("input");
  const [errorMsg, setErrorMsg] = useState("");
  const [txHash, setTxHash] = useState("");

  if (!isOpen) return null;

  const handleDepositSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setErrorMsg("Amount must be greater than 0");
      return;
    }

    if (parsedAmount > walletBalance) {
      setErrorMsg("Insufficient wallet balance");
      return;
    }

    // Step 1: Simulate Tx
    setStep("simulating");
    
    setTimeout(() => {
      // Step 2: Mining Tx on Mantle Network
      setStep("mining");
      
      setTimeout(() => {
        // Step 3: Success
        const mockHash = "0x" + Array.from({ length: 64 }, () => 
          Math.floor(Math.random() * 16).toString(16)
        ).join("");
        setTxHash(mockHash);
        setStep("success");
        onDeposit(parsedAmount);
      }, 2000);
    }, 1200);
  };

  const handleClose = () => {
    // Reset state before closing
    setAmount("100.0");
    setStep("input");
    setErrorMsg("");
    setTxHash("");
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 className="modal-title">Deposit to KET Vault</h3>
          <button className="modal-close-btn" onClick={handleClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          {step === "input" && (
            <form onSubmit={handleDepositSubmit} className="deposit-form">
              <div className="deposit-info-card">
                <div className="info-row">
                  <span className="info-label">Smart Contract:</span>
                  <span className="info-val font-mono">0x8004...a690</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Available Balance:</span>
                  <span className="info-val">{walletBalance.toLocaleString()} MNT</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Amount to Deposit (MNT)</label>
                <div className="input-with-button">
                  <input
                    type="number"
                    className="form-input"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="100.0"
                    step="0.01"
                    min="0.01"
                    required
                  />
                  <button
                    type="button"
                    className="max-btn"
                    onClick={() => setAmount(walletBalance.toString())}
                  >
                    MAX
                  </button>
                </div>
                {errorMsg && <p className="error-message">{errorMsg}</p>}
              </div>

              <button type="submit" className="submit-btn">
                Deposit Tokens
              </button>
            </form>
          )}

          {step === "simulating" && (
            <div className="blockchain-connecting-state">
              <span className="blockchain-spinner" />
              <p className="connecting-text">Simulating Transaction...</p>
              <p className="connecting-subtext">
                Verifying transaction health and estimating gas limit on Mantle Network.
              </p>
            </div>
          )}

          {step === "mining" && (
            <div className="blockchain-connecting-state">
              <span className="blockchain-spinner slow" />
              <p className="connecting-text">Mining Block...</p>
              <p className="connecting-subtext">
                Broadcasting to Mantle Network nodes. Waiting for confirmation.
              </p>
            </div>
          )}

          {step === "success" && (
            <div className="blockchain-success-state">
              <div className="success-icon-badge">OK</div>
              <p className="connecting-text">Deposit Successful!</p>
              <p className="connecting-subtext">
                Your funds have been deposited into the KET Vault Smart Contract.
              </p>
              <div className="tx-details">
                <div className="info-row">
                  <span className="info-label">Amount Deposited:</span>
                  <span className="info-val">{parseFloat(amount).toLocaleString()} MNT</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Transaction Hash:</span>
                  <a 
                    href={`https://explorer.mantle.xyz/tx/${txHash}`} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="tx-hash-link"
                  >
                    {txHash.slice(0, 10)}...{txHash.slice(-8)}
                  </a>
                </div>
              </div>
              <button onClick={handleClose} className="submit-btn">
                Continue
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
