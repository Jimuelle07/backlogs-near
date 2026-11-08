# PRD — backlogs-near

## 1. Status

Draft, project undecided. Last updated 2026-11-08.

Project-independent sections are complete. Project-specific sections carry a `TBD(project)` marker; fill them once the human picks a direction from §4.

## 2. Problem

> **TBD(project):** the user problem this project solves — inputs: [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 2 (lenses) and Part 4 (per-track real problems with sourced numbers).

Guidance:

- Lead with the user problem, not the technology. The first sentence must make sense to someone who does not know the project.
- Run the lenses from tracks ranked Part 2: the 3 a.m. test, the irreversibility test, the grandmother test, the villain's view, and the Jev test (is there a repeated, fast, judgment-shaped decision where calibrated confidence changes behavior?).
- Cite one sourced scale number (Part 4 lists them per track; sources at the end of that file). Verify it against the primary source before it goes into the README.

## 3. Users & primary scenario

> **TBD(project):** one primary user and the single "one complete moment" the demo shows — inputs: [HACKATHON.md](../hackathon-context/HACKATHON.md) §2 (demo post), the chosen bet's "Demo moment" in §4 below.

Guidance:

- Name one primary user (not a list of personas).
- Write the moment as: real user action → visible result, end to end, with NEAR doing visible work in between.
- Include the escalation path (medium/low confidence) as a second scene, not only the happy path (tracks ranked Part 7 item 6b).

## 4. Candidate directions

From [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 6 (Thesis play detail from Part 4 #10):

| Option | Tracks | Pitch | Demo moment | NEAR role |
| --- | --- | --- | --- | --- |
| Bet A — "Thousand-Agent Market" | Swarms + Agents + Open | Swarm markets have been stuck with dumb scripted bots because LLM agents cost too much per decision. Jev makes every agent smart for ~$0.00002 per decision, so a real market of hundreds of agents runs live. | A live dashboard where 500 agents bid; a side panel shows "cost of this round: $0.004" vs. estimated LLM cost. | Each agent = sub-account; rounds settle via Intents (dry quotes) / testnet transfers; coordinator contract enforces sealed-bid rules. |
| Bet B — "Intent Notary" | Security + Agents + Real-World Money | Spending limits stop big thefts but not smart ones. Intent Notary asks "does this payment actually serve what the user asked for?" before every transaction, with stakes-scaled confidence thresholds. | A prompt-injected agent tries to pay an attacker → blocked with reasons and probabilities; a normal payment goes through in 200 ms. | Function-call-key-scoped agent; contract enforces amount tiers; human approval path; on-chain decision log. |
| Bet C — "Market Town, Live" | Games + Swarms + NFTs | NPC merchants that actually think, in real time, cheaply — the economy is the gameplay. | Flood the market with iron and watch Jev merchants react, tooltips showing their probabilities. | NEP-245 items, merchant wallets as sub-accounts, social login, no wallet popups. |
| Thesis — "NEAR, Labeled" | Investment Thesis | Re-runnable pipeline: BigQuery → Jev labels → dashboard of "organic vs automated activity" over time, Intents volume by user type; THESIS.md with counter-evidence. Lowest build risk, directly in front of investor judges, unique dataset. | _Not specified in source._ A dashboard showing what share of NEAR activity is humans vs bots vs agents, plus labeling accuracy on a hand-checked sample. | Data source (on-chain transactions, Intents volume) that the thesis analyses; publish labeling accuracy on a hand-checked sample. |

Decision criteria (tracks ranked Part 5, each scored 1–5):

- **Power**: size × severity × irreversibility × growth of the problem (Part 3).
- **Space**: inverse crowding (≤20 projects = 5, 21–30 = 4, 31–50 = 3, 51–80 = 2, 80+ = 1).
- **Jev fit**: how central and defensible Jev is.
- **Buildable**: realistic in the remaining days with a polished demo.
- **Judge appeal**: fits this jury (NEAR CEO + crypto VCs + AI screeners).

## 5. Tracks

> **TBD(project):** the track ids this project enters — inputs: [HACKATHON.md](../hackathon-context/HACKATHON.md) Tracks table, tracks ranked Part 5.

Valid ids (exactly 13): `defi`, `thesis`, `privacy`, `business`, `swarms`, `security`, `agents`, `realworld`, `games`, `nfts`, `memecoins`, `social`, `open`.

Multi-track is allowed (one submission, every track that fits). The human makes the final choice at submission time.

## 6. Goals / requirements

### Functional requirements

> **TBD(project):** functional requirements for the chosen direction — inputs: §3 primary scenario, the chosen bet in §4, tracks ranked Part 4 for that track.

| Priority | Requirement |
| --- | --- |
| Must | TBD |
| Should | TBD |
| Won't (this hackathon) | TBD |

### Cross-cutting requirements (apply to any choice)

- **R1.** Every money-moving decision passes a confidence gate with an escalation path, and the demo shows that path ([tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 7 item 6b).
- **R2.** NEAR does real work: custody, limits, settlement, or the decision log (Part 7 item 2).
- **R3.** Dry-run mode with sample data, so judges can try it without keys or funds (Part 7 item 5).
- **R4.** Reproducible local run from the README (HACKATHON.md Q-012).
- **R5.** No secrets in the repository (HACKATHON.md, "Never without the human's explicit confirmation").

## 7. Success metrics

Measured and published in the README (tracks ranked Part 7 item 4):

| Metric | How measured | Target |
| --- | --- | --- |
| Decision latency p50 / p95 | timed DecisionClient calls in the eval script | TBD |
| Cost per 1,000 decisions | input tokens × published price, from the eval run | TBD |
| Accuracy on a labeled sample | eval script over a hand-labeled set | TBD |
| Calibration | confidence-vs-accuracy chart from the same eval run | TBD |
| False-block rate (security-type projects only) | share of legitimate actions refused or escalated | TBD |

> **TBD(project):** numeric targets for each metric — inputs: [arxiv papers](../tools/arxiv_papers_for_build.md) TL;DR #3 (published gate numbers), [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 1 (published Jev latency/price).

## 8. Demo plan

Demo-post rules ([HACKATHON.md](../hackathon-context/HACKATHON.md) §2). The agent may draft; **the human records and posts**:

- Lead with the user problem; the first line must make sense to someone who does not know the project.
- Show one complete moment: real user action → visible result. No long intro, architecture slides, or setup.
- Explain NEAR's role concretely (what NEAR enables and why it matters), never a vague "powered by NEAR".
- Give a next step: link the demo and the public repo; ask a genuine question or invite specific feedback.
- Say it was built at NEAR HACKATHON; tag @NEARProtocol and #NEARHackathon (optional: @NearLegion, @NearBuilders); attach the video or screenshots.
- Local-only demos need a video; screenshots are not enough when judges cannot open the demo (Q-012).

> **TBD(project):** the shot-by-shot demo script (≤2 min) — inputs: §3 primary scenario, the chosen bet's demo moment in §4.

## 9. Timeline

From tracks ranked Part 7 item 8, mapped to dates (PHT days):

| Day | Work |
| --- | --- |
| Sun 8 – Mon 9 Nov | Core loop |
| Tue 10 Nov | NEAR integration |
| Wed 11 Nov | Metrics + attack/edge-case demos |
| Thu 12 Nov | README + video |
| Fri 13 – Fri 14 Nov | Submit (target Fri 14 Nov PHT; don't wait for Sat 07:59) |
| **Hard deadline** | **2026-11-14T23:59Z** (Sat 15 Nov 07:59 PHT) |

## 10. Out of scope

> **TBD(project):** what this project explicitly will not do during the hackathon — inputs: §6 "Won't" row, tracks ranked Part 1 "Honest limits".

## 11. Open questions

- Which project? (§4)
- Which tracks? (§5; the human decides)
