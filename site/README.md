# Landing page (lanes D and E)

Static site for the project: problem, how it works, NEAR's role, Jev's role, safety layers, demo, results, receipts, links. Brand from the "Attested" branding artifact.

## Stack and host (decided in D1, shared by lanes D and E)

Exact versions are pinned in `package.json`; keep them in step with the branding artifact.

| Layer | Choice |
| --- | --- |
| Core | React 18.3.1 + react-dom, plain JavaScript (JSX), no TypeScript |
| Build | Vite 5.4.21 with @vitejs/plugin-react 4.7.0; vite-plugin-singlefile 2.3.4 for a one-file build (`npm run build:single`) |
| 3D | three 0.169.0, @react-three/fiber 8.18.0, @react-three/drei 9.122.0 (three-stdlib 2.36.1 for the ASCII renderer) |
| Motion | GSAP 3.15.1 + ScrollTrigger; Lenis 1.3.27 smooth scroll, driven by GSAP's ticker |
| Canvas | Dot texture, glow and Morse field: plain 2D canvas, no library |
| UI | lucide-react 1.71.0 icons; plain CSS with variables, grid and flexbox, no Tailwind |
| Fonts | Geist, Geist Mono, JetBrains Mono (Google Fonts) |
| Host | Cloudflare Pages, direct upload: free, no sleep, works while the repo is private |

Rules carried from the artifact: honour `prefers-reduced-motion` (no smooth scroll, intro animations or auto-advancing tabs), stop 3D scenes and canvases when off-screen, label buttons, tabs and meters for screen readers.

The skeleton uses only React, lucide-react and CSS so far; the 3D and motion packages are installed for the sections ported next (D2, D6). The live receipts panel (E1) reads Guardian views over the public testnet RPC with plain `fetch`, no wallet.

`npm audit` flags esbuild through Vite 5: it affects only the local dev server, not the built site.

## Commands

From `site/`:

```
npm ci
npm test              # node --test src/*.test.js
npm run dev       # http://localhost:5173
npm run build         # build to site/dist
npm run build:single  # one self-contained dist/index.html
npm run preview   # serve site/dist
```

## Live receipts (E1/E2)

Open `/#receipts` to read `guardian-v2.jimuelle-firewall.testnet`. Public settings live in `src/config.js`: `GUARDIAN_ID` and `NEAR_RPC_URL` (FastNEAR testnet by default). The app creates one reader and passes it to the panel; no wallet, keys or backend environment files are used.

Each refresh reads `get_config` and pins all `list_receipts` pages to the same finalized block. When loaded receipts include holds, all `get_held` pages use that block hash too. Amounts use `get_config.token_decimals` without floating-point conversion. Filters and search apply to loaded receipts; load more to extend them. Auto-refresh runs every 30 seconds while the page is visible and can be disabled.

An RPC failure shows an error and retry button, retaining the last successful read when available. It never substitutes sample receipts. `stub_allow` is labelled as a hard-coded scaffold decision. Explorer links point to account activity; receipts contain no transaction hash.

Click a receipt row, or focus its request button and press Enter or Space, to open its inline details. Close with Escape or Close details; focus returns to the request button. Details show every receipt field, labelled reason codes, copy buttons for recorded hashes, and receiver and Guardian account links. Nullable fields are labelled explicitly, including “No verdict”. Held receipts count down from the snapshot's `release_at_ns` using integer nanoseconds and the device clock; at or past release they show “releasing”. Refresh reads the settlement status; the site does not release funds.

Run `npm ci`, `npm test` and `npm run build` to verify. For a mobile check, open `#receipts` at 390px wide and check the controls and table without horizontal page scrolling.

## Deploy (human, needs a Cloudflare account)

```
npm run build
npx wrangler pages deploy dist --project-name <name>
```

The first run asks for a Cloudflare login and creates the project. Any static host works: `dist/` uses relative paths.

## Where things live

- `src/config.js`: project name, status note, Guardian id, RPC URL, explorer, caps, repo URL. Edit here first.
- `src/App.jsx`: all sections, in page order.
- `src/components/ReceiptsPanel.jsx` and `ReceiptDetail.jsx`: live receipts and inline details in `#receipts`.
- `src/receipt.js`: shared status/reason labels and integer hold countdown formatting.
- `src/near.js`: read-only RPC reader and exact token amount formatting; `src/near.test.js` tests it against the receipt schema example.
- `src/styles.css`: brand tokens (`:root`) and components.

- `src/results.js`: Results section rows, read at build time from `../docs/results/results.json` and `redteam-results.json` (the dev server is allowed to read `..` in `vite.config.js`); `src/results.test.js` checks them against the README Results table.

Open items: project name (team lead decides; set `PROJECT_NAME`), repo URL (set `REPO_URL` once public), demo video (D3/D6).
