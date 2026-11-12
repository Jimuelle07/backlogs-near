import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { accountUrl, createReader, DEFAULT_GUARDIAN, formatAmount, sortReceipts } from './near.js';

const example = JSON.parse(await readFile(new URL('../../schemas/examples/receipt.json', import.meta.url)));
const config = { token_decimals: 6, token_id: 'tusdc.demo.testnet' };
const reply = (value) => new Response(JSON.stringify({ result: {
  result: Array.from(new TextEncoder().encode(JSON.stringify(value))), block_hash: 'snapshot-block', block_height: 123,
} }));

test('amount display preserves base-unit precision, including u128 values', () => {
  assert.equal(formatAmount('18000000', 6), '18');
  assert.equal(formatAmount('47500000', 6), '47.5');
  assert.equal(formatAmount('1', 6), '0.000001');
  assert.equal(formatAmount('1000', 0), '1,000');
  assert.equal(formatAmount('340282366920938463463374607431768211455', 6), '340,282,366,920,938,463,463,374,607,431,768.211455');
  assert.throws(() => formatAmount('1e6', 6));
  assert.throws(() => formatAmount('18', -1));
});

test('request ids sort precisely above the JavaScript safe integer range', () => {
  const input = [{ request_id: '9007199254740992' }, { request_id: '9007199254740993' }, { request_id: '1' }];
  assert.deepEqual(sortReceipts(input).map((r) => r.request_id), ['9007199254740993', '9007199254740992', '1']);
  assert.equal(input[0].request_id, '9007199254740992');
});

test('pagination uses read-only calls at one finalized snapshot and contract limit 50', async () => {
  const calls = [];
  const first = Array.from({ length: 50 }, (_, index) => ({ ...example, request_id: String(index + 1) }));
  const reader = createReader({ fetcher: async (_, options) => {
    const request = JSON.parse(options.body);
    calls.push(request);
    assert.equal(request.method, 'query');
    assert.equal(request.params.request_type, 'call_function');
    assert.equal(request.params.account_id, DEFAULT_GUARDIAN);
    if (request.params.method_name === 'get_config') return reply(config);
    const args = JSON.parse(atob(request.params.args_base64));
    assert.equal(args.limit, 50);
    return reply(args.from_index === 0 ? first : [{ ...example, request_id: '51' }]);
  } });
  const snapshot = await reader.snapshot({ pages: 2 });
  assert.equal(snapshot.receipts.length, 51);
  assert.equal(snapshot.receipts[0].request_id, '51');
  assert.equal(snapshot.hasMore, false);
  assert.equal(calls[0].params.finality, 'final');
  assert.equal(calls[1].params.block_id, 'snapshot-block');
  assert.equal(calls[2].params.block_id, 'snapshot-block');
  assert.equal('finality' in calls[1].params, false);
  assert.deepEqual(JSON.parse(atob(calls[2].params.args_base64)), { from_index: 50, limit: 50 });
});

test('a full page offers more; an empty contract stops pagination', async () => {
  const reader = createReader({ fetcher: async (_, options) => {
    const { method_name } = JSON.parse(options.body).params;
    return reply(method_name === 'get_config' ? config : Array(50).fill(example));
  } });
  assert.equal((await reader.snapshot()).hasMore, true);
  let calls = 0;
  const empty = createReader({ fetcher: async (_, options) => {
    calls++;
    return reply(JSON.parse(options.body).params.method_name === 'get_config' ? config : []);
  } });
  const result = await empty.snapshot({ pages: 3 });
  assert.equal(result.hasMore, false);
  assert.equal(result.receipts.length, 0);
  assert.equal(calls, 2);
});

test('HTTP, RPC, contract and malformed data failures cannot become empty successes', async () => {
  for (const response of [
    () => new Response('', { status: 429 }),
    () => new Response(JSON.stringify({ error: { message: 'unavailable' } })),
    () => new Response(JSON.stringify({ result: { error: 'MethodNotFound' } })),
    () => new Response('{}'),
    () => reply({ token_decimals: -1, token_id: 'token.testnet' }),
  ]) {
    await assert.rejects(createReader({ fetcher: async () => response() }).snapshot());
  }
  const malformed = createReader({ fetcher: async (_, options) => reply(
    JSON.parse(options.body).params.method_name === 'get_config' ? config : [{ ...example, amount: 18000000 }],
  ) });
  await assert.rejects(malformed.snapshot(), /unsupported receipt/);
});

test('all frozen statuses and nullable verdicts are accepted', async () => {
  const receipts = ['paid', 'held', 'refused', 'timed_out', 'transfer_failed', 'paying'].map((status, index) => ({
    ...example, request_id: String(index + 1), status, outcome: status === 'timed_out' ? null : 'allow',
  }));
  const reader = createReader({ fetcher: async (_, options) => {
    const method = JSON.parse(options.body).params.method_name;
    return reply(method === 'get_config' ? config : method === 'get_held' ? [] : receipts);
  } });
  assert.equal((await reader.snapshot()).receipts.length, 6);
});

test('get_held pages and list_receipts are pinned to the same finalized snapshot block', async () => {
  const calls = [];
  const heldReceipt = { ...example, status: 'held', outcome: 'allow' };
  const held = { request_id: example.request_id, receiver_id: example.receiver_id,
    amount: example.amount, release_at_ns: '1794528000000000001' };
  const firstHeldPage = Array.from({ length: 50 }, (_, index) => ({ ...held, request_id: String(index + 2) }));
  const reader = createReader({ fetcher: async (_, options) => {
    const { params } = JSON.parse(options.body);
    calls.push(params);
    const args = JSON.parse(atob(params.args_base64));
    if (params.method_name === 'get_config') return reply(config);
    assert.equal(params.block_id, 'snapshot-block');
    assert.equal('finality' in params, false);
    if (params.method_name === 'list_receipts') return reply([heldReceipt]);
    assert.equal(params.method_name, 'get_held');
    assert.equal(args.limit, 50);
    return reply(args.from_index === 0 ? firstHeldPage : [held]);
  } });
  const snapshot = await reader.snapshot();
  assert.equal(snapshot.blockId, 'snapshot-block');
  assert.equal(snapshot.held.length, 51);
  assert.deepEqual(snapshot.held.find((entry) => entry.request_id === example.request_id), held);
  assert.deepEqual(calls.map((call) => call.method_name), ['get_config', 'list_receipts', 'get_held', 'get_held']);
  assert.deepEqual(JSON.parse(atob(calls[3].args_base64)), { from_index: 50, limit: 50 });
  await assert.rejects(reader.getHeld(), /snapshot block hash/);
});

test('held payment RPC errors, malformed pages and non-string timestamps reject the snapshot', async () => {
  const heldReceipt = { ...example, status: 'held' };
  for (const response of [
    () => new Response('', { status: 503 }),
    () => reply({ release_at_ns: '1794528000000000000' }),
    () => reply([{ request_id: '1', receiver_id: example.receiver_id, amount: example.amount,
      release_at_ns: 1794528000000000000 }]),
  ]) {
    const reader = createReader({ fetcher: async (_, options) => {
      const method = JSON.parse(options.body).params.method_name;
      if (method === 'get_held') return response();
      return reply(method === 'get_config' ? config : [heldReceipt]);
    } });
    await assert.rejects(reader.snapshot());
  }
});

test('caller cancellation reaches fetch', async () => {
  const controller = new AbortController();
  controller.abort();
  const reader = createReader({ fetcher: async (_, options) => {
    options.signal.throwIfAborted();
  } });
  await assert.rejects(reader.snapshot({ signal: controller.signal }), { name: 'AbortError' });
});

test('configuration stays on testnet and explorer URLs point to accounts', () => {
  assert.throws(() => createReader({ guardian: 'guardian.near' }), /testnet/);
  assert.throws(() => createReader({ rpc: 'http://example.com' }), /HTTPS/);
  assert.equal(accountUrl('hostco.demo.testnet'), 'https://testnet.nearblocks.io/address/hostco.demo.testnet');
});
