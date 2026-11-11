export const DEFAULT_GUARDIAN = 'guardian-v2.jimuelle-firewall.testnet';
export const DEFAULT_RPC = 'https://test.rpc.fastnear.com';
export const PAGE_SIZE = 50;
export const STATUSES = ['paid', 'held', 'refused', 'timed_out', 'transfer_failed', 'paying'];

export function accountUrl(account) {
  return `https://testnet.nearblocks.io/address/${encodeURIComponent(account)}`;
}

// Never convert token base units or u64 request ids through floating-point numbers.
export function formatAmount(amount, decimals) {
  if (!/^\d+$/.test(amount) || !Number.isInteger(decimals) || decimals < 0 || decimals > 255) {
    throw new Error('Invalid token amount or decimals.');
  }
  const digits = BigInt(amount).toString().padStart(decimals + 1, '0');
  const whole = decimals ? digits.slice(0, -decimals) : digits;
  const fraction = decimals ? digits.slice(-decimals).replace(/0+$/, '') : '';
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (fraction ? `.${fraction}` : '');
}

export function sortReceipts(receipts) {
  return [...receipts].sort((a, b) => {
    const left = BigInt(a.request_id);
    const right = BigInt(b.request_id);
    return left > right ? -1 : left < right ? 1 : 0;
  });
}

function validateReceipt(receipt) {
  const uint = (value) => typeof value === 'string' && /^\d+$/.test(value);
  if (!receipt || !uint(receipt.request_id) || !uint(receipt.amount)
    || !uint(receipt.requested_block) || !uint(receipt.decided_block)
    || typeof receipt.client_ref !== 'string' || typeof receipt.receiver_id !== 'string'
    || !STATUSES.includes(receipt.status)
    || ![null, 'allow', 'hold', 'block'].includes(receipt.outcome)
    || !Array.isArray(receipt.reasons) || !receipt.reasons.every((reason) => typeof reason === 'string')) {
    throw new Error('The Guardian returned an unsupported receipt format.');
  }
  return receipt;
}

export function createReader({ guardian = DEFAULT_GUARDIAN, rpc = DEFAULT_RPC, fetcher = fetch } = {}) {
  if (!/^[a-z0-9._-]+\.testnet$/.test(guardian)) {
    throw new Error('Choose a named NEAR testnet Guardian account.');
  }
  if (new URL(rpc).protocol !== 'https:') throw new Error('The RPC URL must use HTTPS.');

  async function view(method, args, { signal, blockId } = {}) {
    const timeout = AbortSignal.timeout(12000);
    const response = await fetcher(rpc, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      body: JSON.stringify({
        jsonrpc: '2.0', id: method, method: 'query',
        params: {
          request_type: 'call_function', account_id: guardian, method_name: method,
          args_base64: btoa(JSON.stringify(args)),
          ...(blockId ? { block_id: blockId } : { finality: 'final' }),
        },
      }),
    });
    if (!response.ok) throw new Error(`RPC request failed (HTTP ${response.status}).`);
    const payload = await response.json();
    if (payload.error || payload.result?.error) {
      throw new Error(`The RPC could not read ${method}. Try refreshing or check the Guardian account.`);
    }
    if (!Array.isArray(payload.result?.result) || !payload.result.block_hash) {
      throw new Error('The RPC returned an unexpected response.');
    }
    const value = JSON.parse(new TextDecoder().decode(Uint8Array.from(payload.result.result)));
    return { value, blockId: payload.result.block_hash, blockHeight: payload.result.block_height };
  }

  return {
    guardian, rpc,
    async snapshot({ signal, pages = 1 } = {}) {
      const { value: config, blockId, blockHeight } = await view('get_config', {}, { signal });
      if (!Number.isInteger(config?.token_decimals) || config.token_decimals < 0
        || config.token_decimals > 255 || typeof config.token_id !== 'string') {
        throw new Error('The Guardian returned an unsupported token configuration.');
      }
      const receipts = [];
      let hasMore = false;
      for (let page = 0; page < pages; page++) {
        const { value } = await view('list_receipts', { from_index: page * PAGE_SIZE, limit: PAGE_SIZE }, { signal, blockId });
        if (!Array.isArray(value) || value.length > PAGE_SIZE) throw new Error('Invalid receipt page.');
        receipts.push(...value.map(validateReceipt));
        hasMore = value.length === PAGE_SIZE;
        if (!hasMore) break;
      }
      return { config, receipts: sortReceipts(receipts), hasMore, blockHeight, updatedAt: new Date() };
    },
  };
}
