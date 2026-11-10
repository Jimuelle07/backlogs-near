import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const example = JSON.parse(await readFile(new URL('../../schemas/examples/receipt.json', import.meta.url)));
const statuses = ['paid', 'held', 'refused', 'timed_out', 'transfer_failed', 'paying'];
const receipts = statuses.map((status, index) => ({
  ...example, request_id: String(index + 1), client_ref: `reference-${index + 1}`,
  receiver_id: `receiver-${index + 1}.testnet`, status,
  outcome: status === 'timed_out' ? null : status === 'held' ? 'hold' : status === 'refused' ? 'block' : 'allow',
}));

async function mockRpc(page, state = {}) {
  await page.route('https://test.rpc.fastnear.com/**', async (route) => {
    if (state.fail) return route.fulfill({ status: 503, body: 'RPC unavailable' });
    const { params } = route.request().postDataJSON();
    expect(params.request_type).toBe('call_function');
    const value = params.method_name === 'get_config'
      ? { token_id: 'tusdc.demo.testnet', token_decimals: 6 } : state.empty ? [] : receipts;
    await route.fulfill({ json: { result: {
      result: Array.from(new TextEncoder().encode(JSON.stringify(value))),
      block_hash: 'snapshot-block', block_height: 123,
    } } });
  });
}

test('filters, search, exact amounts and explorer links work without a wallet', async ({ page }) => {
  await mockRpc(page);
  await page.goto('/');
  await expect(page.locator('tbody tr')).toHaveCount(6);
  await expect(page.locator('tbody tr').first()).toContainText('#6');
  await page.getByRole('button', { name: 'Held', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody tr')).toContainText('18');
  await expect(page.locator('tbody tr')).toContainText('hold');
  await expect(page.getByRole('link', { name: 'receiver-2.testnet' })).toHaveAttribute('href', 'https://testnet.nearblocks.io/address/receiver-2.testnet');
  await page.getByLabel('Other receipt status').selectOption('timed_out');
  await expect(page.locator('tbody tr')).toContainText('No verdict');
  await page.getByRole('button', { name: 'All receipts' }).click();
  await page.getByRole('searchbox').fill('reference-3');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody tr')).toContainText('Refused');
  await page.getByRole('searchbox').fill('nonexistent');
  await expect(page.getByRole('heading', { name: 'No matching receipts' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await expect(page.locator('tbody tr')).toHaveCount(6);
});

test('failed refresh retains old data, exposes error and supports retry', async ({ page }) => {
  const state = {};
  await mockRpc(page, state);
  await page.goto('/');
  await expect(page.locator('tbody tr')).toHaveCount(6);
  await page.getByRole('checkbox').uncheck();
  state.fail = true;
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Showing the last successful read');
  await expect(page.locator('tbody tr')).toHaveCount(6);
  state.fail = false;
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.locator('tbody tr')).toHaveCount(6);
});

test('empty live result stays empty; RPC failure does not show mock receipts', async ({ page }) => {
  const state = { fail: true };
  await mockRpc(page, state);
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('Unable to load receipts');
  await expect(page.locator('tbody tr')).toHaveCount(0);
  state.fail = false;
  state.empty = true;
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('heading', { name: 'No receipts yet' })).toBeVisible();
});

test('mobile layout contains the table scroll and keeps filters usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockRpc(page);
  await page.goto('/');
  await expect(page.locator('tbody tr')).toHaveCount(6);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Paid', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page.screenshot({ path: 'test-results/receipts-mobile.png', fullPage: true });
});

test('live testnet receipts load in the browser through CORS', async ({ page }) => {
  test.skip(!process.env.LIVE_RPC, 'Set LIVE_RPC=1 to run a public network smoke check.');
  await page.goto('/');
  await expect(page.locator('tbody tr')).not.toHaveCount(0, { timeout: 20000 });
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.locator('tbody')).toContainText('Scaffold decision');
  await page.screenshot({ path: 'test-results/receipts-live.png', fullPage: true });
});
