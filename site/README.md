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
npm install
npm run dev       # http://localhost:5173
npm run build         # build to site/dist
npm run build:single  # one self-contained dist/index.html
npm run preview   # serve site/dist
```

## Deploy (human, needs a Cloudflare account)

```
npm run build
npx wrangler pages deploy dist --project-name <name>
```

The first run asks for a Cloudflare login and creates the project. Any static host works: `dist/` uses relative paths.

## Where things live

- `src/config.ts`: project name, status note, Guardian id, RPC URL, explorer, caps, repo URL. Edit here first.
- `src/App.tsx`: all sections, in page order.
- `src/components/ReceiptsPanel.tsx`: slot for E1 (live receipts).
- `src/styles.css`: brand tokens (`:root`) and components.

Open items: project name (team lead decides; set `PROJECT_NAME`), repo URL (set `REPO_URL` once public), demo video (D3/D6), results table from `results.json` (E3/D4), architecture diagram (D2).
