// Results section data, read from the committed eval output (docs/results/*.json, C4/C5).
// Labels follow the README Results table, so the site and the README say the same thing.

// q̂ frozen in checker config (FUSION_HOLD_THRESHOLD, sprints.md C5/C6). results.json's own
// q_hat is recomputed from the last preset run, so it is not the frozen value.
export const FROZEN_Q_HAT = 0.84;

const LABELS = {
  no_defense: "No defense",
  policy_only: "Policy rules only",
  code_rules_all_signals: "All signals, code rules only (no Jev)",
  jev_fusion_all_signals: "Jev fusion, all signals (hold threshold 0.5)",
  jev_fusion_conformal: `Jev fusion + conformal hold threshold (ε = 5%, q̂ ${FROZEN_Q_HAT})`,
  jev_fusion_conformal_cascade: "Same, with cascade",
};

// Rows the README lists without numbers; shown so the table never implies they ran.
export const NOT_RUN = [
  ["Injection classifier only", "Not run: the classifier model could not be downloaded"],
  ["Masked re-run (MELON) only", "Not built (cut list)"],
];

const FAMILIES = {
  direct_injection: "Direct injection",
  encoded_injection: "Encoded injection",
  indirect_injection: "Indirect injection",
  memory_poisoning: "Memory poisoning",
  lookalike_receiver: "Lookalike receiver",
  fake_invoice: "Fake invoice",
};

export function pct(value) {
  return `${Number(value.toFixed(2))}%`;
}

export function ms(value) {
  return `${value.toFixed(1)} ms`;
}

export function jevCalls(n) {
  return n ? `${Number(n.toFixed(2))} Jev call${n === 1 ? "" : "s"}` : "0 calls";
}

export function resultRows(results) {
  return results.configurations.map((c) => ({
    key: c.configuration,
    label: LABELS[c.configuration] ?? c.configuration,
    falseHolds: c.false_holds_pct,
    falseBlocks: c.false_blocks_pct,
    missed: c.missed_attacks_pct,
    medianMs: c.median_latency_ms,
    jevCalls: c.jev_calls_per_payment ?? 0,
  }));
}

export function redteamRow(redteam) {
  const s = redteam.summary;
  return {
    total: redteam.attack_total,
    missed: s.missed_attacks_pct,
    allowed: s.missed_attacks,
    held: s.held_attacks,
    blocked: s.blocked_attacks,
    medianMs: redteam.latency_ms.p50_ms,
  };
}

// Detection per attack family at the frozen q̂, from the final conformal run (README Results).
export function familyRows(results) {
  return results.unseen_family_rotation
    .filter((f) => f.family !== "all")
    .map((f) => ({
      key: f.family,
      label: FAMILIES[f.family] ?? f.family,
      detected: f.detected,
      total: f.total,
      detectedPct: Math.round(f.detection_rate * 1000) / 10,
    }));
}

export function headline(results) {
  const find = (key) => results.configurations.find((c) => c.configuration === key);
  const base = find("no_defense");
  const best = find("jev_fusion_conformal");
  return base && best ? { base, best } : null;
}
