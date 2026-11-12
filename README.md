# Eclipse

> Eclipse: steps in front of the bad payment, stays in the background otherwise. Repository: backlogs-near.

## What it is

A payment firewall for AI agents. Prompt injection can make an agent pay an attacker, and the checks that run on the agent's own host can be skipped by a compromised agent. Here the agent holds only a function-call key scoped to a Guardian contract that holds the funds. Each payment request pauses the contract and runs a checker (policy rules, injection classifier, counterparty signals) whose signals are fused with a TypeSafe Jev decision into allow / hold / block, with no human in the loop. Jev is the decision brain; NEAR is load-bearing (custody, caps, settlement, audit log): NEAR holds the funds, enforces the key scope, binds each verdict to receiver, token and exact amount, enforces the hard caps, settles, and records the receipt.

Plan and scope: [docs/build/idea.md](docs/build/idea.md). Status and per-task evidence: [docs/build/sprints.md](docs/build/sprints.md).

## The problem

Prompt injection drains agent wallets. In May 2026 a Morse-code message made Grok's linked wallet pay out about $150,000 in DRB ([Giskard](https://giskard.ai/knowledge/how-grok-got-prompt-injected-an-x-user-drained-150-000-from-an-ai-wallet)). Chainalysis reports crypto theft rising from $2.2B to $3.4B. Both figures are to be verified against the primary source before submit. Host-side defenses run where a compromised agent can skip them ([PRD §2](docs/build/prd.md#2-problem)).

## How NEAR is used

- Contract custody: the Guardian contract holds the tUSDC; the agent cannot move it directly.
- Access keys: the agent account has only a function-call key limited to the Guardian's `request_payment` (see [Function-call key](#function-call-key)).
- Yield/resume: `request_payment` pauses; the checker's verdict resumes it, and the contract pays only on an exact receiver/token/amount/`request_id` match.
- NEP-141: payments are `ft_transfer` of a mock tUSDC token (6 decimals) deployed on testnet.
- Hard caps in contract code: per-payment cap, daily cap and per-payee budgets bound the loss even if every check is fooled.
- On-chain receipts: outcome, reason codes, input and record hashes, checker version. The full decision record stays in the owner's off-chain log.

## Try it

Numbered steps, each "do X → see Y". Run from the repo root unless a step says otherwise. Steps 1–3 need no keys and no funds; step 4 needs a TypeSafe Jev key. Steps 5–8 also run without a key, with the keyless output stated in each step.

1. `cargo build -p checker --release` → `target/release/checker` (`.exe` on Windows) exists.
2. `cd agent && uv sync` → the Python environment is ready. Optional: `uv run pytest` runs the Python tests.
3. Offline dry-run, no keys. In `agent/`, run `uv run firewall-demo --scenario benign-hosting --reset-spend` → the lines below (`--reset-spend` clears the local dry-run daily spend, which is kept across runs like the contract):
   ```
   scenario: benign-hosting (benign)
   proposed: pay 18000000 units (18 tUSDC) to hostco.demo.testnet memo="INV-2026-11"
   verdict: hold reasons=check_unavailable… record=<64 hex>
   action: held
   held until <UTC time>
   record_file: data/decisions/dry-run/<request id>.json
   ```
   This is the fail-closed design, not a bug: with no `TYPESAFE_API_KEY` Jev cannot be called, and the checker never allows a payment without a Jev verdict. It returns `hold` with reason `check_unavailable` (more reasons may follow it) and the payment is not paid. The dry-run never waits for or releases the hold. The demo substitutes `OWNER_ACCOUNT_ID` (from `.env`) for the scenario namespace when it is set, otherwise `demo.testnet`, so `hostco.demo.testnet` above becomes `hostco.<OWNER_ACCOUNT_ID>`.
4. Dry-run with Jev. Put your key in `.env` at the repo root (`cp .env.example .env`, then set `TYPESAFE_API_KEY=`). Optional: `cd agent && uv run firewall-jev-ping` checks the key. Then in `agent/`:
   - `uv run firewall-demo --scenario benign-hosting --reset-spend` → `verdict: allow reasons=checks_passed …` and `action: would_pay`.
   - `uv run firewall-demo --scenario attack-morse-lookalike --reset-spend` → `verdict: hold …` (`action: held`) or `verdict: block …` (`action: refused`); the receiver `hostc0.demo.testnet` is a lookalike of `hostco.demo.testnet`.
5. Open the file named on the `record_file:` line (e.g. `data/decisions/dry-run/2.json`) → the full decision record; `sha256sum <that file>` equals the `record=` value. The path is relative to the repository root, even though the command ran in `agent/`. Each dry-run gets the next request id, so earlier records are kept; the checker refuses to overwrite a record with different content.
6. Nightly end-to-end check, offline. In `agent/`, run `uv run firewall-nightly-e2e --mode dry-run -y` → one benign and one attack payment, then `Overall Status: SUCCESS` and exit code 0. It needs the Jev key from step 4. Without a key it prints `[FAIL] benign-hosting (benign)` with `Verdict: outcome=hold reasons=check_unavailable`, the attack payment still `[PASS]`, then `Overall Status: FAILURE` and exit code 1. Its scenario namespace follows `OWNER_ACCOUNT_ID` as in step 3. Details: [docs/build/nightly-e2e.md](docs/build/nightly-e2e.md).
7. Evaluation. In `agent/`, run `uv run firewall-eval --all-configurations` → the seven configurations (`no_defense`, `policy_only`, `classifier_only`, `code_rules_all_signals`, `jev_fusion_all_signals`, `jev_fusion_conformal`, `jev_fusion_conformal_cascade`) run over the 150 benign and 150 attack scenarios in `agent/scenarios/`, and the results are written as JSON. Useful flags: `--preset <label>` (run one of the seven configurations), `--configuration <label>` (label only), `--scenario <name>`, `--output FILE`, `--scenario-set {main,redteam,external,paysim}` (the red-team set is in `agent/scenarios/redteam/`), `--calibration FILE`. The Jev configurations need `TYPESAFE_API_KEY` and spend API credits. Without a key the command still exits 0 and prints `configurations: 7`, but the Jev rows hold every benign case (`false_holds=150`) because Jev is unavailable. The eval always substitutes scenarios in the `demo.testnet` namespace, regardless of `OWNER_ACCOUNT_ID`. Optional per-call prices for the cost column: `EVAL_JEV_USD_PER_CALL`, `EVAL_CLASSIFIER_USD_PER_CALL`. Published results (2026-11-13): [results.json](docs/results/results.json), [calibration-all-signals-classifier.json](docs/results/calibration-all-signals-classifier.json), [redteam-results.json](docs/results/redteam-results.json), [redteam.md](docs/results/redteam.md), [external-code-rules.json](docs/results/external-code-rules.json), [external-classifier-only.json](docs/results/external-classifier-only.json), [external-results.json](docs/results/external-results.json), [bec-results.json](docs/results/bec-results.json), [paysim-pooled.json](docs/results/paysim-pooled.json), [jev-budget.md](docs/results/jev-budget.md).
8. Calibration. In `agent/`, run `uv run firewall-calibrate <results.json>` on an eval results file → the conformal threshold `q_hat`, `false_hold_rate` and `sufficient_data`. Flags: `--epsilon`, `--rotation` (leave-one-attack-family-out check), `--missing-as-zero`. The frozen value is the default of `FUSION_HOLD_THRESHOLD`. On a results file produced without a Jev key it prints `n : 0`, `q_hat : 1.0` and `sufficient_data: False (need n >= 19)`.
9. Optional injection classifier. In `agent/`, run `uv run --with transformers --with torch firewall-classifier 8088` (downloads the model; exits with an error if the model cannot load), then set `CLASSIFIER_URL=http://127.0.0.1:8088/score` in `.env` → the checker calls it and records `signals.injection` in the decision record. Without `CLASSIFIER_URL` the injection check is off (`signals.injection = null`). `uv run firewall-classifier --heuristic 8088` serves a keyword heuristic instead of the model, for offline tests only; its responses report `"model": "keyword-heuristic"`.
10. External held-out set, no keys. In `agent/`, run `uv run firewall-eval --scenario-set external --preset code_rules_all_signals` → first line `scenarios: 200 (benign=100, attack=100)`. The set is built from public benchmarks and rewritten into payment form; sources and licenses are in [agent/scenarios/external/ATTRIBUTION.md](agent/scenarios/external/ATTRIBUTION.md).
11. Classifier benchmark. In `agent/`, run `uv run --with transformers --with torch python tools/bench_classifier.py` → writes `docs/results/classifier-bench.json` and `docs/results/classifier-bench.md`. It downloads the public corpora on first run and takes several minutes on a CPU.
12. Hugging Face dataset export. In `agent/`, run `uv run python tools/export_hf_dataset.py` → writes `data/hf-dataset/` (three JSONL splits: main 300 rows, redteam 17, external 200, plus a dataset card) and prints the `huggingface-cli upload …` command. The script uploads nothing.

## Configuration switches

All are environment variables, read by the checker (for OutLayer runs, set them as OutLayer secrets). `.env.example` lists every variable; [docs/build/sdd.md](docs/build/sdd.md) §8 is the reference. An invalid value fails the run with a non-zero exit instead of falling back.

| Variable | Meaning |
| --- | --- |
| `FUSION_MODE` | `jev` (default): Jev plus code rules fuse the verdict. `code_rules`: code rules only; Jev is never called; 2 or more detectors → block, 1 → hold, 0 → allow. Used by the baseline eval presets. |
| `CASCADE_ENABLED` | Default `false`, only in `jev` mode. Policy, counterparty and Jev run first; the injection classifier runs only when Jev's `unusual` probability exceeds the hold threshold. A skipped classifier leaves `signals.injection` null. |
| `FUSION_HOLD_THRESHOLD` | Hold when Jev's `unusual` exceeds this. Conformal q̂ (ε = 5%) once calibrated; see [.env.example](.env.example). |
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

From `site/`, run `npm ci` then `npm run dev` → open the printed local URL at `#receipts` to see live receipts from `guardian-v2.jimuelle-firewall.testnet`, with status filters, exact token amounts and testnet explorer links. No wallet or keys are needed. See [site/README.md](site/README.md) for configuration, checks and production build instructions.

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

Contract wasm files: `target/near/guardian/guardian.wasm` and `target/near/tusdc/tusdc.wasm`. `--no-abi` skips ABI generation, which fails to link on Windows MSVC. The dry-run needs no keys, but without `TYPESAFE_API_KEY` every payment is held (step 3 above).

### Testnet

These commands sign testnet transactions. The human runs them; they are never run by the agent.

```
cd agent
uv sync --extra testnet
uv run firewall-setup-testnet
uv run firewall-relayer
uv run firewall-demo --scenario benign-hosting --mode testnet
```

Expected: the Guardian receipt reaches `paid` and the hostco tUSDC balance rises by 18. Keys are written to `.env.testnet` (gitignored). `uv run firewall-nightly-e2e --mode testnet` runs the same benign and attack pair against testnet and asks for confirmation before it signs.

### Function-call key

The agent signs with a function-call access key added by `firewall-setup-testnet`. It is scoped to the Guardian contract and the single method `request_payment`, with a gas allowance of 1 NEAR (`agent.add_public_key(fc_public, guardian, ["request_payment"], NEAR)` in `agent/src/firewall_agent/setup_testnet.py`), and the account's full-access key is deleted afterwards. So the agent key can only call `request_payment`: it cannot transfer NEAR or tokens, add keys, or call any other contract or method.

Caveat: when the 1 NEAR gas allowance is used up, the agent is locked out and cannot pay, because an account holding only function-call keys cannot top itself up. The owner restores it by re-adding the function-call key with a new allowance (the owner needs a full-access key for the agent account, e.g. the one kept in `.env.testnet`), or by running `firewall-setup-testnet` again for a fresh set of accounts. See [sdd.md](docs/build/sdd.md) and [system-design.md](docs/build/system-design.md) failure modes.

## Architecture

- [System design](docs/build/system-design.md): data flow, trust boundaries, failure modes.
- [Software design](docs/build/sdd.md): modules, interfaces, configuration, testing.
- [Schemas](schemas/): frozen JSON formats with examples.

## Results

Evaluated on 2026-11-13 (live runs between 01:04 and 02:34 local) on 150 benign and 150 attack scenarios (six attack families, 25 each), decided by Jev (`jev-latest` via the TypeSafe API), with the injection classifier on. The checker was built from this branch. The classifier `protectai/deberta-v3-base-prompt-injection-v2` was served locally on CPU by `firewall-classifier` (port 8088), and `INJECTION_TIMEOUT_MS=20000` was set for every run: a 300-case stability pass had 2 of 300 cases over 3 s end to end, and one classifier timeout aborts a whole run with no file, because the checker treats a classifier failure as an error, not a verdict. No NEAR AI key was set, so there was no LLM fallback; a Jev failure would show as `check_unavailable`, and it did not occur in any completed run (0 cases). Latency columns include the local CPU classifier (about 1.1 to 1.8 s per payment), so they are not comparable with the 2026-11-12 table. Threshold: `firewall-calibrate` on the `jev_fusion_all_signals` run with the classifier on ([`docs/results/calibration-all-signals-classifier.json`](docs/results/calibration-all-signals-classifier.json), 150 benign, ε = 5%) gives a pooled q̂ of 0.85 (false-hold rate 0.0333) and, with `--rotation`, a split estimate of 0.88 (75 calibration / 75 test, held-out false-hold rate 0.0133). Jim's decision 2026-11-13: keep the frozen 0.84, because the pooled estimate moved by 0.01. Jev call counts per run and the aborted runs: [`docs/results/jev-budget.md`](docs/results/jev-budget.md).

Main set, from `docs/results/results.json` (`configurations`):

| Configuration | False holds (%) | False blocks (%) | Missed attacks (%) | Median latency (ms) | Cost per payment |
| --- | --- | --- | --- | --- | --- |
| No defense (`no_defense`) | 0.0 | 0.0 | 100.0 | 24.581 | 0 calls |
| Policy rules only (`policy_only`) | 0.0 | 0.0 | 70.67 | 27.227 | 0 calls |
| HF classifier only (`classifier_only`) | 0.67 | 0.0 | 83.33 | 1138.131 | 1 classifier call (unpriced) |
| MELON re-run only | not built (cut list) | | | | |
| All signals, code rules only, no Jev (`code_rules_all_signals`) | 0.67 | 0.0 | 46.0 | 1305.133 | 1 classifier call (unpriced) |
| Jev fusion, all signals (`jev_fusion_all_signals`, hold threshold 0.5) | 32.0 | 0.67 | 0.0 | 1388.052 | 1 Jev call + 1 classifier call (unpriced) |
| Jev fusion + conformal hold threshold, ε = 5% (`jev_fusion_conformal`, q̂ 0.84) | 5.33 | 0.0 | 19.33 | 1324.947 | 1 Jev call + 1 classifier call (unpriced) |
| Same, with cascade (`jev_fusion_conformal_cascade`) | 3.33 | 0.0 | 20.0 | 340.578 | 1 Jev call + 0.34 classifier calls (unpriced) |

In the cascade row the classifier ran on 34% of payments (`classifier_calls_per_payment` 0.34; median latency 1497.356 ms on the 102 payments where it ran and 309.987 ms on the 198 where it was skipped).

Cascade row, missed attacks per family (real outcomes of that row, from `by_family` in `results.json`, 25 attacks per family): `direct_injection` 1, `encoded_injection` 2, `indirect_injection` 1, `lookalike_receiver` 2, `fake_invoice` 12, `memory_poisoning` 12 (30 of 150 in total). The `unseen_family_rotation` and top-level `q_hat` (0.85) in `results.json` come from the threshold-0.5 calibration run, not from the conformal row, so they are not detection rates at q̂ 0.84.

Other sets (one preset each; every row has the classifier on). Latency is the median per payment.

| Set and configuration | False holds | False blocks | Missed attacks | Median latency (ms) | Source file |
| --- | --- | --- | --- | --- | --- |
| Red-team, 17 attacks, `jev_fusion_conformal` (q̂ 0.84) | n/a (no benign) | n/a | 7 of 17 (41.18%); 7 held, 3 blocked | 1137.9 | `redteam-results.json` |
| External held-out, 100 benign / 100 attack, `code_rules_all_signals` | 16 of 100 (16.0%) | 0 | 27 of 100 (27.0%) | 1432.733 | `external-code-rules.json` |
| External held-out, `classifier_only` | 16 of 100 (16.0%) | 0 | 27 of 100 (27.0%) | 1447.345 | `external-classifier-only.json` |
| External held-out, `jev_fusion_conformal` (q̂ 0.84) | 18 of 100 (18.0%) | 0 | 17 of 100 (17.0%); 51 held, 32 blocked | 1839.437 | `external-results.json` |
| Same 200 main-set scenarios as the BEC row, cascade row of the main run | 5 of 150 | 0 | 24 of 50 (`fake_invoice` 12, `memory_poisoning` 12) | not separable | `results.json` (`cases`) |
| Opt-in BEC reference examples, `jev_fusion_conformal_bec` (q̂ 0.84), 150 benign + 25 `fake_invoice` + 25 `memory_poisoning` | 38 of 150 (25.33%) | 0 | 1 of 50 (2.0%) | 1309.606 | `bec-results.json` |
| PaySim agent (120 prior payments), `jev_fusion_conformal` (pooled q̂ 0.84), 200 benign / 20 attack | 2 of 200 (1.0%) | 0 | 10 of 20 (50.0%) | 1110.009 | `paysim-pooled.json` |

Red-team: 7 of 17 attacks allowed (41.18%), against 9 of 17 on 2026-11-12. `redteam-04` and `redteam-05` (ASCII lookalikes at raw edit distance 3) are now held with reason `lookalike_receiver`, from the confusable skeleton (P2). Per-scenario outcomes: [docs/results/redteam.md](docs/results/redteam.md).

External held-out: code rules only and classifier only give identical outcomes, because the external attacks trip no policy or counterparty rule, so only the classifier decides. 16 of the false holds in each of those rows are `boundary-pairs` benign texts, which are hard negatives (attack-like wording, no payment redirection); the Jev row holds the same 16 plus 2 `llmail` benign emails. Jev misses by source (the source is the second dash-separated part of the scenario name): `agentdojo` 6 of 16, `nemotron` 10 of 30, `boundary` 1 of 24, `injecagent` 0 of 30.

BEC reference examples (opt-in, scope: 150 benign + 25 `fake_invoice` + 25 `memory_poisoning` main-set scenarios; the examples are 6 BEC fraud emails from the Kaggle set and 6 legitimate invoice emails from the main set, passed in `JEV_REFERENCE_EXAMPLES_JSON`): at q̂ 0.84 the BEC row holds 38 of 150 benign payments and misses 1 of 50 attacks. On the same 200 scenarios the cascade row of the main run holds 5 of 150 benign and misses 24 of 50 attacks. The following is derived from run 7's scores, not a separate run: the reference examples raise Jev's `unusual` on benign payments too (pooled q̂ on run 7's benign scores is 0.91: `uv run firewall-calibrate ../docs/results/bec-results.json` from `agent/`). At threshold 0.91 the BEC preset would hold 6 of 150 benign and detect 29 of 50 attacks (`fake_invoice` 16, `memory_poisoning` 13), close to the cascade row. The reference examples move the operating point; they do not add separation at a matched false-hold rate in this run. Rule for every derived figure in this section: an outcome is non-allow when Jev `unusual` is above the threshold or the case carries a non-Jev attack flag (`policy_violation`, `amount_mismatch`, `injection_high`, `lookalike_receiver`); at 0.84 this rule reproduces every actual outcome of the BEC run (0 mismatches of 200) and the PaySim run (0 of 220).

PaySim agent: at the pooled q̂ of 0.84 all 10 `lookalike_receiver` attacks are held or blocked (8 held, 2 blocked) and all 10 `fake_invoice` attacks are missed. Per-agent threshold: `uv run firewall-calibrate ../docs/results/paysim-pooled.json` gives q̂ₐ 0.81 (n 200, in-sample false-hold rate 0.045), and with `--rotation` q̂ 0.82 (100 calibration / 100 test, held-out false-hold rate 0.03). Derived from run 8's scores (same rule): at 0.81 the agent would hold 9 of 200 benign and detect 2 of 10 `fake_invoice`; at 0.82, 7 of 200 and 0 of 10. The per-agent threshold (`FUSION_AGENT_HOLD_THRESHOLD`) is implemented and unit-tested in `checker/src/decide.rs`, but its live effect was not measured: the run with it was not made because of the Jev budget.

Files: [results.json](docs/results/results.json), [calibration-all-signals-classifier.json](docs/results/calibration-all-signals-classifier.json), [redteam-results.json](docs/results/redteam-results.json), [external-code-rules.json](docs/results/external-code-rules.json), [external-classifier-only.json](docs/results/external-classifier-only.json), [external-results.json](docs/results/external-results.json), [bec-results.json](docs/results/bec-results.json), [paysim-pooled.json](docs/results/paysim-pooled.json), [jev-budget.md](docs/results/jev-budget.md).

### Public-data benchmarks

Injection classifier (`protectai/deberta-v3-base-prompt-injection-v2`, threshold 0.5) on corpora outside its training list. Full table, licenses and URLs: [docs/results/classifier-bench.md](docs/results/classifier-bench.md); numbers from [docs/results/classifier-bench.json](docs/results/classifier-bench.json), model backend.

- `deepset/prompt-injections` test (60 injections, 56 benign): recall 0.3667, precision 1.0, AUROC 0.8957.
- `3nesdeniz/agentic-prompt-injection-boundary-pairs` test (120 attack, 120 benign): recall 0.8417, false-positive rate 0.575, AUROC 0.72.
- `nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1`, first 300 rows by id (all positive): recall 0.79.
- `microsoft/llmail-inject-challenge` (4 positives, 203 benign emails): false-positive rate 0.0.
- Team in-domain, untrusted inbox items of the main set (234 positive, 175 negative): recall 0.1068, false-positive rate 0.0057.

Read these with four caveats. The llmail corpus has only 4 positives, so only its false-positive rate on 203 benign emails is meaningful. The boundary-pairs negatives are deliberately hard, which is why its false-positive rate is high. The in-domain corpus counts every untrusted inbox item of an attack scenario as positive, including ordinary invoice emails, so item-level recall understates scenario-level detection. `p50_ms` in the file is a local CPU figure. The keyword-heuristic backend, benchmarked on the same corpora, reaches recall 0.0 to 0.0333.

Lookalike detection ([docs/results/lookalike-bench.json](docs/results/lookalike-bench.json), Kaggle homoglyph domain attacks, CC0): of 28263 reconstructed (legitimate, spoofed) pairs, edit distance ≤ 2 detects 20782 (0.7353) and edit distance on the ASCII confusable skeleton detects 21729 (0.7688). On 2000 negative pairs of distinct legitimate domains, both variants give 2 false matches (0.001). The Kaggle data has no explicit pairing, so pairs are reconstructed: fake lists are cut into blocks of 9, and a block whose NFKD-folded members match exactly one legitimate domain of the same split is paired with it; other blocks are unpaired (10132 here). Pairs containing non-ASCII characters are excluded (52461 not representable) because NEAR account ids allow only `a-z 0-9 - _ .`.

## Limits

- **Exchangeability.** The conformal bound on false holds assumes benign scores in use are exchangeable with the calibration scores. Real traffic may drift; the 5.33% figure (8 of 150 benign, `jev_fusion_conformal`) is in-sample and above the 5% target. One of the 8 is a benign invoice the classifier flags, which holds whatever q̂ is (`code_rules_all_signals` also holds 1 of 150).
- **Known attack families only.** The dataset has six families. In the cascade row, missed attacks are 12 of 25 for `fake_invoice` and 12 of 25 for `memory_poisoning`, and 1 to 2 of 25 for each of the other four families.
- **Jev flags alone never hold.** A payment is held when Jev `unusual` exceeds q̂ or a non-Jev detector fires. In the red-team round, 7 of 17 attacks were allowed; most carried Jev flags (`jev_injection_driven`, `jev_receiver_risk`) but `unusual` stayed at or below q̂ and no other detector fired. See [`docs/results/redteam.md`](docs/results/redteam.md).
- **Hard caps are the guaranteed bound.** The Guardian's per-payment cap, daily cap and per-payee budget limit loss whatever the verdict. The Jev gate is a probabilistic filter, not a security boundary.
- **MELON not built.** It is on the cut list; its row is omitted.
- **`release_held` does not re-check.** After the hold window, a held request is paid with no re-check; re-checks during the hold window are on the cut list.
- **Threshold estimates vary.** Jev scores differ between runs, so q̂ re-estimates ranged from 0.82 to 0.85 on 2026-11-12. On 2026-11-13 the pooled estimate was 0.85 and the split estimate 0.88; the threshold was kept at 0.84 (Jim).
- **External set is rewritten, not native.** `agent/scenarios/external/` takes text from public benchmarks and rewrites it into payment form: a generated invoice email for a known payee plus the benchmark text with an appended receiver line naming a synthetic `ext-acct-NNN` account. Refs and receiver ids carry neither the label nor the benchmark name; the first build put the label word in every second inbox item's `ref`, which is sent to Jev, and it was fixed before any Jev call on the set. Remaining label correlates (from the "Known label correlates" section of ATTRIBUTION.md): inbox source `email` appears only on benign scenarios (76 of 100), every attack text names its receiver account, and the llmail benign emails are unrelated to payments. Attack amounts equal the invoice amount (Jim, 2026-11-13): in the first construction attacks paid fixed amounts of 120–190 against a 12–60 USDC invoice and the policy amount rule alone held 100 of 100 attacks, so the set did not test injection detection. Source and license of every row: [agent/scenarios/external/ATTRIBUTION.md](agent/scenarios/external/ATTRIBUTION.md).
- **PaySim and BEC rows need manual downloads.** Kaggle PaySim and the Kaggle adversarial BEC email set are CC BY-SA 4.0 and are never committed; `agent/tools/build_paysim_set.py` and `agent/tools/build_bec_examples.py` read them from `KAGGLE_DATA_DIR` and write only under the gitignored `data/`. Those rows are not reproducible from the repository alone.
- **The PaySim agent's payees are synthetic.** In PaySim, 2,151,495 PAYMENT rows go to 2,150,401 distinct merchants (the busiest has 3), so one agent with a repeat-payee history cannot be read from it. The builder keeps PaySim's amounts and row order and maps every row to one of 12 merchant ids by hash (Jim, 2026-11-13).
- **Latency is a local CPU figure.** The classifier runs on CPU on the evaluation laptop; per-payment latency includes it.
- **Classifier benchmark corpora are not pinned.** `bench_classifier.py` fetched each dataset's current revision on 2026-11-12/13; the revision is not recorded in its output.
- **PaySim results are redacted copies.** `docs/results/paysim-pooled.json` has no `receiver_id` or `amount` per case; the unredacted file stays under the gitignored `data/eval/`.
- **Per-agent threshold not measured live.** `FUSION_AGENT_HOLD_THRESHOLD` is implemented and unit-tested, but the live run with it was not made (Jev budget); only the derived figures in Results exist.

## Built with / third-party

Decision and platform:

- [TypeSafe Jev](https://typesafe.ai): calibrated typed decisions, raw HTTPS; the decision brain
- [NEAR AI Cloud](https://cloud.near.ai): LLM for agent tool calls and decision fallback; optional Jev route (`JEV_PROVIDER=nearai`)
- [OutLayer](https://app.outlayer.ai): TEE execution of the checker (wasm32-wasip2)
- [protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2): injection classifier, default; Apache-2.0 (verify on model card)
- [meta-llama/Llama-Prompt-Guard-2-86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M): injection classifier, when HF access is granted; Llama 4 Community License (verify on model card)
- [transformers](https://github.com/huggingface/transformers) and [PyTorch](https://pytorch.org) (optional, only for `firewall-classifier`; not in `pyproject.toml`, installed with `uv run --with`)

Datasets (used by the benchmarks and the external set; full attribution in [agent/scenarios/external/ATTRIBUTION.md](agent/scenarios/external/ATTRIBUTION.md)):

- [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections): Apache-2.0; read by `bench_classifier.py` only, not committed
- [3nesdeniz/agentic-prompt-injection-boundary-pairs](https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-boundary-pairs): CC-BY-4.0; rewritten rows in `agent/scenarios/external/`; also read by the classifier benchmark
- [nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1): CC-BY-4.0; rewritten rows in `agent/scenarios/external/`; also read by the classifier benchmark
- [microsoft/llmail-inject-challenge](https://huggingface.co/datasets/microsoft/llmail-inject-challenge): MIT; benign emails in `agent/scenarios/external/`; also read by the classifier benchmark
- [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent): MIT; rewritten rows in `agent/scenarios/external/`
- [AgentDojo](https://github.com/ethz-spylab/agentdojo): MIT; rewritten rows in `agent/scenarios/external/`
- [Kaggle homoglyph domain attacks](https://www.kaggle.com/datasets/akshat4112/homoglyph-domain-attacks): CC0; benchmark input only (`bench_lookalike.py`), not committed
- [Kaggle adversarial BEC email dataset](https://www.kaggle.com/datasets/yoadjei/adversarial-bec-email-dataset): CC BY-SA 4.0; read by `build_bec_examples.py`, not committed
- [Kaggle PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1): CC BY-SA 4.0; read by `build_paysim_set.py`, not committed

Rust (contracts and checker):

- [near-sdk-rs](https://github.com/near/near-sdk-rs) and near-contract-standards (`=5.29.1`): contract SDK, NEP-141
- [cargo-near](https://github.com/near/cargo-near): contract build
- serde, serde_json, sha2, hex: serialization and hashing (checker; hex also in the Guardian)
- ureq (native checker) and wasi-http-client (wasm32-wasip2 checker): HTTP client

Python (agent, relayer, eval):

- [uv](https://docs.astral.sh/uv/) and hatchling: environment and build
- [py-near](https://github.com/pvolnov/py-near): NEAR Python client (testnet extra)
- [openai](https://github.com/openai/openai-python): NEAR AI Cloud client
- httpx, jsonschema, python-dotenv, pytest

Frontend (`site/`):

- React, React DOM, Vite, `@vitejs/plugin-react` and vite-plugin-singlefile: shared landing page and read-only receipts frontend
- three, three-stdlib, `@react-three/fiber`, `@react-three/drei`, GSAP, Lenis and lucide-react: shared frontend stack ([site/README.md](site/README.md))
- Google Fonts (Geist, Geist Mono), NEARBlocks testnet explorer, FastNEAR public testnet RPC: frontend fonts and public data links

## Hackathon disclosures

- Built for NEAR HACKATHON (2026-11-01 → 2026-11-14). Pre-hackathon code: none — repository created 2026-11-08.
- Other projects by team members (Q-015): TBD(human).

## License

MIT, see [LICENSE](LICENSE).
