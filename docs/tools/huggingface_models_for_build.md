# Hugging Face Models & Datasets We Can Leverage — NEAR HACKATHON + Jev

- **Researched:** Sun 8 Nov 2026, ~13:25–13:50 PHT, live in Chrome on huggingface.co (model/dataset/space search, model cards, Hub API for license and size)
- **Companion files:** `near_hackathon_web.md` (hackathon data) · `near_hackathon_tracks_ranked.md` (track ranking + Jev)
- **How to read "trust":** download counts on the Hub can be inflated; likes, a real model card, a known organization and a recent update are better signals. Low-trust picks are flagged.

---

## TL;DR — the 10 most useful finds

| # | Model / resource | What it gives us | License | Size | Best track(s) |
|---|---|---|---|---|---|
| 1 | **baselabs/elephant-1** | Open **Jev-style decision model**: state + questions → calibrated probability for every option, one pass. Best <15B on the community Jev Decision Index. | **MIT** | 9.4B | Security, Agents, Swarms, **Privacy** (self-host) |
| 2 | **autotrust/JEV-9B** | Open model claiming System-1 decisions *matching TypeSafe Jev 1.13* + normal text generation from the same weights | Apache-2.0 | 9.0B | Same as above; fallback for TypeSafe API |
| 3 | **multimodalart/jev-decision-index** (Space) | Leaderboard of **274 open reproductions of Jev**, with a calibration tab — lets us pick a model with evidence | — | — | Model selection, README credibility |
| 4 | **meta-llama/Llama-Prompt-Guard-2-22M / 86M** | Tiny prompt-injection/jailbreak classifiers — run on every tool output in milliseconds, on CPU | Llama license | 0.07B / 0.28B | **Security**, Agents |
| 5 | **protectai/deberta-v3-base-prompt-injection-v2** | Most-downloaded open prompt-injection classifier | Apache-2.0 | 0.18B | Security |
| 6 | **openbmb/MiniCPM-OCR-Jev** | Scores whether an OCR result is **correct** (0–1) → auto-accept vs human review | Apache-2.0 | 2.2B | **Real-World Money** (invoices/receipts) |
| 7 | **zai-org/GLM-OCR** / **baidu/Unlimited-OCR-2** | Strong, permissive OCR for receipts, invoices, IDs | MIT / MIT | 1.3B / 3.3B | Real-World Money |
| 8 | **amazon/chronos-2** | Time-series forecasting foundation model, zero-shot | Apache-2.0 | 0.12B | **Thesis**, DeFi, Business |
| 9 | **Qwen/Qwen3-Embedding-0.6B** + **BAAI/bge-reranker-v2-m3** | Embeddings + reranker — pre-filter hundreds of candidates before a Jev Choice (Jev caps at 255 options) | Apache-2.0 | 0.6B / 0.57B | Agents, Swarms, Thesis |
| 10 | **nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1** (dataset) | Real indirect-prompt-injection attacks against agents — ready-made **attack demo + eval set** | (check card) | — | Security, Agents |

---

## Discovery #1 — There is a whole open "Jev" ecosystem on Hugging Face

This is the biggest finding. Since TypeSafe launched Jev (Sep 2026), the community has built open-weight "decision models" that copy its interface: **state + typed questions → probabilities**, single pass, no text generation.

### The leaderboard: Jev Decision Index 0.4.1
- Space: `huggingface.co/spaces/multimodalart/jev-decision-index` (880 likes)
- **274 open reproductions of TypeSafe Jev's decision model**, 275 models total, updated **6 Nov 2026**, reference Jev = **jev-1.14.0**, reproductions run on one NVIDIA RTX PRO 6000.
- Ranked by a "Full score" (private tests mirroring 37 public benchmarks + private tasks from new domains); tabs: Ranking · How it is scored · Head to head · Full results · **Calibration** · All benchmarks · Methodology; filters by parameter size and by method (full fine-tune, LoRA, inference technique, head/adapter).
- **What it showed (screenshot reading):**
  - All sizes: top scores 74.0 (REAX 1.3, 57B), 73.4 (GLiDE 27B), 71.9 (KnowLine 31B Gen1.5), 71.6 (FlexDM-LoRA 2.1 Gemma 4 31B), 71.1 (Sieve 31B v3) … AutoTrust JEV-27B v1.1 ~68.0.
  - **≤10B:** GLiDE 9B **62.5** · baselabs elephant-1 (9B) **60.3** · **Jev 1.14 (the TypeSafe reference) 60.2** · Cerno 9B v1.2 59.0 · KnowLine 9B Gen1 58.4 · StartLux-Decision v1.1 9B 58.1 · Piccolo 9B 57.3 · Adjudex-9B v2 57.2 · KnowLine 4B Gen5.5 56.0 · Dexy-Decision-9B-V2 55.4 · StartLux-Decision v1.1 4B 54.8 …
- **Takeaway:** on this community benchmark, the best open 9B models are **level with hosted Jev**, and big open models score higher. Treat it as a *community* index (not TypeSafe's official evals), but it's strong evidence that self-hosting is viable.

### The models worth knowing

| Model | Org | Size | License | Notes |
|---|---|---|---|---|
| **baselabs/elephant-1** | Base Labs at **Baseten** | 9.4B (from Qwen3.5-9B) | **MIT** | Text + images; full fine-tune for single-pass calibrated decisions; card claims best <15B on Decision Index 0.4 (62.65, tied #8 of 208) and 65.2 on a replica of the Artificial Analysis Decision Index; one-GPU setup script (`hf download baselabs/elephant-1` → `setup.sh` → `qev.engine.DecisionEngine`); **"Try on Baseten"** hosted option; 109 likes |
| **baselabs/mammoth-1** | Base Labs | 27.4B | MIT | Bigger sibling, more general knowledge |
| **autotrust/JEV-9B** | AutoTrust AI | 9.0B | Apache-2.0 | Card claims System-1 decisions "indistinguishable from TypeSafe Jev 1.13 by KL" **plus** System-2 text/reasoning from the same weights in one vLLM engine; about a third of the hosted API's latency for a single decision; trained on `SargeDev/jev-distill-corpus-v3`; also does computer-use / robot-arm demos from screenshots (~0.2 s) |
| **autotrust/JEV-35B** (+ NVFP4 25.6 GB version) | AutoTrust AI | 36B MoE (~3B active) | Apache-2.0 | Up to 256 options per pass; median ~204 ms per request on one B200; `POST /v1/decide` via `serve.sh` (vLLM); FP4 version fits one 32–48 GB GPU. **The card states it is not affiliated with or endorsed by TypeSafe.** |
| **autotrust/JEV-27B-VL** | AutoTrust AI | 27B | (check) | Vision decisions; card recommends it for **game play** |
| **fastino/GLiDE-9B / GLiDE-27B** | Fastino | 7.9B / 27B | "other" — read terms | Top of the leaderboard in their size classes; few likes so far |
| **openbmb/MiniCPM-OCR-Jev** | OpenBMB | 2.2B | Apache-2.0 | Jev-style **OCR correctness judge** (see Discovery #3) |

### Datasets in the same family
- **ZefanCai/Open-Jev** — 12 frozen configs of typed-decision tasks (yes/no probabilities, choice distributions, label probabilities, ordinal decisions) with train/calibration/validation/test/OOD splits (e.g. 113,568 rows in `release-v2-redistributable`). Mostly synthetic; explicitly **not** TypeSafe data and not affiliated. 116 likes.
- **tasksource/tasksource-jev-typed-decisions** — typed-decision version of tasksource tasks (25K downloads).
- **Praveenrajus/jev-bench**, **benchmarkheaven/JevBench** (Space) — community benchmarks.

### Why this matters for our build
1. **It fixes Jev's two weak spots from the track analysis:**
   - *Privacy track:* TypeSafe Jev is a hosted API (data leaves your machine). An **MIT/Apache decision model can run on your own GPU or inside a TEE**, so sensitive data never leaves. That reopens the Privacy track for a Jev-style design.
   - *Vendor dependency / outage risk:* same request shape, swap the backend.
2. **A hybrid is the strongest story:** TypeSafe Jev for speed on normal decisions; a self-hosted open decision model for confidential or high-stakes ones; both feeding the same confidence gates and the same NEAR contract.
3. **"Two independent judges" pattern:** for money above a threshold, require TypeSafe Jev *and* elephant-1 to agree (or both be confident). Disagreement → human. That's a genuinely new, demo-able safety mechanism.

### Cautions
- **APIs differ:** TypeSafe uses `POST /v1/systemone` with `choice / score / noul / box`; AutoTrust serves `POST /v1/decide`; elephant-1 ships its own `DecisionEngine`. Write one thin adapter.
- **Distillation:** some open models (e.g. JEV-9B) are trained to imitate TypeSafe's outputs. Check TypeSafe's terms before presenting it as "Jev"; describe it as "an open, independent decision model".
- **Hardware:** a 9B model needs one ~24 GB GPU (bf16) — use a cloud GPU, Baseten, or a Hugging Face Inference Endpoint; don't plan to run it on a laptop.
- **The leaderboard is community-run** — cite it as such.

---

## Discovery #2 — The security stack (for Intent Notary / Security track)

Layered defense: **tiny classifiers first (milliseconds, free) → Jev/elephant intent check → NEAR contract enforces.**

### Prompt-injection & jailbreak detectors
| Model | Size | License | Notes |
|---|---|---|---|
| meta-llama/Llama-Prompt-Guard-2-22M | 0.07B | Llama license ("other") | Fastest; good first filter on every web page/tool output; 85 likes |
| meta-llama/Llama-Prompt-Guard-2-86M | 0.28B | Llama license | More accurate; 364 likes |
| meta-llama/Prompt-Guard-86M (v1) | — | Llama license | 1.87M downloads, 434 likes — older |
| protectai/deberta-v3-base-prompt-injection-v2 | 0.18B | **Apache-2.0** | 555K downloads, 129 likes, updated Jul 2026 |
| protectai/deberta-v3-small-prompt-injection-v2 | small | Apache-2.0 | Lighter variant |
| rogue-security/prompt-injection-jailbreak-sentinel-v2 | 0.6B | "other" | 65 likes |
| patronus-studio/wolf-defender-prompt-injection (+ small) | — | check | 28 likes |
| meta-llama/Llama-Guard-4-12B | 12B | Llama license | Full content-safety classifier (multimodal); heavier |
| gravitee-io/Llama-Prompt-Guard-2-86M-onnx | — | — | ONNX build for fast CPU/browser inference |

### Phishing & scam detectors (for "who is the agent paying?" and family-scam warnings)
| Model | Size | License | Notes |
|---|---|---|---|
| cybersectony/phishing-email-detection-distilbert_v2.4.1 | 0.07B | Apache-2.0 | 311K downloads |
| CrabInHoney/urlbert-tiny-v4-phishing-classifier | tiny | Apache-2.0 | Classifies URLs — good for links in invoices / payment requests |
| Horizon-Labs/phishing-scam-detector-base (+ ONNX) | — | check | Low likes |
| aaaa47080/CryptoMind-Guard-0.6B | 0.6B | check | Crypto-specific guard, low trust (9 likes) |

**Low-trust, skip:** `JackKozmo29/*-jev-style-1.5b` (mailguard/codeguard/etc.) — advertise "drop-in local Jev" but are small Qwen fine-tunes emitting JSON, no calibrated probabilities, ~1–2 likes despite high download counts.

### Datasets for attack demos and evals
- **nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1** — indirect prompt injection against agents (exactly the "poisoned web page tells the agent to pay" scenario).
- **deepset/prompt-injections** (200 likes), **xTRam1/safe-guard-prompt-injection**, **Necent/llm-jailbreak-prompt-injection-dataset**, **neuralchemy/Prompt-injection-dataset**.
- Phishing: **zefang-liu/phishing-email-dataset**, **ealvaradob/phishing-dataset**, **pirocheto/phishing-url**.
- **Use:** report catch rate and false-block rate on a held-out slice in the README — judges (and the AI screeners) love numbers.

---

## Discovery #3 — Documents, receipts and the Philippines (Real-World Money)

### OCR + "is the OCR right?"
| Model | Size | License | Notes |
|---|---|---|---|
| **zai-org/GLM-OCR** | 1.33B | MIT | 1.76M downloads, 2,205 likes — strong, light |
| **baidu/Unlimited-OCR-2** | 3.34B | MIT | Trending #1 OCR, updated 2 Nov 2026 (v1 has 4,961 likes) |
| datalab-to/chandra-ocr-2 | — | check | 1.4M downloads |
| openbmb/MiniCPM-OCR-1.0 | — | check | Pairs with the judge below |
| xiaomi-research/Xiaomi-OCR-0 | — | check | Trending |
| **openbmb/MiniCPM-OCR-Jev** | 2.2B | Apache-2.0 | Given a region image + candidate text, returns **0–1 probability the OCR is correct**; card reports AUROC 93.6 on JevOCRBench (above JEV-35B-A3B's 90.1, near Qwen3.5-397B's 93.8), stable 91.9–93.4 across four OCR engines. Use: auto-accept confident fields, send the rest to a human, or pick the best of several OCR outputs |
| impira/layoutlm-invoices | — | check | Classic invoice question-answering (229 likes) |

**Pattern:** OCR → MiniCPM-OCR-Jev confidence per field → TypeSafe Jev/elephant decides "pay / ask / reject" → NEAR Intents pays. Every step carries a probability — that's the "bookkeeper-proof" README story.

### Filipino / Tagalog language and speech
| Model | Notes |
|---|---|
| Khalsuu/filipino-wav2vec2-l-xls-r-300m-official | Filipino speech-to-text, Apache-2.0, 1.1M downloads — voice notes like "padalhan mo si Nanay ng 5,000" |
| nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B | Trending big ASR model (33.7B, license "other") — check language list |
| jcblaise/roberta-tagalog-base / -large | Tagalog language understanding (fine-tune for scam-message detection) |
| meedan/paraphrase-filipino-mpnet-base-v2, danjohnvelasco/filipino-sentence-roberta-v1 | Filipino sentence embeddings |
| Datasets: SilencioNetwork/tagalog-filipino-speech, SpeechDataAI/tagalog-conversational-speech, PiotrSty/law-ph-english-tagalog | Speech & legal text |

(Reminder: TypeSafe says Jev 1.14's biggest gain is **multilingual** — test Taglish directly first.)

---

## Discovery #4 — Forecasting, tabular and market data (Thesis, DeFi, Business)

| Model | Size | License | Use |
|---|---|---|---|
| **amazon/chronos-2** (also autogluon/chronos-2) | 0.12B | Apache-2.0 | Zero-shot forecasting of NEAR activity, Intents volume, treasury runway; 8.4M downloads |
| amazon/chronos-bolt-small / -mini | small | Apache-2.0 | Faster variants |
| google/timesfm-3.0-pytorch | 0.33B | "other" | Google's forecaster (1,013 likes) — read terms |
| Prior-Labs/tabpfn_3_5 | — | "other" | Tabular classifier with **probabilistic outputs** on small data — e.g. "is this wallet a bot?" from on-chain features |
| ElKulako/cryptobert | 0.12B | MIT | Crypto social sentiment |
| covalenthq/cryptoNER | — | MIT | Extracts tokens/addresses/entities from crypto text |
| Salesforce/moirai-2.0-R-small | 0.01B | **CC-BY-NC** | Non-commercial — avoid |
| ProsusAI/finbert | 0.11B | **CC-BY-NC-SA** | Non-commercial — avoid |

**Thesis angle:** BigQuery NEAR data → Jev labels each transaction (bot / human / agent / arbitrage) → **Chronos-2 forecasts** each segment → THESIS.md shows "organic activity forecast with uncertainty bands". Probabilities end to end.

Related datasets: **Intent2Tx/web3_intents_to_ethereum_transactions** (natural-language intents → Ethereum transactions — useful for training/evaluating intent-matching), RBudzynski/Transactions-Ethereum-Cryptocurrency-Data.

---

## Discovery #5 — Agents, retrieval and general models

| Model | Size | License | Use |
|---|---|---|---|
| **Qwen/Qwen3-Embedding-0.6B** | 0.6B | Apache-2.0 | Embed agents/vendors/bounties; 9.3M downloads |
| **google/embeddinggemma-2** | 0.74B | Apache-2.0 | Trending #1 embedding (3,190 likes), updated 28 Oct 2026 |
| Qwen/Qwen3-VL-Embedding-8B | 8B | check | Image + text embeddings |
| **BAAI/bge-reranker-v2-m3** | 0.57B | Apache-2.0 | Cut 10,000 candidates to the top 200, then one Jev Choice (Jev max = 255 options) |
| Qwen/Qwen3-Reranker-0.6B / 4B | — | check | Alternatives |
| **Qwen/Qwen3.8-27B** | 27.8B | Apache-2.0 | Today's most-liked open general model (19,348 likes, updated 7 Nov 2026) — the "System 2" for writing reports, negotiation messages, README text |
| Qwen/Qwen3.8-Flash-Next | 180B | "other" | Too big for us |
| Salesforce/Llama-xLAM-2-8b-fc-r | 8B | **CC-BY-NC** | Good function-calling, but non-commercial |
| mrm8488/embeddinggemma-2-ft-typed-decision | — | check | Embedding model fine-tuned for typed decisions (87 likes) — an ultra-cheap pre-classifier idea |

**Swarm angle:** 500 agents × embeddings to find compatible buyers → reranker → Jev/elephant decides bids. Cheap at every layer.

---

## Discovery #6 — Smart contracts (gap = opportunity)

- **Chain-GPT/Solidity-LLM** (2.78B, MIT, 1,591 likes) — Solidity generation; CodeLlama-Solidity GGUFs.
- Smart-contract **vulnerability** detectors on the Hub are tiny, untested uploads (≈0 downloads).
- **Nothing NEAR-specific:** searches for NEAR models, NEAR datasets and NEAR Spaces returned **zero** results. No Rust/NEAR contract auditor exists.
- **Opportunity:** publish our labeled data (e.g. "agent payment: legitimate vs injected" or "NEAR transactions labeled by Jev") as a Hugging Face dataset and link it in the README — first NEAR dataset on the Hub, re-runnable evidence for judges, and good for the Thesis track's "anyone can re-run" requirement.

---

## How these plug into the three recommended builds

### Bet B — Intent Notary (Security + Agents + Real-World Money)
```
tool output / web page ──► Prompt-Guard-2-22M (ms, CPU) ──► injected? ─► block
                                    │ clean
payment request ──► TypeSafe Jev  (intent match, allow/warn/block + confidence)
                └─► elephant-1    (independent second opinion for amounts > threshold)
                                    │
                         NEAR contract: function-call-key scope, amount tiers,
                         human approval on disagreement/low confidence, on-chain log
```
Eval: Nemotron indirect-injection set + deepset/prompt-injections → catch rate, false-block rate, p50/p95 latency, cost per 1,000 checks.

### Bet A — Thousand-Agent Market (Swarms + Agents)
Qwen3-Embedding + bge-reranker to match buyers/sellers → TypeSafe Jev for live bids (fast, cheap) → optional self-hosted elephant-1/JEV-9B run to show "no API needed" → settlement on NEAR sub-accounts. Chronos-2 can forecast demand per round.

### Bet C — Market Town (Games)
TypeSafe Jev (or JEV-27B-VL, which its card recommends for games) for merchant decisions every tick; probabilities shown in tooltips; NEP-245 items on NEAR.

### Real-World Money variant ("Padala Rails")
Filipino wav2vec2 voice note → GLM-OCR/Unlimited-OCR-2 for receipts → MiniCPM-OCR-Jev field confidence → URL/phishing + Jev scam check → NEAR Intents payout to a named account.

---

## License cheat sheet (safe for a public hackathon repo)

| ✅ Permissive (MIT / Apache-2.0) | ⚠️ "Other"/custom — read terms | ⛔ Non-commercial |
|---|---|---|
| elephant-1, mammoth-1, JEV-9B, JEV-35B, protectai deberta v2, MiniCPM-OCR-Jev, GLM-OCR, Unlimited-OCR-2, chronos-2, Qwen3-Embedding-0.6B, embeddinggemma-2, bge-reranker-v2-m3, Qwen3.8-27B, cryptobert, cryptoNER, Solidity-LLM, phishing distilbert, urlbert-tiny, filipino wav2vec2 | Llama Prompt Guard 2, Llama Guard 4, GLiDE-9B/27B, timesfm-3.0, TabPFN 3.5, sentinel-v2, Nemotron Transcribe, Qwen3.8-Flash-Next | finbert, moirai-2.0, xLAM-2 |

Licenses read from each model's Hub metadata on 8 Nov 2026; confirm on the model page before shipping.

---

## Practical notes for the next 6 days
1. **Don't self-host everything.** Use TypeSafe's hosted Jev for the main loop; add *one* open decision model (elephant-1 via Baseten, or a Hugging Face Inference Endpoint) only if it powers a feature you'll demo (privacy path or second-opinion check).
2. **Tiny classifiers run anywhere** (Prompt Guard 2 22M, urlbert, deberta) — CPU or even ONNX in the browser.
3. **Name every model in the README** with license and role — Q-005 requires listing libraries/AI code, and it shows judges a deliberate architecture.
4. **Publish a dataset** to Hugging Face from your eval — cheap, and nobody else on the NEAR side has done it.

## Sources (all on huggingface.co, visited 8 Nov 2026)
- spaces/multimodalart/jev-decision-index · baselabs/elephant-1 · autotrust/JEV-9B · autotrust/JEV-35B · openbmb/MiniCPM-OCR-Jev · JackKozmo29/mailguard-jev-style-1.5b · datasets/ZefanCai/Open-Jev
- Hub API searches (`/api/models`, `/api/datasets`, `/api/spaces`) for: prompt-injection, prompt-guard, Llama-Guard, jailbreak, phishing, scam, smart contract vulnerability, solidity, tagalog, filipino, chronos, timesfm, moirai, TabPFN, receipt, invoice, OCR, function/tool calling, xLAM, embedding, reranker, Qwen3.8, crypto, blockchain, fraud, anomaly, finbert, jev, typesafe, near protocol; plus the site-wide trending list
