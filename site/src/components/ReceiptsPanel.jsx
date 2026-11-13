import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { formatAmount, STATUSES } from '../near.js';
import { reasonLabel, statusLabels as labels, statusTones } from '../receipt.js';
import { ExternalLink, ReceiptDetail } from './ReceiptDetail.jsx';
import { Ban, Check, Hourglass, ListChecks } from 'lucide-react';

const FILTER_ICONS = { all: ListChecks, paid: Check, held: Hourglass, refused: Ban };

export function ReceiptsPanel({ reader }) {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [request, setRequest] = useState({ pages: 1, revision: 0 });
  const [selectedId, setSelectedId] = useState(null);
  const active = useRef(false);
  const detailTrigger = useRef(null);
  const tableRegion = useRef(null);

  const closeDetail = useCallback(() => {
    setSelectedId(null);
    const target = detailTrigger.current?.isConnected ? detailTrigger.current : tableRegion.current;
    target?.focus();
  }, []);

  useEffect(() => {
    if (selectedId === null) return;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closeDetail();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [selectedId, closeDetail]);

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
  useEffect(() => {
    if (selectedId !== null && !visible.some((receipt) => receipt.request_id === selectedId)) {
      closeDetail();
    }
  }, [visible, selectedId, closeDetail]);

  function toggleDetail(receipt, event) {
    if (selectedId === receipt.request_id) return closeDetail();
    detailTrigger.current = event.currentTarget.closest('tr').querySelector('.receipt-trigger');
    setSelectedId(receipt.request_id);
  }
  const counts = Object.fromEntries(STATUSES.map((status) => [status, receipts.filter((r) => r.status === status).length]));
  const refresh = () => setRequest((previous) => ({ ...previous, revision: previous.revision + 1 }));

  return <section className="receipts-panel" aria-labelledby="payment-receipts-title">
      <div className="panel-heading"><span className="win-dots" aria-hidden="true"><i /><i /><i /></span><h3 id="payment-receipts-title">Payment receipts</h3>
        <div className="refresh-controls"><label className="auto-refresh"><input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} /> Auto-refresh · 30s</label>
          <button className="refresh-button" onClick={refresh} disabled={busy}><span aria-hidden="true" className={busy ? 'spin' : ''}>↻</span> {busy ? 'Reading…' : 'Refresh'}</button></div></div>

      <p className="panel-source">NEAR testnet · Read only · No wallet needed<br />Guardian: <ExternalLink account={reader.guardian}>{reader.guardian}</ExternalLink></p>
      <p className="scaffold-note"><code>stub_allow</code> (Scaffold decision) is a hard-coded allow.</p>

      <div className="stats" aria-label="Counts for loaded receipts">
        {[['Loaded receipts', snapshot ? receipts.length : '—'], ['Paid', snapshot ? counts.paid : '—'], ['Held', snapshot ? counts.held : '—'], ['Refused', snapshot ? counts.refused : '—']].map(([label, value], index) =>
          <div className="stat" key={label}><span>{label}</span><strong className={`stat-${index}`}>{value}</strong><small>{index === 0 ? 'From the Guardian' : 'In loaded receipts'}</small></div>)}
      </div>

      <div className="toolbar"><div className="filters" role="group" aria-label="Filter receipt status">
        {['all', 'paid', 'held', 'refused'].map((status) => { const Icon = FILTER_ICONS[status]; return <button key={status} aria-pressed={filter === status} className={filter === status ? 'selected' : ''} onClick={() => setFilter(status)}><Icon size={15} aria-hidden="true" />{status === 'all' ? 'All receipts' : labels[status]}</button>; })}
        <label className="sr-only" htmlFor="other-status">Other receipt status</label>
        <select id="other-status" value={['timed_out', 'transfer_failed', 'paying'].includes(filter) ? filter : ''} onChange={(event) => setFilter(event.target.value || 'all')}>
          <option value="">Other statuses</option>{['timed_out', 'transfer_failed', 'paying'].map((status) => <option key={status} value={status}>{labels[status]}</option>)}
        </select></div>
        <label className="search"><span aria-hidden="true">⌕</span><span className="sr-only">Search request ID, reference, or receiver</span><input type="search" placeholder="Search ID or receiver" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      </div>

      {error && <div role="alert" className="error"><strong>{snapshot ? 'Live refresh unavailable.' : 'Unable to load receipts.'}</strong> {error} {snapshot && 'Showing the last successful read.'}<button onClick={refresh} disabled={busy}>Try again</button></div>}
      <div className="table-wrap" ref={tableRegion} tabIndex="0" role="region" aria-label="Payment receipts table" aria-busy={busy}>
        <table><caption className="sr-only">Public Guardian receipts. Amounts use the token decimals configured on the Guardian. Explorer links open account activity.</caption>
          <thead><tr><th scope="col">Request / reference</th><th scope="col">Receiver</th><th scope="col" className="amount">Amount</th><th scope="col">Status / verdict</th><th scope="col">Reason</th><th scope="col"><span className="sr-only">Explorer</span></th></tr></thead>
          <tbody>{visible.map((receipt) => <React.Fragment key={receipt.request_id}><tr className="receipt-row" onClick={(event) => {
            if (!event.target.closest('a, button')) toggleDetail(receipt, event);
          }}>
            <td data-label="Request / reference"><button className="request-id receipt-trigger" aria-expanded={selectedId === receipt.request_id}
              aria-controls={selectedId === receipt.request_id ? `receipt-detail-${receipt.request_id}` : undefined}
              aria-label={`Details for request ${receipt.request_id}`} onClick={(event) => toggleDetail(receipt, event)}>#{receipt.request_id}</button><span className="secondary reference">{receipt.client_ref}</span></td>
            <td data-label="Receiver"><ExternalLink account={receipt.receiver_id} className="receiver">{receipt.receiver_id}</ExternalLink><span className="secondary">Block {receipt.decided_block}</span></td>
            <td data-label="Amount" className="amount"><strong>{formatAmount(receipt.amount, snapshot.config.token_decimals)}</strong><span className="secondary" title={snapshot.config.token_id}>tokens</span></td>
            <td data-label="Status / verdict"><span className={`vchip ${statusTones[receipt.status]}`}>{labels[receipt.status]}</span><span className="secondary verdict">{receipt.outcome ?? 'No verdict'}</span></td>
            <td data-label="Reason" className="reasons">{receipt.reasons.length ? receipt.reasons.map((reason, index) => <span key={`${reason}-${index}`} title={reason} className={reason === 'stub_allow' ? 'stub-reason' : ''}>{reasonLabel(reason)}</span>) : <span className="secondary">No reason recorded</span>}</td>
            <td data-label="Explorer"><ExternalLink account={reader.guardian} aria-label={`View Guardian activity for request ${receipt.request_id}`}><span className="explorer-label">Explorer</span></ExternalLink></td>
          </tr>{selectedId === receipt.request_id && <tr className="receipt-detail-row"><td colSpan={6}>
            <ReceiptDetail receipt={receipt} config={snapshot.config} guardian={reader.guardian}
              held={snapshot.held.find((entry) => entry.request_id === receipt.request_id)} onClose={closeDetail} />
          </td></tr>}</React.Fragment>)}</tbody>
        </table>
        {!snapshot && !error && <div className="empty" role="status"><span className="loading-mark" aria-hidden="true">◌</span><h4>Reading the Guardian…</h4><p>Fetching public payment receipts from testnet.</p></div>}
        {snapshot && visible.length === 0 && <div className="empty"><span aria-hidden="true">≡</span><h4>{receipts.length ? 'No matching receipts' : 'No receipts yet'}</h4><p>{receipts.length ? 'Try another status or search term. Filters apply to loaded receipts.' : 'Receipts will appear here after the Guardian records a payment request.'}</p>{receipts.length > 0 && <button onClick={() => { setFilter('all'); setSearch(''); }}>Clear filters</button>}</div>}
      </div>

      <div className="panel-footer"><p role="status">{snapshot ? <>{visible.length} of {receipts.length} loaded receipts <span aria-hidden="true">·</span> Updated {snapshot.updatedAt.toLocaleTimeString()} <span aria-hidden="true">·</span> Block {snapshot.blockHeight}</> : error ? 'No live data available' : 'Connecting to testnet…'}</p>
        {snapshot?.hasMore && <button disabled={busy} onClick={() => setRequest((previous) => ({ pages: previous.pages + 1, revision: previous.revision + 1 }))}>Load more receipts ↓</button>}</div>
      {snapshot && <p className="token-note">Token: <ExternalLink account={snapshot.config.token_id}>{snapshot.config.token_id}</ExternalLink> · {snapshot.config.token_decimals} decimals</p>}
    </section>;
}
