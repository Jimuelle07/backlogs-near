# E1: live receipts panel

React + Vite, with public read-only NEAR JSON-RPC calls. No wallet, account key, server, or paid API is needed. This is the lane E component and its standalone shell; lane D can reuse `ReceiptsPanel` in the landing page.

Requires Node.js 22.12+ and npm. From the repo root:

1. `cd web` then `npm ci` → installs the locked frontend dependencies. In Windows PowerShell, use `npm.cmd` if script execution is disabled.
2. `npm run dev` → open the printed localhost URL. The panel reads `guardian-v2.jimuelle-firewall.testnet` through `https://test.rpc.fastnear.com`.
3. Check request IDs, amounts, status, verdict and reason codes; use the status filters and search by ID, client reference or receiver. Filters and counts apply to loaded receipts. Load more reads another 50 receipts; the contract's iteration order is not assumed to be chronological. Loaded rows are sorted by request ID descending.
4. Select an explorer link → opens the receiver or Guardian **account activity** on NEARBlocks testnet. The receipt view has no transaction hash, so the panel does not invent transaction-specific links.
5. `npm test` → verifies exact amount conversion, u64 sorting, read-only RPC calls, snapshot pagination, cancellation and error handling. `npm run build` → static site in `dist/`. `npm run preview` serves that build locally.

`npm run test:browser` runs browser checks for filters, search, explorer links, refresh failure/retry, empty states and mobile overflow. It uses installed Edge on Windows; on other systems install Playwright Chromium with `npx playwright install chromium`. Override the browser using `PLAYWRIGHT_CHANNEL` if needed. Set `LIVE_RPC=1` to include the browser's public RPC/CORS smoke check (PowerShell: `$env:LIVE_RPC='1'; npm.cmd run test:browser`). Test screenshots and reports are gitignored.

`node scripts/check-live.mjs` makes a read-only live smoke check and prints the returned receipt statuses. It needs internet but no credentials. Testnet state can change; the historical A1 receipts include two `paid` and one `timed_out` receipt, and `stub_allow` is a scaffold decision, not evidence that an attack was blocked.

Verified 2026-11-11: 8 unit tests passed; 5 Edge browser checks passed including live browser RPC/CORS access and a 390px mobile layout; production build passed. The live Guardian returned requests 3 and 2 as `paid` / `stub_allow`, and request 1 as `timed_out` with no verdict. Helena's frontend review remains pending.

Configuration is optional: copy `.env.example` to `.env.local`, edit the named testnet Guardian or HTTPS RPC endpoint and restart Vite. Vite only reads the `web/` environment; it does not load the repository's private `.env` or `.env.testnet`. All `VITE_*` values are public browser configuration. Never put a secret in them.

The panel reads `get_config` at finality `final`, then reads `list_receipts({from_index, limit: 50})` at that same block hash. Refresh re-reads the loaded pages at a new finalized block every 30 seconds while the tab is visible; it can be disabled. Failed refreshes retain the last successful read with an explicit error. It never substitutes sample receipts for live data. Amounts retain integer precision and use `get_config.token_decimals`; the token account is linked beneath the panel. The public RPC must support browser CORS.

Integration: import `ReceiptsPanel` from `src/ReceiptsPanel.jsx` when combining the lane D shell. Preserve its stable `reader` prop (created once with `createReader`), and import `src/styles.css` or adapt the styles to D1. E2 detail pages and countdowns, and E5 hosting/uptime, remain later tasks.

Third-party tools: React, React DOM, Vite, `@vitejs/plugin-react`, Playwright (browser tests); Google Fonts (DM Sans and Manrope, with system fallbacks); NEARBlocks account explorer; FastNEAR public testnet RPC. RPC wire format follows the [NEAR contract view documentation](https://docs.near.org/api/rpc/contracts).
