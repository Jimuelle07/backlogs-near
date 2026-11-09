# SDD — backlogs-near software design

## 1. Status

Project chosen: "Attested Payment Firewall" (working name; the human sets the final name at submission). Plan: [idea.md](idea.md). Last updated 2026-11-09.

Implemented as of the Sunday scaffold: frozen formats (`schemas/`), mock token, Guardian with `request_payment` and yield/resume, a checker that returns a hard-coded allow, and a Python agent with a key-free dry-run. Everything else is marked below with the idea.md day that adds it.

## 2. Stack

Same decision as [AGENTS.md §5](../../AGENTS.md#5-stack-decided).

| Layer | Choice | Notes |
| --- | --- | --- |
| Guardian contract | Rust, `near-sdk` 5.29.1, `cargo-near` 0.21.1 | Yield/resume per docs.near.org yield-resume. 5.30.1 needs rustc 1.95; the toolchain here is 1.94 |
| Mock token | NEP-141 tUSDC (`near-contract-standards` 5.29.1) | 6 decimals, deployed by us on testnet |
| Checker | Rust bin | `wasm32-wasip2` on OutLayer, native for local/eval |
| Decision model | TypeSafe Jev, raw HTTPS from the checker | `model: "jev-latest"`; fields checked against docs.typesafe.ai/api/system-one |
| LLM | NEAR AI Cloud (OpenAI-compatible) | Agent tool calls, MELON re-run, decision fallback |
| Agent / relayer / eval | Python 3.12, managed by uv | |
| NEAR Python client | py-near | Optional `testnet` extra; dry-run and tests never import it |
| Injection classifier | `protectai/deberta-v3-base-prompt-injection-v2` default; `Llama-Prompt-Guard-2-86M` when HF access is granted | Hosted outside the TEE until the OutLayer runtime question is settled ([PRD §11](prd.md)) |
| Tests | `cargo test` (contracts, checker), `pytest` (agent) | See §9 |

## 3. Repo layout

```
Cargo.toml          Cargo workspace (guardian, token, checker)
contract/guardian/  crate `guardian`: Guardian contract
contract/token/     crate `tusdc`: mock NEP-141 token
checker/            crate `checker`: bin; reads CheckerInput on stdin, prints Verdict on stdout
schemas/            JSON Schema 2020-12 for every wire format; schemas/examples/ one valid example each
agent/              uv project `firewall-agent`, package `firewall_agent`: agent, relayer, setup, dry-run
data/decisions/     checker records from native runs (gitignored)
docs/               see docs/index.md
```

Dependency rules:

- The contracts depend on nothing in the repo. They mirror `schemas/` by hand and unit-test against `schemas/examples/`.
- The checker reads only stdin and environment variables. It never reads repo files or calls the agent.
- The agent talks to the checker only through the `CHECKER_BIN` subprocess (native/dry-run) or through the Guardian (testnet). It never links Rust code.
- `schemas/` is the source of truth for formats. Rust types (`guardian/src/types.rs`, `checker/src/formats.rs`) and Python builders (`firewall_agent/formats.py`) mirror it; a format change edits the schema and its example first.
- The eval harness (Thu) runs the same checker binary the demo uses, so eval numbers describe the shipped behavior.

## 4. DecisionClient

Every Jev call in the checker goes through this trait in `checker/src/decision.rs`. **Implemented Tue/Wed ([idea.md Day-by-day plan](idea.md#day-by-day-plan-nov-814)).** Shapes follow the TypeSafe System One API: `POST https://api.typesafe.ai/v1/systemone`, body `{model, state, questions}`, response `{model, answers, usage}`.

```rust
pub enum Question {
    Choice { instructions: String, criteria: BTreeMap<String, String> },
    Score { instructions: String, criteria: Vec<String> },
    Noul { instructions: String },
}
pub enum Answer {
    Choice { choice: String, probabilities: BTreeMap<String, f64>, confidence: f64 },
    Score { score: f64, probabilities: BTreeMap<String, f64>, confidence: f64 },
    Noul { noul: f64 },
}
pub trait DecisionClient {
    fn decide(
        &self,
        state: &serde_json::Value,
        questions: &BTreeMap<String, Question>,
    ) -> Result<BTreeMap<String, Answer>, DecisionError>;
}
```

- **Primary: `JevDecisionClient`.** `Authorization: Bearer $TYPESAFE_API_KEY`, `model: "jev-latest"`. The four questions (`verdict`, `unusual`, `injection_driven`, `receiver_risk`) are in [idea.md Tech stack](idea.md#tech-stack-and-models). Questions stay atomic; combination happens in code, not in prompts.
- **Fallback: `LlmDecisionClient`.** Calls NEAR AI Cloud and coerces the reply into the same `Answer` shape; off-schema output is retried once, then it is an error (the check becomes `check_unavailable`).
- **HTTP** sits behind a `checker::http` module: `ureq` natively, `wasi-http-client` under `cfg(target_os = "wasi")`. No other module opens sockets.
- **Selection:** `DECISION_BACKEND=jev|llm`, default `jev`. On error or timeout from Jev, fall back to `llm` automatically; the record logs `backend: "llm"`.
- `firewall-jev-ping` (agent package) sends the same four questions once, to verify the API shape and key.

## 5. Verdict rules

Verdicts are allow / hold / block. There is no human step. Source: [idea.md Decision model](idea.md#decision-model-allow-hold-block-no-human).

- **Hold** when Jev's `unusual` probability `s` exceeds the conformal threshold:

  $$\hat q_{\text{hold}} = \lceil (n+1)(1-\varepsilon) \rceil\text{-th smallest of } n \text{ normal calibration scores},\quad n \ge 1/\varepsilon - 1;\quad \text{hold if } s > \hat q_{\text{hold}}$$

  ε = 5%, pooled calibration set (n ≥ 19 covers it from day one). A per-agent threshold applies only after ≥99 normal payments. The false-hold bound assumes exchangeability; state that caveat wherever the number is quoted.
- **Block** only when `s > q̂` and two attack signals from different detectors agree, at most one of them from Jev (`jev_injection_driven`, `jev_receiver_risk`). Other detectors: policy, injection classifier, MELON, counterparty.
- **Thresholds live in checker config**, never in prompts.
- **No AI judges an amount.** The verdict binds receiver, token, exact amount and `request_id` (one-time nonce); the contract pays only on an exact match. Hard caps live in contract code ([idea.md Amount safety rules](idea.md#amount-safety-rules)).
- **A Jev gate alone is not a security boundary.** Attackers can steer Jev-style models to a wrong-but-allowed answer ([arxiv papers](../tools/arxiv_papers_for_build.md) TL;DR #1 JevBreak 2611.03759, #2 2610.12292). The contract's binding, caps and function-call key bound the loss.
- **Jev hardening:** neutral option labels (A/B/C plus definitions; mapped to outcomes in code); probabilities never returned to the agent or written on-chain; untrusted text goes into `state` as data only; policies written as examples plus counterexamples (arxiv TL;DR #3, 2611.02155).
- **Unavailable checks** yield a null signal plus reason `check_unavailable`; an `allow` is then downgraded to `hold`.

## 6. NEAR integration

Project-independent:

- **Accounts:** testnet accounts for development and the demo; faucet funds only ([HACKATHON.md](../hackathon-context/HACKATHON.md) Q-008, Q-010). Anything that signs a testnet transaction needs human confirmation (AGENTS.md §4).
- **Keys:** the agent signs with a function-call access key scoped to the Guardian and to `request_payment`, never a full-access key. Caveat: an account holding only function-call keys cannot transfer NEAR or add keys, and is locked out when the gas allowance runs out; the owner restores it by re-adding the key (README).
- **RPC:** a free public provider from https://docs.near.org/api/rpc/providers (Q-009), configured via `NEAR_RPC_URL`.
- **NEAR Intents:** not used.

### Guardian (`contract/guardian`, crate `guardian`) — scaffold

State: `owner_id`, `agent_id`, `token_id`, `token_decimals`, `checker_id`, `next_request_id` (starts at 1), `pending: IterableMap<u64, Pending>`, `receipts: IterableMap<u64, Receipt>`, `refs: LookupMap<String, u64>` (client_ref → request_id). Limits: context ≤ 8192 serialized bytes, ≤ 8 context items, ≤ 16 pending requests.

| Method | Kind | Behavior |
| --- | --- | --- |
| `new(owner_id, agent_id, token_id, token_decimals, checker_id)` | init | Sets config |
| `ft_on_transfer(sender_id, amount, msg)` | change | Panics `Unsupported token` unless the caller is `token_id`; refunds unless `sender_id == owner_id` (owner deposits fund custody) |
| `request_payment(client_ref, receiver_id, amount, memo, user_request, context)` | change (agent only) | Validates, assigns `request_id`, builds CheckerInput, stores `input_sha256`, yields to `on_verdict`, emits `payment_requested` |
| `submit_verdict(request_id, verdict)` | change (checker only) | Rejects any verdict whose format, request_id, receiver, token or amount differs, or with bad reasons/hash; resumes the yield |
| `on_verdict(request_id, verdict)` | private callback | Never panics. `allow` → `ft_transfer`; `hold` → `held`; `block` → `refused`; yield timeout → `timed_out`; emits `payment_decided` |
| `on_transfer_done(request_id)` | private callback | `paid` or `transfer_failed` |
| `get_config()` | view | Config |
| `get_pending(from_index, limit)` | view | Pending requests with `checker_input` and `input_sha256`, for the relayer |
| `get_receipt(request_id)` / `get_receipt_by_ref(client_ref)` | view | One receipt |
| `list_receipts(from_index, limit)` | view | Receipts, limit clamped to 50 |

Validation lives in `validate.rs` as pure functions (`binds`). The callback times out after 200 blocks; validation happens in `submit_verdict`, never in the callback. Events use NEP-297 with standard `payment_firewall`.

### Token (`contract/token`, crate `tusdc`) — scaffold

NEP-141 (FungibleToken), NEP-145 (storage management) and NEP-148 (metadata: "Test USDC (backlogs-near)", `tUSDC`, 6 decimals) via `near-contract-standards`. `new(owner_id)` starts at zero supply. `mint(account_id, amount)` is owner-only, registers the account without a storage deposit (testnet mock) and emits the standard `FtMint` event.

### Planned additions

| Addition | Day ([idea.md](idea.md#day-by-day-plan-nov-814)) |
| --- | --- |
| `CheckerMode::{Relayer, OutLayer{project_id, version_key}}`: in OutLayer mode `request_payment` calls `outlayer.testnet` `request_execution` with a deposit, `on_verdict` reads stdout via `env::promise_result`; `version_key` pins the checker wasm sha256 | Mon–Tue |
| Hard caps: $200 per payment, $500 per day (starting values, tuned Thu) | Mon–Wed |
| Per-payee budgets (learned, contract state) | Wed |
| Hold escrow with `release_held` / `cancel_held`: hold windows exceed the 200-block yield timeout, so a hold is contract state released by a later call (auto-release if the TEE re-check is clean, otherwise refund), not a yield | Wed |
| Receiver auto-registration with the token before `ft_transfer` | Wed |

The relayer mode (scaffold) is not attested: `firewall-relayer` polls `get_pending`, runs the native checker, and calls `submit_verdict` as `checker_id`. It is the skeleton and the fallback if OutLayer yield/resume is not working by Tuesday night.

OutLayer facts: stdout ≤ 900 bytes, 60 s max execution, secrets arrive as env vars, HTTP needs `wasm32-wasip2`. The TDX attestation is published by OutLayer per execution and is not delivered to the contract; the receipt binds a result to code through the pinned `version_key` plus `input_sha256` and `record_sha256`.

## 7. Decision log

Formats are frozen in `schemas/` (version tags `firewall.checker_input.v1`, `firewall.verdict.v1`, `firewall.decision_record.v1`).

- **Verdict** (checker stdout, ≤ 900 bytes): `format`, `request_id`, `receiver_id`, `token_id`, `amount`, `outcome`, `reasons` (1–6 ReasonCodes), `record_sha256`, `checker_version`.
- **DecisionRecord** (off-chain, owner only): `format`, `input_sha256` (sha256 of the exact stdin bytes), `request_id`, `checker_version`, `outcome`, `reasons`, and `signals` with required keys `policy`, `injection`, `melon`, `counterparty`, `jev`, each `null` (check disabled) or the check's output. Jev's probabilities live here and nowhere public (JevBreak needs them to tune attacks).
- **Receipt** (on-chain, public, `get_receipt`): `request_id`, `client_ref`, `receiver_id`, `amount`, `input_sha256`, `outcome`, `reasons`, `record_sha256`, `checker_version`, `status` (`paying|paid|transfer_failed|refused|held|timed_out`), `requested_block`, `decided_block`.
- ReasonCode (frozen): `stub_allow`, `policy_violation`, `injection_high`, `melon_match`, `lookalike_receiver`, `new_receiver`, `young_account`, `contract_code_changed`, `unusual_for_agent`, `jev_injection_driven`, `jev_receiver_risk`, `amount_mismatch`, `check_unavailable`.

`record_sha256` is the sha256 of the serialized record bytes, so anyone given the record can check it against the receipt.

Storage:

- **Native / dry-run (scaffold):** the checker writes the record to `CHECKER_RECORD_DIR/<request_id>.json`, the same bytes that were hashed, and refuses to overwrite an existing record with different bytes (exit 2). Dry-run (`LocalGuardian`) uses `CHECKER_RECORD_DIR/dry-run/` and continues request ids from the highest existing record; the relayer uses `CHECKER_RECORD_DIR/<GUARDIAN_ID>/`.
- **OutLayer (Mon/Wed):** the 900-byte stdout limit forces an off-chain sink. The checker POSTs the record to `DECISION_LOG_URL` (an OutLayer secret); if that POST fails, `allow` is downgraded to `hold`.

## 8. Configuration

All configuration comes from environment variables; `.env.example` is the canonical list. The agent package loads the repo-root `.env`, then `.env.testnet` (no override). `.env.testnet` is written by `firewall-setup-testnet` and is gitignored.

| Variable | Purpose | Read by |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | Jev API key, from console.typesafe.ai/keys | `firewall-jev-ping` (jev_ping); checker (from Tue) |
| `NEAR_AI_API_KEY` | NEAR AI Cloud key, from https://cloud.near.ai | agent config (`--llm near-ai`); checker (MELON, fallback; from Tue) |
| `NEAR_AI_BASE_URL` | `https://cloud-api.near.ai/v1` | agent config |
| `AGENT_MODEL` | NEAR AI Cloud model id with tool calling (list via `GET $NEAR_AI_BASE_URL/models`) | agent config |
| `NEAR_NETWORK` | `testnet` (default); mainnet only with human confirmation | agent config, setup_testnet, relayer |
| `NEAR_RPC_URL` | RPC endpoint from https://docs.near.org/api/rpc/providers | agent config, setup_testnet, relayer |
| `OWNER_ACCOUNT_ID` | Owner account; also the namespace for sub-accounts (default `demo.testnet`) | agent config, setup_testnet |
| `OWNER_PRIVATE_KEY` | Owner key; never committed | setup_testnet |
| `GUARDIAN_ID` | Guardian contract account | agent config (testnet guardian), relayer |
| `TOKEN_ID` | tUSDC contract account | agent config, setup_testnet |
| `AGENT_ACCOUNT_ID` | Agent account | agent config (testnet guardian) |
| `AGENT_PRIVATE_KEY` | Agent function-call key only | agent config (testnet guardian) |
| `CHECKER_ACCOUNT_ID` | Account allowed to call `submit_verdict` | relayer, setup_testnet |
| `CHECKER_PRIVATE_KEY` | Key for `CHECKER_ACCOUNT_ID` | relayer |
| `CHECKER_BIN` | Checker binary; default `target/release/checker(.exe)` | agent config (LocalGuardian, relayer) |
| `CHECKER_RECORD_DIR` | Record output dir, default `data/decisions` | checker (native), agent config |

Added later:

| Variable | Purpose | Added by |
| --- | --- | --- |
| `DECISION_BACKEND` | `jev` (default) or `llm`; see §4 | Tue |
| `CLASSIFIER_URL` | Hosted injection classifier endpoint | Tue |
| `HF_TOKEN` | Hugging Face token for the gated Prompt Guard 2 | Tue |
| `DECISION_LOG_URL` | Off-chain record sink for OutLayer runs (OutLayer secret) | Mon/Wed |
| `OUTLAYER_PROJECT_ID` | OutLayer project for `CheckerMode::OutLayer` | Tue |

## 9. Testing & evaluation

Run from the repo root unless noted (full command list: [AGENTS.md §6](../../AGENTS.md)).

- **Rust:** `cargo test --workspace`. Guardian: every `request_payment` panic including the 8192/8193-byte context boundary, CheckerInput equals the request fields, `schemas/examples/` parse into the guardian types, `binds` rejects each mismatched field, `on_verdict` mapping of allow/hold/block/error, `ft_on_transfer` handling. Token: owner-only mint, auto-registration, decimals. Checker: verdict binds input, `record_sha256` matches, ≤ 900 bytes with maximum-length ids and 6 reasons, wrong format or unknown field rejected.
- **Contract builds:** `cargo near build non-reproducible-wasm --no-abi` inside `contract/guardian` and `contract/token` → `target/near/guardian/guardian.wasm`, `target/near/tusdc/tusdc.wasm` (`--no-abi`: the ABI step fails to link on Windows MSVC). Checker builds: `cargo build -p checker --release` and `cargo build -p checker --target wasm32-wasip2 --release`.
- **Python:** `cd agent && uv sync && uv run pytest`. `test_formats` (amount conversion, context limits), `test_schemas` (every example and every built request validates against its schema), `test_local_guardian` (needs the built checker; verdict and record validate, record sha256 matches, a tampered verdict is rejected).
- **No sandbox tests:** `near-workspaces` is not used (Windows host). The yield/resume path against a real chain is covered by the human-run testnet smoke (`firewall-demo --mode testnet`), listed in the README.
- **Eval (Thu):** about 300 labelled cases (150 benign / 150 attack, six families), calibration/test split, per-check and combined ablation, unseen-family rotation, cost and latency with and without the cascade. Protocol and results table: [idea.md Evaluation and calibration](idea.md#evaluation-and-calibration). Attack fixture candidates: [huggingface models](../tools/huggingface_models_for_build.md) and [arxiv papers](../tools/arxiv_papers_for_build.md) (CrAIBench 2503.16248, Agentic Commerce Bench 2609.35886); verify each license before use.

## 10. Modules

One line each, with the idea.md day that adds it ([Day-by-day plan](idea.md#day-by-day-plan-nov-814)).

- `checker/src/decide.rs` — scaffold stub returning `allow` / `stub_allow`; later calls the checks below and fusion (Sun scaffold, replaced Tue/Wed).
- Policy rules (deterministic: allowlists, per-payee limits, memo/amount sanity) — Tue.
- Injection classifier client (HTTP to `CLASSIFIER_URL`, scores each context item) — Tue.
- MELON masked re-run (NEAR AI Cloud inside the checker; compares the tool call with the user request masked) — Tue.
- Counterparty signals (account age, contract code hash changes, prior payments, lookalike distance, via OutLayer RPC `view`) — Tue.
- Jev fusion (`DecisionClient` plus the conformal threshold and the two-signal block rule) — Wed.
- Cascade (cheap checks first; MELON only for ambiguous cases) — Thu, evaluated in the cost table.
- `agent/firewall_agent/agent.py` and `llm.py` — bill-paying agent with a `pay_invoice` tool; scripted or NEAR AI Cloud LLM (Sun).
- `agent/firewall_agent/guardian.py` — `LocalGuardian` (dry-run, mirrors the contract) and `TestnetGuardian` (Sun).
- `agent/firewall_agent/relayer.py` — polls `get_pending`, runs the checker, calls `submit_verdict`; human-gated (Sun; Mon wire path).
- `agent/firewall_agent/setup_testnet.py` — creates accounts, deploys, funds, scopes the agent key; human-gated (Sun).
- Eval and conformal calibration (Python, runs the checker binary over labelled cases) — Thu.
