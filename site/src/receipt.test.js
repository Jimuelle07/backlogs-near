import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { formatHoldCountdown, reasonLabels } from './receipt.js';
import { accountUrl, DEFAULT_GUARDIAN } from './near.js';

// Use the site's JSX compiler while retaining node --test and the pinned React version.
const server = await createServer({ configFile: false, server: { middlewareMode: true, watch: null }, appType: 'custom' });
after(() => server.close());
const { ReceiptDetail } = await server.ssrLoadModule('/src/components/ReceiptDetail.jsx');
const example = JSON.parse(await readFile(new URL('../../schemas/examples/receipt.json', import.meta.url)));
const config = { token_decimals: 8, token_id: 'tusdc.demo.testnet' };
const nowMs = 1794528000000;
const nowNs = BigInt(nowMs) * 1_000_000n;

function render(receipt, held) {
  return renderToStaticMarkup(React.createElement(ReceiptDetail, {
    receipt, held, config, guardian: DEFAULT_GUARDIAN, onClose() {},
  }));
}

for (const [status, label, outcome, reasons] of [
  ['paid', 'Paid', 'allow', ['checks_passed']],
  // A payee budget can hold an allow verdict: status and outcome must stay distinct.
  ['held', 'Held', 'allow', ['unusual_for_agent', 'new_receiver']],
  ['refused', 'Refused', 'block', ['policy_violation', 'injection_high']],
  ['timed_out', 'Timed out', null, ['check_unavailable']],
]) {
  test(`receipt detail renders ${status} with exact fields and account links`, (t) => {
    t.mock.method(Date, 'now', () => nowMs);
    const receipt = { ...example, request_id: '9007199254740993', amount: '123456789012345678901',
      status, outcome, reasons, ...(outcome === null ? { record_sha256: null, checker_version: null } : {}) };
    const html = render(receipt, { release_at_ns: String(nowNs + 3_600_000_000_000n) });
    for (const value of [receipt.request_id, receipt.client_ref, receipt.receiver_id,
      receipt.input_sha256, receipt.requested_block, receipt.decided_block, label,
      '1,234,567,890,123.45678901', '123456789012345678901 base units',
      'aria-label="Copy input_sha256"', 'Close details', 'tabindex="-1"',
      accountUrl(DEFAULT_GUARDIAN), accountUrl(receipt.receiver_id), outcome ?? 'No verdict']) {
      assert.ok(html.includes(value), `Missing ${value}`);
    }
    for (const reason of reasons) {
      assert.ok(html.includes(`<code>${reason}</code>`));
      assert.ok(html.includes(reasonLabels[reason]));
    }
    if (outcome !== null) {
      assert.ok(html.includes(receipt.record_sha256));
      assert.ok(html.includes(receipt.checker_version));
      assert.ok(html.includes('aria-label="Copy record_sha256"'));
    } else {
      assert.match(html, /Not recorded/);
      assert.doesNotMatch(html, /aria-label="Copy record_sha256"/);
    }
    assert.equal(html.includes('Hold countdown'), status === 'held');
    if (status === 'held') assert.ok(html.includes('1h 0m 0s remaining'));
    assert.equal((html.match(/href=/g) ?? []).length, 2);
    assert.doesNotMatch(html, /probabilit|\/txns\//i);
  });
}

for (const [name, offsetNs, expected] of [
  ['before release', 61_000_000_000n, '0h 1m 1s remaining'],
  ['one nanosecond before release', 1n, '0h 0m 1s remaining'],
  ['exactly at release', 0n, 'releasing'],
  ['one nanosecond after release', -1n, 'releasing'],
  ['after release', -1_000_000_000n, 'releasing'],
]) {
  test(`hold countdown ${name}`, (t) => {
    t.mock.method(Date, 'now', () => nowMs);
    const releaseAtNs = String(nowNs + offsetNs);
    assert.equal(formatHoldCountdown(releaseAtNs), expected);
    const html = render({ ...example, status: 'held', outcome: 'hold' }, { release_at_ns: releaseAtNs });
    assert.ok(html.includes(expected));
  });
}

test('missing hold data is explicit and does not invent a release time', () => {
  const html = render({ ...example, status: 'held' });
  assert.match(html, /Release time unavailable/);
  assert.doesNotMatch(html, /remaining|releasing/);
});

test('every frozen reason code has a readable label', async () => {
  const schema = JSON.parse(await readFile(new URL('../../schemas/verdict.schema.json', import.meta.url)));
  for (const code of schema.$defs.ReasonCode.enum) {
    assert.equal(typeof reasonLabels[code], 'string', `Missing label for ${code}`);
  }
});
