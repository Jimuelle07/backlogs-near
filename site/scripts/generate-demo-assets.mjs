import { readFile, mkdir, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { mapSlideMetrics } from "../src/demo-assets.js";
import { validateResultsFormat } from "../src/results.js";
import { PROJECT_NAME } from "../src/config.js";
import { renderNumbersSlide, renderSlideHtml } from "./demo-assets/numbers-slide.js";

const root = fileURLToPath(new URL("../../", import.meta.url));
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const textHash = (bytes) => hash(bytes.toString().replaceAll("\r\n", "\n"));

export async function loadResultsSource(primary, fallback, forceSample = false) {
  let path = forceSample ? fallback : primary;
  let bytes;
  try { bytes = await readFile(path); } catch (error) {
    if (forceSample || error.code !== "ENOENT") throw error;
    path = fallback;
    bytes = await readFile(path);
  }
  const results = JSON.parse(bytes);
  validateResultsFormat(results);
  return { results, path, bytes, sample: path === fallback };
}

export function extractContractCaps(source) {
  const get = (name) => {
    const match = source.match(new RegExp(`pub const ${name}: u128 = ([\\d_]+);`));
    const value = match ? Number(match[1].replaceAll("_", "")) : NaN;
    if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`Missing or invalid Rust constant ${name}`);
    return value;
  };
  return { perPayment: get("PER_PAYMENT_CAP_WHOLE"), perDay: get("DAILY_CAP_WHOLE") };
}

export function extractBrandTokens(css) {
  return Object.fromEntries(["ground", "surface", "line", "text", "muted", "accent", "alarm"].map((name) => {
    const value = css.match(new RegExp(`--${name}:\\s*(#[a-fA-F0-9]{6})\\s*;`))?.[1];
    if (!value) throw new Error(`Missing site brand token --${name}`);
    return [name, value];
  }));
}

export async function generateDemoAssets({ sample = false, output = resolve(root, "site/public/demo") } = {}) {
  const source = await loadResultsSource(resolve(root, "docs/results/results.json"), resolve(root, "schemas/examples/results.json"), sample);
  const sources = {};
  const input = async (path) => {
    const bytes = await readFile(resolve(root, path));
    sources[path] = { sha256: path.endsWith(".ttf") ? hash(bytes) : textHash(bytes) };
    return bytes;
  };
  const mainPath = source.sample ? "schemas/examples/results.json" : "docs/results/results.json";
  sources[mainPath] = { sha256: textHash(source.bytes) };
  const external = source.sample ? null : JSON.parse(await input("docs/results/external-results.json"));
  const caps = extractContractCaps((await input("contract/guardian/src/lib.rs")).toString());
  const tokens = extractBrandTokens((await input("site/src/styles.css")).toString());
  const fonts = {
    regular: (await input("site/scripts/demo-assets/fonts/Geist-Regular.ttf")).toString("base64"),
    medium: (await input("site/scripts/demo-assets/fonts/Geist-Medium.ttf")).toString("base64"),
  };
  fonts.license = (await input("site/scripts/demo-assets/fonts/OFL.txt")).toString();
  for (const path of ["site/src/config.js", "site/src/results.js", "site/src/demo-assets.js", "site/scripts/generate-demo-assets.mjs", "site/scripts/demo-assets/numbers-slide.js", "docs/build/demo-storyboard.md"]) await input(path);
  const metrics = mapSlideMetrics(source.results, { external, sample: source.sample, caps });
  const manifest = {
    mainSource: mainPath,
    externalSource: source.sample ? null : "docs/results/external-results.json",
    hashEncoding: "SHA-256 of UTF-8 text with LF line endings; TTF fonts hashed as binary bytes",
    sources,
    selections: {
      headline: `configurations.${metrics.mainConfiguration}`,
      baseline: `configurations.${metrics.baselineConfiguration}`,
      families: metrics.families ? "by_family (final preset: jev_fusion_conformal_cascade)" : null,
      target: "caveats: epsilon percentage (not unseen_family_rotation)",
      caps: "Rust PER_PAYMENT_CAP_WHOLE and DAILY_CAP_WHOLE; whole tUSDC limits, not evaluation metrics",
      latency: "configurations.jev_fusion_conformal.median_latency_ms / 1000; seconds, rounded to 3 decimals",
    },
    metrics,
  };
  const data = `${JSON.stringify(manifest, null, 2)}\n`;
  // Render from the same JSON snapshot saved beside the slide.
  const snapshot = JSON.parse(data);
  const sourceLabel = source.sample ? "Sample data · schemas/examples/results.json · contract caps · provenance: numbers-slide.data.json" : "Sources: docs/results/results.json + external-results.json · contract caps · provenance: numbers-slide.data.json";
  const svg = renderNumbersSlide(snapshot.metrics, { tokens, fonts, projectName: PROJECT_NAME, sourceLabel });
  await mkdir(output, { recursive: true });
  await writeFile(resolve(output, "numbers-slide.data.json"), data);
  await writeFile(resolve(output, "numbers-slide.svg"), svg);
  await writeFile(resolve(output, "numbers-slide.html"), renderSlideHtml(svg));
  return { source: mainPath, sample: source.sample, output };
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  try {
    const args = process.argv.slice(2);
    if (args.some((arg) => arg !== "--sample")) throw new Error("Usage: node site/scripts/generate-demo-assets.mjs [--sample]");
    console.log(JSON.stringify(await generateDemoAssets({ sample: args.includes("--sample") }), null, 2));
  } catch (error) {
    console.error(`E4 asset generation failed: ${error.message}`);
    process.exitCode = 1;
  }
}
