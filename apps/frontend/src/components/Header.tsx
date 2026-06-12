import { useEffect, useState } from "react";

interface Props {
  isWalletConnected: boolean;
  walletAddress: string;
  walletBalance: number;
  vaultBalance: number;
  onConnectClick: () => void;
  onDepositClick: () => void;
}

export function Header({
  isWalletConnected,
  walletAddress,
  walletBalance,
  vaultBalance,
  onConnectClick,
  onDepositClick,
}: Props) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("ket-theme") || "cyberpunk";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "neumorphism") {
      root.classList.add("theme-neumorphism");
      root.classList.remove("theme-cyberpunk");
    } else {
      root.classList.add("theme-cyberpunk");
      root.classList.remove("theme-neumorphism");
    }
    localStorage.setItem("ket-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "cyberpunk" ? "neumorphism" : "cyberpunk"));
  };

  const truncateAddress = (addr: string) => {
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  return (
    <header className="header">
      <div className="header-left">
        <span className="header-logo">[KET]</span>
        <div>
          <h1 className="header-title">KET Board of Directors</h1>
          <p className="header-subtitle">AI Treasury Consensus Engine</p>
        </div>
      </div>
      <div className="header-right">
        {isWalletConnected ? (
          <div className="wallet-dashboard-info">
            <div className="wallet-meta">
              <span className="wallet-address-badge">
                {truncateAddress(walletAddress)}
              </span>
              <span className="wallet-balance">
                {walletBalance.toLocaleString()} MNT
              </span>
            </div>
            <div className="vault-meta">
              <span className="vault-lbl">Vault:</span>
              <span className={`vault-balance ${vaultBalance >= 10 ? "funded" : "empty"}`}>
                {vaultBalance.toLocaleString()} MNT
              </span>
            </div>
            <button className="deposit-vault-btn" onClick={onDepositClick}>
              Deposit
            </button>
          </div>
        ) : (
          <button className="connect-wallet-btn" onClick={onConnectClick}>
            Connect Wallet
          </button>
        )}

        <button
          className="theme-toggle-btn"
          onClick={toggleTheme}
          aria-label="Toggle Theme"
        >
          {theme === "cyberpunk" ? (
            <>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="theme-icon"
              >
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
              </svg>
              <span>LIGHT</span>
            </>
          ) : (
            <>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="theme-icon"
              >
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
                <rect x="9" y="9" width="6" height="6" rx="1" />
              </svg>
              <span>DARK</span>
            </>
          )}
        </button>
        <div className="network-badge">
          <span className="network-dot" />
          <span>Mantle Network</span>
        </div>
      </div>
    </header>
  );
}
