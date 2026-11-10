# Changelog

Ledger of MAJOR updates only, newest first. What counts as MAJOR: [AGENTS.md §10](AGENTS.md#10-docs-upkeep).

## 2026-11-11

- **Sign-off:** Jim signed off Sprint 1 backend tasks A2, A3 (PR #6), B1 (PR #3), B2 (PR #9), C1 and C2 (PR #7); [sprints.md](docs/build/sprints.md#progress-updated-2026-11-11) marks them Done.
- **Format:** results.json frozen as [schemas/results.schema.json](schemas/results.schema.json) with [schemas/examples/results.json](schemas/examples/results.json); five DecisionRecord fixtures in [schemas/fixtures/](schemas/fixtures/) (C1, PR #7).
- **Component:** nightly end-to-end testnet script firewall-nightly-e2e (agent/src/firewall_agent/nightly_e2e.py, scripts/nightly-e2e.*), runbook [nightly-e2e.md](docs/build/nightly-e2e.md) (B2, PR #9).
- **Rules:** agents should not co-author commits, push or merge ([AGENTS.md §4](AGENTS.md#4-human-only-actions)).
- **Docs:** added this CHANGELOG.md; MAJOR updates are logged here ([AGENTS.md §10](AGENTS.md#10-docs-upkeep)).

## 2026-11-10

- **Rules:** docs-first authority order: the docs outrank everyone except Jim speaking directly to the agent ([AGENTS.md §0](AGENTS.md#0-authority-docs-first)). Format changes need Jim's approval and update the schema first ([sprints.md](docs/build/sprints.md#how-the-lanes-stay-parallel)).
