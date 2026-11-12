import test, { after } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { familyRows, formatCalls, formatResultNumber, headline, mapResultsRows, redteamRow, validateResultsFormat } from "./results.js";

const example = JSON.parse(await readFile(new URL("../../schemas/examples/results.json", import.meta.url)));
const results = JSON.parse(await readFile(new URL("../../docs/results/results.json", import.meta.url)));
const redteam = JSON.parse(await readFile(new URL("../../docs/results/redteam-results.json", import.meta.url)));
const schema = JSON.parse(await readFile(new URL("../../schemas/results.schema.json", import.meta.url)));
// Compile the real JSX with the site's existing toolchain; keep node --test.
const server = await createServer({ configFile: false, esbuild: { jsx: "automatic" },
  server: { middlewareMode: true, watch: null }, appType: "custom" });
after(() => server.close());
const { ResultsSection } = await server.ssrLoadModule("/src/components/ResultsSection.jsx");

test("accepts the C1 example's frozen format", () => {
  assert.equal(example.format, schema.properties.format.const);
  assert.doesNotThrow(() => validateResultsFormat(example));
});

test("rejects missing, unknown and non-string formats before mapping rows", () => {
  for (const invalid of [null, undefined, {}, { format: "firewall.results.v2" }, { format: null }, { format: true }]) {
    assert.throws(() => validateResultsFormat(invalid), /Unsupported results format: expected firewall\.results\.v1/);
    assert.throws(() => mapResultsRows(invalid), /Unsupported results format/);
  }
});

test("maps every real configuration in source order with a README label", () => {
  const rows = mapResultsRows(results);
  assert.equal(rows.length, results.configurations.length);
  for (const [index, entry] of results.configurations.entries()) {
    assert.equal(rows[index].configuration, entry.configuration);
    assert.notEqual(rows[index].label, entry.configuration, `no label for ${entry.configuration}`);
    assert.equal(rows[index].missedAttacksPct, entry.missed_attacks_pct);
    assert.equal(rows[index].jevCalls, entry.jev_calls_per_payment ?? 0);
  }
});

test("headline, red-team and family numbers match the README Results section", () => {
  const { base, best } = headline(results);
  assert.deepEqual([base.missed_attacks_pct, best.missed_attacks_pct, best.false_blocks_pct, best.false_holds_pct], [100, 19.33, 0, 5.33]);
  assert.deepEqual(redteamRow(redteam), { total: 17, missedPct: 41.18, missed: 7, held: 7, blocked: 3, medianMs: 1137.9 });
  const missed = Object.fromEntries(familyRows(results).map((f) => [f.family, f.total - f.caught]));
  assert.deepEqual(missed, { direct_injection: 1, encoded_injection: 2, indirect_injection: 1, lookalike_receiver: 2, fake_invoice: 12, memory_poisoning: 12 });
});

test("calls per payment replace the unpriced cost column", () => {
  assert.equal(formatCalls({ jevCalls: 0, classifierCalls: 0 }), "0 calls");
  assert.equal(formatCalls({ jevCalls: 1, classifierCalls: 1 }), "1 Jev call + 1 classifier call");
  assert.equal(formatCalls({ jevCalls: 1, classifierCalls: 0.34 }), "1 Jev call + 0.34 classifier calls");
});

test("renders the real results with all rows, units and caveats, and no sample label", () => {
  const html = renderToStaticMarkup(React.createElement(ResultsSection));
  for (const entry of results.configurations) assert.ok(html.includes(entry.configuration), entry.configuration);
  for (const label of ["False holds (%)", "False blocks (%)", "Missed attacks (%)", "Median latency (ms)", "Per payment",
    "19.33%", "exchangeability", "in-sample", "six evaluated attack families", "Not built (cut list)", "docs/results/results.json"]) {
    assert.ok(html.includes(label), `Missing ${label}`);
  }
  assert.doesNotMatch(html, /Sample data|Cost per payment|Numbers land after/);
});

test("renders one SVG with two data-driven bars per configuration and labelled axes", () => {
  const html = renderToStaticMarkup(React.createElement(ResultsSection));
  assert.equal((html.match(/<svg /g) ?? []).length, 1);
  assert.equal((html.match(/<rect /g) ?? []).length, results.configurations.length * 2);
  assert.ok(html.includes("Rate (%)"));
  for (const entry of results.configurations) {
    for (const [field, label] of [["missed_attacks_pct", "Missed attacks"], ["false_blocks_pct", "False blocks"]]) {
      assert.ok(html.includes(`<title>${entry.configuration}: ${label} ${formatResultNumber(entry[field])}%</title>`));
    }
  }
});
