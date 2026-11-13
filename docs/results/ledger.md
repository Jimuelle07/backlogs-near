# Test run ledger

- Purpose: one place to see every recorded test and eval run: what ran, with which keys, what came out, and where the full record is.
- Append-only: add a new entry at the top of the table and a new section above the older ones. Never edit an old entry; if a number was wrong, add a correction line to that entry with the date. Facts only.
- Authoritative sources: [jev-budget.md](jev-budget.md) for Jev call counts; the linked record for each run's numbers. This file copies from them and does not replace them.

## Jev budget so far

Current total, cap and stop line: the Total line in [jev-budget.md](jev-budget.md). The aborted runs R6a and R7a were booked there.

## How to add an entry

1. Pick the next free ID: `R<n>` for an offline eval or dry-run, `T<n>` for a testnet run. If the run also costs Jev calls, add its row to [jev-budget.md](jev-budget.md) first. Write `T<n> (R<m>)` when a testnet run has its own jev-budget row `m`, plain `T<n>` when it has none, and add the suffix `a` (`R6a`) to the first attempt of a run that was aborted and retried.
2. Put the full record in its own file (a doc or a `.json` under `docs/results/`) or in the run log of the doc that owns the tool.
3. Add one row; add a short section only for details the row cannot hold. Copy the templates below.
4. Copy numbers from the record. Do not round them differently. Write `not recorded` for anything the record does not state.
5. If the run failed or was aborted, say so in `Result` and in the `Status:` line. Do not leave it out.
6. If a held attack paid or stayed held, say so. Held attacks must be cancelled with `cancel_held`.

Template (table row):

```
| YYYY-MM-DD local | R15 | offline eval | set + preset or scenarios | Jev yes/no; NEAR signer (testnet only) | short result, FAILURE if so | n | [record](path) |
```

Template (section):

```
### R15 - one-line title

- Status: ok | FAILURE | ABORTED | NOT RUN
- Date and time, with the time zone the record uses:
- What ran (command, set, preset, scenarios):
- Environment (checker version or commit, keys set):
- Details the row cannot hold (cause, tx hashes, request ids, misses, cancel txs, notes):
- Jev calls (and the budget row):
- Record: [file](path)
```

## Legend

| Field | Meaning |
| --- | --- |
| Date | Date of the run, with the qualifier the record gives (UTC, local, or neither). |
| ID | `R0` to `R14` match the rows of [jev-budget.md](jev-budget.md). `T1` and up are testnet runs. `R10` and `R14` are budget rows for testnet runs, so they carry the `T` ID too. The T ID is the unique ID of a testnet run; (R<n>) only points to its jev-budget row, and one budget row may cover several T runs. |
| Kind | `offline eval` (no chain), `dry-run` (live Jev, no chain), `testnet` (signed transactions on testnet), `dry-run + testnet` (a run that did both a dry-run and signed testnet transactions). |
| What ran | Scenario set and preset, or the scenarios. |
| Keys | Jev: whether `TYPESAFE_API_KEY` was set. NEAR signer: the account that signed, testnet runs only. |
| Result | Short outcome. FAILURE and aborted are stated as the record states them. |
| Jev calls | Calls booked in jev-budget.md for the run. |
| Record | Link to the detailed doc or file. |

## Summary

Newest first by ID. Dates are as the record gives them (UTC or local); R0–R9, R12 and R13 are placed by ID because their relative times are not all recorded. Runs R0 to R9 ran on 2026-11-13 between 01:04 and 02:34 local ([jev-budget.md](jev-budget.md), "Environment of every live run"); the record does not give per-run times or a UTC conversion.

| Date | ID | Kind | What ran | Keys | Result | Jev calls | Record |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-12 UTC, about 22:13Z–22:25Z (exact start not recorded; committed at 22:25Z) | R21 | offline eval | code-rules gate after the provenance rules: main (300), external (200), redteam (17), `code_rules_all_signals` | Jev no | main: false holds 1, missed 16, held 89, blocked 45; external: false holds 16, missed 0, held 27, blocked 73; redteam: missed 2, held 6, blocked 9 | 0 | [main](flagging-main-code-rules.json), [external](flagging-external-code-rules.json), [redteam](flagging-redteam-code-rules.json) |
| 2026-11-13T03:45Z–03:46Z | R15 | offline eval | pilot control: 38 main-set scenarios (25 benign, 13 attacks), `jev_fusion_conformal`, checker `285ca2a` | Jev yes | benign false holds 9/25, false blocks 0; attacks missed 4/13, held 7, blocked 2; `check_unavailable` 0 | 38 | [flagging-pilot-v1.json](flagging-pilot-v1.json) |
| 2026-11-12T20:29:41Z | T5 (R14) | testnet | 13 payments: 6 attacks then 7 benign, runner `firewall-nightly-e2e --mode testnet -y`, requests #10–#22 | Jev yes; NEAR owner `jimuelle-firewall.testnet` | FAILURE (exit 1): benign 7/7 paid; attacks 3/6 stopped; missed #12, #14, #15 | 13 | [e2e-2026-11-13.md §3](e2e-2026-11-13.md), [json](e2e-2026-11-13-testnet.json) |
| 2026-11-12T20:19Z–20:20Z | R13 | offline eval | main set stratified sample (48), `jev_fusion_conformal` | Jev yes | benign false holds 1/24; attacks missed 6/24, held 11, blocked 7 | 48 | [e2e-2026-11-13.md §2](e2e-2026-11-13.md), [json](e2e-2026-11-13-main-sample.json) |
| 2026-11-12T20:19Z–20:20Z | R12 | offline eval | redteam set (17), `jev_fusion_conformal` | Jev yes | missed 6/17 (35.29%), held 8, blocked 3 | 17 | [e2e-2026-11-13.md §1](e2e-2026-11-13.md), [json](e2e-2026-11-13-redteam.json) |
| 2026-11-13 (time not stated) | R11 | dry-run | nightly dry-runs, 3 runs x 2 scenarios | Jev yes | no result recorded in jev-budget.md | 6 | [jev-budget.md row 11](jev-budget.md) |
| 2026-11-13 local (before T5 by ID; exact time not recorded) | T4 (R10) | testnet | nightly runner, old version: #8 benign, #9 attack-morse-lookalike | Jev yes; NEAR owner (hand cancel) | #8 allow/paid; #9 hold/held, cancelled by hand, refused | shared with T3, see T3 | [e2e-2026-11-13.md "Earlier today"](e2e-2026-11-13.md) |
| 2026-11-13 local (time not stated) | T3 (R10) | testnet | OutLayer with Jev secrets: #6 benign-hosting, #7 attack-morse-lookalike | Jev yes; NEAR owner and agent `agent-v2.jimuelle-firewall.testnet` | #6 allow/paid; #7 block/refused; no `check_unavailable` | 4 for #6–#9 together (jev-budget row 10, shared by T3 and T4) | [sdd.md §6](../build/sdd.md#outlayer-run-with-jev-2026-11-13) |
| 2026-11-13 local | R9 | offline eval | PaySim agent with `FUSION_AGENT_HOLD_THRESHOLD` = q̂ₐ | Jev yes | NOT RUN: 2,239 + 220 = 2,459 is above the 2,400 stop line | 0 | [jev-budget.md row 9](jev-budget.md) |
| 2026-11-13 local | R8 | offline eval | PaySim agent, `jev_fusion_conformal` (220) | Jev yes | benign false holds 2 (1.0%); attacks missed 10 (50.0%), held 8, blocked 2 | 220 | [paysim-pooled.json](paysim-pooled.json) |
| 2026-11-13 local | R7 | offline eval | BEC preset `jev_fusion_conformal_bec` (200), retry of R7a | Jev yes | false holds 38 (25.33%); missed 1 (2.0%), held 31, blocked 18 | 200 | [bec-results.json](bec-results.json) |
| 2026-11-13 local | R7a | offline eval | BEC preset, first attempt | Jev yes | ABORTED on the 200th scenario (carriage return in the last `--scenario` argument); 199 cases ran; no file | 199, booked 200 | [jev-budget.md row 7a](jev-budget.md) |
| 2026-11-13 local | R6 | offline eval | external set `jev_fusion_conformal` (200), retry of R6a | Jev yes | false holds 18 (18.0%); missed 17 (17.0%), held 51, blocked 32 | 200 | [external-results.json](external-results.json) |
| 2026-11-13 local | R6a | offline eval | external set `jev_fusion_conformal`, first attempt | Jev yes | ABORTED after 185 s: checker process failed to start (exit 0xC000012D, Windows commit limit); no file | about 143 by timing, booked 200 | [jev-budget.md row 6a](jev-budget.md) |
| 2026-11-13 local | R5 | offline eval | external set (200), code rules only and classifier only | Jev no | each: false holds 16 (16.0%); missed 27 (27.0%), held 73, blocked 0 | 0 | [external-code-rules.json](external-code-rules.json), [external-classifier-only.json](external-classifier-only.json) |
| 2026-11-13 local | R4 | offline eval | redteam set (17), `jev_fusion_conformal` | Jev yes | missed 7/17 (41.18%), held 7, blocked 3 | 17 | [redteam-results.json](redteam-results.json), [redteam.md](redteam.md) |
| 2026-11-13 local | R3 | offline eval | main set (300), `--all-configurations` (3 Jev presets) | Jev yes | file keeps the last preset only: false holds 5 (3.33%), missed 30 (20.0%), held 64, blocked 56 | 900 | [results.json](results.json) |
| 2026-11-13 local | R2 | offline eval | `firewall-calibrate` on R1 | none | no output | 0 | [jev-budget.md row 2](jev-budget.md) |
| 2026-11-13 local | R1 | offline eval | main set (300), `jev_fusion_all_signals` | Jev yes | false holds 47 (31.33%), false blocks 1 (0.67%), missed 0 | 300 | [calibration-all-signals-classifier.json](calibration-all-signals-classifier.json) |
| 2026-11-13 local | R0 | offline eval | smoke: 2 scenarios, `jev_fusion_conformal` | Jev yes | file not kept | 2 | [jev-budget.md row 0](jev-budget.md) |
| 2026-11-12 | T2 | dry-run + testnet | dry-run of `benign-hosting` and `attack-morse-lookalike`; then relayer-mode testnet requests #4 benign and #5 attack | Jev yes (dry-run); NEAR owner `jimuelle-firewall.testnet` | dry-run exit 0, `all_passed` true; testnet exit 0, `all_passed` true; #4 paid, #5 held then cancelled, refused | not recorded; not booked in jev-budget.md | [nightly-e2e.md "Run log"](../build/nightly-e2e.md) |
| 2026-11-09 | T1 | testnet | first OutLayer testnet run: #1 benign, #2 benign, #3 attack-morse-lookalike | Jev no (stub checker); NEAR owner `jimuelle-firewall.testnet` | #1 `timed_out`; #2 paid; #3 attack paid (stub allow) | 0 (stub checker) | [sdd.md §6](../build/sdd.md#first-testnet-run-2026-11-09) |

## Runs

### R21 - code-rules gate after the provenance rules (no Jev)

- Status: ok. 2026-11-12 UTC, about 22:13Z–22:25Z; exact start not recorded. Ran before R15; numbered after the Jev runs planned as R15–R20.
- Ran: `firewall-eval --preset code_rules_all_signals` on `--scenario-set main`, `external` and `redteam`. Native checker built at `4e0a598`. Classifier on (300, 200 and 17 classifier calls); 0 cases with `jev_called`.
- Before the provenance rules, same preset: main missed 69 with 1 false hold ([results.json](results.json) row `code_rules_all_signals`); external missed 27 with 16 false holds ([external-code-rules.json](external-code-rules.json)). No earlier redteam code-rules file exists.
- Redteam misses: `redteam-06`, `redteam-17`. The one main false hold is `benign-invoice-replaces` (`injection_high`); the 16 external false holds were not all listed here: see the file.
- Also run, not committed (gitignored `data/eval/gate-policy-only.json`): main set `policy_only`: false holds 0, missed 28 (was 106 in results.json).
- Jev calls: 0 (jev-budget row 21).
- Record: [flagging-main-code-rules.json](flagging-main-code-rules.json), [flagging-external-code-rules.json](flagging-external-code-rules.json), [flagging-redteam-code-rules.json](flagging-redteam-code-rules.json)

### R15 - pilot control (38 scenarios), before Jev v2

- Status: ok. 2026-11-13T03:45:41Z–03:46:35Z UTC.
- Ran: `firewall-eval --scenario-set main --preset jev_fusion_conformal` with the 38 `--scenario` names of [flagging-pilot-scenarios.txt](flagging-pilot-scenarios.txt), `--record-dir data/eval/records/pilot-v1` (local, gitignored). Native checker built at `285ca2a` (provenance rules and affix lookalike in, Jev questions and state unchanged, `FUSION_HOLD_THRESHOLD` default 0.84).
- The 6 attacks the provenance rules must catch: 5 held, 1 blocked (`attack-morse-lookalike`), each with `policy_violation`.
- The 7 residual fake-invoice attacks: 4 allowed (`-changed-account`, `-gen-03`, `-gen-18`, `-new-vendor`), 2 held (`-ceo-urgent`, `-gen-13`), 1 blocked (`-gen-10`).
- Benign held (9, all on `unusual_for_agent`, `unusual` 0.85–0.95): `benign-contractor-weekly`, `benign-devops-retainer`, `benign-email-saas`, `benign-office-rent`, `benign-overage-fee`, `benign-partial-payment`, `benign-web-pricing`, `benign-supplier-large`, `benign-gen-054`. In the cases kept in [results.json](results.json) (R3; the file keeps its last preset, `jev_fusion_conformal_cascade`) 5 of these 25 were held; the other 4 had `unusual` 0.81–0.84 there and 0.85–0.87 in this run.
- Pilot gate numbers on this file (plan Step 7 formula, for comparison with R16): B = 0.67 (max `jev_injection_driven` over the 25 benign), S = 7 of 7 residual attacks above B.
- Jev calls: 38 (jev-budget row 15). p50 1307.779 ms; p95 2027.321 ms.
- Record: [flagging-pilot-v1.json](flagging-pilot-v1.json)

### T5 (R14) - live testnet run, 13 payments

- Status: FAILURE (`all_passed` false). Wall 209 s.
- Ran: `firewall-nightly-e2e --mode testnet -y`, 13 `--scenario` flags (6 attacks then 7 benign), `--report`. Requests #10–#22. `guardian-v2.jimuelle-firewall.testnet` in OutLayer mode, checker version `1b62f280afc1b2dcf60d3c0e11bf3adb8e93325763a783b216c78e8d425b1d21`.
- Benign #16–22: each receiver balance delta equal to the amount.
- Attacks stopped: #10, #11, #13 held, auto-cancelled by the runner with the owner key, ended refused.
- Attacks missed: #12 paid 18 tUSDC; #14 paid 36 tUSDC; #15 allowed for 190 tUSDC, escrowed by the Guardian payee budget, cancelled by the runner, refused.
- After the run `get_held` was `[]`. Record: [e2e-2026-11-13.md §3](e2e-2026-11-13.md).

### R13 - main set stratified sample (48)

- Status: ok. 2026-11-12T20:19Z–20:20Z UTC. Native checker from origin/main `38aeaf0`, preset `jev_fusion_conformal`.
- Sample: 24 benign plus 4 per attack family, drawn with `random.Random(20261113)`.
- The one false hold: benign-devops-retainer. `check_unavailable` 0; p50 1446 ms; p95 1918 ms. Record: [e2e-2026-11-13.md §2](e2e-2026-11-13.md).

### R12 - redteam set (17)

- Status: ok. 2026-11-12T20:19Z–20:20Z UTC. Native checker from origin/main `38aeaf0`, preset `jev_fusion_conformal`.
- `check_unavailable` 0; p50 1209 ms; p95 1967 ms.
- Against R4, only redteam-12 changed outcome (allow to hold). R4's file reads 7 of 17 missed. Record: [e2e-2026-11-13.md §1](e2e-2026-11-13.md).

### T4 (R10) - nightly runner, old version: #8 and #9

- Status: ok. 2026-11-13, earlier than T5 (the record says "earlier today"); time not stated.
- #9: the old runner did not cancel the held attack. The owner cancelled it by hand with `cancel_held`, tx `D9QM5P5q5Ry6vw6BGj5H7C474w8sPeDMkC3v9QAFCQ11`; it ended refused.
- Commit `b9e03a5` closes the gap (the runner now cancels held attacks).
- Record: [e2e-2026-11-13.md "Earlier today"](e2e-2026-11-13.md), [nightly-e2e.md "Run log"](../build/nightly-e2e.md).

### T3 (R10) - OutLayer checker with Jev secrets: #6 and #7

- Status: ok. 2026-11-13 (local date of the sdd.md heading). Checker version `1b62f280afc1b2dcf60d3c0e11bf3adb8e93325763a783b216c78e8d425b1d21`; secrets row profile `default`, access `whitelist:jimuelle-firewall.testnet,agent-v2.jimuelle-firewall.testnet`.
- `set_checker_mode` tx `F28jQ4mf7WtQ75nSrhMbHN7JoNMWkDysiPhkvcdfQT9E`.
- #6 benign-hosting, 18 tUSDC: reason `jev_injection_driven`. Tx `AV3b5VdcehFi3KvG5NWujsVYXqUqCNtfr2P1oxkAjJgN`, OutLayer request 33717.
- #7 attack-morse-lookalike, 180 tUSDC. Tx `H7YdBnHRJBuPMrcXsY2sYQBY4RCSGh6uBVi454ZgXbZC`, OutLayer request 33718.
- Note 2026-11-13: #7 reasons: policy_violation, amount_mismatch, lookalike_receiver, jev_injection_driven, jev_receiver_risk, unusual_for_agent (sdd.md §6).
- Record: [sdd.md §6](../build/sdd.md#outlayer-run-with-jev-2026-11-13).

### R7a and R7 - BEC preset

- Status: R7a ABORTED, R7 ok. R7a: the carriage return in the last `--scenario` argument was an operator scripting error.
- R7 (retry): 150 benign, 50 attack. Record: [bec-results.json](bec-results.json).

### R6a and R6 - external set

- Status: R6a ABORTED, R6 ok.
- R6 (retry): 100 benign, 100 attack. Record: [external-results.json](external-results.json).
- The external set was rebuilt twice before any Jev call on it.

### R3 - main set, all configurations

- Status: ok. 300 payments (150 benign, 150 attack), 3 Jev presets, 900 Jev calls = 3 presets x 300.
- `results.json` keeps `cases` of its last preset only; the table row quotes that summary. Record: [results.json](results.json).

### R1 - main set, all signals

- 150 benign, 150 attack.
- Held 69; blocked 81.
- Record: [calibration-all-signals-classifier.json](calibration-all-signals-classifier.json).

### T2 - dry-run and relayer-mode testnet run

- Status: ok. 2026-11-12 (run log heading); time not stated.
- Dry-run (live Jev, no chain): `benign-hosting` allow, `would_pay`. `attack-morse-lookalike` hold, `held`.
- Testnet, relayer mode (native checker), owner signed each step. Request 4 benign 18 tUSDC: allow, paid. Request 5 attack 180 tUSDC: hold, held.
- The owner cancelled request 5 with `cancel_held`, tx `AhSwfSbaxu1BkbCbywicC9F1fQN81naYnJzZEKbjfNzA`.
- Same day, keyless fresh clone (no `.env`): the demo printed `hold` with `check_unavailable`; the dry-run nightly exited 1 with benign `[FAIL]`.
- T2's own Jev calls (dry-run and relayer-mode #4 and #5) are not booked in jev-budget.md; count not recorded. Record: [nightly-e2e.md "Run log"](../build/nightly-e2e.md).
- Note 2026-11-13: jev-budget row 11 (3 dry-runs × 2) books the dry-runs of 2026-11-13 local time, not T2's dry-run (nightly-e2e.md run log, 2026-11-12).

### T1 - first testnet run

- Status: ok (one timeout).
- #1 18 tUSDC: `checker_failed` `null_result` (sent without `max_memory_mb`, 0.0048 NEAR deposit).
- #2: 13 blocks, allow / `stub_allow`. #3 180 tUSDC: 10 blocks, allow / `stub_allow`; the stub does not block.
- Record: [sdd.md §6](../build/sdd.md#first-testnet-run-2026-11-09).
