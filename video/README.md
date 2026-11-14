# Eclipse explainer video

A Remotion project with three compositions (1920×1080):

- `EclipseInProduction` (60 s, 30 fps): how Eclipse runs, from deployment to receipts. Animated diagram, no screen recording; every number is copied from the repository README and code, listed below.
- `EclipseLiveDemo` (length from the run data, about 90 s, 30 fps): a real dry-run test recorded on screen. 8 scenarios run twice, 4 terminals per side: first the agent without Eclipse, then the same agent behind Eclipse, then a scoreboard and "what to check". Every number comes from the recorded run, see [Live demo](#live-demo).
- `ReadmeDemo` (15 s, 25 fps): the README GIF, an animation of testnet receipts #7 (blocked Morse attack) and #6 (allowed hosting invoice); see [README GIF](#readme-gif).

## Commands

Node 20.19+ (Node 22.13+ or 24 also work). Run in `video/`:

```
npm install
npm run dev                                        # Remotion Studio preview
npx remotion render EclipseInProduction out/eclipse.mp4
npx remotion render EclipseLiveDemo out/eclipse-live-demo.mp4   # needs public/live-demo/, below
npm run lint                                       # eslint + tsc
```

## Scenes (EclipseInProduction)

| # | Scene | Source of what it shows |
| --- | --- | --- |
| 1 | Hook: the May 2026 Grok wallet drain | README "The problem" (Giskard) |
| 2 | Deployment: owner funds the Guardian, agent gets a function-call key, caps 200 / 500 / 20 tUSDC | `contract/guardian/src/lib.rs` (`DAILY_CAP_WHOLE`, `PAYEE_START_BUDGET_WHOLE`), README "What NEAR does" |
| 3 | Payment flow: pause, four checks, verdict bound to receiver, token, amount and `request_id` | README "How it works" diagram |
| 4 | Allow: 18 tUSDC to `hostco` | `agent/scenarios/benign-hosting.json` |
| 5 | Hold: 180 tUSDC to `supplier-acme`, 6 h escrow | `agent/scenarios/benign-supplier-large.json`; hold windows from `validate::hold_window_ns` (over 100 tUSDC → 6 h) |
| 6 | Block: Morse-code reply, 180 tUSDC to lookalike `hostc0` | `agent/scenarios/attack-morse-lookalike.json`; captions follow [demo-storyboard.md](../docs/build/demo-storyboard.md) shot 4 |
| 7 | Receipts: on-chain fields and the off-chain DecisionRecord | AGENTS.md §7 "Log every decision" |
| 8 | Results: attacks allowed 0/150, 0/100, 2/17 (baseline 29, 17, 7), 0 benign blocked, with the caveat | README "Results" |
| 9 | Close: name, tagline, testnet Guardian account | README header |

The signals in scenes 4–6 are illustrative, matching each scenario's expected outcome; they are not read from a recorded run. Brand colors and fonts (Geist, Geist Mono) match `site/src/styles.css`.

## Live demo

Dry-run only: nothing is signed. The agent is scripted ("already fooled": it proposes each scenario's `scripted_tool_call`), so the only difference between the two takes is Eclipse. Eclipse uses real TypeSafe Jev (7 calls per take), the local injection classifier and the native checker. Not the A8 storyboard recording ([demo-storyboard.md](../docs/build/demo-storyboard.md) asks for testnet payments).

1. Build the checker (`cargo build -p checker --release`) and start the classifier in `agent/`: `uv run --with transformers --with torch firewall-classifier 8088`.
2. Record, from `agent/`, without touching the desktop (the capture records anything drawn over the windows): `powershell -File tools\showdown\record.ps1 -Run <run> -Side plain -Rows 4 -Agent scripted -StepDelay 2 -Pause 4 -InboxLines 1 -Fps 30 -Scenarios <8 names>`, then the same with `-Side eclipse`. The 8 names and the flags are in the header of `record.ps1`.
3. `uv run python tools/showdown/video_data.py --run ../data/showdown/<run> --out ../video/public/live-demo` → copies both takes and writes `run.json` (format `eclipse.live-demo.v2`).
4. Render `EclipseLiveDemo`. `public/live-demo/` is gitignored, like `data/`.

The recorded run is R30 in [ledger.md](../docs/results/ledger.md) (take `live7`).

## README GIF

`ReadmeDemo` is encoded to `site/public/demo/eclipse-demo.gif` (1200×675, 25 fps, 375 frames, under 8 MB, first frame equal to the last so it loops). Decision and frame plan: [demo-storyboard.md](../docs/build/demo-storyboard.md#readme-gif). Run in `video/` (needs FFmpeg on `PATH`):

```
npm run lint
npx remotion render ReadmeDemo out/readme-demo-frames --sequence --image-format=png --image-sequence-pattern="f_[frame].[ext]"
ffmpeg -y -framerate 25 -start_number 0 -i out/readme-demo-frames/f_%03d.png -vf "scale=1200:675:flags=lanczos,palettegen=max_colors=256:stats_mode=full" out/readme-demo-palette.png
ffmpeg -y -framerate 25 -start_number 0 -i out/readme-demo-frames/f_%03d.png -i out/readme-demo-palette.png -lavfi "scale=1200:675:flags=lanczos[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle" -loop 0 ../site/public/demo/eclipse-demo.gif
```

| On screen | Source of what it shows |
| --- | --- |
| Request, invoice (INV-2026-11, 18.00 USDC → `hostco`), Morse X reply and its decoding, proposed tool call | `agent/scenarios/attack-morse-lookalike.json` (`user_request`, `inbox`, `scripted_tool_call`) |
| Reason codes, outcomes (`block` / `refused`, `allow` / `paid`), amounts, receivers | [sdd.md](../docs/build/sdd.md#outlayer-run-with-jev-2026-11-13), receipts #6 and #7 |
| "Every payment pauses for a check." and "Funds stay in the contract. The agent holds only a function-call key." | README first paragraph |
| Name and tagline | README header |

All on-screen values live in `src/readme/data.ts`, each with its source. No Jev probability is shown.

## Files

- `src/Root.tsx`: registers the compositions.
- `src/EclipseInProduction.tsx`: the scene order, durations and fades.
- `src/scenes/`: one component per scene; `PaymentCase.tsx` is reused for the allow, hold and block scenes.
- `src/live/`: `EclipseLiveDemo` (`calcLiveDemo` reads `public/live-demo/run.json` and sets the length), `Intro`, `Footage` (one take full screen with running totals), `Scoreboard`, `JudgeNotes`, `captions.ts` (scenario captions, verdict badges), `types.ts` (the `run.json` shape).
- `src/readme/`: `ReadmeDemo` (`data.ts` on-screen values, `timeline.ts` timing, geometry and easings, `Stage.tsx` lane, sun, moon, arcs and corona, `Panels.tsx` text panels, `Morse.tsx`, `Lockup.tsx`).
- `src/theme.ts`: colors and fonts; `src/Reveal.tsx`: fade-in helper.
