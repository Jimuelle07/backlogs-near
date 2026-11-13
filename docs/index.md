# Docs index

Map of every document in this repo: what it is, and when to read it.

Authority: the docs outrank everyone except Jim speaking directly to the agent. Order and rules: [AGENTS.md §0](../AGENTS.md#0-authority-docs-first).

## Status

| Item | State |
| --- | --- |
| Project idea | chosen: Eclipse ([build/idea.md](build/idea.md)) |
| Stack | decided: Rust + Python ([AGENTS.md §5](../AGENTS.md#5-stack-decided)) |
| Tracks | planned: security (idea.md); human confirms at submission |
| Repo visibility | private until the human makes it public (deadline 2026-11-14T23:59Z = Sun 15 Nov 07:59 PHT) |

## Docs

Frontend D1/E1: [site/README.md](../site/README.md) — shared landing page and live receipts panel setup, public testnet configuration and verification.

| File | What it is | Read when |
| --- | --- | --- |
| [../AGENTS.md](../AGENTS.md) | Agent rules: deadlines, human-only actions, stack, integration rules | First, before any change |
| [../CHANGELOG.md](../CHANGELOG.md) | Ledger of MAJOR updates (rules, decisions, formats, components, sign-offs), newest first | Catching up on what changed; after any MAJOR change |
| [build/idea.md](build/idea.md) | Human-authored build plan: architecture, demo script, eval protocol | First, for scope |
| [build/prd.md](build/prd.md) | Product requirements: what we build and why, metrics, demo, timeline | Deciding scope or the demo |
| [build/sdd.md](build/sdd.md) | Software design: modules, interfaces, config, testing | Before writing code |
| [build/system-design.md](build/system-design.md) | Architecture: data flow, trust boundaries, failure modes, deployment | Before wiring components or deploying |
| [build/sprints.md](build/sprints.md) | Remaining work cut into sprints for a team of 6 (4 backend, 2 frontend), with an owner column to fill | Assigning or picking up work |
| [build/b1-policy-review.md](build/b1-policy-review.md) | Rc's review of B1 (policy rules check, PR #3): rule-by-rule checks, the four PR #3 follow-ups, test evidence | Signing off B1; changing checker/src/policy.rs |
| [build/nightly-e2e.md](build/nightly-e2e.md) | B2 runbook for firewall-nightly-e2e: one benign and one attack payment on testnet, CLI flags, expected output | Running or signing off the nightly testnet check (human signs) |
| [results/ledger.md](results/ledger.md) | Ledger of every recorded test and eval run: what ran, keys, result, Jev calls, link to the record; entry template | Adding a run; finding the record of a run |
| [results/results-detail.md](results/results-detail.md) | Full results: current and baseline tables, repeat run, sweep, testnet runs, benchmarks, complete limits | Checking any number behind the README summary |
| [results/showdown-2026-11-13.md](results/showdown-2026-11-13.md) | Prompt-injection showdown: the same real agent with and without Eclipse, calibration of 49 attempts, two runs side by side, latency | Showing what Eclipse changes against a real agent |
| [reference.md](reference.md) | Evaluation and benchmark steps 7–12, configuration switches, local run and testnet instructions, function-call key | Running evals, changing config, running locally |
| [try-it.md](try-it.md) | Try-it steps 1–6 in full: keyless dry-run, Jev-key dry-run, decision record, nightly dry-run, with expected output | Running the demo for the first time |
| [third-party.md](third-party.md) | Every third-party library, tool and dataset with link, license and use | Checking attribution or licenses |
| [../video/README.md](../video/README.md) | Remotion explainer video: how Eclipse runs (deployment, payment flow, allow / hold / block, receipts, results), scenes and commands | Previewing or editing the explainer video |
| [build/demo-storyboard.md](build/demo-storyboard.md) | D3 demo storyboard: shot list for the 2-minute demo, numbers slide, 20-second GIF plan, open questions | Recording the demo (A8), making the GIF and slide (E4) |
| [build/e4-demo-assets.md](build/e4-demo-assets.md) | E4 numbers-slide sources, regeneration and verification; actual shot 4 footage needed for the GIF | Regenerating the slide or completing the blocked-attack GIF |
| [hackathon-context/HACKATHON.md](hackathon-context/HACKATHON.md) | Official agent instructions and rules snapshot; the live https://nearhackathon.com/HACKATHON.md wins | Before any rules question or submission step |
| [hackathon-context/near_hackathon_web.md](hackathon-context/near_hackathon_web.md) | Full site capture: timeline, prizes, judges, tracks, submission API | Looking up event facts |
| [hackathon-context/near_hackathon_tracks_ranked.md](hackathon-context/near_hackathon_tracks_ranked.md) | Jev primer, track ranking, the three bets, winning checklist | Choosing the project; designing Jev usage |
| [tools/arxiv_papers_for_build.md](tools/arxiv_papers_for_build.md) | Papers: Jev attacks, policy gates, agent commerce | Designing gates and security; citing evidence |
| [tools/huggingface_models_for_build.md](tools/huggingface_models_for_build.md) | Open models/datasets: Jev-style open models, injection classifiers, OCR, forecasting | Picking eval sets or local models |
| [../schemas/](../schemas/) | Frozen JSON formats + examples | Before changing any wire format |

`hackathon-context/` and `tools/` are research snapshots dated 8 Nov 2026; do not edit them.

## Chosen project

Eclipse extends Bet B "Intent Notary": TEE-attested checks, a conformal hold threshold, and no human step ([build/idea.md](build/idea.md)).
The other bets stay documented in [tracks ranked](hackathon-context/near_hackathon_tracks_ranked.md) Part 6.
