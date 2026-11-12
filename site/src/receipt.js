export const statusLabels = {
  paid: 'Paid', held: 'Held', refused: 'Refused', timed_out: 'Timed out',
  transfer_failed: 'Transfer failed', paying: 'Paying',
};
export const statusTones = {
  paid: 'allow', held: 'hold', refused: 'block', timed_out: 'hold', transfer_failed: 'block', paying: 'hold',
};
export const reasonLabels = {
  stub_allow: 'Scaffold decision', policy_violation: 'Policy violation', injection_high: 'Injection detected',
  melon_match: 'Masked re-run match', lookalike_receiver: 'Lookalike receiver', new_receiver: 'New receiver',
  young_account: 'Young account', contract_code_changed: 'Contract changed', unusual_for_agent: 'Unusual payment',
  jev_injection_driven: 'Jev: injection driven', jev_receiver_risk: 'Jev: receiver risk',
  amount_mismatch: 'Amount mismatch', check_unavailable: 'Check unavailable', checks_passed: 'Checks passed',
};

export function reasonLabel(reason) {
  return reasonLabels[reason] ?? reason.replaceAll('_', ' ');
}

export function formatHoldCountdown(releaseAtNs, nowMs = Date.now()) {
  const remaining = BigInt(releaseAtNs) - BigInt(nowMs) * 1_000_000n;
  if (remaining <= 0n) return 'releasing';
  // Round up only after comparing nanoseconds: even one ns left is still held.
  const seconds = (remaining + 999_999_999n) / 1_000_000_000n;
  return `${seconds / 3600n}h ${(seconds / 60n) % 60n}m ${seconds % 60n}s remaining`;
}
