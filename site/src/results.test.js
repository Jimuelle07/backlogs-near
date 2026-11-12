import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { familyRows, headline, jevCalls, ms, pct, redteamRow, resultRows } from "./results.js";

const read = (name) => JSON.parse(readFileSync(new URL(`../../docs/results/${name}`, import.meta.url), "utf8"));
const results = read("results.json");
const redteam = read("redteam-results.json");

test("every configuration in results.json becomes a row with a README label", () => {
  const rows = resultRows(results);
  assert.equal(rows.length, results.configurations.length);
  for (const row of rows) assert.notEqual(row.label, row.key, `no label for ${row.key}`);
  const conformal = rows.find((r) => r.key === "jev_fusion_conformal");
  assert.deepEqual([conformal.falseHolds, conformal.falseBlocks, conformal.missed], [4.67, 0, 20.67]);
});

test("headline compares no defense with the conformal row", () => {
  const { base, best } = headline(results);
  assert.equal(base.missed_attacks_pct, 100);
  assert.equal(best.missed_attacks_pct, 20.67);
});

test("family rows cover six families and match the README percentages", () => {
  const rows = familyRows(results);
  assert.equal(rows.length, 6);
  assert.deepEqual(rows.map((r) => r.detectedPct), [96, 92, 96, 48, 92, 52]);
});

test("red-team row matches the README", () => {
  assert.deepEqual(redteamRow(redteam), { total: 17, missed: 52.94, allowed: 9, held: 7, blocked: 1, medianMs: 418.421 });
});

test("formatting", () => {
  assert.equal(pct(20.67), "20.67%");
  assert.equal(pct(0), "0%");
  assert.equal(ms(402.756), "402.8 ms");
  assert.equal(jevCalls(1), "1 Jev call");
  assert.equal(jevCalls(0), "0 calls");
});
