// Post-build step (npm run build): prerender the page into dist/index.html so crawlers and AI
// answer engines that do not run JavaScript read the full content, then write the JSON-LD,
// sitemap.xml, robots.txt and llms.txt from the same config and data the page renders.
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToString } from "react-dom/server";
import { createServer } from "vite";

const root = fileURLToPath(new URL("..", import.meta.url));
const dist = (name) => new URL(`../dist/${name}`, import.meta.url);

const server = await createServer({
  root, configFile: false, logLevel: "error", appType: "custom",
  esbuild: { jsx: "automatic" }, server: { middlewareMode: true, watch: null, hmr: false },
});

try {
  const { default: App } = await server.ssrLoadModule("/src/App.jsx");
  const config = await server.ssrLoadModule("/src/config.js");
  const { FAQ, faqJsonLd } = await server.ssrLoadModule("/src/faq.js");
  const { headline } = await server.ssrLoadModule("/src/results.js");
  const results = JSON.parse(await readFile(new URL("../../docs/results/results.json", import.meta.url), "utf8"));

  const { SITE_URL, PROJECT_NAME, PROJECT_TAGLINE, PER_PAYMENT_CAP, DAILY_CAP, GUARDIAN_ID, REPO_URL } = config;
  const description = "Payment firewall for AI agents on NEAR: a Guardian contract holds the funds, an off-host checker stops prompt-injection payments, and every verdict leaves an on-chain receipt.";

  // 1. Static HTML of the page, hydrated by src/main.jsx.
  const html = renderToString(React.createElement(App));
  const template = await readFile(dist("index.html"), "utf8");
  if (!template.includes('<div id="root"></div>')) throw new Error("dist/index.html has no empty #root to fill");

  // 2. Structured data: what the site and the software are, plus the visible FAQ.
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "WebSite", "@id": `${SITE_URL}#website`, url: SITE_URL, name: PROJECT_NAME, description, inLanguage: "en" },
      {
        "@type": "SoftwareApplication",
        "@id": `${SITE_URL}#software`,
        name: PROJECT_NAME,
        alternateName: "Eclipse payment firewall",
        description,
        url: SITE_URL,
        applicationCategory: "SecurityApplication",
        operatingSystem: "NEAR testnet (Guardian contract); Linux, macOS, Windows (checker and agent)",
        license: "https://opensource.org/licenses/MIT",
        isAccessibleForFree: true,
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        ...(REPO_URL ? { codeRepository: REPO_URL } : {}),
        keywords: ["AI agent payments", "prompt injection", "payment firewall", "NEAR Protocol", "smart contract", "agent wallet security", "TypeSafe Jev", "OutLayer TEE"],
        featureList: [
          "Agent holds only a function-call key scoped to request_payment",
          "Guardian contract holds the funds and pays only on an exact receiver, token, amount and request id match",
          "Off-host checker: policy rules, injection classifier, counterparty and lookalike signals",
          "TypeSafe Jev fuses the signals into allow, hold or block, with no human step",
          `Hard caps in contract code: ${PER_PAYMENT_CAP} tUSDC per payment, ${DAILY_CAP} tUSDC per UTC day`,
          "On-chain receipt for every payment: outcome, reason codes, input and record hashes, checker version",
        ],
        isPartOf: { "@id": `${SITE_URL}#website` },
      },
      { ...faqJsonLd(), "@id": `${SITE_URL}#faq`, url: `${SITE_URL}#faq` },
    ],
  };
  const ld = `<script type="application/ld+json">${JSON.stringify(jsonLd).replace(/</g, "\\u003c")}</script>`;
  await writeFile(dist("index.html"), template.replace('<div id="root"></div>', `<div id="root">${html}</div>`).replace("</head>", `    ${ld}\n  </head>`));

  // 3. Crawl files.
  const today = new Date().toISOString().slice(0, 10);
  await writeFile(dist("sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${SITE_URL}</loc><lastmod>${today}</lastmod></url>
</urlset>
`);
  await writeFile(dist("robots.txt"), `# Everyone, search and AI crawlers included, may read the whole site.
User-agent: *
Allow: /

Sitemap: ${new URL("sitemap.xml", SITE_URL)}
`);

  // 4. llms.txt: a plain-text brief for LLMs and answer engines (https://llmstxt.org).
  const top = headline(results);
  const pct = (n) => `${Number(n.toFixed(2))}%`;
  await writeFile(dist("llms.txt"), `# ${PROJECT_NAME}

> ${PROJECT_NAME} is a payment firewall for AI agents on NEAR. ${PROJECT_TAGLINE} The agent can only ask a Guardian contract for a payment; the contract holds the funds and pays only after an off-host checker returns allow. Every verdict leaves an on-chain receipt. NEAR HACKATHON 2026 build, NEAR testnet, MIT licence.

## Key facts

- Problem: prompt injection can make an AI agent pay an attacker, and guardrails on the agent's own host can be skipped by a compromised agent.
- Custody: the Guardian contract (${GUARDIAN_ID}) holds a mock tUSDC token (NEP-141, 6 decimals). The agent account has only a function-call key limited to request_payment.
- Decision: a checker runs policy rules, an injection classifier and counterparty signals; TypeSafe Jev fuses them into allow, hold or block, with no human step. The checker runs on OutLayer (Intel TDX TEE).
- Safety: the verdict binds receiver, token, exact amount and a one-time request id. No AI decides an amount. Hard caps in contract code: ${PER_PAYMENT_CAP} tUSDC per payment, ${DAILY_CAP} tUSDC per UTC day.
- Results (${results.benign_total} benign, ${results.attack_total} attack payments, six attack families): ${top ? `missed attacks ${pct(top.best.missed_attacks_pct)} vs ${pct(top.base.missed_attacks_pct)} with no defense; false blocks ${pct(top.best.false_blocks_pct)}; false holds ${pct(top.best.false_holds_pct)} (in-sample, above the 5% target)` : "see the site"}.
- Not built: the masked re-run (MELON) and a re-check during the hold window.

## FAQ

${FAQ.map(({ q, a }) => `### ${q}\n\n${a}`).join("\n\n")}

## Links

- [Site](${SITE_URL})
- [How it works](${SITE_URL}#how)
- [Results](${SITE_URL}#results)
- [Live testnet receipts](${SITE_URL}#receipts)
- [Guardian contract on NearBlocks](https://testnet.nearblocks.io/address/${GUARDIAN_ID})
${REPO_URL ? `- [Source code](${REPO_URL})\n` : ""}`);

  console.log(`prerendered ${(html.length / 1024).toFixed(1)} kB of HTML; wrote sitemap.xml, robots.txt, llms.txt`);
} finally {
  await server.close();
}
process.exit(0);
