import test from "node:test";
import assert from "node:assert/strict";
import { readFile, mkdtemp, writeFile, rm } from "node:fs/promises";
import { join, dirname, resolve } from "node:path";
import { tmpdir } from "node:os";
import { createHash } from "node:crypto";
import { mapSlideMetrics } from "./demo-assets.js";
import { extractBrandTokens, extractContractCaps, generateDemoAssets, loadResultsSource } from "../scripts/generate-demo-assets.mjs";

const load = async (path) => JSON.parse(await readFile(new URL(path, import.meta.url)));
const results = await load("../../docs/results/results.json");
const external = await load("../../docs/results/external-results.json");
const sample = await load("../../schemas/examples/results.json");
const contract = await readFile(new URL("../../contract/guardian/src/lib.rs", import.meta.url), "utf8");
const caps = extractContractCaps(contract);
const options = { external, caps };
const clone = (value) => structuredClone(value);
const mainRow = (data) => data.configurations.find((r) => r.configuration === "jev_fusion_conformal");

async function temp(t) {
  const directory = await mkdtemp(join(tmpdir(), "backlogs-e4-test-"));
  t.after(async () => {
    assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
    assert.ok(directory.split(/[\\/]/).at(-1).startsWith("backlogs-e4-test-"));
    await rm(directory, { recursive: true });
  });
  return directory;
}

test("maps the exact conformal preset and no-defense baseline, not the final summary", () => {
  const metrics = mapSlideMetrics(results, options);
  const row = mainRow(results);
  assert.equal(metrics.missedPct, row.missed_attacks_pct);
  assert.equal(metrics.falseHoldsPct, row.false_holds_pct);
  assert.equal(metrics.falseBlocksPct, row.false_blocks_pct);
  assert.equal(metrics.falseHolds, row.false_holds);
  assert.equal(metrics.benign, results.benign_total);
  assert.equal(metrics.baselineMissedPct, results.configurations.find((r) => r.configuration === "no_defense").missed_attacks_pct);
  const altered = clone(results);
  altered.summary = { missed_attacks_pct: 99, false_blocks_pct: 88, false_holds_pct: 77 };
  altered.configurations.reverse();
  assert.deepEqual(mapSlideMetrics(altered, options), metrics);
});

test("maps measured latency in seconds, calls and the JSON target, without a cost value", () => {
  const metrics = mapSlideMetrics(results, options);
  const row = mainRow(results);
  assert.equal(metrics.medianSeconds, row.median_latency_ms / 1000);
  assert.equal(metrics.jevCalls, row.jev_calls_per_payment);
  assert.equal(metrics.classifierCalls, row.classifier_calls_per_payment);
  assert.ok(results.caveats.some((c) => c.includes(`epsilon = ${metrics.targetPct}%`)));
  assert.equal(metrics.targetRelation, "above");
  assert.equal(Object.hasOwn(metrics, "costPerPaymentUsd"), false);
});

test("uses the external conformal row rather than its summary or main outcomes", () => {
  const altered = clone(external);
  altered.summary = {};
  const metrics = mapSlideMetrics(results, { caps, external: altered });
  const row = mainRow(external);
  assert.deepEqual(metrics.heldOut, {
    benign: external.benign_total, attack: external.attack_total,
    missedPct: row.missed_attacks_pct, falseHoldsPct: row.false_holds_pct, falseBlocksPct: row.false_blocks_pct,
  });
});

test("family caught counts come from final cascade outcomes, never rotation", () => {
  const altered = clone(results);
  altered.unseen_family_rotation = [{ family: "invented", detected: 9999 }];
  const metrics = mapSlideMetrics(altered, options);
  for (const family of metrics.families) {
    const raw = results.by_family[family.family];
    assert.equal(family.caught, raw.hold + raw.block);
    assert.equal(family.total, raw.total);
  }
  assert.deepEqual(metrics.families.slice(0, 2).map((f) => f.family).sort(), ["fake_invoice", "memory_poisoning"]);
  assert.ok(metrics.families.every((f) => f.family !== "none"));
});

test("updates values from changed JSON instead of freezing the current measurements", () => {
  const altered = clone(results);
  const row = mainRow(altered);
  row.missed_attacks = 15; row.missed_attacks_pct = 10;
  row.false_holds = 0; row.false_holds_pct = 0;
  row.median_latency_ms = 2500;
  row.jev_calls_per_payment = 2;
  const metrics = mapSlideMetrics(altered, options);
  assert.equal(metrics.missedPct, 10);
  assert.equal(metrics.falseHoldsPct, 0);
  assert.equal(metrics.targetRelation, "below");
  assert.equal(metrics.medianSeconds, 2.5);
  assert.equal(metrics.jevCalls, 2);
});

test("rejects unsupported main and external formats before reading metrics", () => {
  for (const invalid of [null, {}, { format: null }, { format: "firewall.results.v2" }, { format: true }]) {
    assert.throws(() => mapSlideMetrics(invalid, options), /Unsupported results format/);
    assert.throws(() => mapSlideMetrics(results, { caps, external: invalid }), /Unsupported results format/);
  }
});

test("rejects missing or duplicate presets and absent required measured fields", () => {
  for (const key of ["no_defense", "jev_fusion_conformal", "jev_fusion_conformal_cascade"]) {
    const altered = clone(results);
    altered.configurations = altered.configurations.filter((r) => r.configuration !== key);
    assert.throws(() => mapSlideMetrics(altered, options), /Expected exactly one/);
  }
  const duplicate = clone(results);
  duplicate.configurations.push(mainRow(duplicate));
  assert.throws(() => mapSlideMetrics(duplicate, options), /Expected exactly one/);
  for (const key of ["missed_attacks_pct", "false_holds_pct", "false_blocks_pct", "false_holds", "median_latency_ms", "jev_calls_per_payment", "classifier_calls_per_payment"]) {
    const altered = clone(results);
    delete mainRow(altered)[key];
    assert.throws(() => mapSlideMetrics(altered, options), /Invalid or missing/);
  }
});

test("rejects inconsistent counts, invalid families, and missing or conflicting targets", () => {
  const inconsistent = clone(results);
  mainRow(inconsistent).false_holds = results.benign_total;
  assert.throws(() => mapSlideMetrics(inconsistent, options), /Inconsistent/);
  const badFamily = clone(results);
  badFamily.by_family.fake_invoice.hold = 999;
  assert.throws(() => mapSlideMetrics(badFamily, options), /Invalid/);
  const missingFamily = clone(results);
  delete missingFamily.by_family.fake_invoice;
  assert.throws(() => mapSlideMetrics(missingFamily, options), /Incomplete cascade/);
  assert.throws(() => mapSlideMetrics({ ...results, caveats: [] }, options), /epsilon target/);
  assert.throws(() => mapSlideMetrics({ ...results, caveats: ["epsilon = 1%", "epsilon = 2%"] }, options), /epsilon target/);
});

test("sample mode uses the sample baseline and never borrows real external metrics", () => {
  const metrics = mapSlideMetrics(sample, { external, sample: true, caps });
  assert.equal(metrics.sample, true);
  assert.equal(metrics.baselineConfiguration, "stub_allow");
  assert.equal(metrics.missedPct, mainRow(sample).missed_attacks_pct);
  assert.equal(metrics.heldOut, null);
  assert.equal(metrics.families, null);
  assert.throws(() => mapSlideMetrics(sample, options), /no_defense/);
});

test("extracts cap limits from Rust and brand colors from the existing stylesheet", async () => {
  const css = await readFile(new URL("./styles.css", import.meta.url), "utf8");
  const tokens = extractBrandTokens(css);
  assert.equal(tokens.ground.toLowerCase(), "#15131d");
  assert.equal(tokens.accent.toLowerCase(), "#edb1e8");
  assert.throws(() => extractBrandTokens(""), /Missing site brand token/);
  const changed = contract.replace(/PER_PAYMENT_CAP_WHOLE: u128 = [\d_]+;/, "PER_PAYMENT_CAP_WHOLE: u128 = 123;");
  assert.equal(extractContractCaps(changed).perPayment, 123);
  assert.throws(() => extractContractCaps(""), /Missing or invalid Rust constant/);
  assert.throws(() => mapSlideMetrics(results, { external, caps: { perPayment: 999, perDay: 1 } }), /Invalid contract cap/);
});

test("falls back only on an absent real file and labels the selected source", async (t) => {
  const directory = await temp(t);
  const primary = join(directory, "results.json");
  const fallback = join(directory, "sample.json");
  await writeFile(fallback, JSON.stringify(sample));
  assert.equal((await loadResultsSource(primary, fallback)).sample, true);
  await writeFile(primary, JSON.stringify(results));
  assert.equal((await loadResultsSource(primary, fallback)).sample, false);
  assert.equal((await loadResultsSource(primary, fallback, true)).sample, true);
  await writeFile(primary, JSON.stringify({ format: "firewall.results.v2" }));
  await assert.rejects(loadResultsSource(primary, fallback), /Unsupported results format/);
  await writeFile(primary, "{");
  await assert.rejects(loadResultsSource(primary, fallback), SyntaxError);
});

test("generates portable slide sources and provenance from the same measured JSON", async (t) => {
  const directory = await temp(t);
  await generateDemoAssets({ output: directory });
  const manifest = JSON.parse(await readFile(join(directory, "numbers-slide.data.json")));
  const svg = await readFile(join(directory, "numbers-slide.svg"), "utf8");
  const html = await readFile(join(directory, "numbers-slide.html"), "utf8");
  assert.equal(manifest.mainSource, "docs/results/results.json");
  assert.equal(manifest.metrics.missedPct, mainRow(results).missed_attacks_pct);
  assert.equal(manifest.metrics.falseBlocksPct, mainRow(results).false_blocks_pct);
  for (const input of ["docs/results/results.json", "docs/results/external-results.json", "contract/guardian/src/lib.rs", "site/src/styles.css"]) {
    assert.match(manifest.sources[input].sha256, /^[a-f0-9]{64}$/);
    const text = await readFile(new URL(`../../${input}`, import.meta.url), "utf8");
    assert.equal(manifest.sources[input].sha256, createHash("sha256").update(text.replaceAll("\r\n", "\n")).digest("hex"));
  }
  for (const phrase of ["MISSED ATTACKS", "FALSE BLOCKS", "in-sample", "above the", "HELD-OUT", "known attack families", "calibration history", "Cost unpriced", "s</text>", "tUSDC per payment", "SIL OPEN FONT LICENSE", "data:font/ttf;base64"]) assert.ok(svg.includes(phrase), phrase);
  assert.ok(html.includes(svg));
  assert.doesNotMatch(svg, /Sample data|MELON|\$0|19\.33%.*held-out/i);
  assert.doesNotMatch(svg, /(?:href|src)="https?:/);
});

test("sample output is visibly labelled and omits real external results", async (t) => {
  const directory = await temp(t);
  await generateDemoAssets({ sample: true, output: directory });
  const manifest = JSON.parse(await readFile(join(directory, "numbers-slide.data.json")));
  const svg = await readFile(join(directory, "numbers-slide.svg"), "utf8");
  assert.equal(manifest.mainSource, "schemas/examples/results.json");
  assert.equal(manifest.externalSource, null);
  assert.equal(manifest.metrics.sample, true);
  assert.ok(svg.includes("Sample data"));
  assert.ok(svg.includes("Not supplied for sample data"));
  assert.equal(Object.hasOwn(manifest.sources, "docs/results/external-results.json"), false);
});
