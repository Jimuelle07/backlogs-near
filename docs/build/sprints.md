# Sprints

Remaining work for a team of 6 (4 backend, 2 frontend), cut into **five parallel lanes** so nobody waits on anyone else inside a sprint. A lane is one person's worth of work per sprint; the backend lead also reviews and pairs. Assign tasks by filling in **Owner**. Size: S ≈ half a day, M ≈ a day.

Done before Sprint 1: Guardian caps and hold escrow, `DecisionClient` (Jev primary, NEAR AI LLM fallback), 60 scenarios, dry-run mirroring the contract, testnet end-to-end in relayer mode (paid, refused by cap, timed out), OutLayer checker mode in code (not yet run live). Details: [sdd.md](sdd.md).

Signing steps (deploys, testnet transactions, OutLayer registration) are run by a human ([AGENTS.md §4](../../AGENTS.md#4-human-only-actions)).

## Team

| Team | Lead | Members |
| --- | --- | --- |
| Backend (lanes A, B, C) | Jim | Rc, paticolcol, Jesus |
| Frontend (lanes D, E) | Helena | Ace |

Leads pair with their members on the hardest task of the sprint and review every task in their team before it is marked done.

**Backend testing is always Jim's.** Backend members write the code and the tests that come with it; Jim runs the checks (`cargo test --workspace`, `cd agent && uv run pytest`, the builds and any testnet run) and confirms each "done when" line before a backend task counts as done. A backend task is not done until Jim has signed it off.

## How the lanes stay parallel

Lanes never block each other inside a sprint because every hand-off goes through a frozen format plus a fixture:

| Hand-off | Frozen format | Lets this start early |
| --- | --- | --- |
| Checks → fusion | `signals` in [decision-record.schema.json](../../schemas/decision-record.schema.json) (already frozen: `policy`, `injection`, `melon`, `counterparty`, `jev`) | C3 builds on fixture signals while B1/C2/B3 are written |
| Eval → website | `results.json` (defined in C1, Sprint 1) | E3 renders sample results while C4 runs |
| Contract → website | Guardian views (`list_receipts`, `get_held`, `get_daily_spent`, `get_config`) and [receipt.schema.json](../../schemas/receipt.schema.json) | E1/E2 build on the live testnet Guardian today |
| Checker → eval | the checker binary (stdin CheckerInput → stdout Verdict) | A3 runs on the stub checker; numbers fill in as checks land |

Rule for every lane: code against the frozen format and a fixture; swap in the real producer when it lands. A format change needs the owners of both sides and Jim's approval, and edits the schema and its example before any code ([AGENTS.md §0](../../AGENTS.md#0-authority-docs-first)).

## Lane overview

| Lane | Track | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
| --- | --- | --- | --- | --- | --- |
| A — chain & demo | Backend | A1 OutLayer live · A2 record sink · A3 eval harness skeleton | A4 contract: per-payee budgets + receiver registration · A5 unprotected-agent mode | A6 dataset to 150/150 · A7 red-team round | A8 record the demo |
| B — checks | Backend | B1 policy rules · B2 nightly e2e script | B3 counterparty signals · B4 checker hardening | B5 cascade · B6 README draft | B7 fresh-clone test + fixes |
| C — decision & eval | Backend | C1 results.json format + signal fixtures · C2 injection classifier | C3 Jev fusion in `decide()` | C4 full eval run · C5 conformal calibration + unseen-family rotation | C6 README results + limits, freeze thresholds |
| D — landing page | Frontend | D1 landing page skeleton | D2 "How it works" section · D3 demo storyboard | D4 results section (real data) · D5 copy pass with backend | D6 final: video, GIF, meta, accessibility |
| E — live views | Frontend | E1 live receipts panel | E2 receipt detail view · E3 results section on sample JSON | E4 demo assets: GIF, numbers slide | E5 hosting and uptime check · E6 X post visuals |

Sync points (the only moments lanes must meet): **end of Sprint 2** — testnet gate G2; **end of Sprint 3** — numbers frozen for the demo and site.

## Progress (updated 2026-11-12)

Status: **Done** (merged and signed off by Jim), **In progress** (work merged or started, sign-off pending), **Not started** (no branch or PR on GitHub as of 2026-11-10); a backend task counts as done only after Jim signs it off.

| ID | Task | Owner | Status | Evidence |
| --- | --- | --- | --- | --- |
| A1 | OutLayer live | Jim | **Done** | merged to main (`5d47f5b`, `928b0aa`), signed off `4100de8`; [A1 log](#a1-log-done-2026-11-10) |
| A1-FU | A1 follow-ups: full setup saves `GUARDIAN_PRIVATE_KEY`; keys saved before account creation | Jim | **Done** | PR #2 |
| A2 | Record sink | Jesus | **Done** | Merged in PR #6: `checker/src/sink.rs`; signed off by Jim 2026-11-11 |
| A3 | Eval harness skeleton | Jesus | **Done** | Merged in PR #6: `agent/src/firewall_agent/eval.py` (`firewall-eval`); signed off by Jim 2026-11-11 |
| A4 | Per-payee budgets + receiver registration | Jim | **Done** (PR #21; signed off by Jim 2026-11-12) | `6a4c380`; guardian-v2 redeployed with the A4 wasm 2026-11-12 (tx `6ia53LjrQhbiqQYcy9gdqAAqGdYBkLpXzes8gb3QdEwA`) |
| A6 | Dataset to 150/150 | Jesus | **Done** (PR #21; signed off by Jim 2026-11-12) | `930fe6a`: 150 benign + 150 attack (6 families × 25), `agent/tools/generate_scenarios.py` |
| A7 | Red-team round | Jesus | **Done** (PR #21; signed off by Jim 2026-11-12) | `930fe6a`: 17 scenarios in `agent/scenarios/redteam/`; 9 of 17 missed (52.94%); `docs/results/redteam.md` |
| B1 | Policy rules check | Rc (pairs with Jim) | **Done** | Merged in PR #3; Rc review completed in PR #9 ([b1-policy-review.md](b1-policy-review.md)); signed off by Jim 2026-11-11 |
| B2 | Nightly e2e script | Rc | **Done** | Merged in PR #9: `agent/src/firewall_agent/nightly_e2e.py` (`firewall-nightly-e2e`), `scripts/nightly-e2e.*`; unit tests in `agent/tests/test_nightly_e2e.py`; expected output in [nightly-e2e.md](nightly-e2e.md); signed off by Jim 2026-11-11 |
| B3 | Counterparty signals | Rc | **Done** (PR #21; signed off by Jim 2026-11-12) | merge `d8f10f3`; `checker/src/counterparty.rs` fixes `fa659e3`, `a40f7d6` (qualified ids never match bare profile names; `COUNTERPARTY_NAMESPACE`) |
| B5 | Cascade | Rc | **Done** (PR #21; signed off by Jim 2026-11-12) | `fa659e3`: `CASCADE_ENABLED`, `FUSION_MODE` in `checker/src/{fusion,decide}.rs`; "trusted repeat payments skip expensive checks" not implemented; classifier not run in the evaluation |
| B6 | README draft | Rc | **Done** (PR #21; signed off by Jim 2026-11-12) | `0962bfb`: `README.md`, `docs/build/nightly-e2e.md`; fresh-clone fixes `5626a8c` |
| B7 | Fresh-clone test | — | **Done** (PR #21; signed off by Jim 2026-11-12) | fresh clone without `.env`; README fixes `5626a8c`; keyless demo `hold` + `check_unavailable`, keyless nightly dry-run exit 1 |
| C1 | results.json format + fixtures | paticolcol | **Done** | Merged in PR #7: `schemas/results.schema.json`, `schemas/examples/results.json`, 5 fixtures in `schemas/fixtures/`; signed off by Jim 2026-11-11 |
| C2 | Injection classifier | paticolcol | **Done** | Merged in PR #7: `checker/src/injection.rs` (wired in `decide.rs`), `agent/src/firewall_agent/classifier.py` (`firewall-classifier`); signed off by Jim 2026-11-11 |
| C3 | Jev fusion in `decide()` | paticolcol | **In progress** | Merged in PR #18 (`136224d`): `checker/src/fusion.rs` + `decide.rs` wiring; awaiting Jim's sign-off |
| C4 | Full eval run | paticolcol | **Done** (PR #21; signed off by Jim 2026-11-12) | `73a0e0d` (seven presets, call counts, cost); `docs/results/results.json` (`78e3fcb`, total 300); `classifier_only` not run (classifier model download failed); MELON not built |
| C5 | Conformal hold threshold + unseen-family rotation | paticolcol | **Done** (PR #21; signed off by Jim 2026-11-12) | q̂ frozen at 0.84 (`61e9f52`), 150 benign, ε = 5%; realised false-hold 4.67% (7/150); `calibration.py` strict `>` fix `28a33e9` |
| C6 | README results and limits; freeze thresholds | — | **Done** (PR #21; signed off by Jim 2026-11-12) | `README.md` Results and Limits from `docs/results/results.json` (`78e3fcb`); `FUSION_HOLD_THRESHOLD` 0.84 |
| D1 | Landing page skeleton | Helena | **Not started** | No branch or PR yet |
| E1 | Live receipts panel | Ace | **In progress** | PR #11 review changes: panel integrated into `site/` using the shared React 18.3.1 / Vite 5.4.21 stack and brand; standalone app removed. 8/8 unit tests, production build and 7 Edge browser checks pass (390px, no horizontal scroll); Helena's re-review pending; see [site/README.md](../../site/README.md) |
| E2 | Receipt detail view | Ace | **In progress** | 2026-11-13: local implementation on `feat/e2-receipt-detail` from `origin/main` after PR #11 merged. Inline details, keyboard opening, Escape/close with focus restoration, hash copy controls, account links and integer hold countdown; `get_held` pages pinned to the receipt snapshot. `cd site && npm test`: 21/21 pass; `npm run build`: pass. Browser interaction checks and Helena's review pending. |

Sign-off checks 2026-11-11 (A2, A3, B1, B2, C1, C2): `cargo test --workspace --no-fail-fast` passed (checker 49, guardian 91, tusdc 3; 2 ignored) after fixing the A2 test server in `checker/src/sink.rs` to read the full request body; `cd agent && uv run pytest` passed (158).

Sprints 2–3: planned (owners and due dates below), not started. Sprints 4–5: not started.

## Sprint 1 — due Tue 10 Nov, 23:59 PHT (15:59Z)

| Who | Role this sprint |
| --- | --- |
| Jim (backend lead) | Tests and signs off every backend task; A1 OutLayer live (signs the testnet steps); pairs with Rc on B1 |
| Rc | B1 policy rules, B2 nightly e2e script |
| paticolcol | C1 results format and fixtures first (unblocks A3 and frontend), then C2 classifier |
| Jesus | A2 record sink, A3 eval harness skeleton |
| Helena (frontend lead) | D1 landing page skeleton; picks the stack and host for both frontend lanes; reviews E1 |
| Ace | E1 live receipts panel (uses Helena's stack choice) |

| ID | Lane | Track | Size | Task | Done when | Starts from | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | A | Backend | M | OutLayer live: build the checker wasm, upload and deploy, redeploy the Guardian, `set_checker_mode`, run one benign and one attack payment ([sdd.md §6](sdd.md) runbook; human signs). **Done, signed off by Jim 2026-11-10: benign receipt `paid` through OutLayer on `guardian-v2.jimuelle-firewall.testnet`, attack run (`paid`, `stub_allow`), open questions answered in [sdd.md §6 First testnet run](sdd.md#first-testnet-run-2026-11-09)** | Receipt `paid` through OutLayer; sdd §6 open questions answered (Text result shape, deposit, timeout delivery) | — | Jim | Done |
| A2 | A | Backend | S | Record sink: checker POSTs each DecisionRecord to `DECISION_LOG_URL`; POST failure turns `allow` into `hold` ([sdd.md §7](sdd.md)). **Done, merged in PR #6 (`checker/src/sink.rs` + wired in `checker/src/decide.rs`); signed off by Jim 2026-11-11** | Unit tests; records arrive from an OutLayer run once A1 is live | — | Jesus | Done |
| A3 | A | Backend | S | Eval harness skeleton: run the checker binary over every scenario, label vs. verdict, write `results.json` (C1 format). **Done, merged in PR #6 (`agent/src/firewall_agent/eval.py` (`firewall-eval`) + `agent/tests/test_eval.py`); signed off by Jim 2026-11-11** | Runs on the stub checker today | C1 format (fixture until then) | Jesus | Done |
| B1 | B | Backend | M | Policy rules check: allowlist, memo and amount sanity, amount must match the user request or invoice; output the frozen `signals.policy` shape; config switch. **Done, merged in PR #3 (checker/src/policy.rs): signals.policy filled; violation ids receiver_not_allowlisted, memo_too_long, memo_bad_chars, amount_invalid, amount_over_cap, amount_mismatch_request, amount_mismatch_invoice; config POLICY_ENABLED, POLICY_ALLOWLIST, POLICY_MAX_AMOUNT, POLICY_MAX_MEMO_CHARS; attack-fake-invoice-amount-inflation flagged; Rc review in PR #9 ([b1-policy-review.md](b1-policy-review.md)); signed off by Jim 2026-11-11** | Unit tests; `attack-fake-invoice-amount-inflation` flagged | frozen `signals.policy` | Rc (pairs with Jim) | Done |
| B2 | B | Backend | S | Nightly end-to-end script: one benign and one attack payment on testnet (human runs it). **Done, merged in PR #9 (`agent/src/firewall_agent/nightly_e2e.py` (`firewall-nightly-e2e`), `scripts/nightly-e2e.*`; unit tests in `agent/tests/test_nightly_e2e.py`; runbook & expected output in [nightly-e2e.md](nightly-e2e.md)); signed off by Jim 2026-11-11** | Script plus expected output | — | Rc | Done |
| C1 | C | Backend | S | Freeze `results.json` (schema + example under `schemas/`) and add fixture DecisionRecords with filled signals for fusion tests. **Done, merged in PR #7; signed off by Jim 2026-11-11** | Schema and example committed; E3 and A3 can use them | — | paticolcol | Done |
| C2 | C | Backend | M | Injection classifier: host `protectai/deberta-v3-base-prompt-injection-v2`, checker client scores each context item into `signals.injection`, measure latency. **Done, merged in PR #7; signed off by Jim 2026-11-11** | Score per item in the record; latency recorded | frozen `signals.injection` | paticolcol | Done |
| D1 | D | Frontend | M | Landing page skeleton: choose a static stack and host (must stay up through 2026-11-18, ideally 2026-11-25); sections: problem, how it works, NEAR's role, Jev's role, safety layers, demo, results, links | Deployed URL with draft copy | — | Helena | Not started |
| E1 | E | Frontend | M | Live receipts panel: read-only calls to Guardian views over a public testnet RPC, explorer links, no wallet. **2026-11-11: integrated into `site/`, with filtering, pagination, refresh and exact token amounts; Helena's re-review pending.** | Shows the existing testnet receipts | live testnet Guardian | Ace | In progress |

**Decision at the end of Sprint 1:** if A1 is not working, lane A replaces A4 with **A0: HTTPS + signed-verdict fallback mode** ([idea.md Risks](idea.md#risks-and-fallbacks)) in Sprint 2 and A4 moves to Sprint 3.

### A1 log (done 2026-11-10)

Merged to `main` on GitHub: branch `a1-outlayer-live`, commit `5d47f5b`, merge `928b0aa`, sign-off `4100de8`.

| Area | What changed |
| --- | --- |
| Contract (`contract/guardian/src/lib.rs`) | Every OutLayer request now sends `max_memory_mb: 128` (`OUTLAYER_MAX_MEMORY_MB`). The request args are built in `outlayer_request_args`, covered by the test `outlayer_request_args_set_every_limit`. Storage layout unchanged. |
| Setup (`agent/src/firewall_agent/setup_testnet.py`) | New `firewall-setup-testnet --redeploy SUFFIX`: creates `guardian-SUFFIX` (3.5 NEAR, 200 tUSDC) and `agent-SUFFIX` (0.5 NEAR, `request_payment`-only key), reusing `tusdc.`, `checker.`, `hostco.` and `hostc0.`. It saves `GUARDIAN_PRIVATE_KEY` to `.env.testnet` and backs up the old file. |
| Docs (`sdd.md` §6) | [First testnet run](sdd.md#first-testnet-run-2026-11-09): tx hashes, the answers to the three open questions, runbook steps 5–6 updated. |

Testnet state:

- The current Guardian is `guardian-v2.jimuelle-firewall.testnet`, its agent `agent-v2.jimuelle-firewall.testnet`.
- OutLayer project `jimuelle-firewall.testnet/firewall-checker`, version `c00b7995…d173`. Deposit 0.01 NEAR, 50 requests per day.
- The old `guardian.jimuelle-firewall.testnet` cannot be upgraded (its full-access key was never saved). It stays as is for its relayer-mode receipts.
- E1 and E5 should read receipts from `guardian-v2`.

Runs on `guardian-v2`:

| Request | Scenario | Result |
| --- | --- | --- |
| 1 | benign, 18 tUSDC | `timed_out`; no memory limit sent, 0.0048 NEAR deposit. Failed closed, no transfer. |
| 2 | benign, 18 tUSDC | `paid` in 13 blocks; hostco's balance rose 36 → 54 tUSDC |
| 3 | attack `attack-morse-lookalike`, 180 tUSDC | `paid` with `stub_allow`, as expected until C3 lands |

Answers to the open questions:

- **Result shape:** a `Text` result arrives as a JSON string holding the verdict.
- **Real cost:** about 0.001 NEAR per run against a 0.004 NEAR estimate; the rest is refunded.
- **Timeout:** after 200 blocks the callback gets `null`, and the receipt is recorded `timed_out`.

Verified with `cargo test --workspace` (112 passed) and `uv run pytest` (134 passed), plus two independent tester/reviewer passes with no blockers.

Follow-ups, not scheduled:

- Done in PR #2 (2026-11-10): full setup saves `GUARDIAN_PRIVATE_KEY` and `.env.example` lists it; both setup paths write every key (and the agent's function-call key) to `.env.testnet.pending` before using it, and a leftover pending file stops the next run.
- `TYPESAFE_API_KEY` is already set. guardian-v2's mode still has `secrets_ref: null`, so once `decide()` calls Jev (C3), call `set_checker_mode` with `secrets_ref` `{profile, account_id}` so the checker receives the key.

## Sprint 2 — due Wed 11 Nov, 23:59 PHT (15:59Z)

Goal: gate G2. Frontend first finishes the Sprint 1 carry-over (D1 In progress in PR #14, E1 Not started), since D2 and E2 build on them.

| Who | Role this sprint |
| --- | --- |
| Jim (backend lead) | Tests and signs off every backend task; A4 contract change (signs the redeploy); pairs with paticolcol on C3; after C3, calls `set_checker_mode` with `secrets_ref` and runs G2 (signs) |
| Rc | B3 counterparty signals |
| paticolcol | C3 Jev fusion (pairs with Jim) |
| Jesus | A5 unprotected-agent mode, then B4 checker hardening (lane B overflow; B3 alone fills Rc's sprint) |
| Helena (frontend lead) | Finish D1 first; then D2 "How it works" and D3 demo storyboard; reviews E2, E3 |
| Ace | Finish E1 first; then E2 receipt detail view and E3 results section on the C1 example |

| ID | Lane | Track | Size | Task | Done when | Starts from | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A4 | A | Backend | M | Contract: per-payee budgets; register the receiver with the token before `ft_transfer` (sdd §6 planned additions) | Unit tests; human redeploys | — | Jim | **Done** (PR #21; signed off by Jim 2026-11-12): `6a4c380`; guardian-v2 redeployed with this wasm on testnet 2026-11-12 (tx `6ia53LjrQhbiqQYcy9gdqAAqGdYBkLpXzes8gb3QdEwA`, `get_payee_budget(hostco…)` = 20000000) |
| A5 | A | Backend | S | Unprotected-agent mode for demo step 3: plain agent with a full-access key pays the attack | Attack pays without the Guardian on testnet | — | Jesus | In progress |
| B3 | B | Backend | M | Counterparty signals over RPC: account age, is-contract, code-hash change, prior payments, lookalike distance; agent behaviour profile; output `signals.counterparty` | `hostc0` flagged as lookalike of `hostco` | frozen `signals.counterparty` | Rc | **Done** (PR #21; signed off by Jim 2026-11-12): merged `d8f10f3`; fixes `fa659e3`, `a40f7d6` (qualified account ids never match bare profile names; optional `COUNTERPARTY_NAMESPACE`) |
| B4 | B | Backend | S | Checker hardening: range-check Jev `confidence`/`score` and choice vs argmax, HTTPS-only base URL, no HTTP redirects, timeout budget fitted to OutLayer's limit | Tests; review findings closed | — | Jesus | Not started |
| C3 | C | Backend | M | Jev fusion in `decide()`: build Jev `state` from signals and profile, ask the four questions, apply hold/block thresholds from checker config; block only when two detectors agree, at most one of them Jev | Stub allow removed; tests on C1 fixtures; real reason codes | C1 fixtures (real B1/C2/B3 outputs swap in as they land) | paticolcol (pairs with Jim) | Done, awaiting sign-off (merged in PR #18, `136224d`; no `agent_profile` in the state until a profile producer exists) |
| D2 | D | Frontend | M | "How it works" section: architecture diagram (agent → Guardian → checker → verdict → transfer), allow/hold/block, amount-safety table | Section live; copy approved by a backend owner | D1 | Helena | Not started |
| D3 | D | Frontend | S | Demo storyboard: shot list for the ~2-minute script ([idea.md Demo script](idea.md#demo-script-about-2-minutes)), numbers slide, 20-second GIF plan | Storyboard approved | — | Helena | Done (storyboard in [demo-storyboard.md](demo-storyboard.md), PRs #16, #20 and #26; signed off by Jim 2026-11-13) |
| E2 | E | Frontend | M | Receipt detail view: verdict, reason codes, input and record hashes, explorer link, hold countdown | Works for paid, held, refused and timed-out receipts | E1 | Ace | In progress (2026-11-13: implemented locally on `feat/e2-receipt-detail`; 21/21 node tests and production build pass; browser interaction checks and Helena's review pending) |
| E3 | E | Frontend | S | Results section rendering `results.json` (table plus a simple chart) with the stated caveats (exchangeability, known attack families) | Renders the C1 example | C1 example | Ace | Not started |
| G2 | All | — | — | **Gate:** on testnet through the real checker, one benign payment pays and one attack is blocked | Receipts show both | C3, A1 or A0 | Jim (signs) | Not started |

## Sprint 3 — due Thu 12 Nov, 23:59 PHT (15:59Z)

Goal: numbers frozen for the demo and site (sync point at the end of this sprint).

| Who | Role this sprint |
| --- | --- |
| Jim (backend lead) | Tests and signs off every backend task; pairs with paticolcol on C5 |
| Rc | B5 cascade, then B6 README draft |
| paticolcol | C4 full eval run, then C5 conformal calibration (pairs with Jim) |
| Jesus | A6 dataset to 150/150 first (C4 needs it), then A7 red-team round (Jesus did not build the checks) |
| Helena (frontend lead) | D4 results section on the real `results.json`, D5 copy pass with Rc (B6 owner); reviews E4 |
| Ace | E4 demo assets: GIF and numbers slide |

| ID | Lane | Track | Size | Task | Done when | Starts from | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A6 | A | Backend | M | Grow the dataset to about 150 benign / 150 attack (templated variants plus AgentDojo-derived cases, licences checked); include amount-inflation, replay and budget-grooming cases | Balance test passes; families balanced across splits | — | Jesus | **Done** (PR #21; signed off by Jim 2026-11-12): `930fe6a`; 150 benign + 150 attack in `agent/scenarios/` (6 families × 25), generated by `agent/tools/generate_scenarios.py` |
| A7 | A | Backend | S | Red-team round (lane A did not build the checks): attack with full knowledge of the design; log what got through and the fixes | Red-team row filled; fixes filed to lane B | G2 | Jesus | **Done** (PR #21; signed off by Jim 2026-11-12): `930fe6a`; 17 scenarios in `agent/scenarios/redteam/`; `docs/results/redteam-results.json` (`jev_fusion_conformal`): 9 of 17 missed (52.94%), 7 held, 1 blocked; log in `docs/results/redteam.md` |
| B5 | B | Backend | M | Cascade: cheap checks first, Jev escalates ambiguous cases, trusted repeat payments skip expensive checks | Cost and latency logged per path | C3 | Rc | **Done** (PR #21; signed off by Jim 2026-11-12): `fa659e3`, `CASCADE_ENABLED` and `FUSION_MODE` in `checker/src/{fusion,decide}.rs`; "trusted repeat payments skip expensive checks" is not implemented; the classifier was not run in the evaluation, so the cascade row never calls it |
| B6 | B | Backend | S | README draft for the AI screeners ([AGENTS.md §9](../../AGENTS.md#9-readme-rules-for-judges)): what, problem, NEAR's role in the first paragraph, numbered "do X → see Y" steps, dry-run, every third-party tool (Jev included), disclosures, function-call key caveat | Checklist in AGENTS.md §9 met except results | — | Rc | **Done** (PR #21; signed off by Jim 2026-11-12): `0962bfb` `README.md`, `docs/build/nightly-e2e.md`; fresh-clone fixes in `5626a8c` |
| C4 | C | Backend | M | Full eval run: every check on/off, fill the results table ([idea.md](idea.md#evaluation-and-calibration)), cost and latency, write `results.json` | Every row filled; JSON committed | A3, A6, C3 | paticolcol | **Done** (PR #21; signed off by Jim 2026-11-12): `73a0e0d` seven presets in `eval.py`; `docs/results/results.json` (`78e3fcb`, total 300) from six of the seven presets; `classifier_only` not run (classifier model download failed); MELON not built; cost unpriced, Jev calls per payment reported (1 in Jev rows) |
| C5 | C | Backend | M | Conformal hold threshold at ε = 5% on the pooled calibration set; unseen-family rotation through all six families | False-hold rate reported against the target | C4 | paticolcol (pairs with Jim) | **Done** (PR #21; signed off by Jim 2026-11-12): q̂ frozen at 0.84 (`61e9f52`) from 150 benign, ε = 5%; realised false-hold rate 4.67% (7/150, in-sample) on the final conformal run; unseen-family detection 79.33% (119/150) in `unseen_family_rotation` |
| D4 | D | Frontend | S | Results section switched to the real `results.json` | Shows the committed numbers | C4 (E3 already built) | Helena | Not started |
| D5 | D | Frontend | S | Copy pass with a backend owner: every claim on the site matches the README and the numbers | No unsupported claims left | B6 | Helena (with Rc) | Not started |
| E4 | E | Frontend | M | Demo assets: 20-second GIF of the blocked attack, numbers slide from `results.json` | Assets in the repo | D3 | Ace | Not started |

## Sprint 4

| ID | Lane | Track | Size | Task | Done when | Starts from | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A8 | A | Backend | M | Record the demo on testnet with real transactions (human signs) | Video file plus explorer links | G2, A5 | |
| B7 | B | Backend | S | Fresh-clone test on a machine that never saw the repo; fix what breaks. **Done** (PR #21; signed off by Jim 2026-11-12): fresh clone without `.env` run against the README; fixes in `5626a8c`; keyless demo gave `hold` with `check_unavailable` and keyless nightly dry-run exited 1 with benign `[FAIL]`, as the README says | README steps pass as written | B6 | |
| C6 | C | Backend | S | README results and limits sections; freeze thresholds and tuned caps. **Done** (PR #21; signed off by Jim 2026-11-12): `FUSION_HOLD_THRESHOLD` frozen at 0.84 (`61e9f52`); Results and Limits filled from `docs/results/results.json` (`78e3fcb`) | README complete | C5 | |
| D6 | D | Frontend | M | Landing page final: embed video and GIF, final copy, mobile and accessibility pass, meta and preview image, link check | Production URL | A8, E4 | |
| E5 | E | Frontend | S | Hosting check: uptime through 2026-11-25; receipts panel points at the final Guardian | Uptime check in place | D6 | |
| E6 | E | Frontend | S | Visuals for the X demo post (cover frame, screenshots) | Ready for the human to post | A8 | |

## Sprint 5 — submit

| ID | Lane | Track | Size | Task | Done when | Starts from | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | — | Human | S | Re-read the live https://nearhackathon.com/HACKATHON.md; make the repo public | Repo public | B7 | |
| S2 | — | Human | S | X demo post with the video, tagging @NEARProtocol and #NEARHackathon (agent may draft) | Post URL | A8, E6 | |
| S3 | — | Human | S | Submission: human-only fields filled by the human; agent prints the payload, human confirms before it is sent | Submitted | S1, S2 | |
| S4 | All | — | — | Buffer: fixes only, no new features | — | — | |

## Critical path and cuts

```mermaid
flowchart LR
  C1[C1 formats + fixtures] --> C3[C3 Jev fusion]
  B1[B1 policy] -.real signals.-> C3
  C2[C2 classifier] -.real signals.-> C3
  B3[B3 counterparty] -.real signals.-> C3
  A1[A1 OutLayer live] -->|or A0 fallback| G2{G2 gate}
  C3 --> G2 --> C4[C4 eval] --> A8[A8 record demo] --> S3[S3 submit]
```

Dotted edges are swaps from fixture to real data, not waits.

- Frontend lanes D and E depend only on the live testnet Guardian and the C1 format; backend progress never blocks them.
- Not scheduled: MELON masked re-run (first on the [cut list](idea.md#mitigations-for-the-three-trade-offs)), re-checks during the hold window, shared blocklist. A backend lane that finishes early picks up MELON.
