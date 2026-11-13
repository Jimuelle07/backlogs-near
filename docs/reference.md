# Reference

Moved from the README on 2026-11-13: evaluation and benchmark steps 7–12, configuration switches, and local run instructions. Steps 1–6 stay in [README Try it](../README.md#try-it).

## Evaluation and benchmarks


7. Evaluation. In `agent/`, run `uv run firewall-eval --all-configurations` → the seven configurations (`no_defense`, `policy_only`, `classifier_only`, `code_rules_all_signals`, `jev_fusion_all_signals`, `jev_fusion_conformal`, `jev_fusion_conformal_cascade`) run over the 150 benign and 150 attack scenarios in `agent/scenarios/`, and the results are written as JSON. Useful flags: `--preset <label>` (run one of the seven configurations), `--configuration <label>` (label only), `--scenario <name>`, `--output FILE`, `--scenario-set {main,redteam,external,paysim}` (the red-team set is in `agent/scenarios/redteam/`), `--calibration FILE`, `--record-dir DIR` (keep the decision records), `--refuse-from RESULTS.json` (re-score a recorded Jev run at the current thresholds without calling Jev). The Jev configurations need `TYPESAFE_API_KEY` and spend API credits. Without a key the command still exits 0 and prints `configurations: 7`, but the Jev rows hold every benign case (`false_holds=150`) because Jev is unavailable. The eval always substitutes scenarios in the `demo.testnet` namespace, regardless of `OWNER_ACCOUNT_ID`. Optional per-call prices for the cost column: `EVAL_JEV_USD_PER_CALL`, `EVAL_CLASSIFIER_USD_PER_CALL`. Published results, current checker (2026-11-13): [flagging-main.json](results/flagging-main.json), [flagging-main-calibration.json](results/flagging-main-calibration.json), [flagging-external.json](results/flagging-external.json), [flagging-redteam.json](results/flagging-redteam.json). Baseline (2026-11-13): [results.json](results/results.json), [calibration-all-signals-classifier.json](results/calibration-all-signals-classifier.json), [redteam-results.json](results/redteam-results.json), [redteam.md](results/redteam.md), [external-code-rules.json](results/external-code-rules.json), [external-classifier-only.json](results/external-classifier-only.json), [external-results.json](results/external-results.json), [bec-results.json](results/bec-results.json), [paysim-pooled.json](results/paysim-pooled.json), [jev-budget.md](results/jev-budget.md).
8. Calibration. In `agent/`, run `uv run firewall-calibrate <results.json>` on an eval results file → the conformal threshold `q_hat`, `false_hold_rate` and `sufficient_data`. Flags: `--epsilon`, `--score {unusual,injection_driven}` (default `unusual`), `--rotation` (leave-one-attack-family-out check), `--missing-as-zero`. The two frozen values are the defaults of `FUSION_HOLD_THRESHOLD` (`--epsilon 0.04`) and `FUSION_JEV_INJECTION_HOLD_THRESHOLD` (`--score injection_driven --epsilon 0.01`). On a results file produced without a Jev key it prints `n : 0`, `q_hat : 1.0` and `sufficient_data: False (need n >= 19)`.
9. Optional injection classifier. In `agent/`, run `uv run --with transformers --with torch firewall-classifier 8088` (downloads the model; exits with an error if the model cannot load), then set `CLASSIFIER_URL=http://127.0.0.1:8088/score` in `.env` → the checker calls it and records `signals.injection` in the decision record. Without `CLASSIFIER_URL` the injection check is off (`signals.injection = null`). `uv run firewall-classifier --heuristic 8088` serves a keyword heuristic instead of the model, for offline tests only; its responses report `"model": "keyword-heuristic"`.
10. External set (public benchmarks, rewritten into payment form), no keys. In `agent/`, run `uv run firewall-eval --scenario-set external --preset code_rules_all_signals` → first line `scenarios: 200 (benign=100, attack=100)`. The set is built from public benchmarks and rewritten into payment form; sources and licenses are in [agent/scenarios/external/ATTRIBUTION.md](../agent/scenarios/external/ATTRIBUTION.md).
11. Classifier benchmark. In `agent/`, run `uv run --with transformers --with torch python tools/bench_classifier.py` → writes `docs/results/classifier-bench.json` and `docs/results/classifier-bench.md`. It downloads the public corpora on first run and takes several minutes on a CPU.
12. Hugging Face dataset export. In `agent/`, run `uv run python tools/export_hf_dataset.py` → writes `data/hf-dataset/` (three JSONL splits: main 300 rows, redteam 17, external 200, plus a dataset card) and prints the `huggingface-cli upload …` command. The script uploads nothing. The published copy is at [Jim10/attested-payment-firewall-scenarios-eclipse](https://huggingface.co/datasets/Jim10/attested-payment-firewall-scenarios-eclipse).

## Configuration switches

All are environment variables, read by the checker (for OutLayer runs, set them as OutLayer secrets). `.env.example` lists every variable; [docs/build/sdd.md](build/sdd.md) §8 is the reference. An invalid value fails the run with a non-zero exit instead of falling back.

| Variable | Meaning |
| --- | --- |
| `FUSION_MODE` | `jev` (default): Jev plus code rules fuse the verdict. `code_rules`: code rules only; Jev is never called; 2 or more detectors → block, 1 → hold, 0 → allow. Used by the baseline eval presets. |
| `CASCADE_ENABLED` | Default `false`, only in `jev` mode. Policy, counterparty and Jev run first; the injection classifier runs only when Jev's `unusual` probability exceeds the hold threshold. A skipped classifier leaves `signals.injection` null. |
| `FUSION_HOLD_THRESHOLD` | Hold when Jev's `unusual` exceeds this. Default 0.81, the conformal threshold q̂ (the benign-score quantile fixed by the target false-hold rate ε) at ε = 4%; see [.env.example](../.env.example). |
| `FUSION_JEV_INJECTION_HOLD_THRESHOLD` | In `jev` mode, hold a payment to a new receiver when Jev's `injection_driven` exceeds this. Default 0.81, the conformal q̂ at ε = 1%; `1.0` turns the rule off. |
| `FUSION_INJECTION_THRESHOLD`, `FUSION_JEV_INJECTION_THRESHOLD`, `FUSION_JEV_RECEIVER_RISK_THRESHOLD` | Probabilities in [0, 1] above which the classifier, Jev's injection option or Jev's receiver-risk option counts as a detector. |
| `FUSION_YOUNG_ACCOUNT_DAYS` | Receiver accounts younger than this many days count as young. |
| `FUSION_AGENT_HOLD_THRESHOLD` | Optional probability in [0, 1] that replaces `FUSION_HOLD_THRESHOLD` only when the agent profile has `payments_last_90d >= 99`. |
| `JEV_REFERENCE_EXAMPLES_JSON` | Optional, opt-in, never set by default. JSON object with `fraud_examples` and `legitimate_examples` (1–10 strings each, ≤ 600 chars); adds `reference_cases` to the Jev state. |
| `POLICY_ENABLED`, `INJECTION_ENABLED`, `COUNTERPARTY_ENABLED` | `0` turns that check off (its signal is null). |
| `COUNTERPARTY_TIMEOUT_MS` | Counterparty RPC timeout (default 2000). `COUNTERPARTY_RPC_URL` must be HTTPS. |
| `CLASSIFIER_URL` | Injection classifier endpoint (see step 9). |
| `INJECTION_TIMEOUT_MS` | HTTP timeout of the classifier call in milliseconds (default 3000). A call that fails or times out is a checker error, not a verdict: the run ends with no decision record. |
| `JEV_PROVIDER` | `typesafe` (default) or `nearai` (Jev through NEAR AI Cloud). |

## Run locally

### Read-only receipts panel (React)

From `site/`, run `npm ci` then `npm run dev` → open the printed local URL at `#receipts` to see live receipts from `guardian-v2.jimuelle-firewall.testnet`, with status filters, exact token amounts and testnet explorer links. No wallet or keys are needed. See [site/README.md](../site/README.md) for configuration, checks and production build instructions.

### Agent and contracts

Prerequisites: Rust 1.94+, `rustup target add wasm32-wasip2`, cargo-near 0.21.1 (`cargo install cargo-near --version 0.21.1 --locked --no-default-features`; on Windows use the [release binary](https://github.com/near/cargo-near/releases/tag/cargo-near-v0.21.1), since the source build needs a full Perl for OpenSSL), [uv](https://docs.astral.sh/uv/).

```
cp .env.example .env
cargo test --workspace
cargo build -p checker --release
cargo build -p checker --target wasm32-wasip2 --release
(cd contract/guardian && cargo near build non-reproducible-wasm --no-abi)
(cd contract/token && cargo near build non-reproducible-wasm --no-abi)
cd agent && uv sync && uv run pytest
```

Contract wasm files: `target/near/guardian/guardian.wasm` and `target/near/tusdc/tusdc.wasm`. `--no-abi` skips ABI generation, which fails to link on Windows MSVC. The dry-run needs no keys, but without `TYPESAFE_API_KEY` every payment is held (step 3 of Try it in the [README](../README.md#try-it)).

### Testnet

These commands sign testnet transactions. The human runs them; they are never run by the agent.

```
cd agent
uv sync --extra testnet
uv run firewall-setup-testnet
# relayer checker mode only
uv run firewall-relayer
uv run firewall-demo --scenario benign-hosting --mode testnet
```

Expected: the Guardian receipt reaches `paid` and the hostco tUSDC balance rises by 18. Keys are written to `.env.testnet` (gitignored).

`firewall-relayer` is needed only in relayer checker mode. OutLayer checker mode does not use it ([sdd.md §6](build/sdd.md#outlayer-checker-mode)).

`uv run firewall-nightly-e2e --mode testnet` runs a list of scenarios against testnet (`--scenario NAME`, repeatable; with none it runs the default benign and attack pair), one signed `request_payment` each:

- It cancels held attacks with the owner key, so it needs `OWNER_ACCOUNT_ID` and `OWNER_PRIVATE_KEY`.
- It fails a step whose receipt reasons contain `check_unavailable`.
- It checks that each benign receiver's tUSDC balance rises by exactly the amount.
- `--report FILE` writes the JSON report to `FILE`.
- It asks for confirmation before it signs, unless `-y` is given.

Details: [docs/build/nightly-e2e.md](build/nightly-e2e.md).

### Function-call key

The agent signs with a function-call access key added by `firewall-setup-testnet`. It is scoped to the Guardian contract and the single method `request_payment`, with a gas allowance of 1 NEAR (`agent.add_public_key(fc_public, guardian, ["request_payment"], NEAR)` in `agent/src/firewall_agent/setup_testnet.py`), and the account's full-access key is deleted afterwards. So the agent key can only call `request_payment`: it cannot transfer NEAR or tokens, add keys, or call any other contract or method.

Caveat: when the 1 NEAR gas allowance is used up, the agent is locked out and cannot pay, because an account holding only function-call keys cannot top itself up. The owner restores it by re-adding the function-call key with a new allowance (the owner needs a full-access key for the agent account, e.g. the one kept in `.env.testnet`), or by running `firewall-setup-testnet` again for a fresh set of accounts. See [sdd.md](build/sdd.md) and [system-design.md](build/system-design.md) failure modes.
