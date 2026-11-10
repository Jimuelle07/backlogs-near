# PRD — backlogs-near

## 1. Status

Project chosen: "Attested Payment Firewall" (working name; the human sets the final name at submission). Plan: [idea.md](idea.md). Last updated 2026-11-09.

Tracks are planned, not final (§5). Open questions are in §11.

## 2. Problem

Prompt injection drains agent wallets. In May 2026 a Morse-code message made Grok's linked wallet pay out about $150,000 in DRB ([Giskard](https://giskard.ai/knowledge/how-grok-got-prompt-injected-an-x-user-drained-150-000-from-an-ai-wallet)). Chainalysis puts crypto theft at $2.2B → $3.4B ([tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 4 #1). Both figures: verify against the primary source before the README.

Today's defenses run on the agent's own host, so a compromised agent can skip them. The firewall moves the check and the funds off the agent: the agent holds only a function-call key scoped to a Guardian contract, and the contract pays only after a TEE-attested verdict ([idea.md Summary](idea.md#summary)).

## 3. Users & primary scenario

**Primary user:** the owner who gives an AI agent a wallet to pay bills.

- **Primary scene** ([idea.md Demo script](idea.md#demo-script-about-2-minutes) steps 2 and 4): the agent pays an 18 USDC hosting invoice (allow, receipt on the explorer); then the same agent, fed a Morse-code reply, proposes paying a lookalike account and is blocked, with reasons on-chain.
- **Escalation scene** (demo step 5): an unusual but legitimate payment is held in escrow, re-checked and released automatically. No human step.

## 4. Chosen direction

The Attested Payment Firewall extends Bet B "Intent Notary": a TEE-attested checker runs four checks (policy rules, injection classifier, MELON masked re-run, counterparty signals); Jev fuses them into allow / hold / block; the hold threshold is a conformal quantile with a stated false-hold bound; there is no human in the loop. NEAR holds the funds, scopes the agent's key, binds each verdict to receiver, token and exact amount, enforces caps and records the receipt.

Pitch: "Give your agent a wallet, not the keys: every payment ships with a hardware-signed proof that it passed the check."

The other candidate bets (A, C, Thesis) stay documented in [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 6.

## 5. Tracks

`security` ([idea.md Summary](idea.md#summary)). `privacy` is dropped: Jev and the agent's LLM are outside services, so no claim that data never leaves the TEE. The human confirms at submission.

Valid ids (exactly 13): `defi`, `thesis`, `privacy`, `business`, `swarms`, `security`, `agents`, `realworld`, `games`, `nfts`, `memecoins`, `social`, `open`.

## 6. Goals / requirements

### Functional requirements

| Priority | Requirement |
| --- | --- |
| Must | Guardian contract holds the funds; the agent holds only a function-call key |
| Must | Verdict bound to receiver, token, exact amount and one-time `request_id` ([idea.md Amount safety rules](idea.md#amount-safety-rules)) |
| Must | Four checks (policy, injection classifier, MELON masked re-run, counterparty), each behind a config switch |
| Must | Jev fusion into allow / hold / block |
| Must | Hard caps in contract code: $200 per payment, $500 per day (starting values, tuned Thu) |
| Must | Hold escrow with auto-release or refund |
| Must | On-chain receipt (outcome, reason codes, input and record hashes, checker version) |
| Must | Dry-run with sample data, no keys or funds |
| Must | Eval on ~300 labelled cases ([idea.md Evaluation](idea.md#evaluation-and-calibration)) |
| Should | OutLayer yield/resume mode (fallback: HTTPS mode with a signed verdict) |
| Should | Cascade (MELON only when another signal is borderline) |
| Should | Unseen-family test and a red-team round |
| Should | Public landing page explaining the product (problem, how it works, NEAR's role, Jev's role, results) with a read-only live receipts panel; hosted through 2026-11-18, ideally 2026-11-25 ([sprints.md](sprints.md)) |
| Won't (this hackathon) | Human approval UI; mainnet; Privacy-track claims; shared blocklist (stretch only); NEAR Intents |

### Cross-cutting requirements (apply to any choice)

- **R1.** Every payment gets allow / hold / block; hold is the escalation path (escrow + re-check + auto-release), and the demo shows it.
- **R2.** NEAR does real work: custody, limits, settlement, or the decision log (Part 7 item 2).
- **R3.** Dry-run mode with sample data, so judges can try it without keys or funds (Part 7 item 5).
- **R4.** Reproducible local run from the README (HACKATHON.md Q-012).
- **R5.** No secrets in the repository (HACKATHON.md, "Never without the human's explicit confirmation").

## 7. Success metrics

Measured and published in the README (tracks ranked Part 7 item 4). Results table: [idea.md Evaluation](idea.md#evaluation-and-calibration).

| Metric | How measured | Target |
| --- | --- | --- |
| False-hold rate | held benign payments on the test split | ≤ ε = 5% (conformal bound; holds only while the agent behaves like its calibration history) |
| Worst-case loss per day | contract caps, attack set incl. budget-grooming case | ≤ daily cap ($500) |
| False-block rate | benign payments blocked on the test split | measured and reported; no target claimed |
| Missed attacks | attacks allowed, per family and on an unseen family | measured and reported; no target claimed |
| Latency p50 / p95 | timed checker runs in the eval script | measured and reported; no target claimed |
| Cost per payment | token usage × published price, from the eval run | measured and reported; no target claimed |

## 8. Demo plan

Demo-post rules ([HACKATHON.md](../hackathon-context/HACKATHON.md) §2). The agent may draft; **the human records and posts**:

- Lead with the user problem; the first line must make sense to someone who does not know the project.
- Show one complete moment: real user action → visible result. No long intro, architecture slides, or setup.
- Explain NEAR's role concretely (what NEAR enables and why it matters), never a vague "powered by NEAR".
- Give a next step: link the demo and the public repo; ask a genuine question or invite specific feedback.
- Say it was built at NEAR HACKATHON; tag @NEARProtocol and #NEARHackathon (optional: @NearLegion, @NearBuilders); attach the video or screenshots.
- Local-only demos need a video; screenshots are not enough when judges cannot open the demo (Q-012).

Shot-by-shot script (about 2 min): [idea.md Demo script](idea.md#demo-script-about-2-minutes).

## 9. Timeline

Remaining work is cut into sprints: [sprints.md](sprints.md).

| Milestone | When |
| --- | --- |
| **Hard deadline** | **2026-11-14T23:59Z** (Sun 15 Nov 07:59 PHT) |

## 10. Out of scope

- Human approval UI; mainnet; Privacy-track claims; shared blocklist (stretch only); NEAR Intents.
- What we claim honestly ([idea.md](idea.md#research-grounding)): the policy layer is deterministic; the false-alarm bound holds only while the agent behaves like its calibration history (exchangeability); Jev's calibration is the vendor's claim until our own eval confirms it; the attestation proves which checker code ran on which inputs, not that Jev's or the LLM's answers were right.
- Tracks ranked Part 1 "Honest limits": Jev is not a TEE and its accuracy is about 68% on the vendor's own chart, so no single Jev answer is a security boundary.

## 11. Open questions

- Can the 86M Prompt Guard classifier run inside the OutLayer runtime, or does it need NEAR AI Cloud / a pinned service?
- Will Hugging Face grant gated access to Llama-Prompt-Guard-2-86M? (Default: protectai/deberta-v3-base-prompt-injection-v2.)
- Receipt panel technology: React + Vite (`web/`), chosen by Ace on 2026-11-11; shared landing-page integration and hosting remain D1/E5 work.
- Human-only submission fields: final project name, tracks, NEAR payout wallet, Q-015 disclosure, X post.
