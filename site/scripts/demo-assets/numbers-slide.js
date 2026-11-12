const fmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 });
const n = (value) => fmt.format(value);
const xml = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[c]);

export function renderNumbersSlide(m, { tokens, fonts, projectName, sourceLabel }) {
  const t = (x, y, text, size = 28, fill = tokens.text, weight = 400, extra = "") =>
    `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" font-weight="${weight}" ${extra}>${xml(text)}</text>`;
  const label = (x, y, text) => t(x, y, text, 22, tokens.muted, 500, 'letter-spacing="1.6"');
  const line = (x1, y1, x2, y2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${tokens.line}"/>`;
  const weakest = m.families?.slice(0, 2);
  const others = m.families?.slice(2);
  // Compare rates rather than raw counts in case a future dataset changes family sizes.
  const othersText = others?.map((f) => `${f.label.toLowerCase()} ${n(f.caught)}/${n(f.total)}`).join(" · ");
  const external = m.heldOut;
  const familyCount = m.families?.length;
  const caveat = familyCount ? `Detection covers ${n(familyCount)} known attack families.` : "Detection covers the known attack families in the sample.";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-labelledby="title desc">
<title id="title">${xml(projectName)} — payment firewall evaluation${m.sample ? " — Sample data" : ""}</title>
<desc id="desc">Conformal evaluation compared with no defense. Only the external check is held-out. Main false holds are in-sample. ${xml(sourceLabel)}</desc>
<metadata>${xml(fonts.license)}</metadata>
<defs><style>
@font-face{font-family:Geist;src:url(data:font/ttf;base64,${fonts.regular}) format('truetype');font-weight:400}
@font-face{font-family:Geist;src:url(data:font/ttf;base64,${fonts.medium}) format('truetype');font-weight:500}
text{font-family:Geist,system-ui,sans-serif}
</style><pattern id="grid" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.6" fill="${tokens.line}"/></pattern></defs>
<rect width="1920" height="1080" fill="${tokens.ground}"/>
<rect x="1340" width="580" height="470" fill="url(#grid)" opacity="0.45"/>
${t(88, 74, projectName, 32, tokens.accent, 500)}
${t(1818, 74, m.sample ? "Sample data" : "Committed evaluation", 24, tokens.accent, 500, 'text-anchor="end"')}
${t(88, 139, "Payment firewall · evaluation results", 48, tokens.text, 500)}
${t(90, 177, `${n(m.benign)} benign + ${n(m.attack)} attack payments · Jev fusion + conformal hold threshold · main set`, 26, tokens.muted)}
${line(88, 206, 1832, 206)}
${label(88, 256, "MISSED ATTACKS")}
${t(78, 402, `${n(m.missedPct)}%`, 154, tokens.accent, 500, 'letter-spacing="-7"')}
${t(94, 452, `vs ${n(m.baselineMissedPct)}% with no defense`, 32)}
${label(1090, 256, "FALSE BLOCKS")}
${t(1078, 402, `${n(m.falseBlocksPct)}%`, 154, tokens.text, 500, 'letter-spacing="-7"')}
${t(1094, 452, `Benign payments blocked · no defense: ${n(m.baselineFalseBlocksPct)}%`, 27, tokens.muted)}
${line(1008, 242, 1008, 465)}
${line(88, 490, 1832, 490)}
${label(88, 539, "FALSE HOLDS")}
${t(88, 589, `${n(m.falseHoldsPct)}%`, 43, tokens.accent, 500)}
${t(88, 631, `${n(m.falseHolds)} of ${n(m.benign)} benign · in-sample`, 26)}
${t(88, 668, `${m.targetRelation} the ε = ${n(m.targetPct)}% target`, 26, tokens.alarm)}
${line(446, 525, 446, 675)}
${label(484, 539, "EXTERNAL CHECK · HELD-OUT")}
${t(484, 588, external ? `${n(external.missedPct)}% missed · ${n(external.falseHoldsPct)}% false holds` : "Not supplied for sample data", 30, tokens.text, 500)}
${t(484, 630, external ? `${n(external.falseBlocksPct)}% false blocks` : "No real-data outcomes mixed in", 28)}
${t(484, 668, external ? `${n(external.benign)} benign / ${n(external.attack)} attack payments` : "", 25, tokens.muted)}
${line(1066, 525, 1066, 675)}
${label(1104, 539, "MEDIAN LATENCY")}
${t(1104, 589, `${n(m.medianSeconds)} s`, 43, tokens.text, 500)}
${t(1104, 631, "per payment", 27)}
${t(1104, 668, m.sample ? "Sample timing" : "Local CPU classifier", 24, tokens.muted)}
${line(1407, 525, 1407, 675)}
${label(1444, 539, "CALLS / PAYMENT")}
${t(1444, 586, `${n(m.jevCalls)} Jev call${m.jevCalls === 1 ? "" : "s"}`, 31, tokens.text, 500)}
${t(1444, 628, `+ ${n(m.classifierCalls)} classifier call${m.classifierCalls === 1 ? "" : "s"}`, 31)}
${t(1444, 668, "Cost unpriced", 26, tokens.muted)}
${line(88, 704, 1832, 704)}
${label(88, 748, "WEAKEST FAMILIES · CASCADE ROW")}
${t(88, 793, weakest ? weakest.map((f) => `${f.label}: ${n(f.caught)}/${n(f.total)} caught`).join(" · ") : "Cascade family outcomes not reported in sample data", 31)}
${t(88, 835, othersText || "", 24, tokens.muted)}
${t(88, 888, `Worst case: ${n(m.caps.perPayment)} tUSDC per payment, ${n(m.caps.perDay)} tUSDC per day, in contract code`, 30, tokens.accent, 500)}
${line(88, 918, 1832, 918)}
${t(88, 959, "The false-hold bound holds only while an agent behaves like its calibration history.", 28)}
${t(88, 1000, caveat, 28)}
${t(88, 1047, sourceLabel, 19, tokens.muted)}
</svg>\n`;
}

export function renderSlideHtml(svg) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Payment firewall — numbers slide</title><style>html,body{margin:0;background:#15131d}svg{display:block;width:100vw;height:auto;max-height:100vh} @page{size:16in 9in;margin:0}@media print{svg{width:100%;height:100%}}</style></head><body>${svg}</body></html>\n`;
}
