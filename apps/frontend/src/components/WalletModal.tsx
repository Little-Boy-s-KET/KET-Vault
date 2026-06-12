/**
 * KET Board - Wallet Connect Modal.
 */

import { useState } from "react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onConnect: (address: string, balance: number) => void;
}

const WALLETS = [
  {
    id: "metamask",
    name: "MetaMask",
    logo: "/assets/metamask.svg", // Mock logo path
    description: "Connect using your browser extension",
  },
  {
    id: "rabby",
    name: "Rabby Wallet",
    logo: "/assets/rabby.svg",
    description: "Connect using Rabby extension",
  },
  {
    id: "walletconnect",
    name: "WalletConnect",
    logo: "/assets/walletconnect.svg",
    description: "Scan QR code with your mobile wallet",
  },
];

export function WalletModal({ isOpen, onClose, onConnect }: Props) {
  const [connectingId, setConnectingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleWalletSelect = (walletId: string) => {
    setConnectingId(walletId);
    
    // Simulate connection lag
    setTimeout(() => {
      setConnectingId(null);
      // Generate a mock address and balance
      const mockAddress = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e";
      const mockBalance = 10000.0; // 10,000 $MNT
      onConnect(mockAddress, mockBalance);
      onClose();
    }, 1500);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 className="modal-title">Connect Wallet</h3>
          <button className="modal-close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          {connectingId ? (
            <div className="wallet-connecting-state">
              <span className="blockchain-spinner" />
              <p className="connecting-text">
                Connecting to {WALLETS.find((w) => w.id === connectingId)?.name}...
              </p>
              <p className="connecting-subtext">
                Please approve the connection in your wallet extension.
              </p>
            </div>
          ) : (
            <div className="wallets-list">
              {WALLETS.map((wallet) => (
                <button
                  key={wallet.id}
                  className="wallet-item-btn"
                  onClick={() => handleWalletSelect(wallet.id)}
                >
                  <div className="wallet-logo-placeholder">
                    {wallet.name[0]}
                  </div>
                  <div className="wallet-info">
                    <span className="wallet-name">{wallet.name}</span>
                    <span className="wallet-desc">{wallet.description}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
