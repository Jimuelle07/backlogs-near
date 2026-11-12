import React, { useEffect, useRef, useState } from 'react';
import { accountUrl, formatAmount } from '../near.js';
import { formatHoldCountdown, reasonLabel, statusLabels, statusTones } from '../receipt.js';

export function ExternalLink({ account, children, ...props }) {
  return <a href={accountUrl(account)} target="_blank" rel="noopener noreferrer" {...props}>{children}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span></a>;
}

function HashField({ label, value }) {
  const [message, setMessage] = useState('');
  useEffect(() => setMessage(''), [value]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setMessage('Copied');
    } catch {
      setMessage('Copy unavailable. Select and copy the hash.');
    }
  }

  return <div className="detail-hash"><dt>{label}</dt><dd>
    {value === null ? <span className="secondary">Not recorded</span> : <>
      <code>{value}</code><button onClick={copy} aria-label={`Copy ${label}`}>Copy</button>
    </>}
    <span className="copy-status" role="status">{message}</span>
  </dd></div>;
}

function HoldCountdown({ releaseAtNs }) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return <>{formatHoldCountdown(releaseAtNs, now)}</>;
}

export function ReceiptDetail({ receipt, config, guardian, held, onClose }) {
  const panel = useRef(null);
  useEffect(() => { panel.current?.focus(); }, []);
  const titleId = `receipt-detail-title-${receipt.request_id}`;

  return <section id={`receipt-detail-${receipt.request_id}`} className="receipt-detail" ref={panel}
    tabIndex={-1} aria-labelledby={titleId}>
    <div className="detail-heading"><h4 id={titleId}>Receipt #{receipt.request_id}</h4>
      <button onClick={onClose}>Close details <span aria-hidden="true">×</span></button></div>
    <dl className="detail-fields">
      <div><dt>Request ID</dt><dd><code>{receipt.request_id}</code></dd></div>
      <div><dt>Client ref</dt><dd><code>{receipt.client_ref}</code></dd></div>
      <div><dt>Receiver</dt><dd><ExternalLink account={receipt.receiver_id}>{receipt.receiver_id}</ExternalLink></dd></div>
      <div><dt>Guardian</dt><dd><ExternalLink account={guardian}>{guardian}</ExternalLink></dd></div>
      <div><dt>Exact amount</dt><dd><strong>{formatAmount(receipt.amount, config.token_decimals)}</strong> tokens
        <span className="secondary">{receipt.amount} base units · {config.token_id} · {config.token_decimals} decimals</span></dd></div>
      <div><dt>Status</dt><dd><span className={`vchip ${statusTones[receipt.status]}`}>{statusLabels[receipt.status]}</span> <code>({receipt.status})</code></dd></div>
      <div><dt>Outcome</dt><dd>{receipt.outcome ?? 'No verdict'}</dd></div>
      <div><dt>Checker version</dt><dd><code>{receipt.checker_version ?? 'Not recorded'}</code></dd></div>
      <div><dt>Requested block</dt><dd><code>{receipt.requested_block}</code></dd></div>
      <div><dt>Decided block</dt><dd><code>{receipt.decided_block}</code></dd></div>
      {receipt.status === 'held' && <div className="detail-wide"><dt>Hold countdown</dt><dd>
        {held ? <HoldCountdown releaseAtNs={held.release_at_ns} /> : 'Release time unavailable'}
        <span className="secondary">Uses your device clock. Refresh to read the settlement status.</span>
      </dd></div>}
      <div className="detail-wide"><dt>Reason codes</dt><dd>{receipt.reasons.length ? <ul className="detail-reasons">
        {receipt.reasons.map((reason, index) => <li key={`${reason}-${index}`}><code>{reason}</code> — {reasonLabel(reason)}</li>)}
      </ul> : 'No reason recorded'}</dd></div>
      <HashField label="input_sha256" value={receipt.input_sha256} />
      <HashField label="record_sha256" value={receipt.record_sha256} />
    </dl>
  </section>;
}
