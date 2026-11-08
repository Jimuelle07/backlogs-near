# NEAR HACKATHON — The 13 Tracks, Understood, Ranked, and Jev-Powered

- **Written:** Sun 8 Nov 2026, 13:10 PHT
- **Time left:** deadline is 14 Nov 23:59 UTC = **Sat 15 Nov, 07:59 PHT** → about **6 days 19 hours**
- **Inputs:** the 13 official starter prompts (github.com/nearai/near-hackathon-prompt-examples), HACKATHON.md, the live submission feed (268 projects), and TypeSafe AI's Jev docs + launch post.
- **Companion file:** `near_hackathon_web.md` (raw data capture).

> **Browser-verified at 13:15 PHT:** typesafe.ai (homepage, all FAQ answers, Series A post, Jev 1.14 post), the live NEAR submission feed (still 268, counts unchanged), and every scale figure below (sources at the end).

---

## Part 1 — What Jev actually is (and isn't)

**TypeSafe AI** (SF lab founded by Diogo Almeida, ex-OpenAI, who worked on the research behind ChatGPT) released **Jev** on 15 Sep 2026: the first "**System One Model**". The name comes from Kahneman's fast/slow thinking (System 1) and from economist William Stanley Jevons (cheaper intelligence → far more uses).

### The core idea in one line
Jev is a **frontier-intelligence function call**: send unstructured *state* + typed *questions* → get back **typed answers with calibrated probabilities**. No text generation, no parsing, no type errors.

### Primitives (question types)
| Type | Asks | Returns |
|---|---|---|
| **Choice** | pick one option from a list (up to 255 options) | `choice`, `probabilities`, `confidence` |
| **Score** | place the state on an ordered rubric | `score`, `probabilities`, `confidence` |
| **Noul** | is this statement true? | `noul` = probability 0–1 |
| **Box** | where is X in this image? | `box` (top/bottom/left/right), `confidence` |

- Many questions per request, evaluated **in parallel and in isolation** against the same state → adding questions barely adds latency and causes no "context rot".
- Best practice: **atomic gut-check questions**, combined with logic **in your code** (weights live in code, not in prompts).

### Numbers TypeSafe publishes
| Claim | Value |
|---|---|
| Latency | 70–500 ms end-to-end (served from US West) |
| Price | **$0.042 per million input tokens** ($42 per billion); output free |
| vs LLM workflows | "193.6× faster, 444.6× cheaper" (their workflow evals; they say this is the high end) |
| Example call | $0.000081 and 0.114 s vs an LLM at $0.013880 and 8.566 s |
| Type safety | schema-guaranteed, 0 type errors; they claim it "can't hallucinate" in the sense of off-schema output |
| Real-time demo | Jev playing Doom at ~10 decisions/sec ≈ $7/hour |
| Case study | Jack & Jill cut candidate-screening cost 88%, 2× faster |
| Accuracy (their workflow chart) | Jev ≈ **68%**; similar to GPT-5.6 Terra and Claude Sonnet 5 at far lower cost; GPT-5.6 Sol and Claude Opus 5 score higher but cost much more |
| Format errors (OpenRouter snapshot, 10 Sep 2026) | Jev 0.00% structured-output and tool-call errors (a schema guarantee, not a measured error rate); e.g. Claude Sonnet 5 12.6% structured-output errors, GPT-5.6 Sol 22.1% tool-call errors |
| Price vs. Claude Fable 5.1 | 238× lower input price ($0.042 vs $10 per million tokens) |

### What the FAQ says (expanded in the browser)
- **Good at:** common-sense judgments — classifying content, routing requests, scoring responses, evaluating information — combined in code into bigger workflows.
- **Struggles with:** tasks needing extended reasoning, e.g. complex math or chess-like planning → use a reasoning model there.
- **Can it be wrong?** Yes. It guarantees the *shape* of the answer, not correctness: it can't invent an option outside your list, but it can pick the wrong one. Use probabilities/confidence to decide when to act vs. review.
- **Deterministic?** They aim for *consistency* (similar meaning → similar decision even if wording changes), which they consider more useful than exact determinism.
- **Prices subsidized?** They say Jev is served profitably at current prices and they expect prices to fall.
- **Availability:** **Jev is now open to everyone** — create an account; support@typesafe.ai, sales@typesafe.ai, and a Discord for questions.
- **vs JSON mode:** forcing an LLM into JSON gives valid format but can waste intelligence; Jev is trained for structured decisions from the start.

### Company status (matters for judging)
- **Series A, 9 Oct 2026: $870M at a $7.5B valuation, led by Andreessen Horowitz (a16z)**, with Sequoia and existing investor DCVC; **Martin Casado** (a16z) joined the board. They report a third of the Fortune 500 using Jev.
- **Judging angle:** NEAR judge **Eddy Lazzarin is from a16z crypto**. A16z backed TypeSafe. This doesn't change scoring rules, but a well-used Jev integration is a credible, recognizable stack choice for at least one judge — and an easy talking point in the demo post.

### Jev 1.14 (14 Oct 2026) — new "danger zone" options
- `jev-latest` now points to **jev-1.14.0** (small improvements everywhere, biggest gains in **multilingual** — useful for Taglish/Filipino inputs).
- Experimental flags via API headers (not production-vouched): `TypeSafe-Danger-Zone-Images: true` (images anywhere in state, instructions or criteria), the **Box** type (bounding box, jev-1.14.0 only), `TypeSafe-Danger-Zone-Long-Context: true`.
- They state they **don't train on your queries** (optional opt-in only helps them debug).

### The confidence pattern (the part that matters most for this hackathon)
Every Choice/Score answer carries `confidence` (0 = even spread, 1 = certain). TypeSafe's recommended architecture:
- **High confidence → act automatically**
- **Medium → ask / confirm / gather more**
- **Low → refuse, escalate to a human, or fall back**
- **Thresholds scale with stakes**: a read-only action can run at 0.5; moving money needs 0.9+.

**This is exactly the shape of half the hackathon.** The organizers' own prompts ask for "allow / warn / block", "ask a human when it's warn", "counter once then accept or walk", "small payouts auto-approve, mid needs one council member, large become a DAO proposal". Those are confidence-and-stakes gates. Jev ships that pattern natively.

### API in 10 seconds
`POST https://api.typesafe.ai/v1/systemone` with `Authorization: Bearer $TYPESAFE_API_KEY`, body `{ state, model: "jev-latest", questions: {...} }`. SDKs: `pip install typesafe-sdk` / `npm install @typesafe-ai/sdk`. Agent skill: `npx skills add typesafe-ai/skills --skill typesafe-ai`. Playground: console.typesafe.ai/playground.

### Honest limits (plan around these)
1. **Access is open now** (no waitlist) — still create the account and key *today*. Build behind a small interface with TypeSafe's open-source "System One LLM" adapter (github.com/typesafe-ai/system-one-adapter-python) as a fallback, so an outage never kills the demo.
1b. **~68% workflow accuracy** in their own chart — strong per dollar, not the most accurate model. Design for it: atomic questions, confidence gates, and human/LLM escalation for the uncertain tail.
2. **Not a TEE.** Data goes to TypeSafe's servers. This clashes with the *Privacy* track's spirit unless Jev only sees non-sensitive features.
3. **No long reasoning, no text output.** Decompose; use an LLM (NEAR AI Cloud) for anything that must be written.
4. **Centralized dependency.** Judges will ask "where is NEAR essential?" — Jev must be the *brain*, NEAR must be the *hands and the ledger* (custody, settlement, enforcement, audit trail).
5. **Latency from Manila → US West** adds round-trip time; fine for everything except HFT-style DeFi.
6. Rules check: third-party tools are allowed (Q-005, Q-011). Name Jev in the README.

### The cost story you can put in any README
A check of ~500 input tokens costs ≈ **$0.000021**. One million agent decisions ≈ **$21**. That makes "check *every* action" economically trivial — which LLM-based guardrails can't claim.

---

## Part 2 — The lenses (creative questions used on every track)

Ordinary questions ("is it big?") produce ordinary answers. These are the lenses used below:

1. **The 3 a.m. test** — Who loses money while everyone is asleep if this isn't solved?
2. **The irreversibility test** — When it goes wrong, can it be undone? (Blockchains say no.)
3. **The grandmother test** — Would someone who has never heard of crypto benefit without learning a single new word?
4. **The 10× tomorrow test** — If AI agents are 10× more common next year, does this problem grow, shrink, or vanish?
5. **The silent-victim test** — Who is harmed but would never file a complaint (because they don't know, or can't)?
6. **The duct-tape census** — What spreadsheet, group chat, or manual approval is doing this job today?
7. **The villain's view** — How would an attacker profit from this problem *not* being solved?
8. **The "oh" moment** — What is the single 30-second clip that makes a judge say "oh"?
9. **The crowd test** — How many of the 268 submissions already chase this? Where's the empty lane?
10. **The Jev test** — Is there a repeated, fast, judgment-shaped decision here where calibrated confidence changes behavior?

---

## Part 3 — Ranking by POWER of the topic (impact if solved)

Power = size of the problem × severity × irreversibility × how urgently it grows. Competition and buildability are scored separately in Part 5.

| Rank | Track | Power | One-line reason |
|---|---|---|---|
| 1 | AI Security & Defense | ★★★★★ | Every agent that holds money is one prompt injection away from an irreversible loss, and agents are multiplying. |
| 2 | Real-World Money | ★★★★★ | Hundreds of billions of dollars a year move through slow, expensive rails used by the people who can least afford fees. |
| 3 | Agent Economy | ★★★★★ | Whoever defines how machines pay machines defines the next payment network. |
| 4 | Privacy & Private AI | ★★★★☆ | Everyone's most sensitive data is being pasted into AI; nobody can verify where it goes. |
| 5 | Autonomous Business | ★★★★☆ | One-person companies run by agents are coming; the missing part is safe, auditable money flows. |
| 6 | Unstoppable DeFi | ★★★★☆ | Censorship-resistant markets matter most where banks fail people — but it's a crowded, mature category. |
| 7 | AI Swarms | ★★★☆☆ | Multi-agent markets are early; huge later, speculative today. |
| 8 | Social Money | ★★★☆☆ | Communities run billions in treasuries through slow multisig votes and spreadsheets. |
| 9 | Open Innovation | ★★★☆☆ | Ceiling is unlimited, floor is zero — power depends entirely on the idea. |
| 10 | Investment Thesis | ★★☆☆☆ | Real value to NEAR and investors, small value to the world — but highly relevant to *these* judges. |
| 11 | NFTs That Do Something | ★★☆☆☆ | "NFT as account" is a genuinely good primitive, but demand is currently thin. |
| 12 | Games With Real Economies | ★★☆☆☆ | Billions of gamers, but real-money game economies have a long failure history. |
| 13 | Memecoins With Mechanics | ★☆☆☆☆ | Entertainment; the main "problem solved" is that most memecoins are pure extraction. |

---

## Part 4 — Each track, deeply

Format for every track: **What they're really asking → The real problem → Scale & who's hurt → Lens answers → Starter-prompt critique → Jev leverage → Idea(s) → Risks.**

---

### #1 · AI Security & Defense (`security`) — POWER ★★★★★

**What they're really asking:** "Give AI money without giving it the keys to everything." Spending limits, policy engines, sandboxed wallets, reputation, scam detection. The starter idea is a *counterparty check* returning allow/warn/block before an agent pays.

**The real problem:** An agent that can sign transactions will eventually read a malicious web page, email, or tool output telling it to send funds. On a blockchain, that mistake is final.

**Scale & who's hurt:**
- Crypto theft: **$2.2B in 2024 → $3.4B in 2025** (Chainalysis; Bybit alone $1.5B). Personal-wallet compromises hit **158,000 incidents / 80,000+ victims** in 2025. That's *before* autonomous agents hold meaningful balances.
- Who's hurt: every user who delegates spending to an agent; every business that lets an AI pay invoices; every DAO with an agent treasurer.

**Lens answers:**
- *3 a.m.:* exactly the hours agents run unattended.
- *Irreversibility:* total. No chargebacks.
- *10× tomorrow:* the problem scales linearly with agent adoption — the strongest "grows with time" track.
- *Villain's view:* prompt injection is cheap to attempt and profitable at scale; one poisoned web page can hit thousands of agents.
- *Silent victim:* the user who sees a "successful" agent run and never notices a small, repeated leak.
- *Crowd test:* **140 of 268 projects** picked this track. "Leash", "Guard", "Tollgate", "Allowance" appear many times. Spending caps alone won't stand out.

**Starter-prompt critique:** Strong (signals list, function-call key scoping, attack demo). Weakness: rule-based signals (age, code change) are easy to game, and nearly every competitor will build them.

**Jev leverage — very high (best natural fit):**
- Turn every outgoing transaction into a Jev request: state = tx + agent's task + recent context; questions = `Choice(allow|warn|block)`, `Noul("this transfer serves the user's stated task")`, `Noul("instructions came from untrusted content")`, `Score(drift from user intent)`.
- **Stakes-scaled thresholds:** $1 needs confidence 0.5; $1,000 needs 0.95 + human tap. This is TypeSafe's own documented pattern, applied to money.
- Speed + cost = check **every** action, not samples. ~$0.00002 per check.
- Differentiator vs the 140: **calibrated intent-matching**, not just limits.

**Ideas:**
- **"Intent Notary"** — a NEAR contract that only executes an agent's payment if a Jev verdict (signed by a relayer/attestation of the call) matches policy; graded autonomy by amount; human approval flow for "warn"; full on-chain audit log. Attack demo: prompt-injected agent tries to drain → stopped with the reasons shown.
- **"Second Opinion"** — Jev audits the *reasoning trace* of a big LLM agent before it signs ("does the plan contain a step the user never asked for?"). TypeSafe lists "verify everything / detect jailbreaks" as a core use.

**Risks:** crowded; judges will have seen 100 guards. Win on **calibration + attack demo + numbers** (false-block rate, catch rate, cost per 1,000 checks).

---

### #2 · Real-World Money (`realworld`) — POWER ★★★★★

**What they're really asking:** payroll, invoices, remittances, merchant payments — "something a normal company could use tomorrow". Starter: freelancer invoicing where the client pays from any chain and the freelancer gets USDC on NEAR, gasless.

**The real problem:** Moving money across borders is still slow, opaque and expensive, and the cost falls on the people with the least.

**Scale & who's hurt:**
- Global remittances **$905B in 2024, $685B to low/middle-income countries**; average cost of sending $200 was **6.36% in Q3 2025** — more than double the UN 3% target; **banks average ~15%** (World Bank RPW Issue 54).
- The Philippines received a record **$39.62B in personal remittances in 2025** (cash: $35.63B, **7.3% of GDP**; top source the US at 39.7%) — BSP. You are building from the right country for this track.
- Back-of-envelope: at ~6% on the Philippines' cash flows alone, fees are on the order of **$2B a year** leaving OFW families (rough illustration, not an official figure).
- Who's hurt: OFW families, freelancers paid by foreign clients, small merchants losing margin to card fees.

**Lens answers:**
- *Grandmother test:* the only track where the end user may never know crypto is involved — that's the win condition.
- *Duct-tape census:* GCash screenshots in group chats, manual invoice chasing, a bookkeeper re-typing bank statements.
- *Silent victim:* the receiver who loses 5–8% to fees and FX spread and thinks that's just "the rate".
- *Crowd test:* 56 projects — moderate.

**Starter-prompt critique:** Excellent framing ("write the README for a bookkeeper"). Hard parts: compliance/KYC (out of scope for a hackathon; acknowledge it), and Intents has no testnet (Q-007: tiny mainnet amounts + `dry: true` quotes).

**Jev leverage — high:**
- Invoice/receipt understanding (Choice: expense category; Score: completeness; Box: find total/date on a photographed receipt).
- **Payment reconciliation:** match incoming transfers to open invoices (Choice over candidates, confidence → auto-match vs. "please confirm").
- **Fraud / fake-invoice screening** before paying ("does this invoice match a known vendor's style?").

**Ideas:**
- **"Padala Rails"** — an OFW sends USDC/any token via Intents; the family receives to a NEAR named account (`lola.near`) and cashes out; Jev auto-categorizes and flags unusual requests ("urgent, send now" scams targeting families). Demo in Taglish for authenticity.
- **"Bookkeeper-proof invoicing"** — the starter idea plus Jev reconciliation and an accountant-ready CSV.

**Risks:** real off-ramps need licensed partners — be explicit about what's simulated.

---

### #3 · Agent Economy (`agents`) — POWER ★★★★★

**What they're really asking:** agents that earn, spend, negotiate, hire other agents and pay for APIs/compute/data. Starter: a "general contractor" agent that splits a task, buys parts of it, checks the work, pays — all inside a budget.

**The real problem:** Agents can *do* work but can't *transact* safely: no identity, no budget enforcement, no way to judge whether bought work is any good.

**Scale & who's hurt:** Every API, dataset and compute provider will be sold to machines; x402-style "pay per call" is emerging (PingPay facilitator is in the prompt). The hurt party today: builders paying flat subscriptions for APIs their agents call twice.

**Lens answers:**
- *10× tomorrow:* grows with agents.
- *Villain's view:* agents selling junk to other agents; agents overpaying because negotiation is naive.
- *"Oh" moment:* an agent hiring another agent on market.near.ai, rejecting the first delivery, and paying the second — live.
- *Crowd test:* **130 projects.** Heavily overlapped with security.

**Starter-prompt critique:** Very good, but "checks the work" is the hard, under-specified part — that's where most entries will be weak.

**Jev leverage — high:**
- **Quality gate on delivered work:** Score against acceptance criteria, Noul("meets spec"), confidence → pay / dispute / ask human.
- **Negotiation decisions:** Choice(accept|counter|walk) given quote, budget, history.
- **Vendor selection** across up to 255 candidate agents in one call.

**Idea:** **"Escrow Judge"** — buyer funds escrow in a NEAR contract; seller agent delivers; Jev scores the delivery against the job spec; high confidence → auto-release, medium → partial release + revision request, low → human arbiter. Every verdict + probabilities logged on-chain. Works for Agent Market jobs.

**Risks:** crowded; differentiate with the *verification* angle, which most agent-payment projects skip.

---

### #4 · Privacy & Private AI (`privacy`) — POWER ★★★★☆

**What they're really asking:** confidential compute, private finance, AI on sensitive data with proof (TEE attestation via NEAR AI Cloud). Starter: private expense auditor with a verified-attestation panel.

**The real problem:** People paste medical records, bank statements and contracts into AI with no way to verify who sees them.

**Scale & who's hurt:** essentially every AI user; most acutely health, legal, finance, journalists, dissidents.

**Lens answers:**
- *Silent victim:* the person whose data leaks into training or logs and never finds out.
- *Grandmother test:* "the AI read your bank statement and *proved* nobody else could" is understandable.
- *Crowd test:* 44 projects.

**Jev leverage — LOW / conflicting.** Jev is not a TEE; sending private data to it undermines the track's thesis. Only safe uses: Jev on *redacted/derived features*, or Jev as a router that decides *which* data needs the TEE path. Honest recommendation: **don't make Jev central here**; use NEAR AI Cloud.

**Idea (if you still want it):** **"Privacy Router"** — Jev sees only metadata ("document type", "contains IDs?" via local pre-redaction) and routes sensitive items to NEAR AI Cloud TEE, non-sensitive to cheap processing; dashboard proves which path each item took with attestation. Still a stretch.

---

### #5 · Autonomous Business (`business`) — POWER ★★★★☆

**What they're really asking:** AI-run businesses (treasury, sales, procurement, revenue share) where humans only set constraints. Starter: one-agent research shop with config.yaml rules and a kill switch.

**The real problem:** Solo founders and tiny teams drown in operations; full autonomy is unsafe without enforceable limits and a public ledger.

**Lens answers:**
- *Duct-tape census:* Stripe dashboard + spreadsheet + founder approving every refund at midnight.
- *"Oh" moment:* a business completes sale → buys its own inference → pays contributors, all within 2 minutes, with a public ledger.
- *Crowd:* 46.

**Jev leverage — high:** every operational micro-decision (refund? discount? which supplier? is this lead real? should this ticket escalate?) is a Choice/Noul with confidence. The **constraint file becomes thresholds** — "refunds under $20 at confidence ≥0.8 auto-approve".

**Idea:** **"Policy-as-thresholds company"** — config.yaml maps each decision type to Jev questions + confidence/amount thresholds; NEAR enforces spend caps via function-call keys; every decision is logged with its probabilities; kill switch on-chain.

---

### #6 · Unstoppable DeFi (`defi`) — POWER ★★★★☆

**What they're really asking:** exchanges, perps, lending, vaults, trading agents settling cross-chain via NEAR Intents. Starter: cross-chain DCA vault with slippage limits and a dry-run mode.

**The real problem:** cross-chain value movement is still fragmented, custodial and full of bridges that get hacked.

**Lens answers:**
- *Villain's view:* MEV, bad quotes, phishing tokens.
- *Crowd:* 40, but a very mature category; RHEA added token prizes (more attention).
- *Grandmother test:* weak, unless it's "save in bitcoin automatically".

**Jev leverage — medium:** quote sanity checks, token-scam detection ("is this token a lookalike?"), risk scoring of a pool before depositing. Latency (Manila→US) rules out sub-second trading edges.

**Idea:** **"Sane DCA"** — the starter vault plus a Jev pre-trade gate (scam-token Noul, abnormal-market Score) that pauses buys during manipulation, with a log of skipped buys and why.

---

### #7 · AI Swarms (`swarms`) — POWER ★★★☆☆ (but a hidden gem — see Part 5)

**What they're really asking:** many agents, one economy — bidding, pooling, intent-settled markets. Starter: group-buying swarm (20 buyers, 5 sellers, sealed bids), each agent a sub-account, plus an LLM-free simulation mode.

**The real problem:** single agents are weak buyers; pooled demand gets better prices — but coordinating hundreds of agents with LLMs is slow and expensive, which is *why* the starter prompt asks for scripted strategies.

**Lens answers:**
- *10× tomorrow:* the more agents exist, the more this matters.
- *"Oh" moment:* 500 agents bidding live on screen, clearing price moving, each with an on-chain sub-account.
- *Crowd:* **only 19 projects.**

**Jev leverage — VERY HIGH (best "why only Jev makes this possible" story):** The prompt explicitly avoids LLMs because they're too slow/costly per agent per round. Jev removes that constraint: **hundreds of genuinely intelligent agents deciding every round, at ~100–300 ms and fractions of a cent.** That's a narrative no LLM-based swarm can tell.
- Each agent: `Choice(bid level)`, `Noul("join this pool")`, `Score(urgency)` from its own private state.
- Calibrated confidence = agents that *know* when they're unsure bid conservatively → emergent, more stable markets (measurable!).

**Idea:** **"Thousand-Agent Market"** — compare three runs side by side: scripted agents, LLM agents (capped by cost), Jev agents (many). Show price efficiency, cost per round, latency. Settle winning rounds via Intents/testnet sub-accounts (`buyer-417.swarm.testnet`).

---

### #8 · Social Money (`social`) — POWER ★★★☆☆

**What they're really asking:** build *on* Sputnik DAO / Trezu — shared budgets, rewards, reputation-gated access. Starter: bounty board with earned trust and tiered approvals.

**The real problem:** DAOs and communities approve every small payout through slow council votes or trust a few people blindly; contributors wait weeks to get paid.

**Lens answers:**
- *Duct-tape census:* Discord threads + Google Sheets + "ping the multisig signers".
- *Silent victim:* contributors who quietly leave because payment is slow.
- *Crowd:* **only 15 projects.**

**Jev leverage — high:** judge bounty completion (Score vs acceptance criteria; Noul "evidence link actually shows the work"), spam/duplicate claim detection, reputation updates — and map confidence × reputation × amount onto the starter's three approval tiers.

**Idea:** **"Fast Lane Treasury"** — Trezu/Sputnik remains custody; Jev verdict + contributor reputation decides auto-approve / one-signer / full proposal; public board; every reputation point traceable to a verified bounty.

---

### #9 · Open Innovation (`open`) — POWER ★★★☆☆ (variable)

**What they're really asking:** anything that fits nowhere else; can be combined with any track. Starter: inheritance account via Chain Signatures with guardians and cancellable release.

**Note:** the inheritance starter is *genuinely powerful* (lost-forever crypto when holders die is a real, large problem) and is competing with only a few "Heir" projects. Jev fits it nicely: classify guardian claims and evidence, detect coercion signals, score "owner may be alive but offline" scenarios.

**Jev leverage:** depends on idea; Open is also the best **second track** to add to any Jev project.

---

### #10 · Investment Thesis (`thesis`) — POWER ★★☆☆☆ (but judge-magnet)

**What they're really asking:** an evidence-first thesis on NEAR with re-runnable queries, dashboards, THESIS.md with evidence for *and against*.

**Why it matters more than its "power" score:** the judges are NEAR's CEO and top crypto VCs (a16z crypto, Electric, Dragonfly, cyber•Fund). This track is literally them reading investment research.

**Crowd:** 24.

**Jev leverage — high, unusual angle:** **map-reduce over the chain.** BigQuery gives raw transactions; Jev can *label* them at scale (Choice: "retail swap / arbitrage bot / market maker / airdrop farming / agent payment") for dollars, not thousands. That produces a metric nobody else has: *what share of NEAR activity is real humans vs bots vs agents*.
- 1M transactions × ~500 tokens ≈ **$21** on Jev.

**Idea:** **"NEAR, Labeled"** — re-runnable pipeline: BigQuery → Jev labels → dashboard of "organic vs automated activity" over time, Intents volume by user type; THESIS.md with counter-evidence. Publish labeling accuracy on a hand-checked sample.

---

### #11 · NFTs That Do Something (`nfts`) — POWER ★★☆☆☆

**What they're really asking:** NFTs as accounts (own money, royalties, credentials). Starter: membership NFT controlling a sub-account; selling the NFT moves wallet + rights.

**Real value:** transferable businesses/memberships with built-in cash flow; clean ownership transfer. **Crowd:** 20.

**Jev leverage — low/medium:** credential verification, metadata quality, "does this holder meet the club's rules?". Not central.

---

### #12 · Games With Real Economies (`games`) — POWER ★★☆☆☆ (but best Jev demo)

**What they're really asking:** NPCs with wallets and self-adjusting economies; judged on the game loop; bonus if players never notice the chain. Starter: market-town game with NPC merchants pricing from stock and demand, fast-forward mode.

**Real value:** modest for the world; huge for *demo impact*. **Crowd:** only 17.

**Jev leverage — VERY HIGH:** TypeSafe's flagship demo *is* a game (Jev playing Doom at 10 decisions/sec ≈ $7/hour). NPC merchants that make real-time, calibrated pricing/trading decisions every tick are exactly Jev's strength — and "show the merchant's reasoning in a tooltip" maps to showing Jev's probabilities.

**Idea:** **"Market Town, Live"** — dozens of Jev merchants reacting every second, fast-forward week in a minute, items as NEP-245, social login, merchants' wallets as sub-accounts. The tooltip shows "70% raise price / 25% hold / 5% close shop".

---

### #13 · Memecoins With Mechanics (`memecoins`) — POWER ★☆☆☆☆

**What they're really asking:** memecoins whose meme *does* something; judged on the mechanic. Starter: streak coin with daily community check-ins, mint/burn.

**Real problem:** Solidus Labs' 2025 Rug Pull Report found **98.6% of 7M+ Pump.fun tokens** showed pump-and-dump/rug patterns (only ~97,000 kept $1,000+ liquidity) and **93% of 361,000 Raydium pools** showed soft-rug traits; Pump.fun disputed the methodology. **Crowd:** only 10 (emptiest track).

**Jev leverage — medium:** sybil scoring of check-ins (Score "how bot-like is this account?"), meme challenges judged by Jev ("does this submission complete today's ritual?").

---

## Part 5 — Ranking by OPPORTUNITY (what to actually build)

Every track pays the same $10K / $3K / $2K, so a less crowded track is worth more per unit of effort. Scores 1–5:

- **Power** — from Part 3
- **Space** — inverse crowding (≤20 projects = 5, 21–30 = 4, 31–50 = 3, 51–80 = 2, 80+ = 1)
- **Jev fit** — how central and defensible Jev is
- **Buildable** — realistic in ~6.5 days with a polished demo
- **Judge appeal** — fits this jury (NEAR CEO + crypto VCs + AI screeners)

| Rank | Track | Power | Space | Jev fit | Buildable | Judges | **Total /25** | Projects now |
|---|---|---|---|---|---|---|---|---|
| 1 | **AI Swarms** | 3 | 5 | 5 | 4 | 4 | **21** | 19 |
| 2 | AI Security & Defense | 5 | 1 | 5 | 4 | 5 | **20** | 140 |
| 3 | **Social Money** | 3 | 5 | 4 | 4 | 3 | **19** | 15 |
| 3 | **Games With Real Economies** | 2 | 5 | 5 | 4 | 3 | **19** | 17 |
| 3 | **Investment Thesis** | 2 | 4 | 4 | 5 | 4 | **19** | 24 |
| 3 | Agent Economy | 5 | 1 | 4 | 4 | 5 | **19** | 130 |
| 3 | Real-World Money | 5 | 2 | 4 | 4 | 4 | **19** | 56 |
| 8 | Autonomous Business | 4 | 3 | 4 | 3 | 4 | **18** | 46 |
| 9 | Unstoppable DeFi | 4 | 3 | 3 | 3 | 4 | **17** | 40 |
| 10 | Open Innovation | 3 | 3 | 4 | 3 | 3 | **16** | 45 |
| 10 | Privacy & Private AI | 4 | 3 | 2 | 3 | 4 | **16** | 44 |
| 12 | NFTs That Do Something | 2 | 5 | 2 | 3 | 3 | **15** | 20 |
| 12 | Memecoins With Mechanics | 1 | 5 | 3 | 4 | 2 | **15** | 10 |

**Big takeaways**
- **Security and Agents are the most powerful *and* most crowded** (270 combined selections). Enter them only as a *secondary* track or with a sharp differentiator.
- **Swarms, Games and Social are under-filled and Jev-shaped.** Same prize as Security, a tenth of the competition.
- **Multi-track is allowed** (one submission, select every track that fits). A well-designed project can legitimately qualify for 3–4 tracks *and* the $55K grand prize.

---

## Part 6 — Three recommended Jev builds (best bets)

### Bet A — "Thousand-Agent Market" (Swarms + Agents + Open)
- **Pitch:** Swarm markets have been stuck with dumb scripted bots because LLM agents cost too much per decision. Jev makes every agent smart for ~$0.00002 per decision, so a real market of hundreds of agents runs live.
- **NEAR role:** each agent = sub-account; rounds settle via Intents (dry quotes) / testnet transfers; coordinator contract enforces sealed-bid rules.
- **Demo moment:** a live dashboard where 500 agents bid; a side panel shows "cost of this round: $0.004" vs. estimated LLM cost.
- **Proof metrics:** price efficiency vs scripted baseline, cost per round, latency, how calibrated agents behave when uncertain.

### Bet B — "Intent Notary" (Security + Agents + Real-World Money)
- **Pitch:** Spending limits stop big thefts but not smart ones. Intent Notary asks "does this payment actually serve what the user asked for?" before every transaction, with stakes-scaled confidence thresholds.
- **NEAR role:** function-call-key-scoped agent; contract enforces amount tiers; human approval path; on-chain decision log.
- **Demo moment:** a prompt-injected agent tries to pay an attacker → blocked with reasons and probabilities; a normal payment goes through in 200 ms.
- **Differentiation from the 140:** calibration, intent-matching, measured false-block rate.

### Bet C — "Market Town, Live" (Games + Swarms + NFTs)
- **Pitch:** NPC merchants that actually think, in real time, cheaply — the economy is the gameplay.
- **NEAR role:** NEP-245 items, merchant wallets as sub-accounts, social login, no wallet popups.
- **Demo moment:** flood the market with iron and watch Jev merchants react, tooltips showing their probabilities.

**Safer data play:** "NEAR, Labeled" (Thesis) — lowest build risk, directly in front of investor judges, and a unique dataset.

---

## Part 7 — Winning checklist for any Jev project

1. **Get a TypeSafe API key today** (console.typesafe.ai/keys). Build behind an interface with an LLM fallback so the demo never blocks.
2. **Make NEAR load-bearing.** Jev decides; NEAR holds keys, enforces limits, settles and records. Say this in the first README paragraph.
3. **Log Jev's probabilities on-chain or in a public ledger** — that turns "AI said so" into an auditable record (very on-theme).
4. **Show numbers:** latency p50/p95, cost per 1,000 decisions, accuracy on a labeled sample, and a confidence-vs-accuracy chart (calibration is Jev's headline claim — prove it in *your* domain).
5. **README for the AI screeners:** "do X → see Y" steps, a dry-run mode, sample data, no secrets.
6. **Demo post on X:** problem first, one complete moment, NEAR's concrete role, tag @NEARProtocol #NEARHackathon (+ optional @typesafeai for extra reach; TypeSafe actively courts builders via its Discord).
6b. **Design for Jev's ~68% accuracy:** every money-moving decision gets a confidence gate and an escalation path — and show that path in the demo, not just the happy path.
7. **Pick every fitting track** — and include Open Innovation if the idea stretches beyond one.
8. **Timeline (PHT):** Sun–Mon core loop → Tue NEAR integration → Wed metrics + attack/edge demos → Thu README + video → Fri submit (don't wait for Sat 07:59).

---

## Sources

- NEAR prompts & rules: github.com/nearai/near-hackathon-prompt-examples · nearhackathon.com/HACKATHON.md · nearhackathon.com/api/projects (track counts at 13:10 PHT, 8 Nov 2026)
- Jev: typesafe.ai · typesafe.ai/blog/introducing-system-one-models-and-jev · docs.typesafe.ai/introduction · docs.typesafe.ai/introduction/quickstart.md · docs.typesafe.ai/confidence.md
- Jev (browser check, 8 Nov 2026): typesafe.ai FAQ · typesafe.ai/blog/series-ai · typesafe.ai/blog/jev-1-14
- Remittances: World Bank Remittance Prices Worldwide Issue 54 (Sep 2025), via axis-intelligence.com/cross-border-payments-statistics · BSP data via bworldonline.com (16–17 Feb 2026) and philstar.com (17 Feb 2026)
- Crypto theft: Chainalysis via theblock.co/post/382477 (18 Dec 2025)
- Memecoins: Solidus Labs 2025 Rug Pull Report via coindesk.com (7 May 2025) and benzinga.com
