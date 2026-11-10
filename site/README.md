# Landing page (lanes D and E)

Static site for the project: problem, how it works, NEAR's role, Jev's role, safety layers, demo, results, receipts, links. Brand from the "Attested" branding artifact.

## Stack and host (decided in D1)

| Choice | Why |
| --- | --- |
| Vite + React 18 + TypeScript | Same stack as the branding artifact, so its sections port over; builds to plain static files |
| lucide-react | Icons, as in the artifact |
| Cloudflare Pages (direct upload) | Free, no sleep, works while the GitHub repo is private; easy to keep up through 2026-11-25 |

No wallet and no keys: the live receipts panel (E1) reads Guardian views over the public testnet RPC with plain `fetch`.

## Commands

From `site/`:

```
npm install
npm run dev       # http://localhost:5173
npm run build     # type-check + build to site/dist
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
