# Jev call budget ledger (Sprint 4b, P6)

Budget: at most 3,100 Jev calls (raised from 2,500 by Jim, 2026-11-13). Stop line for starting a new run: 3,000. Calls are counted as cases with `jev_called` in each output file; the two aborted runs have no file and are booked at the counts below.

## Environment of every live run

Runs of 2026-11-13, 01:04 to 02:34 local. The checker was built from this branch. The injection classifier `protectai/deberta-v3-base-prompt-injection-v2` was served locally on CPU (`firewall-classifier`, port 8088). `INJECTION_TIMEOUT_MS=20000` was set for every run: a 300-case stability pass had 2 of 300 cases over 3 s end to end, and one classifier timeout aborts a whole run with no file (the checker treats a classifier failure as an error, not a verdict). `TYPESAFE_API_KEY` was set. No NEAR AI key was set, so there was no LLM fallback; a Jev failure would show as `check_unavailable`. No profile, reference-example or threshold variables were exported except where a preset sets them. Latency columns in the results include the local CPU classifier (about 1.1 to 1.8 s per payment).

## Ledger

| # | Run | Output | Jev calls | Cumulative |
| --- | --- | --- | --- | --- |
| 0 | smoke: 2 scenarios, `jev_fusion_conformal` | not kept | 2 | 2 |
| 1 | main set, `jev_fusion_all_signals` | `calibration-all-signals-classifier.json` | 300 | 302 |
| 2 | `firewall-calibrate` on run 1 | none | 0 | 302 |
| 3 | main set, `--all-configurations` (3 Jev presets) | `results.json` | 900 | 1,202 |
| 4 | red-team set, `jev_fusion_conformal` | `redteam-results.json` | 17 | 1,219 |
| 5 | external set, code rules and classifier only | `external-code-rules.json`, `external-classifier-only.json` | 0 | 1,219 |
| 6a | external set, `jev_fusion_conformal`: aborted after 185 s because the checker process failed to start (exit 0xC000012D, Windows commit limit reached); no file | none | about 143 by timing, booked 200 | 1,419 |
| 6 | external set, `jev_fusion_conformal` (retry) | `external-results.json` | 200 | 1,619 |
| 7a | BEC preset `jev_fusion_conformal_bec`: aborted on the 200th scenario because an operator scripting error added a carriage return to the last `--scenario` argument; 199 cases had run; no file | none | 199, booked 200 | 1,819 |
| 7 | BEC preset (retry) | `bec-results.json` | 200 | 2,019 |
| 8 | PaySim agent, `jev_fusion_conformal` | `paysim-pooled.json` | 220 | 2,239 |
| 9 | PaySim agent with `FUSION_AGENT_HOLD_THRESHOLD` = q̂ₐ | not run: 2,239 + 220 = 2,459 is above the 2,400 stop line, and the plan's cut rule drops run 9 first | 0 | 2,239 |
| 10 | OutLayer testnet payments #6–#9 (2026-11-13; the checker in the TEE calls Jev with the same key, so these count) | none | 4 | 2,243 |
| 11 | nightly dry-runs, 3 runs × 2 scenarios | none | 6 | 2,249 |
| 12 | redteam eval, `jev_fusion_conformal` | `e2e-2026-11-13-redteam.json` | 17 | 2,266 |
| 13 | main-set stratified sample (48), `jev_fusion_conformal` | `e2e-2026-11-13-main-sample.json` | 48 | 2,314 |
| 14 | live testnet run #10–#22 | `e2e-2026-11-13-testnet.json` | 13 | 2,327 |
| 15 | pilot control: 38 main-set scenarios ([flagging-pilot-scenarios.txt](flagging-pilot-scenarios.txt)), `jev_fusion_conformal`, checker `285ca2a` (Jev questions and state as before) | `flagging-pilot-v1.json` | 38 | 2,365 |
| 16 | pilot on Jev v2: same 38 scenarios, `jev_fusion_conformal`, checker `6622e50` (agent_profile in the Jev state, example/counterexample questions; injection hold off) | `flagging-pilot-v2.json` | 38 | 2,403 |
| 17 | calibration run on Jev v2: main set (300), `jev_fusion_conformal`, checker `6622e50` (thresholds still 0.84 and 1.0) | `flagging-main-calibration.json` | 300 | 2,703 |
| 18 | external held-out set (200), `jev_fusion_conformal`, checker `5d57145` (Jev v2, defaults 0.81 and 0.81) | `flagging-external.json` | 200 | 2,903 |
| 19 | redteam set (17), `jev_fusion_conformal`, checker `5d57145` (Jev v2, defaults 0.81 and 0.81) | `flagging-redteam.json` | 17 | 2,920 |
| 20 | nightly dry-run, 2 scenarios (`benign-hosting`, `attack-morse-lookalike`), checker `5d57145` | none (console output; summary in ledger.md R20) | 2 | 2,922 |
| 21 | code-rules gate after the provenance rules: main, external and redteam sets with `code_rules_all_signals` (no Jev), checker `4e0a598` | `flagging-main-code-rules.json`, `flagging-external-code-rules.json`, `flagging-redteam-code-rules.json` | 0 | 2,922 |
| 22 | main set re-fused at the calibrated defaults: `--all-configurations --refuse-from flagging-main-calibration.json` on the R17 records, checker `5d57145`; the two Jev rows are re-fused with `checker --refuse` (no Jev call; the `jev_called` flags in the file are copied from R17), the four code-rules rows are run, the cascade row is skipped | `flagging-main.json` | 0 | 2,922 |

Total booked: 2,922 calls, of which 400 are booked for the two aborted runs 6a and 7a. This is below the 3,000 stop line (cap 3,100). Runs 10–14 total 88 calls on 2026-11-13 (prior cumulative 2,239). Runs 15 onward (flagging work, branch `flagging-provenance-jev-v2`) total 595 calls.

Runs 10–14 (offline evals 2026-11-12T20:19Z–20:20Z UTC): native checker from origin/main `38aeaf0`, classifier `protectai/deberta-v3-base-prompt-injection-v2` on local CPU (`firewall-classifier`, port 8088, `INJECTION_TIMEOUT_MS=20000`), `TYPESAFE_API_KEY` set, no NEAR AI key, preset `jev_fusion_conformal`. Runs 10 and 14 ran on testnet with `guardian-v2` in OutLayer mode. Results: [e2e-2026-11-13.md](e2e-2026-11-13.md).

Runs 15 onward (flagging work, 2026-11-13 UTC): native checker built from branch `flagging-provenance-jev-v2` at the commit named in each row, classifier `protectai/deberta-v3-base-prompt-injection-v2` on local CPU (`uv run --with transformers --with torch firewall-classifier 8088`, `CLASSIFIER_URL=http://127.0.0.1:8088/score`, `INJECTION_TIMEOUT_MS=20000`), `TYPESAFE_API_KEY` set, `CHECKER_LLM_MODEL` empty (no LLM fallback; a Jev failure shows as `check_unavailable`). DecisionRecords of these runs are kept locally under the gitignored `data/eval/records/` and are not committed.

## Notes

- The external set was rebuilt twice before any Jev call on it (first the attack amounts, then label words in `ref` fields), so no Jev call was spent on a set with those leaks.
- The stop rule (`check_unavailable` above 5% of cases) was never triggered: `check_unavailable` is 0 in every completed run.
- Counts in the table were checked against the committed files: `calibration-all-signals-classifier.json` 300, `redteam-results.json` 17, `external-results.json` 200, `bec-results.json` 200, `paysim-pooled.json` 220 cases with `jev_called`. `results.json` keeps `cases` of its last preset only (300); the 900 for run 3 is 3 Jev presets × 300 payments.
