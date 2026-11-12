import test, { after } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { formatResultNumber, mapResultsRows, validateResultsFormat } from "./results.js";

const example = JSON.parse(await readFile(new URL("../../schemas/examples/results.json", import.meta.url)));
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

test("maps every C1 configuration in source order without substituting summary metrics", () => {
  const rows = mapResultsRows(example);
  assert.equal(rows.length, example.configurations.length);
  for (const [index, entry] of example.configurations.entries()) {
    assert.deepEqual(rows[index], {
      configuration: entry.configuration,
      description: entry.description,
      falseHoldsPct: entry.false_holds_pct,
      falseBlocksPct: entry.false_blocks_pct,
      missedAttacksPct: entry.missed_attacks_pct,
      medianLatencyMs: entry.median_latency_ms,
      costPerPaymentUsd: entry.cost_per_payment_usd,
    });
  }
  const reversed = { ...example, configurations: example.configurations.toReversed() };
  assert.deepEqual(mapResultsRows(reversed), rows.toReversed());
});

test("optional description and cost remain absent rather than borrowing aggregate cost", () => {
  const { description, cost_per_payment_usd, ...entry } = example.configurations.at(-1);
  const [row] = mapResultsRows({ ...example, configurations: [entry] });
  assert.equal(row.description, "");
  assert.equal(row.costPerPaymentUsd, null);
  assert.equal(formatResultNumber(row.costPerPaymentUsd), "Not reported");
  const zeroCost = example.configurations.find((item) => item.cost_per_payment_usd === 0);
  assert.equal(mapResultsRows({ ...example, configurations: [zeroCost] })[0].costPerPaymentUsd, zeroCost.cost_per_payment_usd);
});

test("renders the imported example with all rows, descriptions, units and sample caveats", () => {
  const html = renderToStaticMarkup(React.createElement(ResultsSection));
  const body = html.match(/<tbody>(.*?)<\/tbody>/s)[1];
  const rows = [...body.matchAll(/<tr>(.*?)<\/tr>/gs)];
  assert.equal(rows.length, example.configurations.length);
  for (const [index, entry] of example.configurations.entries()) {
    assert.ok(rows[index][1].includes(entry.configuration));
    assert.ok(rows[index][1].includes(entry.description));
    const cells = [...rows[index][1].matchAll(/<td class="num">(.*?)<\/td>/g)].map((match) => match[1]);
    assert.deepEqual(cells, [entry.false_holds_pct, entry.false_blocks_pct, entry.missed_attacks_pct,
      entry.median_latency_ms, entry.cost_per_payment_usd].map(formatResultNumber));
  }
  for (const label of ["Sample data", "False holds (%)", "False blocks (%)", "Missed attacks (%)",
    "Median latency (ms)", "Cost per payment (USD)", "calibration history (exchangeability)", "known attack families"]) {
    assert.ok(html.includes(label), `Missing ${label}`);
  }
  assert.doesNotMatch(html, /unseen-family row|Numbers land after/);
});

test("renders one SVG with two data-driven bars per configuration and labelled axes", () => {
  const html = renderToStaticMarkup(React.createElement(ResultsSection));
  assert.equal((html.match(/<svg /g) ?? []).length, 1);
  assert.equal((html.match(/<rect /g) ?? []).length, example.configurations.length * 2);
  assert.ok(html.includes("Rate (%)"));
  assert.ok(html.includes("Configuration</text>"));
  for (const entry of example.configurations) {
    for (const [field, label] of [["missed_attacks_pct", "Missed attacks"], ["false_blocks_pct", "False blocks"]]) {
      assert.ok(html.includes(`<title>${entry.configuration}: ${label} ${formatResultNumber(entry[field])}%</title>`));
    }
  }
});
