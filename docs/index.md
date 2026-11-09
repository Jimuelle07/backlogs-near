# Docs index

Map of every document in this repo: what it is, and when to read it.

## Status

| Item | State |
| --- | --- |
| Project idea | chosen: Attested Payment Firewall ([build/idea.md](build/idea.md)) |
| Stack | decided: Rust + Python ([AGENTS.md §5](../AGENTS.md#5-stack-decided)) |
| Tracks | planned: security (idea.md); human confirms at submission |
| Repo visibility | private until the human makes it public (deadline 2026-11-14T23:59Z = Sun 15 Nov 07:59 PHT) |

## Docs

| File | What it is | Read when |
| --- | --- | --- |
| [../AGENTS.md](../AGENTS.md) | Agent rules: deadlines, human-only actions, stack, integration rules | First, before any change |
| [build/idea.md](build/idea.md) | Human-authored build plan: architecture, day-by-day tasks, demo script, eval protocol | First, for scope and schedule |
| [build/prd.md](build/prd.md) | Product requirements: what we build and why, metrics, demo, timeline | Deciding scope or the demo |
| [build/sdd.md](build/sdd.md) | Software design: modules, interfaces, config, testing | Before writing code |
| [build/system-design.md](build/system-design.md) | Architecture: data flow, trust boundaries, failure modes, deployment | Before wiring components or deploying |
| [hackathon-context/HACKATHON.md](hackathon-context/HACKATHON.md) | Official agent instructions and rules snapshot; the live https://nearhackathon.com/HACKATHON.md wins | Before any rules question or submission step |
| [hackathon-context/near_hackathon_web.md](hackathon-context/near_hackathon_web.md) | Full site capture: timeline, prizes, judges, tracks, submission API | Looking up event facts |
| [hackathon-context/near_hackathon_tracks_ranked.md](hackathon-context/near_hackathon_tracks_ranked.md) | Jev primer, track ranking, the three bets, winning checklist | Choosing the project; designing Jev usage |
| [tools/arxiv_papers_for_build.md](tools/arxiv_papers_for_build.md) | Papers: Jev attacks, policy gates, agent commerce | Designing gates and security; citing evidence |
| [tools/huggingface_models_for_build.md](tools/huggingface_models_for_build.md) | Open models/datasets: Jev-style open models, injection classifiers, OCR, forecasting | Picking eval sets or local models |
| [../schemas/](../schemas/) | Frozen JSON formats + examples | Before changing any wire format |

`hackathon-context/` and `tools/` are research snapshots dated 8 Nov 2026; do not edit them.

## Chosen project

The Attested Payment Firewall extends Bet B "Intent Notary": TEE-attested checks, a conformal hold threshold, and no human step ([build/idea.md](build/idea.md)).
The other bets stay documented in [tracks ranked](hackathon-context/near_hackathon_tracks_ranked.md) Part 6.
