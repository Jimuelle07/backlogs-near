# E4 demo assets

Owner: Ace. Branch: `feat/e4-demo-assets`, from `origin/main` after D3 approval
and merge (PR #26; numbers refreshed in PR #28). E4 remains **in progress** until
both the slide and the README GIF are saved and reviewed.

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

## README GIF

Jim's decision of 2026-11-14 ([D3 README GIF](demo-storyboard.md#readme-gif)):
the README GIF is a 15-second motion-graphics animation, not a cut of the shot 4
screen recording, and no longer waits on A8. It animates testnet receipts #7
(the Morse attack, `block`, `refused`) and #6 (the hosting invoice, `allow`,
`paid`) from the [OutLayer run of 2026-11-13](sdd.md#outlayer-run-with-jev-2026-11-13);
the request, Morse text and proposed tool call come from
`agent/scenarios/attack-morse-lookalike.json`. The asset is
`site/public/demo/eclipse-demo.gif`, rendered from the Remotion composition
`ReadmeDemo`. Regenerate it from `video/` (frames in `video/out/`, gitignored):

```powershell
npx remotion render ReadmeDemo out/readme-demo-frames --sequence --image-format=png --image-sequence-pattern="f_[frame].[ext]"
ffmpeg -y -framerate 25 -start_number 0 -i out/readme-demo-frames/f_%03d.png -vf "scale=1200:675:flags=lanczos,palettegen=max_colors=256:stats_mode=full" out/readme-demo-palette.png
ffmpeg -y -framerate 25 -start_number 0 -i out/readme-demo-frames/f_%03d.png -i out/readme-demo-palette.png -lavfi "scale=1200:675:flags=lanczos[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle" -loop 0 ../site/public/demo/eclipse-demo.gif
```

Observed on 2026-11-14: `ffprobe` on `site/public/demo/eclipse-demo.gif` reports
width 1200, height 675, 375 frames at `25/1`, duration 15.000000 s and
2,621,981 bytes (under 8 MB); `cmp out/readme-demo-frames/f_000.png
out/readme-demo-frames/f_374.png` printed nothing, so the first and last frames
are identical and the GIF loops. Twelve stills of the final render (frames
000, 050, 100, 126, 148, 200, 216, 221, 260, 300, 325, 360) were inspected.

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

## Checks

```powershell
cd site
npm test
npm run build
```

Node tests cover format rejection, actual-row selection, count/percentage/unit
mapping, missing data, sample labels, external-set isolation and generated SVG
content. Generated assets include input hashes so later data or template changes
can be detected and regenerated together.

Observed on 2026-11-13: `npm test` passed all 41 tests (13 new E4 tests; existing
parallel Vite SSR tests printed a nonfatal WebSocket-port warning). `npm run
build` passed with Vite 5.4.21. The PNG was rendered with headless Edge at
1920 × 1080 and visually inspected: both headline values, the full secondary
metrics row, family outcomes, cap line, caveats and sources fit without clipping.
The SVG/HTML include the font license and make no external font request.
