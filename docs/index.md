# Docs index

Map of every document in this repo: what it is, and when to read it.

## Status

| Item | State |
| --- | --- |
| Project idea | undecided |
| Stack | decided (see [AGENTS.md](../AGENTS.md#5-stack-decided)) |
| Tracks | undecided (human decides) |
| Repo visibility | private until the human makes it public (deadline 2026-11-14T23:59Z = Sat 15 Nov 07:59 PHT) |

## Docs

| File | What it is | Read when |
| --- | --- | --- |
| [../AGENTS.md](../AGENTS.md) | Agent rules: deadlines, human-only actions, stack, integration rules | First, before any change |
| [build/prd.md](build/prd.md) | Product requirements: what we build and why, metrics, demo, timeline | Deciding scope or the demo |
| [build/sdd.md](build/sdd.md) | Software design: modules, interfaces, config, testing | Before writing code |
| [build/system-design.md](build/system-design.md) | Architecture: data flow, trust boundaries, failure modes, deployment | Before wiring components or deploying |
| [hackathon-context/HACKATHON.md](hackathon-context/HACKATHON.md) | Official agent instructions and rules snapshot; the live https://nearhackathon.com/HACKATHON.md wins | Before any rules question or submission step |
| [hackathon-context/near_hackathon_web.md](hackathon-context/near_hackathon_web.md) | Full site capture: timeline, prizes, judges, tracks, submission API | Looking up event facts |
| [hackathon-context/near_hackathon_tracks_ranked.md](hackathon-context/near_hackathon_tracks_ranked.md) | Jev primer, track ranking, the three bets, winning checklist | Choosing the project; designing Jev usage |
| [tools/arxiv_papers_for_build.md](tools/arxiv_papers_for_build.md) | Papers: Jev attacks, policy gates, agent commerce | Designing gates and security; citing evidence |
| [tools/huggingface_models_for_build.md](tools/huggingface_models_for_build.md) | Open models/datasets: Jev-style open models, injection classifiers, OCR, forecasting | Picking eval sets or local models |

`hackathon-context/` and `tools/` are research snapshots dated 8 Nov 2026; do not edit them.

## Choosing the project

Candidates from [tracks ranked](hackathon-context/near_hackathon_tracks_ranked.md) Part 6 (bets) scored with the Part 5 opportunity table (Power, Space, Jev fit, Buildable, Judge appeal; /25):

- **Bet A — "Thousand-Agent Market"** (Swarms + Agents + Open): AI Swarms is the top opportunity, 21/25 with 19 projects. Hundreds of Jev agents bid live; NEAR sub-accounts and a coordinator contract settle rounds. [Part 6](hackathon-context/near_hackathon_tracks_ranked.md)
- **Bet B — "Intent Notary"** (Security + Agents + Real-World Money): highest power, but Security (140) and Agents (130) are the most crowded tracks; needs the calibration / intent-matching / false-block-rate differentiator. [Part 6](hackathon-context/near_hackathon_tracks_ranked.md)
- **Bet C — "Market Town, Live"** (Games + Swarms + NFTs): Games scores 19/25 with 17 projects and is the best visual Jev demo. [Part 6](hackathon-context/near_hackathon_tracks_ranked.md)
- **Thesis — "NEAR, Labeled"** (Investment Thesis): 19/25 with 24 projects; lowest build risk, directly in front of investor judges, unique dataset. [Part 4 #10 and Part 6](hackathon-context/near_hackathon_tracks_ranked.md)
- **Multi-track is allowed:** one submission, every track that fits; Open Innovation is a good second track for any of the above. [Part 5](hackathon-context/near_hackathon_tracks_ranked.md)

When decided: fill every `TBD(project)` in `build/` and update the status table.
