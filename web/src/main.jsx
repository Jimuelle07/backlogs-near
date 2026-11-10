import React, { StrictMode, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import { ReceiptsPanel } from './ReceiptsPanel.jsx';
import { createReader } from './near.js';
import './styles.css';

function App() {
  const connection = useMemo(() => {
    try {
      return { reader: createReader({
        guardian: import.meta.env.VITE_GUARDIAN_ID,
        rpc: import.meta.env.VITE_NEAR_RPC_URL,
      }) };
    } catch (error) {
      return { error: error.message };
    }
  }, []);

  return (
    <div className="app">
      <header>
        <a className="wordmark" href="./" aria-label="Payment receipts home">
          <span className="brand-icon" aria-hidden="true">▥</span>
          <span>Payment firewall<span className="brand-subtitle">RECEIPTS EXPLORER</span></span>
        </a>
        <span className="network"><span className="dot" /> Testnet <span className="network-divider">/</span> Read only</span>
      </header>
      <main>
        {connection.error
          ? <div role="alert" className="error">Configuration error: {connection.error}</div>
          : <ReceiptsPanel reader={connection.reader} />}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>);
