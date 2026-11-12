export function validateResultsFormat(results) {
  if (results?.format !== "firewall.results.v1") {
    throw new Error(`Unsupported results format: expected firewall.results.v1, received ${JSON.stringify(results?.format)}`);
  }
}

export function mapResultsRows(results) {
  validateResultsFormat(results);
  return results.configurations.map((entry) => ({
    configuration: entry.configuration,
    description: entry.description ?? "",
    falseHoldsPct: entry.false_holds_pct,
    falseBlocksPct: entry.false_blocks_pct,
    missedAttacksPct: entry.missed_attacks_pct,
    medianLatencyMs: entry.median_latency_ms,
    costPerPaymentUsd: entry.cost_per_payment_usd ?? null,
  }));
}

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 20 });
export function formatResultNumber(value) {
  return value == null ? "Not reported" : numberFormat.format(value);
}
