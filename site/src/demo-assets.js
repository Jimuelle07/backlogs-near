import { familyRows, mapResultsRows, validateResultsFormat } from "./results.js";

function number(value, path, { count = false, max = Infinity } = {}) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > max || (count && !Number.isSafeInteger(value))) {
    throw new Error(`Invalid or missing ${path}: ${JSON.stringify(value)}`);
  }
  return value;
}

function counts(results, name) {
  const benign = number(results.benign_total, `${name}.benign_total`, { count: true });
  const attack = number(results.attack_total, `${name}.attack_total`, { count: true });
  if (!benign || !attack || results.total !== benign + attack) throw new Error(`Invalid ${name} dataset totals`);
  return { benign, attack };
}

function preset(results, key) {
  const rows = results.configurations?.filter((row) => row.configuration === key);
  if (rows?.length !== 1) throw new Error(`Expected exactly one ${key} configuration`);
  const raw = rows[0];
  const row = mapResultsRows({ ...results, configurations: [raw] })[0];
  for (const field of ["falseHoldsPct", "falseBlocksPct", "missedAttacksPct"]) number(row[field], `${key}.${field}`, { max: 100 });
  number(row.medianLatencyMs, `${key}.medianLatencyMs`);
  return { raw, row };
}

function rates(raw, totals, name) {
  for (const [countKey, denominator] of [["false_holds", totals.benign], ["false_blocks", totals.benign], ["missed_attacks", totals.attack]]) {
    const count = number(raw[countKey], `${name}.${countKey}`, { count: true, max: denominator });
    if (Math.abs(raw[`${countKey}_pct`] - count / denominator * 100) > 0.011) {
      throw new Error(`Inconsistent ${name}.${countKey} count and percentage`);
    }
  }
}

export function mapSlideMetrics(results, { external = null, sample = false, caps } = {}) {
  validateResultsFormat(results);
  // Real results must never silently fall back to the obsolete stub preset.
  const baselineKey = sample && !results.configurations?.some((row) => row.configuration === "no_defense") ? "stub_allow" : "no_defense";
  const baseline = preset(results, baselineKey);
  const conformal = preset(results, "jev_fusion_conformal");
  const totals = counts(results, "main");
  rates(conformal.raw, totals, "conformal");
  rates(baseline.raw, totals, "baseline");
  // Do not use the helpers' optional-call defaults: absent calls are not measured zeros.
  const jevCalls = number(conformal.raw.jev_calls_per_payment, "conformal.jev_calls_per_payment");
  const classifierCalls = number(conformal.raw.classifier_calls_per_payment, "conformal.classifier_calls_per_payment");
  const targets = (results.caveats ?? []).flatMap((text) => [...text.matchAll(/epsilon\s*=\s*(\d+(?:\.\d+)?)%/g)].map((m) => Number(m[1])));
  if (!targets.length || new Set(targets).size !== 1) throw new Error("Missing or conflicting epsilon target in results JSON caveats");
  const targetPct = number(targets[0], "caveats.epsilon", { max: 100 });
  if (!targetPct) throw new Error("epsilon target must be positive");
  const perPayment = number(caps?.perPayment, "contract.perPayment", { count: true });
  const perDay = number(caps?.perDay, "contract.perDay", { count: true });
  if (!perPayment || perDay < perPayment) throw new Error("Invalid contract cap limits");

  let heldOut = null;
  // A sample slide must not borrow real external outcomes, even when supplied by a caller.
  if (!sample) {
    validateResultsFormat(external);
    const ext = preset(external, "jev_fusion_conformal");
    const extTotals = counts(external, "external");
    rates(ext.raw, extTotals, "external");
    heldOut = { ...extTotals, missedPct: ext.row.missedAttacksPct, falseHoldsPct: ext.row.falseHoldsPct, falseBlocksPct: ext.row.falseBlocksPct };
  }

  let families = null;
  if (!sample || results.configurations.some((row) => row.configuration === "jev_fusion_conformal_cascade")) {
    preset(results, "jev_fusion_conformal_cascade");
    const normalized = Object.fromEntries(Object.entries(results.by_family ?? {}).filter(([key]) => key !== "none").map(([key, value]) => {
      const total = number(value.total, `by_family.${key}.total`, { count: true });
      const outcomes = ["allow", "hold", "block"].map((field) => number(value[field], `by_family.${key}.${field}`, { count: true, max: total }));
      if (!total || outcomes.reduce((a, b) => a + b, 0) !== total || (value.missed_attacks != null && value.missed_attacks !== value.allow)) {
        throw new Error(`Inconsistent by_family.${key} outcomes`);
      }
      return [key, { ...value, missed_attacks: value.allow }];
    }));
    families = familyRows({ by_family: normalized }).sort((a, b) => a.caughtPct - b.caughtPct || a.family.localeCompare(b.family));
    if (families.length < 2 || families.reduce((sum, f) => sum + f.total, 0) !== totals.attack) throw new Error("Incomplete cascade family outcomes");
  }

  return {
    sample,
    ...totals,
    mainConfiguration: conformal.row.configuration,
    baselineConfiguration: baseline.row.configuration,
    missedPct: conformal.row.missedAttacksPct,
    missed: conformal.raw.missed_attacks,
    baselineMissedPct: baseline.row.missedAttacksPct,
    falseBlocksPct: conformal.row.falseBlocksPct,
    baselineFalseBlocksPct: baseline.row.falseBlocksPct,
    falseBlocks: conformal.raw.false_blocks,
    falseHoldsPct: conformal.row.falseHoldsPct,
    falseHolds: conformal.raw.false_holds,
    targetPct,
    targetRelation: conformal.row.falseHoldsPct > targetPct ? "above" : conformal.row.falseHoldsPct < targetPct ? "below" : "at",
    medianSeconds: conformal.row.medianLatencyMs / 1000,
    jevCalls, classifierCalls, heldOut, families,
    caps: { perPayment, perDay },
  };
}
