# NEAR HACKATHON — Full Web Data Capture

- **Captured:** Sunday, 8 November 2026 (Asia/Manila), during the development phase
- **Primary source:** https://nearhackathon.com/ (read live in Chrome), plus its linked pages and files
- **Other pages read:** `nearhackathon.com/HACKATHON.md`, `nearhackathon.com/request-changes`, `nearhackathon.com/api/projects` (public project feed), GitHub repo `nearai/near-hackathon-prompt-examples` (README, 00-setup, SUBMITTING, all 13 track files), NEAR blog posts, Devpost galleries of past NEAR hackathons, news coverage
- **Note on wording:** facts, numbers, names, links and rules are recorded exactly; longer prose from the sources is restated in my own words rather than copied.

---

## 1. Event identity

| Item | Value |
|---|---|
| Official name | NEAR HACKATHON (site logo shorthand: "HCKTHN") |
| Campaign title used by NEAR | "NEAR HACKATHON: Build Beyond Boundaries" |
| Browser title of site | "NEAR HACKATHON — Build what's next" |
| Hero line | The era of programmable money starts here — "Make it real on NEAR" |
| Sub-tagline | Autonomous payments. Intelligent agents. Money with a mind of its own. |
| Scrolling marquee slogans | BUILD WITHOUT PERMISSION ✳ THINK BEYOND THE CHAIN ✳ MAKE YOUR SIGNAL MATTER |
| Footer line | BUILT FOR BUILDERS |
| Organizer / provider | NEAR (NEAR Protocol / NEAR Foundation); listings name NEAR Foundation as provider |
| Format | Fully online, two-week build; no in-person event; no travel |
| Registration | None. No sign-up before the final submission; the submission *is* the registration |
| Entry fee | None mentioned |
| Website | https://nearhackathon.com |
| Agent instruction file | https://nearhackathon.com/HACKATHON.md |
| Change-request page | https://nearhackathon.com/request-changes |
| Submission form | https://nearhackathon.com/#apply |
| Submission API | `POST https://nearhackathon.com/api/applications` |
| Public projects feed | `GET https://nearhackathon.com/api/projects?page=N` (8 per page) |
| Official X | https://x.com/NEARProtocol (blog also says follow **@NEAR_hckthn** for updates) |
| Required tags on demo post | @NEARProtocol and #NEARHackathon (optional: @NearLegion, @NearBuilders) |
| Announcement post | https://x.com/nearprotocol/status/2112257967818997891 (19 Oct 2026) |
| Announcement blog | https://www.near.org/blog/near-hackathon-build-beyond-boundaries (19 Oct 2026) |

**Site navigation sections:** Tracks (#tracks) · Timeline (#timeline) · Projects (#projects) · Judges (#judges) · Ecosystem (#partners) · Toolkit (#resources) · Submit (#apply) · FAQ ("07 / Frequent Queries")

**Site section numbering:** 00 Hackathon Info · 01 Build Directions · 02 Execution Plan · 03 The People · 04 The Ecosystem · 05 Builder Toolkit · 06 Final Submission · 07 Frequent Queries

---

## 2. Timeline (all UTC)

| Milestone | Date / time |
|---|---|
| Announcement (code written from here counts) | 19 Oct 2026 |
| Hackathon starts / submissions open | 1 Nov 2026 · 00:00 (`2026-11-01T00:00:00Z`) |
| Development phase | 1–14 Nov 2026 |
| Development ends = submission deadline | 14 Nov 2026 · 23:59 (`2026-11-14T23:59:00Z`) |
| Judging starts | 16 Nov 2026 · 00:00 |
| Judging & results window | 16–18 Nov 2026 |
| Results announced by | 18 Nov 2026 · 23:59 |
| Keep hosted demos up until | at least 18 Nov 2026, ideally 25 Nov 2026 |
| Prize payout | single payment, within 30 days of results |

Beijing-time equivalents reported by Lookonchain/Gate: runs 08:00 1 Nov → 07:59 15 Nov; results by 07:59 19 Nov.
Manila time (UTC+8) is the same as Beijing: deadline = **15 Nov 2026, 07:59 PHT**.

Site shows a live "DEVELOPMENT ENDS IN" countdown (days/hours/min/sec).

---

## 3. Prizes

Total pool **$250,000**, fixed in USD, **paid in NEAR** to the NEAR account given in the submission. One grand prize overall, plus 1st/2nd/3rd in each of the 13 tracks.

| Prize | Amount | Count | Total |
|---|---|---|---|
| Grand prize | $55,000 | 1 | $55,000 |
| 1st place | $10,000 | 13 | $130,000 |
| 2nd place | $3,000 | 13 | $39,000 |
| 3rd place | $2,000 | 13 | $26,000 |
| **Total** | | **40 awards** | **$250,000** |

- Payout: one payment, no vesting, within 30 days of results (Q-016).
- NEAR's X post called it "$250K+".
- **RHEA Finance** announced (30 Oct 2026) that $RHEA tokens were allocated to the prize pool for cross-chain DeFi built with the RHEA X Chain SDK (powered by NEAR Intents); NEAR reposted it.

---

## 4. Live submission statistics (from the site's public feed at capture time)

- **Submitted projects counter on site:** 268
- **Directory pages:** 34 (8 per page), oldest submissions first
- Projects may select several tracks, so track counts add up to more than 268.

| Track id | Track | Projects selecting it |
|---|---|---|
| security | AI Security & Defense | 140 |
| agents | Agent Economy | 130 |
| realworld | Real-World Money | 56 |
| business | Autonomous Business | 46 |
| open | Open Innovation | 45 |
| privacy | Privacy & Private AI | 44 |
| defi | Unstoppable DeFi | 40 |
| thesis | Investment Thesis | 24 |
| nfts | NFTs That Do Something | 20 |
| swarms | AI Swarms | 19 |
| games | Games With Real Economies | 17 |
| social | Social Money | 15 |
| memecoins | Memecoins With Mechanics | 10 |

Full project list is in Section 16.

---

## 5. The 13 tracks — full detail

Each track on the site has: a code like `[ 01 / DFI ]`, a name, a tagline, a description, three or four hint tags, a "Build in this track" button and an "AI prompt" link to the matching file in https://github.com/nearai/near-hackathon-prompt-examples. Hints and named protocols are **suggestions, not requirements** (Q-011).

### 01 / DFI — Unstoppable DeFi (`defi`)
- **Tagline:** Markets that never close
- **Brief:** exchanges, perps, lending, vaults and trading agents settling cross-chain via NEAR Intents; deep liquidity, no custodian, no off-switch.
- **Hints:** TRADING · NEAR INTENTS · CHAIN SIGNATURES
- **Prompt:** https://github.com/nearai/near-hackathon-prompt-examples/blob/main/tracks/01-defi.md
- **Start-here links:** 1Click API quickstart (docs.near-intents.org/integration/distribution-channels/1click-api/quickstart) · Chain Signatures getting started (docs.near.org/chain-abstraction/chain-signatures/getting-started) · Rhea guide (guide.rhea.finance) · Agent API overview (docs.agentsonintents.com/integration/agent-api/overview) · Aurora Intents (intents.aurora.dev)
- **Starter idea:** cross-chain DCA vault — deposit USDC from any Intents-supported chain, choose BTC/ETH/NEAR and a schedule; each interval fetch a 1Click quote, reject if slippage exceeds the user's limit, swap so funds land in the user's own address. Must use the near-intents skill + 1Click for quotes/deposits/status; handle REFUNDED and FAILED; show where funds are at every step; small UI (deposit, schedule, history with explorer links); dry-run mode with real quotes and no execution. Stretch: NEAR contract owns the vault and controls a derived BTC address via Chain Signatures. Checkpoint: read the quickstart, say what it already handles, propose a file layout, wait.

### 02 / INV — Investment Thesis (`thesis`)
- **Tagline:** Make the long-term case
- **Brief:** a long-term investment thesis for NEAR backed by onchain analytics, live dashboards and re-runnable models. Judged on evidence, not conviction.
- **Hints:** ONCHAIN DATA · DASHBOARDS · RESEARCH
- **Prompt:** .../tracks/02-thesis.md
- **Start-here links:** NEAR BigQuery public dataset (docs.near.org/data-infrastructure/big-query) · NEAR data infrastructure overview (docs.near.org/data-infrastructure/what-is) · NEAR Intents Explorer API (docs.near-intents.org/integration/distribution-channels/1click-api/explorer/introduction)
- **Starter idea:** test a hypothesis (example: Intents cross-chain volume leads real usage better than token price) and report evidence both ways. SQL on `bigquery-public-data.crypto_near_mainnet_us` (daily active accounts, tx counts, contract usage; always filter on `block_date`); Intents Explorer API swap volume (needs partner-dashboard JWT in .env); one command rebuilds all charts; static dashboard with each chart, its query and one plain sentence; THESIS.md with claim, evidence for, evidence against, and what would change the author's mind. Never invent numbers. Checkpoint: list tables + one sample query, wait.
- **Note:** NEAR pays to store the dataset; you pay normal BigQuery query costs (filter on block_date).

### 03 / PRV — Privacy & Private AI (`privacy`)
- **Tagline:** Private by design
- **Brief:** confidential computation, private finance, AI that protects sensitive data — intelligence without exposure.
- **Hints:** PRIVATE AI · TEE · NEAR AI CLOUD
- **Prompt:** .../tracks/03-privacy.md
- **Start-here links:** NEAR AI Cloud quickstart (docs.near.ai/cloud/quickstart) · verification docs (docs.near.ai/cloud/verification) · verification example repo (github.com/near-examples/nearai-cloud-verification-example) · Agent API overview
- **Starter idea:** private expense auditor — upload receipts/statement, a TEE-hosted model on NEAR AI Cloud categorizes and flags anomalies, app proves it ran in a TEE. Use OpenAI-compatible API at `https://cloud-api.near.ai/v1` (key in .env); pick a TEE model from the models endpoint; fetch attestation with a fresh random nonce and verify per docs; "Verified" panel listing checks; keep nothing server-side after a response; ship fictional sample docs. Use the near-ai-cloud skill. Checkpoint: minimal script that does one completion + attestation verification first.

### 04 / BUS — Autonomous Business (`business`)
- **Tagline:** The company of one. Or none
- **Brief:** AI-native businesses with treasury, sales, procurement, cross-chain payments via NEAR Intents and revenue sharing; humans only set constraints.
- **Hints:** AI AGENTS · NEAR INTENTS · CHAIN SIGNATURES
- **Prompt:** .../tracks/04-business.md
- **Start-here links:** AI and NEAR (docs.near.org/ai/introduction) · OutLayer getting started (app.outlayer.ai/docs/getting-started) · 1Click API (docs.near-intents.org/integration/distribution-channels/1click-api/about-1click-api) · Agent API overview · PingPay Agent Pay facilitator (pingpay.gitbook.io/docs/pingpay-api/agent-pay-facilitator)
- **Starter idea:** one-agent research shop selling short market reports; customers pay in any token through Intents; agent buys its own inference on NEAR AI Cloud; fixed revenue share auto-sent to contributors. config.yaml rules: max daily inference spend, min report price, revenue split, kill switch. Agent gets its own NEAR account; never a plain-text full-access key (use OutLayer custody or a scoped function-call key); public ledger page of every sale/cost/payout; testnet demo mode completing a full loop in under two minutes. Checkpoint: read docs, sketch architecture, wait.

### 05 / SWM — AI Swarms (`swarms`)
- **Tagline:** Many agents. One economy
- **Brief:** coordination markets, bidding, collective purchasing, intent-based settlement, emergent agent economies.
- **Hints:** MULTI-AGENT SYSTEMS · NEAR INTENTS · SUB-ACCOUNTS
- **Prompt:** .../tracks/05-swarms.md
- **Start-here links:** What are intents (docs.near-intents.org/getting-started/what-are-intents) · Tools for AI agents (docs.near.org/getting-started/tools-for-ai) · NEAR MCP server (github.com/nearai/near-mcp) · Top Level Accounts (nearaccounts.com) · Agent API overview
- **Starter idea:** group-buying swarm — buyer agents pool demand for e.g. GPU hours and run sealed-bid rounds against seller agents; winner settles via Intents and each buyer pays its share. Each agent is a sub-account under one parent (buyer-1.swarm.testnet…); coordinator opens round, collects sealed bids, reveals, picks winner (rules written in RULES.md first); simulation mode with 20 buyers / 5 sellers and scripted strategies (no LLM); live page of rounds, bids, clearing price, allocations. Checkpoint: RULES.md + text sequence diagram.

### 06 / SEC — AI Security & Defense (`security`)
- **Tagline:** Trust, but verify
- **Brief:** spending limits, policy engines, sandboxed wallets, reputation, scam detection — give AI money without all the keys.
- **Hints:** AGENT SECURITY · FUNCTION CALL KEYS · TEE ATTESTATION
- **Prompt:** .../tracks/06-security.md
- **Start-here links:** Access keys (docs.near.org/protocol/accounts-contracts/access-keys) · OutLayer getting started · NEAR AI Cloud verification · Agent API policies & limits (docs.agentsonintents.com/integration/agent-api/policies-and-limits)
- **Starter idea:** counterparty check service returning allow / warn / block with reasons before an agent pays or calls a contract. Signals: account age and activity; contract or not and recent code changes; prior interactions; shared evidence-backed blocklist. Agent-side wrapper refuses on block, asks a human on warn; agent signs with a function-call key scoped to one contract (limits explained in README); attack demo where a prompt-injected agent tries to pay a known-bad address and is stopped, with log. Checkpoint: list data sources per signal.
- **Note:** accounts holding only function-call keys can't transfer NEAR or add keys, and can lock themselves out if gas allowance runs out.

### 07 / AGT — Agent Economy (`agents`)
- **Tagline:** Give AI a wallet
- **Brief:** agents that earn, spend, negotiate, hire other agents and pay for APIs, compute or data — directly in crypto or via NEAR Intents.
- **Hints:** AGENT COMMERCE · NEAR INTENTS · CHAIN SIGNATURES
- **Prompt:** .../tracks/07-agents.md
- **Start-here links:** NEAR AI Agent Market (market.near.ai/jobs) · NEAR MCP server · 1Click API · Agent API overview · PingPay Agent Pay facilitator
- **Note:** Agent API gives each agent a policy-bound wallet; demo key from partners.demo.agentsonintents.com/dashboard, base URL `https://api.demo.agentsonintents.com`; demo keys are temporary and rotate. PingPay facilitator lets agents pay HTTP 402 (x402) paywalls in USDC on Base and settles to a NEAR recipient via Intents.
- **Starter idea:** general-contractor agent — given a task and budget, splits it up, decides what to do vs. buy, hires agents or buys data, checks work, pays out, never exceeds budget. Investigate how Agent Market jobs are posted/paid programmatically (flag if no public way); one counter-offer with reasoning when a quote is over plan, then accept or walk; pay in USDC or NEAR directly or via Intents; receipt per task (what, from whom, price, pass/fail). Checkpoint: explain key custody and what the agent can't do without the human.

### 08 / RWM — Real-World Money (`realworld`)
- **Tagline:** Bring the boring money onchain
- **Brief:** payroll, invoicing, remittances, merchant payments, stablecoin rails a normal company could use tomorrow.
- **Hints:** STABLECOINS · NEAR INTENTS · META TRANSACTIONS
- **Prompt:** .../tracks/08-realworld.md
- **Start-here links:** 1Click API quickstart · Meta-transaction relayer tutorial (docs.near.org/web3-apps/tutorials/meta-transactions) · NEP-141 standard (github.com/near/NEPs/blob/master/neps/nep-0141.md) · PingPay Agent Pay facilitator
- **Starter idea:** crypto invoicing for freelancers who don't care about crypto — invoice link, client pays from any chain/token, freelancer receives USDC on NEAR without buying NEAR for gas. Invoice page (amount, due date, line items, pay button via 1Click); gasless via a relayer that only pays for calls to the project's own contract; trustworthy statuses (paid/pending/refunded + tx links); accountant-friendly CSV export. Checkpoint: README written for a bookkeeper first, then one full paid-invoice flow on testnet.

### 09 / GAM — Games With Real Economies (`games`)
- **Tagline:** The economy is the gameplay
- **Brief:** NPCs with wallets, player-owned markets, economies that evolve without a dev patch. Judged on the game loop, not the token; bonus if players never notice the chain.
- **Hints:** AGENT NPCS · SOCIAL LOGIN · NEAR INTENTS · NEP-245
- **Prompt:** .../tracks/09-games.md
- **Start-here links:** NEP-245 multi token (github.com/near/NEPs/blob/master/neps/nep-0245.md) · near-dapp agent skill (github.com/near/agent-skills/tree/main/skills/near-dapp) · What are intents
- **Starter idea:** market-town game — players gather and trade with NPC merchant agents that have wallets/inventory and price from stock and demand (flooded iron gets cheap; broke merchants close until someone invests). Items as NEP-245 tokens in one contract; social/email login with no seed phrases, popups or gas prompts in the loop; merchant pricing rules in one readable file with reasoning in a tooltip; fast-forward mode simulating a week in a minute. Checkpoint: paper design of what the player does every 30 s / 5 min / session.

### 10 / NFT — NFTs That Do Something (`nfts`)
- **Tagline:** What comes after the JPEG
- **Brief:** NFTs as accounts — assets that own money, earn royalties, hold inventory, carry credentials, memberships or access rights. Ownership with behavior.
- **Hints:** DYNAMIC NFTS · NEP-171 · SUB-ACCOUNTS
- **Prompt:** .../tracks/10-nfts.md
- **Start-here links:** NEP-171 (github.com/near/NEPs/blob/master/neps/nep-0171.md) · Access keys · near-smart-contracts skill (github.com/near/agent-skills/tree/main/skills/near-smart-contracts) · Top Level Accounts contracts (github.com/houseofstake/tla-contracts) · Sharded NFT items draft (…/docs/sharded-nft-items.md)
- **Note:** in Top Level Accounts, a rented name is an NEP-171 NFT that is also a real NEAR account; no SDK yet, contracts are live and audited on mainnet.
- **Starter idea:** membership NFT with its own wallet — each token maps to a sub-account holding a share of a club treasury and a cut of ticket sales; selling the NFT moves wallet, balance and access. Explain control transfer and how old owner loses access; holder-gated page; per-NFT history; tests for transfer incl. a sale mid-payout. Checkpoint: threat model of every way a seller could keep the money.

### 11 / MEM — Memecoins With Mechanics (`memecoins`)
- **Tagline:** The joke needs rules
- **Brief:** memecoins where the meme does something — community-reactive supply, rule-bound treasuries, onchain rituals and challenges. Judged on the mechanic, not the chart.
- **Hints:** MEMECOINS · TOKEN MECHANICS · NEP-141
- **Prompt:** .../tracks/11-memecoins.md
- **Start-here links:** NEP-141 · meme.cooking (launchpad partner) · near-smart-contracts skill
- **Starter idea:** streak coin — daily check-ins; if the community hits the target, checked-in holders get a small mint; if missed, part of the treasury burns and the streak resets; longest streak shown like a high score. Mechanic lives in the NEP-141 contract; all parameters set at launch, publicly readable, no admin key to change them; demo-grade sybil resistance with limits stated; page with streak, progress, mint/burn log. Checkpoint: simulate 60 days under several scenarios before choosing parameters.

### 12 / SOC — Social Money (`social`)
- **Tagline:** Coordinate value together
- **Brief:** shared budgets, programmable rewards, collective ownership and reputation-based access on top of Sputnik DAO and Trezu. Don't rebuild the multisig — build what communities do with it.
- **Hints:** SPUTNIK DAO · TREZU · NAMED ACCOUNTS
- **Prompt:** .../tracks/12-social.md
- **Start-here links:** Sputnik DAO contract (github.com/near-daos/sputnik-dao-contract) · Trezu docs (github.com/NEAR-DevHub/trezu-docs) · Trezu repo (github.com/NEAR-DevHub/trezu) · near.social · near.social agent guide (near.social/skill.md) · Top Level Accounts (nearaccounts.com)
- **Note:** near.social posts/replies/follows are writes to the `social` account and always show as failed (CodeDoesNotExist) because that account has no contract — expected; data still lands. Confirm with `GET https://api2.near.social/v1/tx/{tx_hash}`.
- **Starter idea:** bounty board with earned trust for a community already on Sputnik DAO or Trezu — post, claim, finish bounties paid from the treasury; reputation tied to named accounts and traceable to finished bounties; tiers (small = auto-approve for trusted, mid = one council member, large = normal DAO proposal); public board. Checkpoint: identify which approval flows already exist.

### 13 / NEW — Open Innovation (`open`)
- **Tagline:** Something we haven't seen
- **Brief:** ideas that don't fit a category — new ways for money, intelligence and ownership to work together. Can be combined with any other track.
- **Hints:** EXPERIMENTAL · CHAIN ABSTRACTION · BUILD YOUR OWN
- **Prompt:** .../tracks/13-open.md
- **Start-here links:** Chain Signatures getting started · NEAR docs (docs.near.org) · HACKATHON.md
- **Starter idea:** inheritance account — one NEAR account controls the owner's BTC/ETH addresses via Chain Signatures; owner checks in on a schedule; after N missed days (e.g. 90) guardians can approve release to named heirs after a cancellable waiting period. Rules in a readable contract; owner can cancel any pending release; testnet demo with timers in minutes; README on failure cases (lost guardian keys, hostile guardian, owner alive but offline). Checkpoint: argue against the idea for a paragraph first.

### Track summary from the NEAR announcement blog (one-liners)
Unstoppable DeFi (cross-chain exchanges, lending, vaults, trading agents) · Investment Thesis (data-backed case for NEAR) · Privacy & Private AI (confidential apps/AI) · Autonomous Business (AI-run businesses within human constraints) · AI Swarms (agents coordinating, bidding, pooling, transacting) · AI Security & Defense (spending limits, safeguards, reputation, scam detection) · Agent Economy (agents earn/spend/negotiate/pay) · Real-World Money (payroll, invoices, remittances, stablecoins) · Games With Real Economies (wallet NPCs, player markets) · NFTs That Do Something (NFTs holding funds, royalties, credentials) · Memecoins With Mechanics (community rules, programmable treasuries) · Social Money (shared budgets, rewards, ownership via Sputnik DAO and Trezu) · Open Innovation (anything beyond the other tracks).

---

## 6. Execution plan (site section "IDEA > BUILD > DEMO", four stages)

1. **Assemble** — bring a team (or go solo) and choose a track; no sign-up to start.
2. **Build** — turn the idea into a working prototype and test the assumptions that matter.
3. **Show it** — publish the repo and post the demo on X tagging @NEARProtocol and #NEARHackathon, with video or screenshots.
4. **Submit** — send the form with both links (repository + demo post).

---

## 7. Judges ("03 / The People — Meet the Judges")

| # | Judge | Organization | X handle |
|---|---|---|---|
| 01 | Illia Polosukhin | NEAR Protocol (co-founder; NEAR Foundation CEO) | @ilblackdragon |
| 02 | Eddy Lazzarin | a16z crypto | @eddylazzarin |
| 03 | Mert Mumtaz | Helius (CEO; joined NEAR Foundation Council Oct 2026) | @0xMert_ |
| 04 | Avichal Garg | Electric Capital | @avichal |
| 05 | Kain Warwick | Synthetix & Infinex | @kain |
| 06 | Haseeb Qureshi | Dragonfly | @hosseeb |
| 07 | Stepan Gershuni | cyber•Fund | @cyntro_py |
| 08 | Claude Code & Codex (AI judges) | Anthropic & OpenAI | @claudeai, @OpenAI |

### How judging works
- Claude Code and Codex **screen every project first**: reproducibility check, verifying features match the README, a structured report and a preliminary score.
- **Humans decide.** A low AI score alone cannot reject a project (Q-017).
- Site FAQ: previous NEAR hackathons judged on **technical implementation, design, impact, originality and sustainability** — recommended as a guide.
- READMEs should be written for machine and human readers: what it is, the problem, and "do X → see Y" steps. No marketing copy.
- Hosted demo is a plus; local-only is acceptable with a public repo, reproducible README and a video in the X post (screenshots alone aren't enough if judges can't open the demo).

---

## 8. Rules (HACKATHON.md "Rules" Q-000 to Q-017, restated)

| # | Question | Answer |
|---|---|---|
| Q-000 | NEAR AI credits? | Buy with crypto or card at cloud.near.ai, or claim $10 by joining NEAR Builders (nearbuilders.org/join). API key generated in the dashboard. |
| Q-001 | Code before 1 Nov? | Yes, from the 19 Oct announcement. Window = 19 Oct → 14 Nov. Earlier commits are baseline. |
| Q-002 | Existing product on another chain? | Allowed; only the NEAR integration built in the window is judged; disclose in README. |
| Q-003 | New repo required? | No. Use a dedicated branch, or tags `pre-hackathon` and `hackathon-submission`, plus a README section linking the diff. |
| Q-004 | Old project / new feature? | Old project as-is: no. New feature built in the window: yes, if separated per Q-003. No minimum code size. |
| Q-005 | Libraries, templates, boilerplate? | All allowed, incl. own pre-hackathon libs and AI-written code; list them in README; own old libs = baseline. |
| Q-006 | 1Click JWT? | Not required; without it there's a 0.2% fee. Register at partners.near-intents.org. |
| Q-007 | Testnet for Intents? | None exists or is planned. Use mainnet, separate dev accounts, tiny amounts, `dry: true` quotes. |
| Q-008 | Test funds? | Testnet NEAR is free (near-cli faucet, near-faucet.io). Mainnet costs not reimbursed by default. |
| Q-009 | RPC & hosting? | Public RPC is free: docs.near.org/api/rpc/providers |
| Q-010 | Testnet-only eligible? | Yes, all tracks; mainnet only where the integration is mainnet-only. |
| Q-011 | Mandatory integrations? | None. Hints are hints. Your own NEAR contract fitting the track is enough. |
| Q-012 | Local-only demo OK? | Yes, with public repo, reproducible README and an X video. Hosted demo is a plus; keep it up to 18 Nov, ideally 25 Nov. |
| Q-013 | Organizer rights to code? | None. Team keeps all rights; organizers get non-exclusive promo rights to name, screenshots, video, repo link. |
| Q-014 | License? | Any (MIT fine). Repo stays public through judging; add a LICENSE file. |
| Q-015 | One person, several projects? | Max 2 different, independent projects; each README must name the other. Not the same project twice. |
| Q-016 | Payout schedule? | Single payment, no vesting, within 30 days of results. |
| Q-017 | Role of Claude Code & Codex? | Screening, not deciding (see Section 7). |

### Site FAQ ("Questions? Start here")
- **Who can take part?** Developers, designers and people with ideas for the NEAR ecosystem. No wallet connection needed — you just enter a NEAR account address for the prize.
- **Need a team already?** No. Solo or team; one submission per project; one person up to 2 independent projects that name each other in their READMEs. Find teammates on NEAR Discord or the Telegram builders chat.
- **When?** Starts 1 Nov 00:00 UTC; development ends 14 Nov 23:59 UTC; results by 18 Nov 23:59 UTC.
- **What to submit?** Working prototype in a public repo + public X demo post saying it was built at NEAR HACKATHON, with video/screenshots; both links via the form before the deadline.
- **Made a mistake — resubmit?** No resubmission; use the Request changes page (email, NEAR wallet, repo link from the submission; tick fields; leave contact). Organizers review by hand and may message to confirm, especially for payout wallet or repo changes.
- **How judged?** AI screening by Claude Code & Codex, decisions by the human judges; past criteria were technical implementation, design, impact, originality, sustainability.
- **Multiple tracks?** Yes — select every track that fits; still one submission.

---

## 9. Submission — requirements, form and API

### Final submission checklist (site section "06 / Final Submission")
1. Build the project (code written since the announcement counts).
2. Publish the repository — judges can't open a private one.
3. Post the demo on X: say it was built at NEAR HACKATHON, tag @NEARProtocol and #NEARHackathon, attach video or screenshots.
4. Submit the repository link and the demo post link — both required.

### Web form fields ("PROJECT SUBMISSION")
| Field | Notes |
|---|---|
| Project name * | |
| Team lead * | |
| Email address * | |
| Team size * | 1 — Solo builder · 2 - 4 people · 4 - 6 people · 6 - 8 people · 8+ people |
| Tracks * | choose all that fit |
| NEAR wallet address * | yours or the team's; prize is sent here |
| Repository link * | must be public; this is what judges review |
| Demo post link * | public X post with video/screenshots |
| What did you build? * | 20–2,000 characters |
| Website | (hidden spam trap — must stay empty) |
| Consent checkbox | "organizers may use these details to review our submission and contact us about this hackathon" |

Button: "Submit your project". One submission per project. No wallet connection needed. Link: "Made a mistake in your submission? Request changes".

### Submission API (`POST https://nearhackathon.com/api/applications`, JSON, body ≤ 12,000 bytes)
| Field | Type | Rule |
|---|---|---|
| requestId | string | UUID, generated once, reused on retries |
| projectName | string | 2–80 chars |
| leadName | string | 2–80 chars |
| email | string | valid, ≤160 chars, max 2 submissions per email |
| size | string | exactly `1`, `2 - 4`, `4 - 6`, `6 - 8` or `8+` |
| tracks | string[] | one or more of `defi, thesis, privacy, business, swarms, security, agents, realworld, games, nfts, memecoins, social, open`, each once |
| nearAddress | string | 2–64 chars, lowercase, regex `^(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$` (named like `team.near` or 64-char implicit; mainnet) |
| projectUrl | string | http(s) public repo, ≤300 chars, unique (each repo once) |
| demoUrl | string | http(s) demo post, ≤300 chars |
| idea | string | 20–2000 chars |
| consent | boolean | `true` only after the human agrees |

No other fields. `website` is a spam trap — any non-empty value rejects the submission.

| HTTP status | Meaning | Action |
|---|---|---|
| 201 | Saved | Done |
| 400 | Validation failed | Fix fields listed in `fields`, resend with same requestId |
| 403 | Not open, or looked cross-site | Don't retry; tell the human |
| 409 | Repo already submitted, or email has 2 submissions | Don't change link/email to get around it; request changes instead |
| 413 | Body too large | Shorten description |
| 503 | Storage temporarily unavailable | Wait a minute, resend with same requestId |

Submissions accepted only 1 Nov 00:00 → 14 Nov 23:59 UTC; outside that the API answers 403.

### What only the human decides (agents must not guess or fill placeholders)
Project name · team lead · email · team size · tracks · mainnet NEAR payout account (never created/invented by the agent) · public repo link · public demo post link (human writes and posts it) · description · consent to the contact notice (read verbatim).

### Never without the human's explicit confirmation (agent rules)
Sending the submission (print full JSON payload first, wait for yes — one attempt per repo) · posting anything on X or elsewhere · making the repo public, pushing or force-pushing · signing transactions, spending tokens, deploying to mainnet · committing secrets (keys go in env vars).

### Demo post guidance (HACKATHON.md, restated)
- Open with the user problem; first line understandable to a stranger.
- Show one complete moment from a real user action to a visible result; skip intros, architecture slides, setup.
- Say concretely what NEAR enables (e.g., cross-chain settlement, private inference, agent-controlled spending) — avoid vague "powered by NEAR".
- Give a next step: link demo and repo, ask a real question or invite specific feedback.
- Always include @NEARProtocol and #NEARHackathon; optionally @NearLegion and @NearBuilders for amplification.

### Pre-submit checklist (SUBMITTING.md in prompt repo)
Repo public with "do X, see Y" README · demo post live on X with video/screenshots and NEAR HACKATHON mention · mainnet NEAR account for payout · every fitting track selected · no keys/secrets anywhere in repo history · before 14 Nov 2026 23:59 UTC.

---

## 10. Request changes page (https://nearhackathon.com/request-changes)

Title: "REQUEST CHANGES — MADE A MISTAKE? CHANGE IT HERE". Organizers review every request by hand before anything changes; submission stays as-is until applied.

Steps: (01) enter email, NEAR wallet and repo link from your submission · (02) tick each field to change and give new values (one request can change several) · (03) leave Discord or Telegram handle; they may message to confirm, especially for wallet or repo changes.

Form fields: Project name* · Email address* · NEAR wallet address* · Repository link* · What needs changing?* (checkboxes: Project name, Team lead, Email address, Team size, Tracks, NEAR wallet address, Repository link, Demo post link, What did you build?) · Anything we should know? · Contact me on* (Discord / Telegram) · Your handle* · Website (spam trap) · consent checkbox · button "Request changes".

---

## 11. Ecosystem partners ("04 / The Ecosystem — Connected by Building")

| Partner | What it is | Website | Docs | Git / API |
|---|---|---|---|---|
| NEAR Intents | Cross-chain execution | intents.near.org | docs.near-intents.org | github.com/near/intents |
| Aurora | Ethereum on NEAR | aurora.dev | doc.aurora.dev | github.com/aurora-is-near |
| HOT | Chain abstraction | hot-labs.org | docs.hotdao.ai | github.com/hot-dao |
| Rhea | DeFi on NEAR | rhea.finance | guide.rhea.finance | github.com/rhea-finance |
| meme.cooking | Memecoin launchpad | meme.cooking | docs.meme.cooking | API: api.meme.cooking |
| HEX | Cross-chain swaps | hex.exchange | hot-labs.gitbook.io/hex/concepts-and-systems/interactive-blocks | — not available |
| NEAR.AI | Private AI | near.ai | docs.near.ai | github.com/nearai/cloud-api |
| SVRN | Sovereign technology | svrn.net | svrn.net/research/near-protocol | — not available |
| Trezu | Multisig treasury for Web3 teams | trezu.org | github.com/NEAR-DevHub/trezu-docs | github.com/NEAR-DevHub/trezu |
| SputnikDAO | DAO infrastructure | x.com/SputnikDAO | github.com/near-daos/sputnik-dao-contract#setup | github.com/near-daos/sputnik-dao-contract |
| OutLayer | Secure transactions for AI agents | outlayer.ai | app.outlayer.ai/docs/getting-started | github.com/out-layer/outlayer |
| GoMining | Bitcoin mining superapp | gomining.com | docs.gomining.com | — not available |
| Agent Market | Marketplace for AI agents | market.near.ai | docs.market.near.ai | API: market.near.ai/docs |
| NEAR Builders | Builder community | nearbuilders.org | nearbuilders.org/build | github.com/nearbuilders |
| Gulf Labs | Invests in blockchain infrastructure | gulf-labs.com | — not available | — not available |
| BRRRAIN | Memecoin with AI rewards | brrrain.fun | brrrain.fun/docs | API: brrrain.fun/docs/api |
| NEAR Business | Confidential multisig treasury | business.near.com | docs.business.near.com | — not available |

Plus RHEA token prize contribution (Section 3). NEAR blog also mentions "documentation from ten ecosystem partners" (the list grew to 17 on the site).

### Partner notes (HACKATHON.md)
- **Rhea** — NEAR's DEX and lending protocol. Build ideas: CLMM/AMM pools, cross-chain swap API, vaults on its lending. SDK/API docs: github.com/rhea-finance/rhea-sdk-docs; CLI: guide.rhea.finance/developers-1/cli-trading.
- **Agent Market** — marketplace where agents are hired and paid per job by people and other agents. List your agent: docs.market.near.ai/list-your-agent; hire agents from Claude/MCP clients: docs.market.near.ai/guides/claude-desktop.
- **NEAR Business** — confidential multisig on NEAR Intents; hides treasury balances/transfers from the public, manages assets on 35+ chains from one dashboard, configurable approval policies. Sign-up: business.near.com/create?ref=og; demo video: app.trupeer.ai/view/OEoiJVjUh/near-business-create-and-manage-a-treasury.

### NEAR tools named in the announcement
NEAR Intents · Chain Signatures · chain abstraction · NEAR AI Cloud · TEEs · 1-Click Swap SDK · function call keys · meta transactions · sub-accounts · named accounts. Listed as starting points, not a checklist; name the ones used in the README.

---

## 12. Builder toolkit & community ("05 / Builder Toolkit — Less setup. More shipping")

- Docs: https://docs.near.org/ ("Read the Docs")
- Download HACKATHON.md — give it to your coding agent; it knows tracks, dates, submission steps and can file the submission.
- More resources: https://nearbuilders.org/build
- AI-oriented docs: https://docs.near.org/llms.txt · https://docs.near-intents.org/llms.txt · Docs MCP
- NEAR agent skills: `npx skills add near/agent-skills` (skills: near-ai-cloud, near-api-js, near-dapp, near-intents, near-kit, near-smart-contracts; single skill: `--skill <name>`)
- NEAR DevHub YouTube (track-prompt walkthroughs): https://www.youtube.com/channel/UCq0iWZQuXhvP8yQzDZsmWfQ
- NEAR AI Cloud credits/API key: https://cloud.near.ai
- RPC providers: https://docs.near.org/api/rpc/providers
- 1Click partner registration: https://partners.near-intents.org

| Channel | Link | Use |
|---|---|---|
| NEAR Discord | https://discord.gg/nearprotocol | questions, finding teammates |
| Telegram builders chat | https://t.me/nearbuilderschat | questions, finding teammates |
| X | https://x.com/NEARProtocol | announcements |

### Prompt repo — github.com/nearai/near-hackathon-prompt-examples
- **Purpose:** copy-paste prompts per track, each giving a coding agent a two-week scope, docs to read first, and a checkpoint where it stops for the human.
- **Usage:** (1) paste `00-setup.md` once (agent reads HACKATHON.md, installs agent skills); (2) paste your track's prompt and edit `[bracketed]` parts; (3) swap in your own idea but keep requirements + checkpoint; (4) go through `SUBMITTING.md`.
- **00-setup.md instructs the agent to:** read HACKATHON.md fully and obey its confirmation list; install NEAR agent skills; use the two llms.txt files and never guess addresses/endpoints/SDK versions; build on testnet first with keys in .env; keep a README for an AI judge from day one; confirm by listing the 13 track ids.
- Repo README restates prizes ($10K/$3K/$2K per track, $55K grand, paid in NEAR), dates, and that the jury includes Claude Code and Codex.

---

## 13. NEAR — organization, team and organizers

### Who runs it
- Hackathon is run by **NEAR / NEAR Foundation** (third-party listings name NEAR Foundation as provider). Announced via @NEARProtocol and the NEAR blog; agent prompt repo is under the **nearai** GitHub org; @NEAR_hckthn named as the updates account.
- NEAR Foundation is a nonprofit (historically registered address Chamerstrasse 12 C, 6300 Zug, Switzerland, per MetaBUILD 2 rules).

### People
| Person | Role |
|---|---|
| Illia Polosukhin (@ilblackdragon) | NEAR Protocol co-founder; NEAR Foundation CEO since Nov 2023; hackathon judge; shared build ideas for Intents and NEAR AI during the event (5 Nov 2026) |
| Alexander (Alex) Skidanov | NEAR Protocol co-founder |
| Chris Donovan | Former NEAR Foundation General Counsel → CEO (after Marieke Flament stepped down) → COO when Illia became CEO |
| Marieke Flament | Former NEAR Foundation CEO (~2 years); stayed on the Council board as advisor after stepping down |
| Bowen Wang | CTO; founder of NEAR One (core R&D team); early engineer |
| George Zeng | Appointed mid-2025 as Chief Product Officer of NEAR Protocol and GM of NEAR AI; NEAR AI launched open-source agent runtime "IronClaw" in Feb 2026 |
| Mert Mumtaz | Helius CEO; joined NEAR Foundation Council (Oct 2026); hackathon judge |
| Sheila Warren | NEAR Foundation Council member (also CEO, Crypto Council for Innovation) |
| Diogo Monica | NEAR Foundation Council member (Anchorage Digital founder) |
| (Kummell) | NEAR Foundation Chief Commercial Officer (ex-DCG, Citi, Citadel, Balyasny, SAC/Point72) |

### Org history notes
- **Jan 2024:** NEAR Foundation cut ~40% of staff (35 people), mainly marketing, BD and community.
- **2024:** dedicated AI team/structure set up ("user-owned AI" strategy).
- **Oct 2025:** five senior executives added from Bloomberg, DCG, Flipside, dYdX and others.
- **May 2025:** mainnet 600 ms block times and 1.2 s finality; target of 200 ms blocks announced.
- **Protocol Rewards** (2025): cohort program for post-hackathon builders; distributed $200K+ to 30+ teams in Q2 2025.
- NEAR Foundation Council (NFC) oversees the executive team, which runs day-to-day operations.
- NEAR docs describe: ~1.3 s deterministic finality, ~$0.002 average fee, sharded, Rust/WASM contracts, Chain Signatures, TEE-backed agents.

---

## 14. Media coverage of this hackathon (summarized)

- **NEAR on X (19 Oct 2026):** launched with "$250K+", no signup, public repo + public demo post between 1–14 Nov.
- **NEAR on X (2 Nov 2026, pinned):** submissions open; 13 tracks; $250,000; no sign-up.
- **NEAR on X (5 Nov 2026):** reminder plus Illia's build ideas for Intents and NEAR AI.
- **Lookonchain / Gate (20 Oct):** reported schedule in Beijing time; focus on agents, autonomous payments, cross-chain value; judges incl. Polosukhin, Mumtaz, Lazzarin.
- **Coinfomania (2 & 4 Nov):** coverage of submissions opening and of the retweet of Illia's post.
- **TronWeekly:** framed it alongside NEAR price outlook (~$6 resistance mentioned).
- **CoinAlertNews (19 Oct):** headline stressed "Top VC Judges".
- **startupgrantsindia.com:** listing (provider NEAR Foundation, online, deadline 05:29 IST 15 Nov).
- **X user @winsznx:** November 2026 roundup listed it among the biggest opportunities; that roundup claimed participants were told not to start before the hackathon — this conflicts with the official rule Q-001 (code since 19 Oct counts).

---

## 15. Past NEAR hackathons & winners

### 15.1 MetaBUIDL (1st series) — Aug 27 – Sep 12, 2021
- $1M across a series of hackathons through end of 2021; themes "Work" and "Play"; local "Hack Nodes" in 3+ cities (up to $5,000 per node prize pool); judges/speakers incl. Illia Polosukhin, Anton Bukov (1inch), Li Jin, James Young (Collab Land). Funding paths: Open Web Collective, NEAR Foundation, NEAR Asia, VCs.
- **Known winner:** **2Dverse (2Dver.se)** — 1st place, "Play Hack" category; social multichain metaverse pulling NFT art from Paras.

### 15.2 MetaBUILD 2 — Dec 22, 2021 – Feb 21, 2022 (extended; winners 31 Mar 2022)
- Devpost (metabuildii.devpost.com); $1,000,005 pool; ~3,838–4,000 participants; 356 projects submitted, 186 eligible; Welcome & Natives tracks + 35 sponsor challenges. Co-organizers: NEAR Foundation, Aurora, Brave, Octopus Network. Coordinator: Maria Yarotska (Pagoda).
- Prize structure: 1st $70K, 2nd $50K, 3rd $30K; per-track categories (Best Technology, Best Design, Most Potential Impact, Biggest Idea, Most Sustainable) $20K pools; sponsor challenges $3K/$2K/$1K; bonus sponsor pool $40K.

| Prize | Winner | What it is |
|---|---|---|
| Grand 1st | **Voog** | UI-based smart contract builder, one-click deploy to NEAR, auto-generated UI |
| Grand 2nd | **MetaAds** | Online-to-offline protocol aggregating metaverse ads with real-world indoor/outdoor ads |
| Grand 3rd | **NEAR Playground** | Browser editor to write/compile/test/call Rust & AssemblyScript contracts |
| Welcome – Best Technology | Rainbow Bridge Explorer | API/explorer for NEAR–Aurora–Ethereum bridge transactions |
| Welcome – Best Technology | MineLand | Play-to-earn NFT game: mint mines, collect resources |
| Welcome – Best Technology | NEAR Playground | (above) |
| Natives – Best Technology | Shizo | Metaverse map mirroring real world; buy/sell digital roads and land |
| Natives – Best Technology | MetaAds | (above) |
| Natives – Best Technology | Voog | (above) |
| Brave CryptoDino 1st | Jeffrey The Dinosaur's Dinotastic Blockchain Adventure | Brave dino game with NEAR login and NFT skins |
| Brave CryptoDino 2nd | OpenSkin | Earn dino points; marketplace for artist skins as tokens |
| Co-organizer "Calling All Liberal Artists" | Bit Civilization | Multi-chain DAO infrastructure protocol |
| "Airtable Is the New Excel" | NEAR Validators Dashboard | View of all NEAR validator details |
| Aurora "Build an NFT Marketplace" | Borealis | Automated NFT marketplace |
| Aurora "Oracles" | Symm Finance | On-chain perpetual futures exchange on Aurora |
| Aurora "ERC20-Factory" | Kahu | Easy ERC20 minting on Aurora |
| Octopus "Appchain Challenges" | SmartCV | Talent-matching for organizations/employees |

Full list: medium.com/nearprotocol/metabuild-2-hackathon-winners-f0daf9586c09

### 15.3 MetaBUILD III — registrations from Sep 1, 2022 (submissions from Sep 23; event dated ~Nov 23, 2022)
- $1M prizes; Native track (new projects) and Web2-to-Web3 track; 8-week incubation with NEAR University content; "challenges instead of bounties"; 20 winners went into an 8-week pre-accelerator with **Startup Wise Guys**. Devpost: metabuild.devpost.com.
- **Winners shown on the Devpost gallery (23 listed + 1 removed):** ChatMe (chats & messages for NEAR) · Refound Journalism (decentralized publishing/news market) · OnlyFunds (crowdfunding on NEAR) · SEED Web3 Career Hub (hiring with on-chain profiles) · RECUR (recurring payments management) · NEAR integration – ZRK.UA (handmade marketplace integration) · NSub (WordPress content subscriptions on NEAR) · Treadle Lifestyle App (racing lifestyle) · Game_bloc (social platform for gamers) · Near Notification Protocol (dapp notification infra) · Indices Finance (decentralized index protocol) · Ghosty (NEAR messaging) · Deer Marketplace (decentralized buy/sell) · LOOKTAB (AR mobile dApp) · dTelecom (Web3 CPaaS) · Waver Finance (decentralized quant trading) · Heir Trust (crypto backup/recovery/inheritance) · Geovox (collect items while travelling) · Equitify Platform (tokenized IDO launchpad) · Yinbox (integrated messenger) · NEAR SMART EVENTS (no-code on-chain event listener) · Rustle (automatic auditor for NEAR contracts) · Road ICM (investigative case management) · [one entry removed]. Prize placement per project was not shown on the gallery.

### 15.4 Near at ETHDenver 2023 bounties (winners posted 13 Mar 2023; 30K+ USDC)
| Pool | Bounty | Winner | Runners-up |
|---|---|---|---|
| Aurora | Open Aurora Bounty | StakingPool Aurora (liquid staking → $stAUR) | Geni (AI security-test spec generator); Demeter (self-paying RWA-yield loans) |
| Proximity | Deploy a Decentralized Frontend Component | BosWrap (BOS ETH wrap/unwrap widget) | ABI BOS Widget; Bossed Up; Atmosph3re (decentralized ID & aid for unhoused people); EthDenver2023UWCA (Rocketpool swap dApp on BOS.GG) |
| DevGov | Extensive Developer Profile Widget | Developer Profile (GitHub-like profile on BOS) | — |
| DevGov | Fuzzy Search / Promoted Posts / Top Posts / Post History | Near.Social DevGovGigs Improvements | — |
| DevGov | Near.Social bots in JS | JS Bot Widget | — |
| DevGov | Verifiable RPC Replies | Near Verifiable RPC Endpoints for Viewing Access Keys | — |

### 15.5 NEARCON 2023 IRL Hackathon — Lisbon, Nov 7–10, 2023 (winners 22 Nov 2023)
- $140K+ prizes; 405 participants on Devpost; theme "Step into the Open Web" on the B.O.S; travel stipends from DevHub; winners eligible for NEAR Horizon pre-acceleration.

| Prize | Winner | Team (as published) | What it is |
|---|---|---|---|
| Main 1st | **Obrigado** | William S, João Vasco Pestana, Igor Perić, Souheila Sidennas, Hojay Lee | Off-chain heavy compute across providers with on-chain bookkeeping, validation, reputation, slashing |
| Main 2nd | **Magic Build** | Hai N, Kuro Denjiro | No-code front-end generation / B.O.S Composer widget linking |
| Main 3rd | **Web3 Plugin** | Muhammad Altabba | web3.js-style plugin for NEAR |
| Developers Track | Quex | Dmitry Meshkov, Alejandro V. Betancourt | AI (ChatGPT)-controlled grant treasury contract |
| Entrepreneurs Track | ClickDapp | João Veiga, Pedro Destri, Rafaeldkb Borges | No-code dApp builder on B.O.S |
| Creators Track | B4B | Anton Pecherkin, Ann Chuhnina, Gregory Melnikov, Aleksandr Sokolov | Influencer-marketing protocol on Near Social Graph |
| Regulators Track | Proof-of-Reputation | Luis Daniel Mendez Castellanos, Irving Yair Nava Hernández, Alan Estrada | Loans using on-chain activity as collateral (SBT-based) |
| Pitch Competition | DeFi Builder | Ravi Rasadiya, Alexe Spataru, Lorenzo Castagnone, Daniel Morosan | AI no-code DeFi launcher incl. AI smart-contract generator |

Judges: Max Zavershynskyi (NEAR DevHub), Eric Winer (Pagoda CTO), Alex Shevchenko (Aurora CEO), Nate Geier (Mintbase CEO), Laura Cunningham (NEAR Horizon GM), Samantha Bohbot (RockawayX), Oleg Fomenko (Sweat Economy), Bowen Wang (Pagoda, Head of Protocol), Sandi Fatic (Calimero), Joe Spano (ShardDog), MJ (Proximity Labs), Diogo Monica (Anchorage Digital). Bounties included Mintbase SDK templates, account abstraction, and Proximity "Innovate Web3 UX with BOS".

(NEARCON 2022 Lisbon also had a 48-hour IRL hackathon, "Building Beyond the Hype" — winner list not captured.)

### 15.6 NEAR Hacks (HackerEarth) — idea phase Dec 7, 2023 – Jan 21, 2024; hack phase Jan 23 – Feb 29, 2024
- 1,572 registered; team size 1–6; 8-week online hack; site states winners announced (names not retrieved).

### 15.7 [REDACTED] Hackathon — online Sep 5 – Oct 31, 2024; IRL finale Bangkok Nov 9–11, 2024
- Replaced NEARCON 2024; AI x Web3 and Chain Abstraction; prizes reported $310K–$500K+; Native Track (top $50K, 3×$20K, best tech $10K, honorable mentions $5K) and Chain Agnostic track; travel scholarships up to $1,000; venue Avani+ Riverside Bangkok; city nodes + Chiang Mai hacker house (6 of 7 house projects won prizes).
- **30 winners on Devpost gallery:** betVEX (esports betting) · Near Yield (multi-chain AI yield) · Onchain Agent AI (user-owned AI platform) · TrustyBite (food transparency devices) · AICrawler (AI semantic crawler) · Omnibets (decentralized betting) · NEAR River (Substreams indexer launcher) · Scavene (NEAR contract security) · SmartPool.near (pooled AI investing) · Intear Oracle (permissionless oracle marketplace) · DeReal (spontaneous social sharing) · VoxChain (voice → blockchain) · Dead Project Snipper (tracks grant recipients' activity) · NearNDear · Block Elf (on-chain LLM search) · JSinRust+NearOpenAI · SwipeX (social prediction betting) · SuperNear (AI blockchain interface) · ORCA (cheap AI training via blockchain) · Raigotchi (virtual pet) · WhoIsTheBoss (prompt-to-earn game) · Motu Pop Bubble Shooter · Chicken Merge & War (on Aurora) · IconicInk (signed collectibles) · Chain Sleuth (AI blockchain detective) · Walllet Analyzer · Nexus (community-owned AI agents) · Icebreak (paid-reply encrypted messenger) · Near you BOT · Night's Watcher (security monitoring). Specific prize per project not shown on the gallery.

### 15.8 Coinbase Onchain AI Hackathon (NEAR bounties) — San Francisco, Feb 1–2, 2025
- Organized with Coinbase Developer Platform, Replit, Anthropic; sponsors incl. Virtuals, NEAR, XMTP, Base, Hyperbolic, Byte; 100+ devs.
- **NEAR bounty winners:** **Chainsmokers** (Matthew Law) — MCP-augmented chatbot pulling tools on demand for cross-chain tx via NEAR AI; **Mosaia / Walley** (Aaron Wong Ellis, Alex Alksne, Cyril Delattre) — smart-wallet agent building tailored investment strategies.
- Notable: A2A Exchange (Jared Grogan, voice-to-voice agent); Alphabot (Chetan Nandakumar, Michael Barry, Anderson Chen, BabuAravind, Kashyab Murali — agent discovery for AgentKit).

### 15.9 One Trillion Agents Hackathon — online, Jan 31 – ~Mar 2, 2025 (winners showcased 21 Mar 2025)
- With NEAR AI and Hackbox; Devpost 1t-agents.devpost.com; $102,550 pool; tracks DeFi Agents, Social Media Agents, Absurd Agents + sponsor bounties (Aurora, Bitte, etc.). Bitte reported 40 top submissions, 14 built on Bitte.
- **24 winners on Devpost gallery:** Dailies, dailies, read all about it (AI financial digest) · HedgeFi (trade/bet on NEAR & Aurora) · betVEX AI Agent · Balancer Assistant (swaps & balance tracking; DeFi track) · Bitcoin Agent (Chain Signatures → Bitcoin L1) · commchain (field-ops blockchain + AI) · NEAR AI Social Scheduler · Aigency (NEAR AI caching CDN/orchestration) · X DropBot (Twitter tips via Chain Signatures) · @SatSlinger (Bitcoin tipping bot on X) · **Ping Subscription Shade Agent** (Absurd Agents track; Ping Pay later joined Protocol Rewards) · AgentFather (create agents on NEAR AI Hub) · AI Agents for Need Of Escrow · Near Anti-rug AI Agent · SquidChain · AURORA AI AGENT LAUNCHPAD · AI Apocalypse Chain · icanguess.ai · IdeaPulse · Fluxfolio (MPC proxy portfolio mgmt) · BetBotX · CoolFi (intents swaps) · Gains.Trade AI Agent · Swan Provider Agent.

### 15.10 Useful Agents Hackathon — San Francisco, Mar 14–15, 2025
- 24-hour sprint; co-organized by NEAR AI, SF Compute, Electric Capital; $20K pool; 100+ devs; agents hosted on NEAR Agent Hub with quantitative benchmarks required. Kickoff panel: Adam Wolff (Anthropic), Illia Polosukhin, Avichal Garg, Evan Conrad (SF Compute). Bounty partners: Coinbase CDP, Phala, xTrace, Nevermined, MIZU, Questflow, Pond, Silverstream AI, PublicAI, Exabits. Guest judges: Anna Turos, Manuel Del Verma (Silverstream), Lincoln Mur (Coinbase), Hang Yin (Phala), Felix Meng (xTrace).

| Place | Winner | Team | What it is / benchmarks |
|---|---|---|---|
| 1st ($5,000) | **Postt** | Zahidul Islam's team | AI social media manager for founders; 92% human approval, +35% engagement, <2% error, 3,000%+ impressions in a week |
| 2nd ($3,000) | **Due Diligence Agent / DiligenceAI** | Vijay Sithambaram & team | 7-agent investment due diligence; 85% faster, 92% risks found, <5% false positives |
| 3rd ($2,000) | **NEAR Food** | Nelson Lai | Finds free-food events while handling anti-bot measures; 92% accuracy; also recognized by Phala and xTrace for TEE privacy |

### 15.11 Other NEAR-linked hackathons found (winners not published/retrieved)
- **Zcash x NEAR Intents Hackathon** — Mar 17–28/30, 2025, Taikai/Hackbox, $70K, ~87–94 participants; judging week of Apr 7.
- **Bankrbot Extension Hackathon** (Shade Agents stack, via Proximity) — winners announced on X May 4, 2025 (deadline extended to May 7).
- **Agents Without Masters Hackathon with NEAR AI** (Hackbox) — 245 going.
- **Abstraction Hacks** — Jan 8–28, account abstraction on NEAR, $20K.
- **ETHGlobal London 2024** — NEAR Protocol $10,000 prize pool.
- **NEAR Blockchain Accelerator India** — winners ArGo Protocol, MotoDB, MooPay.
- **Protocol Rewards alumni highlighted by NEAR:** Ping Pay (1T Agents winner); Finowl (3rd place at a NEAR hackathon).

---

## 16. All submitted projects (268) — public directory at capture time

Order = oldest submission first (site order). Handle = X account that posted the demo (each project's demo link is on nearhackathon.com → Projects). "—" = demo not on X / handle not parsed.

Track ids: defi · thesis · privacy · business · swarms · security · agents · realworld · games · nfts · memecoins · social · open

| # | Project | Tracks | Demo by |
|---|---|---|---|
| 1 | Veto: on-chain spending firewall for AI agents on NEAR | security, agents | @tarantinbv |
| 2 | Semilla1 Guard | security, agents | @Rextropovich |
| 3 | Allowance | business, security, agents | @soldanoandrea |
| 4 | near-thesis: NEAR on the evidence | thesis | @soldanoandrea |
| 5 | LeashPay | security, agents | @rajahassants |
| 6 | NEAR Private OTC | defi | @priva_cie |
| 7 | Tidepool | open | @priva_cie |
| 8 | NEAR Agent Spend Guard | business, security, agents | @mubu_dot |
| 9 | Veridom Pay | privacy, security, realworld, nfts | @KhDidukh |
| 10 | Throughput Treasury | privacy, business, security, agents | @KhDidukh |
| 11 | ÁUREA CONTRACT FOR PRIVACY | privacy | @chun_dik |
| 12 | Morrowseal | privacy, open | @hack_sometimes |
| 13 | Jurat | privacy, realworld | @NFTKINGIII |
| 14 | NEAR Investment Thesis: the evidence | thesis | @ridakalam52 |
| 15 | NEAR Thesis Scorecard | thesis | @CryptHypoBuster |
| 16 | Thesis Agent | agents | @Cryptogiives |
| 17 | AgentGuard | privacy, business, security, agents | @MyCryptoWallet |
| 18 | Tollgate | security, agents | @smartkdy7 |
| 19 | IntentGuard | security | @RobinsomTim |
| 20 | Black box: a verifiable flight recorder for an AI agent's money | security, agents, open | @mr_ghdc |
| 21 | NEAR's agent economy, measured | thesis, agents, open | @mr_ghdc |
| 22 | SpendGuard AI | business, security, agents | @anhmy1312 |
| 23 | agent-pay | security, agents | @chamdom |
| 24 | Terra matcher | defi | @archtum66 |
| 25 | Tripwire | security, agents | @AVIEHUB |
| 26 | NairaRails | realworld | @Esimuda |
| 27 | PinPay | business, agents | @DavidHu178488 |
| 28 | DeadDrop | privacy, realworld | @DavidHu178488 |
| 29 | Leash | security, agents | @TensorustAI |
| 30 | Tollgate | agents, realworld | @TensorustAI |
| 31 | Settled | security, agents, realworld | @ashgoyal1990 |
| 32 | HADES OMEGA — Multi-Agent Orchestration System | business, swarms, security | @diana161184 |
| 33 | Claw Guard: Signing Gate for AI Agents | security, agents | @RUNECLAW_AI |
| 34 | Kyrona | security | @thesithunyein |
| 35 | Tune Up Research Desk | thesis, agents | @TuneUpArgentina |
| 36 | Loca | defi, business, swarms, security, agents | @loca_near |
| 37 | Sentinel | security | @NathanOyewole |
| 38 | Pal | open | @AkpanSunday193 |
| 39 | EarnScout | security, agents, open | @hustleone21 |
| 40 | Bolsillos | security, realworld, open | @TuneUpArgentina |
| 41 | StarFloor: Orbital Market Center & Zero-Gravity Colocation | defi, open | @yeabdotsuperint |
| 42 | NEAR Intents Value Accrual Thesis | thesis | @Apihpih69 |
| 43 | TEE Receipts | privacy, open | @chamdom |
| 44 | Agent Toll | security, agents | @madebydevx |
| 45 | PayPerCall on NEAR | business, agents, realworld | @madebydevx |
| 46 | Tijar app | business | @Musnadey |
| 47 | Agent Leash | security, agents | @tab_for_akshay |
| 48 | Sidelot | defi, agents, realworld, memecoins | — |
| 49 | HoldUp | security, realworld, open | @danial_x4 |
| 50 | AJO ON NEAR | realworld | @ayoadhe |
| 51 | PrivatePay Agent | privacy, agents | @hassan_samimi |
| 52 | TreasureHunt | games | @Sparkler_Labs |
| 53 | Payrein | security, agents | @CrissEthan7au |
| 54 | Approval Moment | security | @minotorXBT |
| 55 | Near Degen toolkit | defi | @cryptoworld_by |
| 56 | Hasp | agents | @thesithunyein |
| 57 | PayGuard | security, agents | @blokceyn |
| 58 | Arkhe Guard | security, agents | @Corvo_Arkhen |
| 59 | NEAR Growth Intelligence | thesis | @insightX01 |
| 60 | NEAR Books | thesis, open | @muliark |
| 61 | AgentVault | agents | @IrmanFebri75rb |
| 62 | ByLaw | security | @boredrhinodev |
| 63 | Bridle | business, security, agents | @UseBridle |
| 64 | NDBOT | defi, memecoins, social, open | @cryptoworld_by |
| 65 | Greed Machine | defi, business, swarms, security, agents, memecoins | @Greyw0rks |
| 66 | Guardrail | privacy, security, realworld, open | @FStrategy001 |
| 67 | Rootbound | swarms, security, agents | @wahabolaniyi090 |
| 68 | presign-guard for NEAR | security, agents | @x402fizzl |
| 69 | Deed | business, security, nfts | @Szczypek_96 |
| 70 | Werracle: Intra-Block AI Shield for NEAR Intents & Aurora EVM | defi, security, agents | @pCwOrM |
| 71 | NEAR Usage Thesis | thesis | @RainO_oDess |
| 72 | NEAR FeeLens | thesis | @37Nerion |
| 73 | Flock | swarms, agents | @Szczypek_96 |
| 74 | Key proof | security | @benny___5 |
| 75 | Leash | security, agents | @Hycorange |
| 76 | Petty Cash | realworld, social | @kasbsquall95 |
| 77 | ZEDEC PQOS aka. TIAMAT | defi, thesis, privacy, business, swarms, security, agents, realworld, open | @JDR1848 |
| 78 | NearGuard | security | @mawidjaya_157 |
| 79 | Measure | privacy, security | @tayonweb |
| 80 | Tollgate | security, agents | @dipo0x |
| 81 | NEXUS AiOS | swarms, security, agents | — |
| 82 | Settl | defi, realworld, open | @settl_near |
| 83 | Workcell | defi, security | @dotmantissa |
| 84 | Quittance | defi, privacy, realworld, open | @AustinChris_ |
| 85 | Judge on NEAR | privacy, security, agents | @cryptovijay1 |
| 86 | dareskro | business, agents, realworld | @Ju_l_C |
| 87 | PrivateDAO | defi, thesis, privacy, business, security, agents, realworld | @privateDAOOS |
| 88 | Redline | privacy, security, realworld | @nearagentic |
| 89 | Cobra on NEAR | agents, realworld | @Cadawallet |
| 90 | VRX | defi, privacy, business, realworld, open | @vettedrealty |
| 91 | NEAR, on evidence | thesis | @orenrot24 |
| 92 | x402-near | security, agents, realworld | @dahlinomine |
| 93 | AgentSig | business, security, agents | @AZ1Z1M |
| 94 | Agent Treasury | defi, business, security, agents, realworld | @isfaggod |
| 95 | Kalfou Swap — Cross-Chain Desk | defi | @Crypto_Lwa |
| 96 | MilestonePay | realworld | @casinodeveloper |
| 97 | Release Passport | security, nfts | @surthenort40906 |
| 98 | Patch Fund | security, social | @surthenort40906 |
| 99 | Sealed Exploit | privacy, security, agents, open | @edycutjong |
| 100 | Tontine | defi, thesis, business, swarms, security, agents | @0x___eth |
| 101 | The Build City Hackathon | privacy | @buidlcity |
| 102 | PROVEN | open | @cryptoAYA33 |
| 103 | Agent Crash Lab | security | @Amiinjalili |
| 104 | AgentTab | security, agents | — |
| 105 | FlashFirm | business, swarms, security, agents | @0xCaptain888 |
| 106 | Chai Pot on NEAR | security, agents, social | @farhanakhan33 |
| 107 | AgentBond | business, security, agents | @ikorofrancis1 |
| 108 | NEAR Intents Thesis — Tested | thesis | @luongs3 |
| 109 | AgentEscrow | security, agents | @dele_dave |
| 110 | nearswaps agent kit | defi, security, agents | @NearSwaps |
| 111 | Agent Allowance Guard | security | @alejandroso54 |
| 112 | NearGuard | security, agents | @georgebuilding2 |
| 113 | NearQuery | thesis | @marrnueldev |
| 114 | AgentGauntlet | security | @i_amtony_ |
| 115 | NEAR Guardian | security | @akihitozinnia |
| 116 | Halter | security, agents | @arashrahmani696 |
| 117 | Near-LEASH | security | @W3B_AI_SR |
| 118 | Proof of Ship on NEAR | agents, realworld, social | @HeyResearch |
| 119 | VAULTRY | defi, privacy, security | @Cryptoworld_01 |
| 120 | Clean Exit | security, agents | @l0rdWells |
| 121 | Tripwire | memecoins | @samaisback |
| 122 | XAUConnect Gold Router | defi, agents, realworld | @xaxmd5 |
| 123 | Sumplus CATS Service Pass | security, agents | @JakobJJJJJX |
| 124 | AgentGuard | security, agents | @Dark_ernity |
| 125 | Agent3 Purser Relay | agents | @JoeyXu13 |
| 126 | ClearSend Intents | realworld | @Emmanue07495029 |
| 127 | RedactGate | privacy, security | @mmixbizca |
| 128 | IntentWatch | security | @Surs51 |
| 129 | near-thesis | thesis | @rajeshmullippa |
| 130 | Leash | security, agents | @Aliqa3a |
| 131 | NePu | thesis, open | @Axlnd3r |
| 132 | Footnote | security, agents | @baegseungh7061 |
| 133 | SpactVault | defi, security, agents | @spactvault |
| 134 | KeyLease | swarms, security, agents | @RUNECLAW_AI |
| 135 | Shelflife | open | @Savage27z |
| 136 | Writ: Who Pays When Your AI Agent Gets Fooled | security, agents, open | @zuemennet |
| 137 | Kite | agents, realworld | @usekite__ |
| 138 | Aureus | defi, privacy, business, security, agents | @Omaofweb3 |
| 139 | Charter | defi, privacy, business, security, agents, open | @Spagero71 |
| 140 | Penstock | privacy, realworld | @_ace_won |
| 141 | TheRascalsDotFun | defi, agents, memecoins, social, open | @therascalsfun |
| 142 | NOVA Copy-Trading | privacy, security, agents | @jcarbonnell |
| 143 | AllTrades | business, agents, realworld | @GiacMoTrieuDo |
| 144 | Invoice Link | business, realworld | @brookxbt |
| 145 | Nims | games | @marrnueldev |
| 146 | Capgrate | business, security, agents | @Adeiza_web3 |
| 147 | Mandate | business, security, agents | @PostcardCrypto |
| 148 | CareRail | business, security, agents | @LainHolic |
| 149 | NEAR SENTINEL | security | @NguyenThan60809 |
| 150 | Lifeguard | defi, security, agents | @Timidan_x |
| 151 | GhostSign | security, agents | @anki_anc |
| 152 | Aegis | open | @AlvinAgustus |
| 153 | Payproof Global | business, realworld, open | @isonidavid |
| 154 | Foreman | business, swarms, security, agents | @SarwarBuild |
| 155 | GhosterDex | privacy, agents | @GhosterDex |
| 156 | Ash. | business, swarms, security, agents, realworld, social | @i_am_festac |
| 157 | Launchline | open | @clarky93795294 |
| 158 | Alphaforge | defi | — |
| 159 | Handover | nfts | @ApexSys_Dev |
| 160 | near-threshold-guardian | security | @exocognosis |
| 161 | Warrant | defi | @emmanuelcesc |
| 162 | NEAR Spending Vault | security | @silence_inf |
| 163 | Maven | security, games | @josephmarv3016 |
| 164 | nearbi | thesis, business | @nearbiai |
| 165 | Agent Undercover | swarms, agents, games | @necklace_btc |
| 166 | Aegis | security | @aegisonnear |
| 167 | Aegis Vault | business, security, agents, realworld | @SDesigan84042 |
| 168 | NEARpedia | agents, open | @UnityNodes |
| 169 | Skarbnik | privacy, security, agents | @pgreyy |
| 170 | NEARPORTAL | agents, realworld | @0xunholy |
| 171 | AgentGuard | security | @MrSharafi4 |
| 172 | Vouch | security, agents, open | @0xDUDS |
| 173 | ProofPay | business, agents, realworld | @the_annon_one |
| 174 | Ballast | defi, agents | @olliechapman |
| 175 | Allowance | security, agents | @Ritesh5969 |
| 176 | PredicTEE | privacy | @zhic18891 |
| 177 | DiveMarket | agents, games | @agungkzn |
| 178 | OddsHedge | defi, agents | @Maribtxn |
| 179 | AgentGuard | security | @Jibsonfta |
| 180 | Mint Scout for NEAR | security, agents, open | @SolGemLab |
| 181 | Agent shield | security | @magnuskrypt |
| 182 | Nearverse | games | @gabquelyn |
| 183 | Settleform | realworld | @DhaneeyP |
| 184 | Gideon | security | @Ade_lekeJr |
| 185 | Plumbline | business, security, agents | @0x_valid |
| 186 | NEAR Usage Thesis | thesis | @jccryp_11 |
| 187 | near | open | @isla69909 |
| 188 | PipTradeDex Private Intent | defi, privacy, security | @PipTradeDex |
| 189 | STYX | security, agents | @stratton001 |
| 190 | NEAR Thesis Lab | thesis | @mikeyXBT_ |
| 191 | GetLeash | privacy, business, security, agents, realworld, open | @usegetleash |
| 192 | AgentFence | security, agents | @jccryp_11 |
| 193 | Zinc | nfts | — |
| 194 | setllend | defi | @setllend |
| 195 | Roomy | realworld, social, open | @FocoBernardo |
| 196 | Buffer | business, security, agents | @therichworth |
| 197 | Overclock | agents, games | @AlvinAgustus |
| 198 | CartelBreaker | security, agents | @PKushneryk |
| 199 | Budget Broker MCP | security, agents | @dwkim601 |
| 200 | TabWrit | security, agents, realworld | @LesnaCrex |
| 201 | DUEL | security, games, social | @tajudeen |
| 202 | AEGIS // COUNTERFACTUAL | security | — |
| 203 | Relay | agents | @Sammy_Cryptguy |
| 204 | Dragons Market | defi, swarms, agents, nfts, social | @DragonsOnNear |
| 205 | Glassbox | security | @Ade_lekeJr |
| 206 | KAVREN | security, agents | @_joelad |
| 207 | Phylaxtag | realworld, nfts, open | @nestarich07 |
| 208 | NearPocket | agents, realworld | @ijustabi |
| 209 | Milestone Vault | privacy, security, agents, realworld | @t7pkaaa |
| 210 | Chaperone | defi, business, security, agents, realworld | @Big14teru |
| 211 | SCOGÉ Universe | games, nfts, open | — |
| 212 | Mandate | business, security, agents | @Emmageneris2001 |
| 213 | Pull Up | realworld | @trextxxy |
| 214 | SafeSpend | security, agents | @CryptoBurrito |
| 215 | Unpair | defi, privacy | @Unpairxyz |
| 216 | OneUp | defi, agents, nfts, open | @EthBoi_ |
| 217 | Sealed Dossier | privacy | @archtum66 |
| 218 | Logen | nfts, open | @chennl1u |
| 219 | NEAR Intents thesis: usage vs value capture | thesis | @Erfanmoheb1373 |
| 220 | Outlive | business, nfts | @olaph_lol |
| 221 | C0-op | swarms, security, agents | @ApexSys_Dev |
| 222 | Presafe | realworld | @Ahmardchain |
| 223 | SpecLock | realworld | @groziez |
| 224 | Torch | nfts | @BimaJadiva07 |
| 225 | Bazaar Sovereign | swarms, agents, games, nfts, open | @ReconScribe |
| 226 | Orbit | defi | @mcgrodeth |
| 227 | Safecell | security, agents, open | — |
| 228 | Saku: an AI agent's budget, enforced on NEAR | security, agents | @Gliana_agent |
| 229 | Stashway | security | @meguru_jr |
| 230 | Writ | nfts | @Viktor_ella_ |
| 231 | Boyun | privacy, swarms, social, open | @QianCherry2102 |
| 232 | VeilProof | privacy, agents | @ritual_meme |
| 233 | Heir | realworld, open | @peter_obisi |
| 234 | BEXLEY | defi, privacy, security | @IzuchukwuOffia |
| 235 | Tripwire | thesis | @danielwalter780 |
| 236 | NEARlyHuman - AI NPC NFT | games, nfts | @alphastack1 |
| 237 | ProofAgent AI | business, agents | @quayycera |
| 238 | Agent NFT | security, nfts | @neqro_61 |
| 239 | ArchivePass | nfts | @MAarashAlijo |
| 240 | AllTogether | social | @MAarashAlijo |
| 241 | Safe Near | security | @Raphael_Hoang |
| 242 | Supply | privacy, realworld | @moltycarlo |
| 243 | Agent-Receipt | business, security, agents | @ghulerushi14 |
| 244 | GhostShift | privacy, business, swarms, security, agents, open | @GGGODLIN |
| 245 | Kinwarden | privacy, security, agents, realworld | — |
| 246 | .Leash | security | @frank_olien123 |
| 247 | Meridian | swarms, agents, games, nfts, memecoins, social | @meridiantown |
| 248 | Sealed Ledger | privacy | @0_x_0_0_0 |
| 249 | DeepSea Hunter | games, nfts | @jarwono4444 |
| 250 | Blast Radius Zero — Agent Wallet Edition | security | @3rsona |
| 251 | AgentPay AI | agents | @BuleZari |
| 252 | Realsies | privacy, games, memecoins | @realsieslol |
| 253 | Leash | security | @peper1zal |
| 254 | TAINT | privacy, security, realworld | @HollowEchoes_23 |
| 255 | NEARShield – AI-Powered Traffic Attack Detection | security | @prathameshjknc |
| 256 | Lockstep | realworld, social | @Marc_Dvci |
| 257 | OATH | memecoins | @OpeyemiBolatit1 |
| 258 | AL-AMANAH FORTRESS | security, agents | @ssifi1972 |
| 259 | TokenGo | games | @r4b1nj0i3 |
| 260 | Public Agent Coin (PAC) | agents, memecoins | @PAC_agent |
| 261 | NEAR Payment Guard | security, agents | @chainwardai |
| 262 | Undiluted | privacy, business, realworld, open | @elioz404 |
| 263 | 777 giros gratis | defi, thesis, agents, realworld, games, memecoins, social, open | — |
| 264 | Clear to Pay | privacy, business, agents, realworld | @joezzyweb3 |
| 265 | NEAR Replay Lab | security | @grasserfa |
| 266 | OneShot | defi, security | @Jrken_ny |
| 267 | Setoff | realworld, open | @elioz404 |
| 268 | Afterlight | games, nfts | @GGGODLIN |

Observations from the list: repeated names (Leash ×5 variants, Tollgate ×3, AgentGuard ×4, Tripwire ×3, Aegis ×3, Allowance ×2, Mandate ×2, NearGuard ×2, NEAR Usage Thesis ×2, Writ ×2); several builders submitted two projects (allowed up to 2).

---

## 17. Gaps / not found

- Winners of this NEAR HACKATHON are not out yet (results due by 18 Nov 2026 23:59 UTC).
- The public project feed exposes only id, name, tracks and demo URL — repository links and descriptions are not public.
- The site does not name an individual organizing team; NEAR / NEAR Foundation is the organizer.
- Illia's 5 Nov list of build ideas lives on X and wasn't readable without login.
- Prize placements per project (1st/2nd/honorable mention) for MetaBUILD III, [REDACTED] and One Trillion Agents were not shown on the Devpost galleries.
- No published winners found for NEAR Hacks (HackerEarth), Zcash x NEAR Intents, Bankrbot/Shade Agents, NEARCON 2022 IRL.

---

## Sources

- https://nearhackathon.com/ · https://nearhackathon.com/HACKATHON.md · https://nearhackathon.com/request-changes · https://nearhackathon.com/api/projects
- https://github.com/nearai/near-hackathon-prompt-examples (README, 00-setup.md, SUBMITTING.md, tracks/01–13)
- https://www.near.org/blog/near-hackathon-build-beyond-boundaries
- https://x.com/NEARProtocol · https://x.com/NEARProtocol/status/2112257967818997891 · https://x.com/winsznx/status/2117178466298720457
- https://www.lookonchain.com/feeds/77712 · https://www.gate.com/en-us/news/detail/near-protocol-launches-hackathon-with-250k-prize-pool-starting-november-1-17905435
- https://coinfomania.com/near-protocol-launches-hackathon-with-250k-prize-pool/ · https://coinfomania.com/near-protocol-retweets-hackathon-announcement-with-250k/ · https://www.tronweekly.com/near-protocol-advances-its-ecosystem-as-near-price-outlook-improves/ · https://coinalertnews.com/news/2026/10/19/near-hackathon-prize-vc-judges · https://www.kucoin.com/news/community/NEAR/6aecc09cbbcb52000745f8af · https://www.startupgrantsindia.com/near-hackathon-2026
- https://www.iq.wiki/en/wiki/near-foundation · https://chaincatcher.com/en/tags/Illia%20Polosukhin · https://beincrypto.com/near-foundation-ceo-marieke-flament-resigns · https://www.mexc.com/news/134801 · https://incrypted.com/es/el-ceo-de-helius-mert-mumtaz-se-ha-incorporado-a-la-junta-directiva-de-la-near-foundation/ · https://iq-wiki-ui.vercel.app/wiki/george-zeng · https://research.nansen.ai/articles/near-quarterly-report-q2-2025
- https://medium.com/nearprotocol/metabuild-2-hackathon-winners-f0daf9586c09 · https://www.herox.com/NEARMetaBUILD · https://medium.com/omnity/2dverse-wins-the-near-metabuidl-hackathon-2021-431ac87324d6 · https://pages.near.org/?p=18193 · https://near.foundation/?p=19756 · https://metabuild.devpost.com/project-gallery
- https://www.near.org/blog/near-at-ethdenver-hackathon-bounty-winners · https://www.near.org/blog/meet-the-2023-nearcon-irl-hackathon-winners · https://nearhacks.hackerearth.com/
- https://redacted.devpost.com/project-gallery · https://thedefiant.io/news/defi/shape-the-user-owned-future-at-redacted-in-bangkok · https://allhackathons.com/hackathon/redacted-hackathon
- https://www.near.org/blog/coinbase-onchain-ai-hackathon · https://1t-agents.devpost.com/project-gallery · https://coinlaunch.space/events-contests/near-protocol-one-trillion-agents-hackathon/ · https://bitteprotocol.substack.com/p/from-experiment-to-adoption-how-bittes
- https://www.near.org/blog/building-useful-agents-sf-hackathon-shows-the-power-of-practical-ai · https://www.near.org/blog/near-protocol-rewards-what-it-means-to-graduate-from-a-hackathon
- https://forum.zcashcommunity.com/t/zcash-x-near-intents-hackathon/50604 · https://fringe-brow-647.notion.site/Bankrbot-Extension-Hackathon-1dd09959836d808f973fec6888301c65
