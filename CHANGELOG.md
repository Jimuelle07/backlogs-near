# Changelog

Ledger of MAJOR updates only, newest first. What counts as MAJOR: [AGENTS.md §10](AGENTS.md#10-docs-upkeep).

## 2026-11-11

- **Component:** counterparty signals in `decide()` ([checker/src/counterparty.rs](checker/src/counterparty.rs), B3): profile-based lookalike distance and prior payments, optional RPC `view_account` (`COUNTERPARTY_RPC_URL` only; the checker no longer falls back to `NEAR_RPC_URL`), filled before the Jev questions so `fusion::jev_state` and `fuse` see it; config in [sdd.md §8](docs/build/sdd.md#8-configuration).
- **Component:** C4 multi-configuration eval and C5 conformal calibration on branch `sprint2-3-paticolcol`: `firewall-eval --all-configurations` runs the checker under three checker-env presets (`no_defense`, `jev_fusion_all_signals`, `jev_fusion_conformal`) and writes one row per configuration, plus `jev_unusual` per case; new `firewall-calibrate` (`agent/src/firewall_agent/calibration.py`) computes the split-conformal q̂ at ε = 5% on the pooled benign set and reports per-family detection at that threshold on a held-out benign split. Neither is signed off yet.
- **Format:** new ReasonCode `checks_passed` (clean allow), appended last in [verdict.schema.json](schemas/verdict.schema.json) and both Rust enums (checker, Guardian; Borsh order kept); `stub_allow` stays decodable for old receipts. The deployed guardian-v2 rejects `checks_passed` until it is redeployed.
- **Component:** Jev fusion in `decide()` ([checker/src/fusion.rs](checker/src/fusion.rs), C3): Jev state from input and signals, four questions through `DecisionClient`, hold/block per [sdd.md §5](docs/build/sdd.md#5-verdict-rules) with `FUSION_*` thresholds (defaults uncalibrated until C5). Jev unavailable → hold with `check_unavailable`; a failed decision-log POST turns `[checks_passed]` into `[check_unavailable]`. Nightly e2e attack steps now pass only when held or blocked.
- **Plan:** Sprint 2 (due Wed 11 Nov) and Sprint 3 (due Thu 12 Nov) planned in [sprints.md](docs/build/sprints.md#sprint-2--due-wed-11-nov-2359-pht-1559z): owners, roles, due dates; D1/E1 carried over into Sprint 2; B4 moved to Jesus.
- **Sign-off:** Jim signed off Sprint 1 backend tasks A2, A3 (PR #6), B1 (PR #3), B2 (PR #9), C1 and C2 (PR #7); [sprints.md](docs/build/sprints.md#progress-updated-2026-11-11) marks them Done.
- **Format:** results.json frozen as [schemas/results.schema.json](schemas/results.schema.json) with [schemas/examples/results.json](schemas/examples/results.json); five DecisionRecord fixtures in [schemas/fixtures/](schemas/fixtures/) (C1, PR #7).
- **Component:** nightly end-to-end testnet script firewall-nightly-e2e (agent/src/firewall_agent/nightly_e2e.py, scripts/nightly-e2e.*), runbook [nightly-e2e.md](docs/build/nightly-e2e.md) (B2, PR #9).
- **Rules:** agents should not co-author commits, push or merge ([AGENTS.md §4](AGENTS.md#4-human-only-actions)).
- **Docs:** added this CHANGELOG.md; MAJOR updates are logged here ([AGENTS.md §10](AGENTS.md#10-docs-upkeep)).

## 2026-11-10

- **Rules:** docs-first authority order: the docs outrank everyone except Jim speaking directly to the agent ([AGENTS.md §0](AGENTS.md#0-authority-docs-first)). Format changes need Jim's approval and update the schema first ([sprints.md](docs/build/sprints.md#how-the-lanes-stay-parallel)).
