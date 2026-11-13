import test, { after } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "vite";

const server = await createServer({ configFile: false, esbuild: { jsx: "automatic" },
  server: { middlewareMode: true, watch: null }, appType: "custom", logLevel: "error" });
after(() => server.close());
const { SITE_URL } = await server.ssrLoadModule("/src/config.js");
const { FAQ, faqJsonLd } = await server.ssrLoadModule("/src/faq.js");
const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
const results = JSON.parse(await readFile(new URL("../../docs/results/results.json", import.meta.url), "utf8"));

test("canonical and social URLs in index.html match SITE_URL", () => {
  assert.match(SITE_URL, /^https:\/\/.+\/$/);
  for (const tag of [`<link rel="canonical" href="${SITE_URL}"`, `property="og:url" content="${SITE_URL}"`,
    `property="og:image" content="${SITE_URL}og.png"`, `name="twitter:image" content="${SITE_URL}og.png"`]) {
    assert.ok(html.includes(tag), `missing ${tag}`);
  }
});

test("title and description stay within search-result lengths", () => {
  const title = html.match(/<title>(.*?)<\/title>/)[1];
  const description = html.match(/<meta name="description" content="(.*?)"/)[1];
  assert.ok(title.length <= 60, `title is ${title.length} chars`);
  assert.ok(description.length >= 70 && description.length <= 170, `description is ${description.length} chars`);
});

test("FAQ answers are complete and quote the committed results", () => {
  assert.ok(FAQ.length >= 6);
  for (const { q, a } of FAQ) {
    assert.ok(q.endsWith("?"), q);
    assert.ok(a.length > 40 && a.length < 700, `${q}: ${a.length} chars`);
  }
  const conformal = results.configurations.find((c) => c.configuration === "jev_fusion_conformal");
  const answer = FAQ.find(({ q }) => q === "How well does it work?").a;
  assert.ok(answer.includes(`${conformal.missed_attacks_pct}%`) && answer.includes(`${conformal.false_holds_pct}%`));
  assert.match(answer, /in-sample/);
});

test("FAQPage structured data mirrors the visible FAQ", () => {
  const ld = faqJsonLd();
  assert.equal(ld["@type"], "FAQPage");
  assert.deepEqual(ld.mainEntity.map((e) => [e.name, e.acceptedAnswer.text]), FAQ.map(({ q, a }) => [q, a]));
});
