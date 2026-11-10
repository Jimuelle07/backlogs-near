import React, { useEffect, useMemo, useRef, useState } from 'react';
import { accountUrl, formatAmount, STATUSES } from './near.js';

const labels = { paid: 'Paid', held: 'Held', refused: 'Refused', timed_out: 'Timed out', transfer_failed: 'Transfer failed', paying: 'Paying' };
const reasonLabels = {
  stub_allow: 'Scaffold decision', policy_violation: 'Policy violation', injection_high: 'Injection detected',
  melon_match: 'Masked re-run match', lookalike_receiver: 'Lookalike receiver', new_receiver: 'New receiver',
  young_account: 'Young account', contract_code_changed: 'Contract changed', unusual_for_agent: 'Unusual payment',
  jev_injection_driven: 'Jev: injection driven', jev_receiver_risk: 'Jev: receiver risk',
  amount_mismatch: 'Amount mismatch', check_unavailable: 'Check unavailable',
};

function ExternalLink({ account, children, ...props }) {
  return <a href={accountUrl(account)} target="_blank" rel="noopener noreferrer" {...props}>{children}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span></a>;
}

export function ReceiptsPanel({ reader }) {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [request, setRequest] = useState({ pages: 1, revision: 0 });
  const active = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    active.current = true;
    setBusy(true);
    setError('');
    reader.snapshot({ signal: controller.signal, pages: request.pages })
      .then((result) => { if (!controller.signal.aborted) setSnapshot(result); })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.name === 'TimeoutError'
          ? 'The RPC took too long to respond. Try refreshing.' : err.message || 'Unable to reach the testnet RPC.');
      })
      .finally(() => {
        if (!controller.signal.aborted) { setBusy(false); active.current = false; }
      });
    return () => controller.abort();
  }, [reader, request]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      if (!active.current && document.visibilityState === 'visible') {
        setRequest((previous) => ({ ...previous, revision: previous.revision + 1 }));
      }
    }, 30000);
    return () => clearInterval(timer);
  }, [autoRefresh]);

  const receipts = snapshot?.receipts ?? [];
  const visible = useMemo(() => receipts.filter((receipt) => {
    const matchesStatus = filter === 'all' || receipt.status === filter;
    const query = search.trim().toLowerCase();
    return matchesStatus && `${receipt.request_id} ${receipt.client_ref} ${receipt.receiver_id}`.toLowerCase().includes(query);
  }), [receipts, filter, search]);
  const counts = Object.fromEntries(STATUSES.map((status) => [status, receipts.filter((r) => r.status === status).length]));
  const refresh = () => setRequest((previous) => ({ ...previous, revision: previous.revision + 1 }));

  return <>
    <section className="intro" aria-labelledby="page-title">
      <div><p className="eyebrow">PUBLIC PAYMENT LOG</p><h1 id="page-title">Every payment.<br /><span>A visible outcome.</span></h1>
        <p className="intro-copy">Follow what the Guardian paid, held, or refused.<br className="desktop-break" /> Read directly from NEAR testnet.</p></div>
      <aside className="source-card"><span className="source-heading"><span className="dot" /> NEAR TESTNET</span>
        <span className="source-label">Guardian contract</span><ExternalLink account={reader.guardian}>{reader.guardian}</ExternalLink>
        <span className="source-foot">Read only <span aria-hidden="true">·</span> No wallet needed</span></aside>
    </section>

    <section className="receipts-panel" aria-labelledby="receipts-title">
      <div className="panel-heading"><div><p className="eyebrow">ON-CHAIN ACTIVITY</p><h2 id="receipts-title">Payment receipts</h2></div>
        <div className="refresh-controls"><label className="auto-refresh"><input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} /> Auto-refresh · 30s</label>
          <button className="refresh-button" onClick={refresh} disabled={busy}><span aria-hidden="true" className={busy ? 'spin' : ''}>↻</span> {busy ? 'Reading…' : 'Refresh'}</button></div></div>

      <div className="stats" aria-label="Counts for loaded receipts">
        {[['Loaded receipts', snapshot ? receipts.length : '—'], ['Paid', snapshot ? counts.paid : '—'], ['Held', snapshot ? counts.held : '—'], ['Refused', snapshot ? counts.refused : '—']].map(([label, value], index) =>
          <div className="stat" key={label}><span>{label}</span><strong className={`stat-${index}`}>{value}</strong><small>{index === 0 ? 'From the Guardian' : 'In loaded receipts'}</small></div>)}
      </div>

      <div className="toolbar"><div className="filters" role="group" aria-label="Filter receipt status">
        {['all', 'paid', 'held', 'refused'].map((status) => <button key={status} aria-pressed={filter === status} className={filter === status ? 'selected' : ''} onClick={() => setFilter(status)}>{status === 'all' ? 'All receipts' : labels[status]}</button>)}
        <label className="sr-only" htmlFor="other-status">Other receipt status</label>
        <select id="other-status" value={['timed_out', 'transfer_failed', 'paying'].includes(filter) ? filter : ''} onChange={(event) => setFilter(event.target.value || 'all')}>
          <option value="">Other statuses</option>{['timed_out', 'transfer_failed', 'paying'].map((status) => <option key={status} value={status}>{labels[status]}</option>)}
        </select></div>
        <label className="search"><span aria-hidden="true">⌕</span><span className="sr-only">Search request ID, reference, or receiver</span><input type="search" placeholder="Search ID or receiver" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      </div>

      {error && <div role="alert" className="error"><strong>{snapshot ? 'Live refresh unavailable.' : 'Unable to load receipts.'}</strong> {error} {snapshot && 'Showing the last successful read.'}<button onClick={refresh} disabled={busy}>Try again</button></div>}
      <div className="table-wrap" tabIndex="0" role="region" aria-label="Payment receipts table" aria-busy={busy}>
        <table><caption className="sr-only">Public Guardian receipts. Amounts use the token decimals configured on the Guardian. Explorer links open account activity.</caption>
          <thead><tr><th scope="col">Request / reference</th><th scope="col">Receiver</th><th scope="col" className="amount">Amount</th><th scope="col">Status / verdict</th><th scope="col">Reason</th><th scope="col"><span className="sr-only">Explorer</span></th></tr></thead>
          <tbody>{visible.map((receipt) => <tr key={receipt.request_id}>
            <td><span className="request-id">#{receipt.request_id}</span><span className="secondary reference">{receipt.client_ref}</span></td>
            <td><ExternalLink account={receipt.receiver_id} className="receiver">{receipt.receiver_id}</ExternalLink><span className="secondary">Block {receipt.decided_block}</span></td>
            <td className="amount"><strong>{formatAmount(receipt.amount, snapshot.config.token_decimals)}</strong><span className="secondary" title={snapshot.config.token_id}>tokens</span></td>
            <td><span className={`badge ${receipt.status}`}><span aria-hidden="true" />{labels[receipt.status]}</span><span className="secondary verdict">{receipt.outcome ?? 'No verdict'}</span></td>
            <td className="reasons">{receipt.reasons.length ? receipt.reasons.map((reason) => <span key={reason} title={reason} className={reason === 'stub_allow' ? 'stub-reason' : ''}>{reasonLabels[reason] ?? reason.replaceAll('_', ' ')}</span>) : <span className="secondary">No reason recorded</span>}</td>
            <td><ExternalLink account={reader.guardian} aria-label={`View Guardian activity for request ${receipt.request_id}`}><span className="explorer-label">Explorer</span></ExternalLink></td>
          </tr>)}</tbody>
        </table>
        {!snapshot && !error && <div className="empty" role="status"><span className="loading-mark" aria-hidden="true">◌</span><h3>Reading the Guardian…</h3><p>Fetching public payment receipts from testnet.</p></div>}
        {snapshot && visible.length === 0 && <div className="empty"><span aria-hidden="true">≡</span><h3>{receipts.length ? 'No matching receipts' : 'No receipts yet'}</h3><p>{receipts.length ? 'Try another status or search term. Filters apply to loaded receipts.' : 'Receipts will appear here after the Guardian records a payment request.'}</p>{receipts.length > 0 && <button onClick={() => { setFilter('all'); setSearch(''); }}>Clear filters</button>}</div>}
      </div>

      <div className="panel-footer"><p role="status">{snapshot ? <>{visible.length} of {receipts.length} loaded receipts <span aria-hidden="true">·</span> Updated {snapshot.updatedAt.toLocaleTimeString()} <span aria-hidden="true">·</span> Block {snapshot.blockHeight}</> : error ? 'No live data available' : 'Connecting to testnet…'}</p>
        {snapshot?.hasMore && <button disabled={busy} onClick={() => setRequest((previous) => ({ pages: previous.pages + 1, revision: previous.revision + 1 }))}>Load more receipts ↓</button>}</div>
    </section>

    <div className="below-panel"><p><span aria-hidden="true">ⓘ</span> <strong>Testnet, real records.</strong> A “Scaffold decision” is a hard-coded allow, not a completed security check.</p>
      {snapshot && <p className="token-note">Token: <ExternalLink account={snapshot.config.token_id}>{snapshot.config.token_id}</ExternalLink> · {snapshot.config.token_decimals} decimals</p>}</div>
    <footer><span>NEAR holds the funds and records the outcome.</span><span>Public receipts only · Private decision records stay off-chain.</span></footer>
  </>;
}

