# AGENTS.md — operating guide for agents in this repo

## 1. What this repo is

- Entry for **NEAR HACKATHON** (https://nearhackathon.com).
- **Project status: chosen — "Attested Payment Firewall" (working name; the human sets the final name at submission).** Plan: [docs/build/idea.md](docs/build/idea.md).
- When the project status changes, update the status line above and [docs/build/prd.md](docs/build/prd.md) in the same change.

## 2. Read first

1. [docs/index.md](docs/index.md): map of every doc.
2. [docs/hackathon-context/HACKATHON.md](docs/hackathon-context/HACKATHON.md): official agent instructions and rules (snapshot).
3. [docs/build/idea.md](docs/build/idea.md): the human-authored plan (architecture, demo script, eval protocol). Work is cut into sprints in [docs/build/sprints.md](docs/build/sprints.md).
4. [docs/build/prd.md](docs/build/prd.md), then [docs/build/sdd.md](docs/build/sdd.md), then [docs/build/system-design.md](docs/build/system-design.md).

Before any submission step, re-read the live https://nearhackathon.com/HACKATHON.md: rules and dates may change, and the live file wins over the snapshot.

## 3. Deadlines (UTC)

| Milestone | When (UTC) | Source |
| --- | --- | --- |
| Hackathon start | 2026-11-01T00:00Z | [HACKATHON.md](docs/hackathon-context/HACKATHON.md) Facts |
| Code window baseline | from the 2026-10-19 announcement; earlier commits are baseline | HACKATHON.md Q-001 |
| Dev end / submission deadline / repo must be public | **2026-11-14T23:59Z** (Sun 15 Nov 07:59 PHT) | HACKATHON.md Facts |
| Judging starts | 2026-11-16T00:00Z | HACKATHON.md Facts |
| Results announced by | 2026-11-18T23:59Z | HACKATHON.md Facts |
| Hosted demo (if any) stays up | through 2026-11-18, ideally 2026-11-25 | HACKATHON.md Q-012 |

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
| Guardian contract | Rust, near-sdk 5.29.1 (5.30.1 needs rustc 1.95; local toolchain is 1.94), cargo-near 0.21.1 |
| Mock token | NEP-141 tUSDC |
| Checker | Rust bin, wasm32-wasip2 on OutLayer, native for local/eval |
| Decision model | Jev via TypeSafe API (jev-latest), the main path; optional NEAR AI Cloud /v1/systemone via JEV_PROVIDER=nearai |
| LLM | NEAR AI Cloud, OpenAI-compatible: agent tool calls, MELON, decision fallback |
| Agent / relayer / eval | Python 3.12 managed by uv |
| NEAR Python client | py-near |
| Injection classifier | protectai/deberta-v3-base-prompt-injection-v2 default; Llama-Prompt-Guard-2-86M when HF access is granted |
| Receipt page | Landing page with a read-only receipts panel ([sprints.md](docs/build/sprints.md) D1, E1, E2) |

Rationale and module boundaries: [docs/build/sdd.md](docs/build/sdd.md).

## 6. Repo layout and commands

```
Cargo.toml         Rust workspace (guardian, tusdc, checker)
contract/guardian/ Guardian contract (crate guardian)
contract/token/    mock NEP-141 tUSDC (crate tusdc)
checker/           checker lib + binary (crate checker); native and wasm32-wasip2
schemas/           frozen JSON Schemas; schemas/examples/ holds one valid example each
agent/             uv project firewall-agent, package firewall_agent
                   scripts: firewall-demo, firewall-relayer, firewall-setup-testnet, firewall-jev-ping
data/decisions/    DecisionRecord output (gitignored)
docs/              see docs/index.md
```

Run from the repo root unless noted.

Prerequisites:

```
rustup target add wasm32-wasip2
cargo install cargo-near --version 0.21.1 --locked --no-default-features
# Windows: that source build needs a full Perl for vendored OpenSSL; use the release binary instead:
# https://github.com/near/cargo-near/releases/tag/cargo-near-v0.21.1 (cargo-near-x86_64-pc-windows-msvc.tar.gz → ~/.cargo/bin)
```

Rust:

```
cargo test --workspace
cargo build -p checker --release                              # target/release/checker(.exe)
cargo build -p checker --target wasm32-wasip2 --release       # target/wasm32-wasip2/release/checker.wasm
cd contract/guardian && cargo near build non-reproducible-wasm --no-abi   # target/near/guardian/guardian.wasm
cd contract/token && cargo near build non-reproducible-wasm --no-abi      # target/near/tusdc/tusdc.wasm
```

`--no-abi`: on Windows MSVC the ABI step links the contract as a native DLL and fails (`LNK1120` unresolved host functions). `.cargo/config.toml` sets `AWS_LC_SYS_PREBUILT_NASM=1` so `cargo test` builds `aws-lc-sys` (via near-sdk `unit-testing`) without `nasm.exe`.

Python (offline, no keys needed):

```
cd agent && uv sync && uv run pytest
cd agent && uv run firewall-demo --scenario benign-hosting       # dry-run, scripted LLM
cd agent && uv run firewall-demo --scenario attack-morse-lookalike
```

The demo needs the native checker built first. `firewall-jev-ping` needs `TYPESAFE_API_KEY`.

Testnet — **human confirmation required** (each signs transactions; agents must not run them):

```
cd agent && uv sync --extra testnet
cd agent && uv run firewall-setup-testnet
cd agent && uv run firewall-relayer
cd agent && uv run firewall-demo --scenario benign-hosting --mode testnet
```

## 7. Integration rules

- **Jev is the decision brain; NEAR is load-bearing** (custody, limits, settlement, audit log). Say so in the README's first paragraph. Source: [tracks ranked](docs/hackathon-context/near_hackathon_tracks_ranked.md) Part 1 limit 4, Part 7 item 2.
- **Verdicts are allow / hold / block, with no human step.** Hold when Jev's `unusual` probability exceeds the conformal threshold q̂ (ε = 5%, pooled calibration set; per-agent threshold only after ≥99 normal payments). Block only when above q̂ and two attack signals from different detectors agree, at most one of them from Jev. Thresholds live in checker config, never in prompts. Source: [idea.md](docs/build/idea.md) "Decision model".
- **All Jev calls go through the `DecisionClient` trait in `checker/src/decision.rs`.** `JevDecisionClient` is primary; `LlmDecisionClient` (NEAR AI Cloud) is the fallback on error or timeout, and the record logs `backend: "llm"`.
- **Jev hardening:** neutral option labels (A/B/C + definitions); probabilities never returned to the agent or written on-chain; untrusted text goes in `state` as data only; policies written as examples + counterexamples. Sources: [arxiv papers](docs/tools/arxiv_papers_for_build.md) TL;DR #1–#3.
- **No AI judges an amount.** The verdict binds receiver, token, exact amount and `request_id` (one-time nonce). The contract pays only on an exact match. Hard caps live in contract code. Source: idea.md "Amount safety rules".
- **A Jev gate alone is not a security boundary.** Enforce hard limits in the contract or keys (function-call access keys, amount caps). Source: arxiv papers TL;DR #1 JevBreak (2611.03759) and #2 (2610.12292).
- **Log every decision.** On-chain receipt = outcome, reason codes, `input_sha256`, `record_sha256`, checker version. The full DecisionRecord (probabilities included) goes to the owner's off-chain log. Source: idea.md "Decision model"; tracks ranked Part 7 item 3.
- **NEAR network: testnet by default.** Any real mainnet transaction needs human confirmation. Source: HACKATHON.md Q-007, Q-008, Q-010.

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
- Open human-only gaps are marked `TBD(human)`; find them with `grep -rn "TBD(human)" docs README.md`.
