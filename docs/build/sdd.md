# SDD — backlogs-near software design

## 1. Status

Project chosen: "Attested Payment Firewall" (working name; the human sets the final name at submission). Plan: [idea.md](idea.md). Last updated 2026-11-09.

Implemented as of the Sunday scaffold: frozen formats (`schemas/`), mock token, Guardian with `request_payment` and yield/resume, a checker that returns a hard-coded allow, and a Python agent with a key-free dry-run. Added Mon: hard caps and hold escrow in the Guardian; the `DecisionClient` (Jev primary, NEAR AI LLM fallback) in the checker, not yet called by `decide()`; 60 dry-run scenarios (30 benign, 30 attack, 5 per family) in `agent/scenarios/`. Everything else is marked below with the idea.md day that adds it.

## 2. Stack

Same decision as [AGENTS.md §5](../../AGENTS.md#5-stack-decided).

| Layer | Choice | Notes |
| --- | --- | --- |
| Guardian contract | Rust, `near-sdk` 5.29.1, `cargo-near` 0.21.1 | Yield/resume per docs.near.org yield-resume. 5.30.1 needs rustc 1.95; the toolchain here is 1.94 |
| Mock token | NEP-141 tUSDC (`near-contract-standards` 5.29.1) | 6 decimals, deployed by us on testnet |
| Checker | Rust bin | `wasm32-wasip2` on OutLayer, native for local/eval |
| Decision model | Jev via the TypeSafe API (`jev-latest`), the main path; optional NEAR-hosted Jev (`typesafe/jev-1.13`, NEAR AI Cloud `/v1/systemone`) via `JEV_PROVIDER=nearai` | Raw HTTPS from the checker; fields checked against docs.typesafe.ai/api/system-one |
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
checker/            crate `checker`: lib + bin (`checker::{decide, decision, formats, http}`); the bin reads CheckerInput on stdin, prints Verdict on stdout
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

Every Jev call in the checker goes through this trait in `checker/src/decision.rs`. Shapes follow the TypeSafe System One API: `POST https://api.typesafe.ai/v1/systemone`, body `{model, state, questions}`, response `{model, answers, usage}`. **The clients, fallback and selection are implemented (Mon). `decide()` in `checker/src/decide.rs` still returns the stub allow and does not call them; wiring and fusion are Wed ([idea.md Day-by-day plan](idea.md#day-by-day-plan-nov-814)).**

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
pub struct Decision { pub backend: JevBackend, pub model: String, pub answers: BTreeMap<String, Answer> }
pub enum DecisionError {
    Config(String), Http(HttpError), Status { status: u16, body: String }, OffSchema(String),
}
pub trait DecisionClient {
    fn decide(
        &self,
        state: &serde_json::Value,
        questions: &BTreeMap<String, Question>,
    ) -> Result<Decision, DecisionError>;
}
```

- **Questions.** `firewall_questions()` returns the four questions (`verdict`, `unusual`, `injection_driven`, `receiver_risk`), the same text as `jev_ping.py` ([idea.md Tech stack](idea.md#tech-stack-and-models)). Questions stay atomic; combination happens in code, not in prompts.
- **Validation.** Both clients run `check_answers`: every asked question is answered in its own shape, a choice is a criteria key, probabilities are finite, in [0, 1] and keyed exactly by the criteria keys (choice) or `"0".."n-1"` (score), `noul` is in [0, 1]. Anything else is `OffSchema`. Unknown response fields (Jev's `legend`) are ignored.
- **Primary: `JevDecisionClient`.** Provider chosen by `JEV_PROVIDER`. `typesafe` (default, the main path): POST `https://api.typesafe.ai/v1/systemone` with `$TYPESAFE_API_KEY` and `model: "jev-latest"`. `nearai` (explicit option): POST `{NEAR_AI_BASE_URL}/systemone` (default base `https://cloud-api.near.ai/v1`, trailing `/` trimmed) with `Authorization: Bearer $NEAR_AI_API_KEY` and `model: "typesafe/jev-1.13"`; same request and response shapes, billed to NEAR AI credits. The NEAR AI Cloud LLM (`CHECKER_LLM_MODEL`) is the fallback if Jev fails. `JEV_MODEL` overrides the model on either; an unknown provider → `Config("JEV_PROVIDER must be nearai or typesafe")`; a missing or empty key → `Config("<KEY NAME> not set")`. 20 s timeout, no retry. `Decision.model` is the model string Jev returns; `backend: jev`. Request and response handling are the pure functions `build_jev_body` and `parse_jev_response`; configuration is testable through `JevDecisionClient::from_vars`.
- **Fallback: `LlmDecisionClient`.** Posts to `{NEAR_AI_BASE_URL}/chat/completions` (default `https://cloud-api.near.ai/v1`) with `model: $CHECKER_LLM_MODEL`, `temperature: 0`, 25 s timeout. The system prompt marks `state` as untrusted data and demands one JSON object of probabilities. `parse_llm_reply` strips fences (first `{` to last `}`), renormalises each probability map whose sum is in [0.98, 1.02] (otherwise `OffSchema`), and derives `choice` (argmax), `score` (Σ level·p) and `confidence` (max p). An off-schema reply is retried once with the same request, then it is an error (the check becomes `check_unavailable`). `backend: llm`, `model` is `CHECKER_LLM_MODEL`.
- **`FallbackDecisionClient`** wraps a primary and an optional fallback: on any primary error it returns the fallback's result, or the primary's error if there is no fallback. The decision record logs `backend: "llm"` when the fallback answered.
- **Selection:** `client_from_env()` reads `DECISION_BACKEND`. Unset or `jev` → Jev with the LLM as fallback (the fallback is dropped if `NEAR_AI_API_KEY` or `CHECKER_LLM_MODEL` is missing); `llm` → LLM only; anything else → `Config("DECISION_BACKEND must be jev or llm")`.
- **HTTP** sits behind `checker::http::post_json(url, bearer, body, timeout)` (sends `Authorization: Bearer` and `Content-Type: application/json`; non-2xx statuses come back as `Ok`, and `DecisionError::Status` carries the first 300 chars of the body): `ureq` 3 natively, `wasi-http-client` under `cfg(target_os = "wasi")` (wasm32-wasip2). Natively `timeout` bounds the whole request; on WASI only a connect timeout exists and OutLayer's 60 s cap bounds the rest. The budgets do not fit under that cap: the LLM client retries once, so the worst case is 20 s (Jev) + 2 × 25 s (LLM) = 70 s, and on WASI a Jev call that stalls after connecting uses the whole 60 s. Both fail closed: no verdict arrives, the yield times out and the Guardian unreserves. The budgets get retuned when the checker is wired to OutLayer (Wed). No other module opens sockets.
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
- **RPC:** default is FastNEAR `https://test.rpc.fastnear.com` (rpc.testnet.near.org is deprecated and rate-limited), configurable via `NEAR_RPC_URL`; other providers at https://docs.near.org/api/rpc/providers (Q-009).
- **NEAR Intents:** not used.

### Guardian (`contract/guardian`, crate `guardian`)

State: `owner_id`, `agent_id`, `token_id`, `token_decimals`, `checker_id`, `next_request_id` (starts at 1), `pending: IterableMap<u64, Pending>`, `receipts: IterableMap<u64, Receipt>`, `refs: LookupMap<String, u64>` (client_ref → request_id), `held: IterableMap<u64, Held>` (hold escrow: `receiver_id`, `amount`, `release_at_ns`, `charged_day`), `spend_day` (UTC day index, `block_timestamp / 86_400_000_000_000`), `spent_today`. Limits: context ≤ 8192 serialized bytes, ≤ 8 context items, ≤ 16 pending requests.

The mode is not part of this struct: see [OutLayer checker mode](#outlayer-checker-mode).

Hard caps (constants in contract code, tuned by redeploying): 200 tUSDC per payment, 500 tUSDC per UTC day. `request_payment` reserves the amount against `spent_today` at request time (`spend_day` rolls the counter), so pending, held and paying amounts together can never exceed the cap. The reservation is released on block, yield timeout, transfer failure and `cancel_held`; paid and paying amounts stay counted. A hold charged on day D and released on D+1 still counts against D (each request records `charged_day`). So the cap bounds amounts committed per request day, and payouts in one wall-clock day can reach about 2× the daily cap (D's holds released on D+1, plus D+1's own requests). The window for a hold depends on its amount: 10 min below 20 tUSDC, 1 h up to 100, 6 h above.

| Method | Kind | Behavior |
| --- | --- | --- |
| `new(owner_id, agent_id, token_id, token_decimals, checker_id)` | init | Sets config |
| `ft_on_transfer(sender_id, amount, msg)` | change | Panics `Unsupported token` unless the caller is `token_id`; refunds unless `sender_id == owner_id` (owner deposits fund custody) |
| `request_payment(client_ref, receiver_id, amount, memo, user_request, context)` | change (agent only) | Validates; panics `Amount exceeds per-payment cap` or `Daily cap reached`; reserves the amount; assigns `request_id`, builds CheckerInput, stores `input_sha256` and `charged_day`; relayer mode yields to `on_verdict`, OutLayer mode calls `request_execution` then `on_outlayer_verdict`; emits `payment_requested` |
| `submit_verdict(request_id, verdict)` | change (checker only) | Rejects any verdict whose format, request_id, receiver, token or amount differs, or with bad reasons/hash; panics `Request is decided by OutLayer` for OutLayer-mode requests; resumes the yield |
| `on_verdict(request_id, verdict)` | private callback | Never panics. `allow` → `ft_transfer`; `hold` → `held` receipt plus a `held` escrow entry with `release_at_ns`; `block` → `refused` (unreserves); yield timeout → `timed_out` (unreserves); emits `payment_decided` with `release_at_ns` (set for holds, otherwise `null`) |
| `on_transfer_done(request_id, charged_day, amount)` | private callback | `paid`, or `transfer_failed` (unreserves) |
| `release_held(request_id)` | change (anyone) | Panics `Unknown hold` or `Hold window not over`; after `release_at_ns` removes the hold, sets the receipt to `paying`, transfers like `allow`, emits `hold_released` |
| `cancel_held(request_id)` | change (owner or checker) | Panics `Only the owner or checker can cancel holds` or `Unknown hold`; removes the hold, receipt becomes `refused` (outcome stays `hold`), unreserves, emits `hold_cancelled` |
| `set_checker_mode(mode)` | change (owner only) | Panics `Only the owner can set the checker mode` or `Invalid checker mode: <field>`; `mode` is `"relayer"` (default) or `{"outlayer": {...}}`; emits `checker_mode_set` |
| `get_checker_mode()` | view | The current mode |
| `on_outlayer_verdict(request_id)` | private callback | OutLayer mode only; parses and binds the verdict, then settles like `on_verdict`; fails closed with `checker_failed` |
| `get_config()` | view | Config, including `per_payment_cap` and `daily_cap` |
| `get_daily_spent()` | view | Amount reserved or spent today; 0 once the UTC day has rolled |
| `get_pending(from_index, limit)` | view | Pending requests with `checker_input` and `input_sha256`, for the relayer |
| `clear_stuck_outlayer(request_id)` | change (owner only) | Panics `Only the owner can clear stuck requests`, `Unknown OutLayer request` or `Request is not stuck` (needs 300 blocks since `requested_block`); unreserves, receipt `timed_out`, emits `checker_failed` (`stuck_cleared`) |
| `get_outlayer_usage()` | view | `{day, used, max_per_day}` of the daily OutLayer request budget, read from the persisted counter whenever it exists (`max_per_day` is 0 in relayer mode); `null` only if OutLayer was never used; `used` is 0 if the stored day is not today |
| `get_held(from_index, limit)` | view | Holds: `request_id`, `receiver_id`, `amount`, `release_at_ns`; limit clamped to 50 |
| `get_receipt(request_id)` / `get_receipt_by_ref(client_ref)` | view | One receipt |
| `list_receipts(from_index, limit)` | view | Receipts, limit clamped to 50 |

Validation lives in `validate.rs` as pure functions (`binds`, `parse_outlayer_output`, `valid_mode`). In relayer mode the yield times out after 200 blocks and validation happens in `submit_verdict`; in OutLayer mode it happens in `on_outlayer_verdict`. Both modes settle through one shared `settle`. Events use NEP-297 with standard `payment_firewall`; OutLayer mode adds `checker_mode_set` and `checker_failed`.

### Token (`contract/token`, crate `tusdc`) — scaffold

NEP-141 (FungibleToken), NEP-145 (storage management) and NEP-148 (metadata: "Test USDC (backlogs-near)", `tUSDC`, 6 decimals) via `near-contract-standards`. `new(owner_id)` starts at zero supply. `mint(account_id, amount)` is owner-only, registers the account without a storage deposit (testnet mock) and emits the standard `FtMint` event.

### Planned additions

| Addition | Day ([idea.md](idea.md#day-by-day-plan-nov-814)) |
| --- | --- |
| ~~`CheckerMode::{Relayer, OutLayer}`~~ implemented, see [OutLayer checker mode](#outlayer-checker-mode); the human registration and the first testnet run remain | Mon–Tue |
| Per-payee budgets (learned, contract state) | Wed |
| TEE re-check during the hold window, and refund (`cancel_held`) on a flagged re-check. Release without a re-check is implemented | Wed |
| Receiver auto-registration with the token before `ft_transfer` | Wed |

The relayer mode (scaffold) is not attested: `firewall-relayer` polls `get_pending`, runs the native checker, and calls `submit_verdict` as `checker_id`. It is the skeleton and the fallback if OutLayer yield/resume is not working by Tuesday night.

### OutLayer checker mode

Implemented in `contract/guardian` and `checker`; **not yet exercised on testnet** (needs the human steps below). Facts below come from OutLayer's own docs and repo (URLs inline).

- `outlayer.testnet` (mainnet `outlayer.near`) `request_execution` (payable): `{source: {Project: {project_id: "<owner>/<name>", version_key: null | "<wasm sha256>"}}, resource_limits: {...}, input_data, secrets_ref?, response_format?, payer_account_id?, params?}`. `resource_limits` must always be passed (even `{}`), or nothing runs. Defaults 1e9 instructions / 128 MB / 60 s; caps 5e11 / 4096 MB / **180 s** ([near-integration](https://app.outlayer.ai/docs/near-integration), [contract README](https://github.com/out-layer/outlayer/blob/main/contract/README.md)).
- The deposit is attached NEAR; unused part is refunded to the caller (`payer_account_id` default). Attach the on-chain view `estimate_execution_cost(resource_limits, input_len)`. Gas: OutLayer's settlement callback takes 50 TGas from the attached gas; docs attach 100 TGas ([contract README](https://github.com/out-layer/outlayer/blob/main/contract/README.md) "Deposit", "Gas").
- `input_data` is the guest's **stdin**; secrets arrive as **env vars**; the build must be a `[[bin]]` with `fn main`, writing JSON to stdout, **≤ 900 bytes**, flushed; `wasm32-wasip2` has no files, so the checker does not write its DecisionRecord there ([wasi](https://app.outlayer.ai/docs/wasi), [secrets](https://app.outlayer.ai/docs/secrets)).
- The calling contract's callback receives the output as a JSON value: a string for `Text` (the Guardian requests `Text`), the guest's JSON for `Json`, and `null` when the run failed or produced nothing ([contract README](https://github.com/out-layer/outlayer/blob/main/contract/README.md) "Return value"). A run that outlives the 200-block yield window pays the base fee; how that reaches the callback is not specified, so any failed promise result and `null` are both treated as failure.
- The TDX attestation (wasm hash, input hash, output hash, worker measurements, quote) is published per execution in OutLayer's coordinator and dashboard (`/executions`); it is **not** delivered to the contract ([tee-attestation](https://app.outlayer.ai/docs/tee-attestation)). The contract trusts that only OutLayer's registered worker key can resume the yield. The receipt ties a result to code via the pinned `version_key` plus `input_sha256` (SHA-256 of the `input_data` the Guardian sent; that it equals OutLayer's attested input hash is an inference, not stated in the docs) and `record_sha256`.

Guardian behavior:

- Mode is `Relayer` (default) or `OutLayer {outlayer_id, project_id, version_key, secrets_ref, deposit_yocto, max_instructions, max_execution_seconds, max_requests_per_day}`. JSON: `"relayer"` or `{"outlayer": {...}}`. `set_checker_mode` is owner-only and validates the fields; `get_checker_mode` is a view. A corrupt stored `checker_mode` panics `Corrupt checker mode` (an absent key is `Relayer`).
- **Storage layout is unchanged.** The `Guardian` borsh root struct, `Pending`, `Held` and `Receipt` are not touched. The mode is one raw storage entry under key `checker_mode` (absent = `Relayer`; setting `Relayer` removes it), and each request sent to OutLayer gets a raw marker `outlayer_req:<request_id u64 LE>` (removed in the callback). No other key starts with these bytes: collection prefixes are the single bytes 0..=3 and the root key is `STATE`. So the already-deployed state at `guardian.jimuelle-firewall.testnet` deserializes as before.
- In OutLayer mode `request_payment` keeps every check, cap and reservation, builds the same `CheckerInput` and `input_sha256`, checks the daily request budget, panics `Guardian balance too low for the OutLayer deposit` unless the spendable balance is at least `deposit_yocto + OUTLAYER_BALANCE_MARGIN` (0.05 NEAR) plus the storage for the request (`(checker_input bytes + 600) × storage byte cost`), checked before any state change, then calls `request_execution` (100 TGas, `deposit_yocto` from the Guardian's own balance, because a function-call key cannot attach a deposit, per [NEAR access keys](https://docs.near.org/protocol/accounts-contracts/access-keys): they "do **not allow** to **attach NEAR tokens** to the call") and `.then` `on_outlayer_verdict` (40 TGas). The agent's `request_payment` call therefore needs at least ~160 TGas attached; the agent's `TestnetGuardian` now attaches 200 TGas to `request_payment`.
- `on_outlayer_verdict` reads the promise result (≤ 2048 bytes), parses a Verdict (≤ 900 bytes), runs `validate::binds` against the pending request, then calls the same `settle` as `on_verdict` (pay / hold escrow / refuse, receipt, `payment_decided`, unreserve). It never panics and fails closed: OutLayer failure, `null`, oversized, unparsable or unbound output → no transfer, reservation released, receipt `timed_out` with no outcome, plus a `checker_failed` event with `reason` ∈ `outlayer_failed`, `null_result`, `bad_result_json`, `bad_result_shape`, `oversized`, `bad_verdict`, `unbound_<field>`.
- `submit_verdict` panics `Request is decided by OutLayer` for a request that was sent to OutLayer. Requests keep the mode they were made under when the mode changes.
- **Daily request budget:** `max_requests_per_day` (1..=1000) caps OutLayer requests per UTC day. The counter is one raw entry `outlayer_day` = borsh `(day_index u64, count u64)`, `day_index = block_timestamp / 86_400_000_000_000`. `request_payment` counts each OutLayer request and panics `OutLayer daily request budget reached` before any state change when the budget is used up. Nothing is refunded: block, failure and timeout still count. `get_outlayer_usage` shows `{day, used, max_per_day}` from the persisted counter.
- **Mode validation** (`valid_mode`) rejects an `outlayer_id` other than `outlayer.testnet` / `outlayer.near`, `deposit_yocto` above `MAX_OUTLAYER_DEPOSIT` (1 NEAR) and `max_requests_per_day` outside 1..=1000. `get_pending` skips requests that carry an `outlayer_req:` marker, so the relayer never tries to answer them.
- **Stuck requests:** `clear_stuck_outlayer(request_id)` (owner only) needs the marker and `block_height >= requested_block + OUTLAYER_STUCK_BLOCKS` (300, beyond the 200-block yield window). It removes marker and pending, unreserves, writes the receipt `timed_out` the same way as a failed callback and emits `checker_failed` with reason `stuck_cleared`.

Human runbook (testnet; each step signs or spends, so the human runs them):

1. Build the wasm: `cargo build -p checker --target wasm32-wasip2 --release` → `target/wasm32-wasip2/release/checker.wasm`. For a reproducible hash (a different toolchain gives different bytes and a different hash) build with OutLayer's `scripts/build_github_wasm.sh --dir . --target wasm32-wasip2`, which builds "in a pinned Docker image, so anyone gets the same hash every time" ([wasi docs](https://app.outlayer.ai/docs/wasi), "Option 1: Reproducible Build"). The relayer is not needed in OutLayer mode.
2. Install the OutLayer CLI and `outlayer login testnet` with the owner account ([CLI docs](https://github.com/out-layer/outlayer/blob/main/docs/CLI.md)).
3. `outlayer upload target/wasm32-wasip2/release/checker.wasm` → note the SHA256 and FastFS URL; then `outlayer deploy firewall-checker <FastFS URL>` → project `<owner>/firewall-checker`, active version = that hash.
4. Secrets (only once `decide()` calls Jev): `outlayer secrets set '{"TYPESAFE_API_KEY":"..."}' --project <owner>/firewall-checker --profile default`. The Guardian passes the row via `secrets_ref` `{profile, account_id: <owner>}`.
5. Read the deposit: `near view outlayer.testnet estimate_execution_cost '{"resource_limits":{"max_instructions":1000000000,"max_execution_seconds":30},"input_len":3000}'`; use that value (or a bit more) as `deposit_yocto`.
6. Redeploy the Guardian wasm (`cd contract/guardian && cargo near build non-reproducible-wasm --no-abi`, then deploy it over the existing account **without calling `new`**; state is kept). Fund the Guardian with NEAR for deposits (each request attaches `deposit_yocto`; the unused part comes back).
7. As the owner: `near call <guardian> set_checker_mode '{"mode":{"outlayer":{"outlayer_id":"outlayer.testnet","project_id":"<owner>/firewall-checker","version_key":"<sha256 from step 3>","secrets_ref":null,"deposit_yocto":"<step 5>","max_instructions":"1000000000","max_execution_seconds":"30","max_requests_per_day":"50"}}}' --accountId <owner>`. Check `get_checker_mode` and `get_outlayer_usage`. Switch back with `'{"mode":"relayer"}'`. A request stuck past 300 blocks is cleared by the owner with `clear_stuck_outlayer '{"request_id":"<id>"}'`.
8. Stop `firewall-relayer` for the test (not needed in OutLayer mode), run the demo in testnet mode (the agent attaches 200 TGas to `request_payment`), then check `get_receipt` and the OutLayer dashboard `/executions` for the attestation. A `checker_failed` event means the callback failed closed; its `reason` says which check.

Open questions for the first testnet run: exact shape of the Text result (JSON string expected; JSON object also accepted), how a yield timeout reaches the callback, and the real deposit.

Next steps (not built): `DECISION_LOG_URL` off-chain record sink (the checker cannot write a record on OutLayer, so the OutLayer-mode DecisionRecord stays unwritten until the sink exists, §7); the HTTPS + signed-verdict alternative mode.

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
| `TYPESAFE_API_KEY` | Jev API key, from console.typesafe.ai/keys; required for the checker's main Jev path (default `JEV_PROVIDER=typesafe`) and `firewall-jev-ping` | `firewall-jev-ping` (jev_ping); checker (`JevDecisionClient`, typesafe provider) |
| `NEAR_AI_API_KEY` | NEAR AI Cloud key, from https://cloud.near.ai | agent config (`--llm near-ai`); checker (`LlmDecisionClient` fallback, and `JevDecisionClient` only with `JEV_PROVIDER=nearai`; MELON from Tue) |
| `JEV_PROVIDER` | `typesafe` (default; api.typesafe.ai) or `nearai` (NEAR AI Cloud `/v1/systemone`) | checker (`JevDecisionClient`) |
| `JEV_MODEL` | Optional Jev model override; default `jev-latest` on typesafe, `typesafe/jev-1.13` on nearai | checker (`JevDecisionClient`) |
| `NEAR_AI_BASE_URL` | `https://cloud-api.near.ai/v1` | agent config; checker (`JevDecisionClient` nearai provider, `LlmDecisionClient`) |
| `AGENT_MODEL` | NEAR AI Cloud model id with tool calling (list via `GET $NEAR_AI_BASE_URL/models`) | agent config |
| `NEAR_NETWORK` | `testnet` (default); mainnet only with human confirmation | agent config, setup_testnet, relayer |
| `NEAR_RPC_URL` | RPC endpoint; default `https://test.rpc.fastnear.com` (the legacy near.org testnet RPC is deprecated and rate-limited) | agent config, setup_testnet, relayer |
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
| `DECISION_BACKEND` | `jev` (default) or `llm`; see §4 | checker (`client_from_env`) |
| `CHECKER_LLM_MODEL` | NEAR AI Cloud model for the checker's LLM decision fallback; required by the `llm` backend, and the fallback is disabled without it | checker (`LlmDecisionClient`) |

Added later:

| Variable | Purpose | Added by |
| --- | --- | --- |
| `CLASSIFIER_URL` | Hosted injection classifier endpoint | Tue |
| `HF_TOKEN` | Hugging Face token for the gated Prompt Guard 2 | Tue |
| `DECISION_LOG_URL` | Off-chain record sink for OutLayer runs (OutLayer secret) | Mon/Wed |
| `OUTLAYER_PROJECT_ID` | Not read by any code: the OutLayer project id is an argument of `set_checker_mode` ([§6 runbook](#outlayer-checker-mode)); kept as a note for the human's shell | runbook only |

## 9. Testing & evaluation

Run from the repo root unless noted (full command list: [AGENTS.md §6](../../AGENTS.md)).

- **Rust:** `cargo test --workspace`. Guardian: every `request_payment` panic including the 8192/8193-byte context boundary, CheckerInput equals the request fields, `schemas/examples/` parse into the guardian types, `binds` rejects each mismatched field, `on_verdict` mapping of allow/hold/block/error, `ft_on_transfer` handling, per-payment and daily caps (boundary, rollover), unreserve on block and timeout, hold window boundaries, `release_held` after the window (and rejection before it), `cancel_held` by the owner (stranger rejected). Token: owner-only mint, auto-registration, decimals. Checker: verdict binds input, `record_sha256` matches, ≤ 900 bytes with maximum-length ids and 6 reasons, wrong format or unknown field rejected; `DecisionClient` request/response parsing, `JevDecisionClient::from_vars` provider selection (default TypeSafe, explicit `nearai`, trailing-slash base URL, `JEV_MODEL` override, unknown provider, missing key), LLM reply normalisation, fallback on primary error, and two `#[ignore]` live calls: `jev_live` (`cargo test -p checker -- --ignored jev_live`; uses the configured provider, so `TYPESAFE_API_KEY` by default, `NEAR_AI_API_KEY` with `JEV_PROVIDER=nearai`) and `llm_live` (`cargo test -p checker -- --ignored llm_live`; needs `NEAR_AI_API_KEY` and `CHECKER_LLM_MODEL`; spends credits).
- **Contract builds:** `cargo near build non-reproducible-wasm --no-abi` inside `contract/guardian` and `contract/token` → `target/near/guardian/guardian.wasm`, `target/near/tusdc/tusdc.wasm` (`--no-abi`: the ABI step fails to link on Windows MSVC). Checker builds: `cargo build -p checker --release` and `cargo build -p checker --target wasm32-wasip2 --release`.
- **Python:** `cd agent && uv sync && uv run pytest`. `test_formats` (amount conversion, context limits), `test_schemas` (every example and every built request validates against its schema; the scenario set is balanced: 30 benign / 30 attack, 5 per attack family), `test_local_guardian` (needs the built checker; verdict and record validate, record sha256 matches, a tampered verdict is rejected).
- **No sandbox tests:** `near-workspaces` is not used (Windows host). The yield/resume path against a real chain is covered by the human-run testnet smoke (`firewall-demo --mode testnet`), listed in the README.
- **Eval (Thu):** about 300 labelled cases (150 benign / 150 attack, six families), calibration/test split, per-check and combined ablation, unseen-family rotation, cost and latency with and without the cascade. Protocol and results table: [idea.md Evaluation and calibration](idea.md#evaluation-and-calibration). Attack fixture candidates: [huggingface models](../tools/huggingface_models_for_build.md) and [arxiv papers](../tools/arxiv_papers_for_build.md) (CrAIBench 2503.16248, Agentic Commerce Bench 2609.35886); verify each license before use.

## 10. Modules

One line each, with the idea.md day that adds it ([Day-by-day plan](idea.md#day-by-day-plan-nov-814)).

- `checker/src/decide.rs` — scaffold stub returning `allow` / `stub_allow`; later calls the checks below and fusion (Sun scaffold, replaced Tue/Wed).
- Policy rules (deterministic: allowlists, per-payee limits, memo/amount sanity) — Tue.
- Injection classifier client (HTTP to `CLASSIFIER_URL`, scores each context item) — Tue.
- MELON masked re-run (NEAR AI Cloud inside the checker; compares the tool call with the user request masked) — Tue.
- Counterparty signals (account age, contract code hash changes, prior payments, lookalike distance, via OutLayer RPC `view`) — Tue.
- Jev fusion (conformal threshold and the two-signal block rule over the `DecisionClient` answers) — Wed. The `DecisionClient` itself landed Mon (§4); fusion and the thresholds are still Wed.
- Cascade (cheap checks first; MELON only for ambiguous cases) — Thu, evaluated in the cost table.
- `agent/firewall_agent/agent.py` and `llm.py` — bill-paying agent with a `pay_invoice` tool; scripted or NEAR AI Cloud LLM (Sun).
- `agent/firewall_agent/guardian.py` — `LocalGuardian` (dry-run, mirrors the contract) and `TestnetGuardian` (Sun).
- `agent/firewall_agent/relayer.py` — polls `get_pending`, runs the checker, calls `submit_verdict`; human-gated (Sun; Mon wire path).
- `agent/firewall_agent/setup_testnet.py` — creates accounts, deploys, funds, scopes the agent key; human-gated (Sun).
- Eval and conformal calibration (Python, runs the checker binary over labelled cases) — Thu.
