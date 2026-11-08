# AGENTS.md — operating guide for agents in this repo

## 1. What this repo is

- Entry for **NEAR HACKATHON** (https://nearhackathon.com).
- **Project status: idea not chosen.** Candidates: Bet A "Thousand-Agent Market", Bet B "Intent Notary", Bet C "Market Town, Live", and the Thesis data play "NEAR, Labeled". See [tracks ranked, Part 6](docs/hackathon-context/near_hackathon_tracks_ranked.md) and the summary in [docs/index.md](docs/index.md#choosing-the-project).
- When the project is chosen, update the status line above and [docs/build/prd.md](docs/build/prd.md) in the same change.

## 2. Read first

1. [docs/index.md](docs/index.md): map of every doc.
2. [docs/hackathon-context/HACKATHON.md](docs/hackathon-context/HACKATHON.md): official agent instructions and rules (snapshot).
3. [docs/build/prd.md](docs/build/prd.md), then [docs/build/sdd.md](docs/build/sdd.md), then [docs/build/system-design.md](docs/build/system-design.md).

Before any submission step, re-read the live https://nearhackathon.com/HACKATHON.md: rules and dates may change, and the live file wins over the snapshot.

## 3. Deadlines (UTC)

| Milestone | When (UTC) | Source |
| --- | --- | --- |
| Hackathon start | 2026-11-01T00:00Z | [HACKATHON.md](docs/hackathon-context/HACKATHON.md) Facts |
| Code window baseline | from the 2026-10-19 announcement; earlier commits are baseline | HACKATHON.md Q-001 |
| Dev end / submission deadline / repo must be public | **2026-11-14T23:59Z** (Sat 15 Nov 07:59 PHT) | HACKATHON.md Facts |
| Judging starts | 2026-11-16T00:00Z | HACKATHON.md Facts |
| Results announced by | 2026-11-18T23:59Z | HACKATHON.md Facts |
| Hosted demo (if any) stays up | through 2026-11-18, ideally 2026-11-25 | HACKATHON.md Q-012 |
| Internal target | submit Fri 14 Nov PHT, not on the last morning | [tracks ranked](docs/hackathon-context/near_hackathon_tracks_ranked.md) Part 7 item 8 |

## 4. Human-only actions

Never do any of these without the human's explicit confirmation ([HACKATHON.md](docs/hackathon-context/HACKATHON.md), "Never without the human's explicit confirmation"):

- Send the submission. Print the full JSON payload first and wait for a yes.
- Post anything on X or any other network on the human's behalf.
- Make the repository public, push, or force-push.
- Sign transactions, spend tokens, or deploy to mainnet.
- Commit secrets.

Only the human decides these fields (HACKATHON.md, "What the human decides"). Never guess, generate, or placeholder them:

- project name, team lead's name, contact email, team size
- tracks
- NEAR mainnet account for the prize payout (never create or invent one)
- public repository URL, public demo post URL
- "what they built" idea text
- consent to the contact notice

One submission per repository. Mistakes are fixed by the human at https://nearhackathon.com/request-changes, never by submitting again.

## 5. Stack (decided)

| Layer | Choice |
| --- | --- |
| Smart contract | Rust with `near-sdk` (near-sdk-rs), built with `cargo near` _(unverified — confirm in https://docs.near.org/ before coding)_ |
| App runtime | TypeScript on Node.js (LTS) |
| Dashboard / UI | Next.js |
| Backend logic (orchestrator, DecisionClient, NEAR client) | Node TS package |
| NEAR JS client | `near-api-js` _(unverified — confirm the current recommended JS SDK at https://docs.near.org/ before coding)_ |
| Decision model | TypeSafe Jev via `@typesafe-ai/sdk` |
| LLM for text output and decision fallback | NEAR AI Cloud (https://cloud.near.ai) |
| Package manager | pnpm workspaces |

Rationale and module boundaries: [docs/build/sdd.md](docs/build/sdd.md).

## 6. Planned repo layout

Not yet scaffolded. Created when the project is chosen.

```
contract/          Rust near-sdk contract (cargo workspace member)
packages/core/     TS: DecisionClient, policy gates, NEAR client, decision log
apps/web/          Next.js dashboard + API routes
scripts/           eval / calibration / demo-seed scripts (TS)
docs/              see docs/index.md
```

No build/test commands exist yet. Add them here (install, build, test, run demo) in the same change that scaffolds the code.

## 7. Integration rules

- **Jev is the decision brain; NEAR is load-bearing** (custody, limits, settlement, audit log). Say so in the README's first paragraph. Source: [tracks ranked](docs/hackathon-context/near_hackathon_tracks_ranked.md) Part 1 limit 4, Part 7 item 2.
- **All Jev calls go through the `DecisionClient` interface** in `packages/core`, with a fallback implementation so a TypeSafe outage never blocks the demo. Source: tracks ranked Part 7 item 1.
- **Confidence gates scale with stakes:** high confidence acts, medium asks/confirms, low refuses/escalates. Reads may run at ≥0.5; money movement needs ≥0.9. Source: tracks ranked Part 1, "The confidence pattern".
- **A Jev gate alone is not a security boundary.** Enforce hard limits in the contract or keys (function-call access keys, amount caps). Source: [arxiv papers](docs/tools/arxiv_papers_for_build.md) TL;DR #1 JevBreak (2611.03759) and #2 (2610.12292).
- **Write policies as examples plus counterexamples.** Source: arxiv papers TL;DR #3 (2611.02155).
- **Log every decision** (inputs hash, question, answer, probabilities, confidence, action taken) to a public or auditable log. Source: tracks ranked Part 7 item 3.
- **NEAR network: testnet by default.** NEAR Intents has no testnet: use mainnet `dry: true` quotes only. Any real mainnet transaction needs human confirmation. Source: HACKATHON.md Q-007, Q-008, Q-010.

## 8. Secrets

- Keys live only in environment variables. `.env.example` lists every variable; `.env` is gitignored.
- Never commit the submission payload: it contains personal data (HACKATHON.md §3). `submission*.json` is gitignored.

## 9. README rules for judges

Claude Code and Codex screen every project before the human jury (HACKATHON.md Q-017). The README must contain:

- what it is, the problem, and NEAR's concrete role
- numbered "do X → see Y" steps, and a dry-run mode with sample data
- every third-party library/tool, Jev included (Q-005)
- disclosures for Q-001 / Q-002 / Q-015 where they apply
- no marketing copy

## 10. Docs upkeep

- When a design decision changes, update the matching `docs/build/*` file in the same change.
- `docs/hackathon-context/` and `docs/tools/` are dated research snapshots (8 Nov 2026). Do not edit them.
- Verify numbers against primary sources before quoting them in the README; the arXiv entries are preprints paraphrased from abstracts.
- Every project-specific gap is marked `TBD(project)`; find them with `grep -rn "TBD(project)" docs README.md`.
