# arXiv Papers to Leverage for the NEAR HACKATHON (+ Jev)

- **Researched:** Sun 8 Nov 2026, ~13:35–14:10 PHT, live in Chrome on arxiv.org (search + abstract pages) and the official arXiv API (export.arxiv.org) after the search page rate-limited us.
- **Companion files:** `near_hackathon_web.md` · `near_hackathon_tracks_ranked.md` · `huggingface_models_for_build.md`
- **Caveat:** arXiv papers are preprints (not necessarily peer-reviewed). Findings below are paraphrased from abstracts; read the full paper before quoting numbers in a README.

---

## TL;DR — the 10 papers that should change how we build

| # | Paper (arXiv ID) | Why it matters to us | Track(s) |
|---|---|---|---|
| 1 | **JevBreak: Your Model, Their Decision** (2611.03759) | Attackers can append text that steers Jev-style decision models to a *wrong but allowed* answer — 32–99% success, using only the returned probabilities. **A Jev gate alone is not a security boundary.** | Security, Agents |
| 2 | **One Word Opens the Gate: The Option-Channel Attack on Typed Decision Models as Agent Guardrails** (2610.12292) | Open decision models as allow/block gates scored 36–72% (chance = 50%); six lines of irrelevant log text raised fail-open from 0% to 63%; misleading option names also flip decisions. | Security |
| 3 | **Decision Models as Policy Gates for Coding Agents** (2611.02155) | The *positive* counterpart: writing policies as explicit **examples + counterexamples** raised recall on all 23 models; **Jev 1.14 went 89.3% → 98.2% recall, false interruptions 30.6% → 4.8%, ~120 ms median, $0.46 per 1,000 requests.** The recipe for our gate. | Security, Agents, Business |
| 4 | **Local Allow, Global Deny: Why Per-Action Authorization Does Not Compose in LLM Agents** (2610.27620) | Proves per-action guards can't catch violations that only appear *across* actions (e.g. many small payments that together break a policy). None of six surveyed guardrails monitors across executions. **This is the gap the 140 "Leash/Guard" submissions leave open.** | Security |
| 5 | **Agentic Commerce Bench: Measuring Fraud Detection for Agents That Spend Money** (2609.35886) | 20 fraud classes, 1,647 service operations, 1,068 settlements; shows the biggest losses come from *legitimate* counterparties overcharging — invisible to identity checks. Ships an open detector stack ("gordonguard") and a replay harness. | Security, Agents, Real-World Money |
| 6 | **Real AI Agents with Fake Memories: Fatal Context Manipulation Attacks on Web3 Agents** (2503.16248) | Memory/context injection made ElizaOS agents make unauthorized transfers; introduces **CrAIBench** (150+ blockchain tasks, 500+ attacks). Ready-made Web3 attack demo set. | Security, Agents, DeFi |
| 7 | **Defeating Prompt Injections by Design (CaMeL)** (2503.18813) | Google DeepMind-style "system layer" defense: separate trusted control flow from untrusted data and enforce capabilities, so the model can be fooled without the system being fooled. Architectural foundation for Intent Notary. | Security |
| 8 | **How Agentic Is Agentic Commerce? x402 Adoption and Authenticity** (2607.12575) | 136.7M x402 settlements on Base worth ~$44.1M over 280 days — but **21.2% fictitious and 63.8% internal to linked clusters**; Gini > 0.98. Great evidence-first material and a warning against vanity metrics. | Thesis, Agents |
| 9 | **Magentic Marketplace** (2510.25779, Microsoft) | Open simulator of agent marketplaces; frontier models degrade with scale and show **severe first-proposal bias (10–30× advantage for speed over quality).** Our swarm can measure and fix this. | Swarms, Agents |
| 10 | **HOT Protocol** (2512.02287) | Paper from **HOT, a hackathon ecosystem partner**: MPC signing network inside TEEs with NEAR as the state layer, letting smart contracts own private keys. Cite it if you use HOT/chain abstraction. | DeFi, Open, Security |

---

## A. The Jev / "System 1 decision model" research wave

Since Jev launched (15 Sep 2026), dozens of preprints study this model class. Search "Jev decision model" returned 50+ results; the most useful:

| ID | Title | Takeaway for us |
|---|---|---|
| 2610.33775 | The Hitchhiker's Guide to System 1 Models: Fast Decision-Making Beyond LLMs | Survey/guide to the whole class (routing, gating, scoring, classification at sub-second latency). Read first. |
| 2611.00505 | To Jev or Not to Jev: When Can System-1 Decision Models Replace LLM Judges? | 14 decision models vs Claude Haiku 5.5, GPT-5.6 and Claude Opus 5.5 on 11 judge benchmarks; 5 match GPT-5.6 (no reasoning) on pairwise tasks, best ones (DReX-Max, d1-ultra) beat Haiku on JudgeBench/LLMBar/RewardBench 2; with a reference answer, 11 models reach 90.3–93.4% on JudgeBench. **Supports using Jev to judge agent work (Escrow Judge idea).** |
| 2611.02155 | Decision Models as Policy Gates for Coding Agents | Examples + counterexamples in policies → big recall gains, fewer false alarms (numbers in TL;DR). |
| 2609.29429 | Just Ask Jev: RLCD as a Zero-Shot Detector of AI Alignment Failures | Jev as a multi-criterion screening detector instead of one generative pass per criterion. |
| 2611.08229 | Escalate or Close: Fast-Tier Models in Two-Tier Triage | Studies exactly our "fast model decides most, escalates the rest" design against held-out attack families — read before tuning thresholds. |
| 2611.01015 | IJev: Order-Invariant Decisions via Iterated Cyclic Reordering | Decision models' answers depend on **option order**; averaging over cyclic shifts removes it. Cheap fix: ask twice with shuffled options for high-stakes calls. |
| 2611.06384 | Presentation Sensitivity in Typed Decision Models | Wording/format of the state changes answers — normalize inputs. |
| 2611.03755 | Honest Small Decision Models for Finance | Trains 0.8B–32B decision models on finance corpora; studies "specialization collapse" and a mixed-corpus fix. Relevant for Real-World Money and Thesis. |
| 2611.04510 | Fast, Cheap, and Fair? Evaluating Decision Models | Fairness of decision models in hiring-style screening — relevant if you score people (bounty contributors, borrowers). |
| 2610.42148 | Flide: Accelerating Decision Inference with Exact State Forking | Faster serving for self-hosted decision models (if you run elephant-1/JEV-9B). |
| 2610.17309 | StartLux-Decision: AutoThink Decision Models with RL | Decision models that can optionally deliberate — middle ground between Jev and LLMs. |
| 2610.25784 | UniJev: Separating Accuracy from Calibration in Trimodal Decision Models | Calibration ≠ accuracy; measure both. |
| 2609.28940 | Calibrated Decision Models for Autonomous Penetration-Testing Harnesses (JEV and Laya) | Decision models steering an offensive-security agent. |
| 2611.07854 | Towards Foundation Decision Models: Drex | Another model family (DReX appears in judge results above). |
| 2611.06238 | Zuse: A Decision Model for European Languages | Multilingual decision models (contrast with Taglish needs). |
| 2611.02654 | VerdictAD: Few-Shot Anomaly Detection via Decision-Guided Refinement | Anomaly detection with decision models — fraud/abnormal-payment angle. |
| 2611.08162 | RouteAlign: Aligning Task Requirements with Model Profiles for LLM Service Selection | Choosing which model/service to buy — fits Agent Economy vendor selection. |

---

## B. Security implications — what these papers mean for "Intent Notary"

Put together, papers 1–7 give a clear, defensible architecture (and a strong "we read the research" README section):

1. **Don't let the model be the boundary** (CaMeL 2503.18813): the NEAR contract + function-call key scope is the hard boundary; the model only advises.
2. **Gate each action with Jev, written as examples + counterexamples** (2611.02155) — measurable recall/false-alarm gains.
3. **Assume the gate can be steered** (2611.03759, 2610.12292):
   - Never show untrusted parties the probabilities (JevBreak needs them to optimize attacks).
   - Strip or summarize untrusted logs/web text before it reaches the gate (six log lines flipped decisions).
   - Use neutral option names ("A/B/C" + definitions), not persuasive ones.
   - Shuffle option order for big amounts (2611.01015).
   - Require **two independent models to agree** above a threshold (TypeSafe Jev + an open model like elephant-1).
4. **Add a cross-action monitor** (2610.27620): track cumulative spend per counterparty/purpose/time window — catches "many small allowed payments". Most competitors won't have this.
5. **Check value, not just identity** (2609.35886): flag overcharging by honest counterparties (price vs. history/market).
6. **Test on real attack suites:** CrAIBench (2503.16248) for Web3 agents, Agentic Commerce Bench (2609.35886) for spending agents, plus the Hugging Face injection datasets from the previous file.

Related security papers found:

| ID | Title | Note |
|---|---|---|
| 2611.02815 | Predictive Safety Guardrails Do Not Always Make LLM Agents Safer | Guardrails can give false comfort — measure, don't assume. |
| 2610.40753 | "Shall We Approve?" Consequence-Aware Approval for Autonomous Coding Agents | Approval should scale with consequences — same as stakes-scaled thresholds. |
| 2609.14744 | Runtime Authorization for Resources Acquired by AI Agents | Payment/budget checks don't decide whether a *returned resource* is authorized. |
| 2610.22899 | Provable Authority: Verifiable Authority Resolution across agents | Delegation chains. |
| 2610.31062 | SCOPE: Compiling Natural-Language Policies into Neurosymbolic Predicate Programs | Turn written policy into enforceable rules (pairs with on-chain enforcement). |
| 2610.16838 | Same Operation, Different Permission | Whether guardrails respect authorization context. |
| 2610.05640 | Can CaMeLs Talk? Securing Multi-Agent Systems Against Indirect Prompt Injection | CaMeL extended to multi-agent (swarms). |
| 2609.37196 / 2611.00729 / 2608.30041 | ToolFence · AgentCap · Reachability-Based Capability Confinement | Capability-based authorization for tool-using agents. |
| 2605.26497 | Aligning Provenance with Authorization: A Dual-Graph Defense for LLM Agents | Tracks where data came from before acting on it. |
| 2610.27483 | Securing Agentic Commerce Through Behavior-Aware Fraud Detection | Behavioral fraud detection for agent commerce. |

---

## C. Agent payments, x402 and agentic commerce

| ID | Title | Takeaway |
|---|---|---|
| 2607.12575 | How Agentic Is Agentic Commerce? x402 Adoption and Authenticity | Most "agent economy" volume is not genuine (see TL;DR). Great for a Thesis track or a "real vs fake activity" metric. |
| 2607.19545 | When HTTP 402 Meets the Blockchain: Risks on Emerging x402 Payments | x402 facilitators centralize trust; one flaw affects many merchants. Relevant because the hackathon's PingPay facilitator uses x402. |
| 2608.01341 | 402Pilot: An x402 Decision Layer for Autonomous Agent Micropayments | Which paid service should an agent buy with a finite wallet? — a *decision* problem, i.e. a natural Jev use. |
| 2609.02208 | Agentic Settlement Protocol: Refundable, Delayed-Fulfilment Agent Commerce on Stablecoin Rails | x402 is atomic and final; this adds refunds/escrow for delayed delivery — blueprint for "Escrow Judge". |
| 2609.00060 | A Formal Analysis of Agent Payment Protocols | Formal guarantees/gaps in agent payment protocols. |
| 2609.02992 | Tempting the Agent: Reputation without Persistent Identity in AI Agent Markets | Reputation breaks when agents can reset identity — NEAR named accounts help; relevant to Social Money and Agent Market. |
| 2607.00245 | Agent-to-Agent Finance: Blockchain Payments and Trust Infrastructure for Autonomous AI Agents | Overview of the infrastructure agents need to transact under delegated authority. |
| 2609.01519 | When Guardrails Look Effective: Construct Validity Failures in LLM Agent Commerce Evaluations | Warns that commerce-guardrail benchmarks can mislead. |
| 2601.00196 | SoK: Stablecoins in Retail Payments | Background for Real-World Money. |

---

## D. NEAR, chain abstraction and cross-chain intents

| ID | Title | Takeaway |
|---|---|---|
| 2512.02287 | HOT Protocol | MPC-in-TEE key management with NEAR as state layer; HOT is a hackathon partner. |
| 2506.05932 | Combating Reentrancy Bugs on Sharded Blockchains | NEAR-style asynchronous cross-contract calls create reentrancy patterns unlike Ethereum's — must-read before writing an escrow/vault contract. |
| 2609.12091 | Shards on a Shoestring: NEAR Nightshade Sharding on Commodity Hardware | First independent measurement of NEAR sharding on cheap hardware (published benchmarks used ~$700/hour GCP). Good Thesis-track evidence. |
| 2602.17805 | Exploiting Liquidity Exhaustion Attacks in Intent-Based Cross-Chain Bridges | Solvers front liquidity; attackers can drain it — systemic risk for intent systems like NEAR Intents. |
| 2609.13004 | IntentFuzz: Invariant Violation Detection in Intent-Based Cross-Chain Bridges | Fuzzer for intent-bridge settlement logic. |
| 2607.08226 | Threshold Authorization Without Threshold Signatures: Signature-Agnostic MPC Custody | Custody design relevant to Chain Signatures / multisig treasuries. |
| 2411.10132 | Omnichain Web: Framework for Chain Abstraction | Background on chain abstraction. |

No arXiv paper mentions "NEAR Intents" by name — another sign that building and publishing evidence here is open ground.

---

## E. Agent markets, swarms and economies

| ID | Title | Takeaway |
|---|---|---|
| 2510.25779 | Magentic Marketplace (Microsoft) | First-proposal bias and degradation at scale (TL;DR). Our swarm demo can show sealed bids + calibrated Jev agents avoid it. |
| 2509.10147 | Virtual Agent Economies (Google DeepMind authors incl. Tomasev, Leibo) | "Sandbox economy" framing; recommends **auction mechanisms** for fair allocation and "mission economies" — directly matches the AI Swarms prompt. Great citation for the pitch. |
| 2507.01413 | Evaluating LLM Agent Collusion in Double Auctions | Agents can collude — add a collusion check to the swarm. |
| 2510.04303 | Audit the Whisper: Detecting Steganographic Collusion in Multi-Agent LLMs | Hidden-message collusion detection. |
| 2605.17698 | Agent Bazaar: Economic Alignment in Multi-Agent Marketplaces | Framework for measuring whether agent markets stay stable. |
| 2604.14256 | Evaluation of Agents under Simulated AI Marketplace Dynamics | Evaluation methodology. |
| 2602.21255 | A General Equilibrium Theory of Orchestrated AI Agent Systems | Theory backing for swarm economics. |
| 2503.22726 | InfoBid: Information Disclosure in Auctions with LLM agents | Auction design with agents. |
| 2603.27304 | EpochX: Infrastructure for an Emergent Agent Civilization | Large-scale agent society infra. |

---

## F. Privacy, TEEs and verifiable AI

| ID | Title | Takeaway |
|---|---|---|
| 2605.03213 | When Agents Handle Secrets: A Survey of Confidential Computing for Agentic AI | Best single overview for the Privacy track (agents with credentials, memory, MCP/A2A). |
| 2604.18231 | AgenTEE: Confidential LLM Agent Execution on Edge Devices | Running agents inside TEEs. |
| 2611.05971 | Enforcing Accountable Disclosure in Confidential AI | Who sees what, provably. |
| 2603.14283 | AEX: Non-Intrusive Multi-Hop Attestation and Provenance for LLM APIs | Evidence that an API's output really matches the request — relevant to proving which model (e.g. Jev) made a payment decision. |
| 2608.09055 | Repeated-Game Security for Restaking-Based Verifiable Inference | Crypto-economic verifiable inference. |
| 1806.03287 | Slalom: Verifiable and Private Execution of Neural Networks in Trusted Hardware | Classic foundation paper. |

---

## G. Memecoins, sybils and on-chain analytics (Memecoins, Thesis, Social Money)

| ID | Title | Takeaway |
|---|---|---|
| 2608.20271 | Catching the Rug: Early Prediction of Fraudulent Memecoins on Solana | ML features for early rug detection. |
| 2602.13480 | MELT: Behavioral Trace Dataset for High-Risk Memecoin Launch Detection | Dataset for launch-risk scoring. |
| 2512.11850 | The Memecoin Phenomenon: Solana's Blockchain Trends | Background/statistics. |
| 2609.05663 | What LLM Trading Agents Actually Do in Production | 3,505 user-funded vaults trading real ETH in Base memecoins (21 days) + 500–599 agents on Hyperliquid — real behavior data for DeFi/agent tracks. |
| 2607.27370 | Compression-Based Behavioral Similarity for Open-World Sybil Discovery on Ethereum | Sybil detection without needing transfers between wallets — useful for streak-coin check-ins or bounty reputation. |
| 2505.09313 | Detecting Sybil Addresses in Blockchain Airdrops | Graph-based sybil features. |
| 2607.27350 | Leakage-Aware Evaluation of Tree-Based Models in Blockchain Analytics | How not to fool yourself when labeling wallets (Thesis track rigor). |
| 2601.14927 | Operationalising DAO Sustainability KPIs: A Multi-Chain Dashboard | Social Money / DAO metrics. |

---

## H. Games with real economies

| ID | Title | Takeaway |
|---|---|---|
| 2506.04699 | Empowering Economic Simulation for MMO Games through Generative Agent-Based Modeling | LLM agents for MMO economies — closest match to the "Market Town" starter idea. |
| 2509.10147 | Virtual Agent Economies | Same economic framing applies to in-game economies. |
| 2607.29577 | DungeonBench: Rules-Rich Tactical Reasoning in D&D Combat | Benchmark if NPCs need tactical decisions. |

---

## How to use these in the submission

1. **README "Research basis" section** — 5–8 citations with one line each on *what design choice it justified*. The AI screeners (Claude Code & Codex) and investor judges will notice.
2. **Turn findings into demo moments:**
   - Show a JevBreak-style injection *succeeding* against a naive Jev gate, then failing against our layered design.
   - Show a "salami" attack (many small allowed payments) caught only by the cross-action monitor (2610.27620).
   - In the swarm, show first-proposal bias with naive agents vs sealed-bid calibrated agents (2510.25779).
3. **Borrow benchmarks instead of inventing them:** CrAIBench, Agentic Commerce Bench, the policy-gate dataset style from 2611.02155.
4. **Thesis track:** reproduce the x402 "fictitious vs genuine" method (2607.12575) on NEAR Intents/agent payments — novel and evidence-first.

## Sources
All papers at `https://arxiv.org/abs/<ID>`; found via arxiv.org search (until rate-limited) and the arXiv API (`export.arxiv.org/api/query`), 8 Nov 2026.
