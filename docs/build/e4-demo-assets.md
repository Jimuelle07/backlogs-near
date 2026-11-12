# E4 demo assets

Owner: Ace. Branch: `feat/e4-demo-assets`, from `origin/main` after D3 approval
and merge (PR #26; numbers refreshed in PR #28). E4 remains **in progress** until
both the slide and the actual blocked-attack GIF are saved and reviewed.

## Storyboard alignment

The approved [D3 storyboard](demo-storyboard.md) is unchanged. Its **Numbers
slide** section and shot 6 specify the slide: conformal and no-defense rows from
`docs/results/results.json`, the external held-out check from
`docs/results/external-results.json`, and cascade family outcomes. The headline
is not the top-level summary (which is the final, cascade preset). Only the
external check is labelled held-out. Costs are unpriced, so show calls instead.
The false-hold figure is in-sample and above the target; include the
exchangeability and known-family caveats. Contract caps are limits, not measured
results, and are extracted from the Rust constants into the generated JSON
manifest before rendering. No metric is transcribed into the slide template.

The slide uses `site/src/styles.css` tokens and embedded, licensed Geist fonts.
Its editable SVG, standalone HTML and PNG preview live in `site/public/demo/`,
following the site's existing `public/` convention for static assets. Sources,
hashes and mapped values are recorded in `numbers-slide.data.json`.
Text input hashes normalize line endings to LF; font hashes use the binary
bytes, so Windows checkout conversion does not change the provenance hashes.

## GIF prerequisite and current blocker

No screen recording was found in the repository, including ignored media.
D3 is a storyboard, not a screen-recorded application implementation. The
documented Morse attempt is request 5: outcome `hold`, later owner-cancelled to
status `refused` ([nightly log](nightly-e2e.md#run-log)). That is not a blocking
run and cannot be used as footage of `block`. G2 and A8 are not recorded as done
in `sprints.md`. An eval case that blocks is not a testnet screen recording.

E4 therefore cannot yet supply `blocked-attack.gif`. The required input is A8's
actual shot 4 screen recording plus its receipt/decision record, transaction
links, unchanged-balance evidence and the receipt numbers of held attempts.
Jim signs each testnet attempt and cancels each held attempt before the next
try, as required by D3 **Shot list**, shot 4, and **Before recording**. No signing
command is run by the E4 generator. No simulated GIF is substituted.

There is an existing documentation mismatch: `idea.md`'s older demo text mentions
MELON and re-checking; D3 **Decisions**, item 6, explicitly records those as not
scheduled and says Jim will update the older docs separately. E4 follows the
approved storyboard and makes neither claim.

## Regenerate the numbers slide

From the repository root, with Node 20+ and existing site dependencies:

```powershell
node site/scripts/generate-demo-assets.mjs
```

This reads the real committed results by default. If the main results file is
absent, it uses `schemas/examples/results.json` and labels the entire slide
**Sample data**. `--sample` explicitly exercises that path. It never mixes the
real external dataset with a sample slide. A malformed file, unsupported format
(anything other than `firewall.results.v1`), missing required preset/metric or
missing real external set fails with a nonzero exit instead of falling back or
inventing values. Restore the real assets after checking sample mode.

The generator imports existing tested results helpers, extracts caps from
`contract/guardian/src/lib.rs`, and reads the target percentage from the JSON's
exchangeability caveat. It does not use `unseen_family_rotation` for family
detection. The vendored Geist font files and license include their source URLs
in `site/scripts/demo-assets/fonts/README.md`; regeneration needs no network.

Create the portable PNG using the installed Chromium browser:

```powershell
powershell -ExecutionPolicy Bypass -File site/scripts/render-demo-preview.ps1
```

Open `site/public/demo/numbers-slide.html` or the PNG to review projection-size
legibility. The HTML and SVG work offline; the PNG is the portable raster preview.

## Capture and encode the GIF once footage exists

Follow D3 **20-second GIF**, cut from the real shot 4 recording:

| Seconds | Footage and caption |
| --- | --- |
| 0–4 | Actual Morse reply in the inbox; decoded instruction beneath it |
| 4–8 | Actual proposed amount and `hostc0` receiver |
| 8–15 | Check log, one line at a time; only the recorded run's fired signals |
| 15–18 | `BLOCK`, `refused`, actual reason codes; “policy + counterparty agree, and Jev scored above the hold threshold” |
| 18–20 | “0 tUSDC moved”, verified unchanged Guardian balance, explorer link |

Keep captions legible at 1200 × 675. Include D3's run-variance disclosure:
“Jev's score varies between runs; this attempt scored above the hold threshold.”
Retain held attempts and their cancellation links in the capture notes. A
cancelled hold must never be presented as a checker block. Do not hide latency
edits; retain the uncut recording as evidence outside the public asset directory.

Use the five beats above to edit an actual 20-second cut with captions. Then,
with FFmpeg installed, encode that reviewed cut (replace the input path):

```powershell
ffmpeg -i shot4-cut.mp4 -filter_complex "[0:v]fps=15,scale=1200:675:force_original_aspect_ratio=decrease,pad=1200:675:(ow-iw)/2:(oh-ih)/2:color=0x15131D,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3" -t 20 -an -loop 0 site/public/demo/blocked-attack.gif
ffprobe -v error -show_entries format=duration,size:stream=width,height,avg_frame_rate,nb_frames -of json site/public/demo/blocked-attack.gif
```

Verify the encoded GIF is exactly 20 seconds, 1200 × 675, 300 frames at nominal
15 fps (GIF delays quantize to hundredths of a second), under 8 MB and loops
cleanly. Inspect all five beats visually alongside D3. If encoding changes the
duration, correct the final frame delay and check again. Do not mark E4 done
until this verification and the actual asset exist.

## Checks

```powershell
cd site
npm test
npm run build
```

Node tests cover format rejection, actual-row selection, count/percentage/unit
mapping, missing data, sample labels, external-set isolation and generated SVG
content. Generated assets include input hashes so later data or template changes
can be detected and regenerated together. Capture evidence and GIF verification
are still pending the source recording.

Observed on 2026-11-13: `npm test` passed all 41 tests (13 new E4 tests; existing
parallel Vite SSR tests printed a nonfatal WebSocket-port warning). `npm run
build` passed with Vite 5.4.21. The PNG was rendered with headless Edge at
1920 × 1080 and visually inspected: both headline values, the full secondary
metrics row, family outcomes, cap line, caveats and sources fit without clipping.
The SVG/HTML include the font license and make no external font request.
No GIF exists yet, so its duration, file size and five beats are not verified.
