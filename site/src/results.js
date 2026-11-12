// Results section data (E3 renderer, D4 real data). Labels and caveats follow the README
// Results section, so the site and the README say the same thing.

export function validateResultsFormat(results) {
  if (results?.format !== "firewall.results.v1") {
    throw new Error(`Unsupported results format: expected firewall.results.v1, received ${JSON.stringify(results?.format)}`);
  }
}

// q̂ frozen in checker config (FUSION_HOLD_THRESHOLD, sprints.md C5/C6). results.json's top-level
// q_hat comes from the threshold-0.5 calibration run, so it is not the frozen value (README Results).
export const FROZEN_Q_HAT = 0.84;

export const CONFIG_LABELS = {
  no_defense: "No defense",
  policy_only: "Policy rules only",
  classifier_only: "Injection classifier only",
  code_rules_all_signals: "All signals, code rules only (no Jev)",
  jev_fusion_all_signals: "Jev fusion, all signals (hold threshold 0.5)",
  jev_fusion_conformal: `Jev fusion + conformal hold threshold (ε = 5%, q̂ ${FROZEN_Q_HAT})`,
  jev_fusion_conformal_cascade: "Same, with cascade",
};

const FAMILY_LABELS = {
  direct_injection: "Direct injection",
  encoded_injection: "Encoded injection",
  indirect_injection: "Indirect injection",
  memory_poisoning: "Memory poisoning",
  lookalike_receiver: "Lookalike receiver",
  fake_invoice: "Fake invoice",
};

export function mapResultsRows(results) {
  validateResultsFormat(results);
  return results.configurations.map((entry) => ({
    configuration: entry.configuration,
    label: CONFIG_LABELS[entry.configuration] ?? entry.configuration,
    description: entry.description ?? "",
    falseHoldsPct: entry.false_holds_pct,
    falseBlocksPct: entry.false_blocks_pct,
    missedAttacksPct: entry.missed_attacks_pct,
    medianLatencyMs: entry.median_latency_ms,
    costPerPaymentUsd: entry.cost_per_payment_usd ?? null,
    jevCalls: entry.jev_calls_per_payment ?? 0,
    classifierCalls: entry.classifier_calls_per_payment ?? 0,
  }));
}

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 20 });
export function formatResultNumber(value) {
  return value == null ? "Not reported" : numberFormat.format(value);
}

// Cost is unpriced in the committed runs, so the table shows calls per payment (README Results).
export function formatCalls({ jevCalls, classifierCalls }) {
  const part = (n, name) => `${numberFormat.format(n)} ${name} call${n === 1 ? "" : "s"}`;
  const parts = [jevCalls && part(jevCalls, "Jev"), classifierCalls && part(classifierCalls, "classifier")].filter(Boolean);
  return parts.length ? parts.join(" + ") : "0 calls";
}

export function headline(results) {
  const find = (key) => results.configurations.find((c) => c.configuration === key);
  const base = find("no_defense");
  const best = find("jev_fusion_conformal");
  return base && best ? { base, best } : null;
}

export function redteamRow(redteam) {
  validateResultsFormat(redteam);
  const s = redteam.summary;
  return {
    total: redteam.attack_total,
    missedPct: s.missed_attacks_pct,
    missed: s.missed_attacks,
    held: s.held_attacks,
    blocked: s.blocked_attacks,
    medianMs: redteam.latency_ms.p50_ms,
  };
}

// Caught per attack family. by_family holds the real outcomes of the last preset run (the cascade
// row); unseen_family_rotation is not a detection rate at q̂ (README Results).
export function familyRows(results) {
  return Object.entries(results.by_family)
    .filter(([family]) => family !== "none")
    .map(([family, f]) => ({
      family,
      label: FAMILY_LABELS[family] ?? family,
      caught: f.total - f.missed_attacks,
      total: f.total,
      caughtPct: Math.round(((f.total - f.missed_attacks) / f.total) * 1000) / 10,
    }));
}
