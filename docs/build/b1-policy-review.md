# B1 Policy Rules Check: Code Review & Sign-Off Document

Author: **Rc** (Backend Lane B, Sprint 1)  
Lead: **Jim** (Backend Lead)  
Task: **B1** (Policy rules check)  
Implementation: `checker/src/policy.rs`, `checker/src/decide.rs` (PR #3)  
Status: **Review Completed — Recommended for Sign-Off**

---

## 1. Executive Summary

As assigned for Lane B in Sprint 1, I have performed a comprehensive code review of the deterministic policy check implementation (`checker/src/policy.rs` and its integration in `checker/src/decide.rs`). 

The implementation fulfills all requirements set forth in [sprints.md](sprints.md), [sdd.md](sdd.md) §4/§7, and [idea.md](idea.md). It operates deterministically with **zero I/O and zero AI dependencies**, strictly outputs the frozen `signals.policy` shape (`{ok: bool, violations: Vec<String>}`), fails closed on corrupt or invalid configuration, and flags the required benchmark attack `attack-fake-invoice-amount-inflation`.

---

## 2. Rule-by-Rule Verification

| Rule ID | Violation Constant | Implementation & Behavior | Status |
| --- | --- | --- | --- |
| 1. Receiver Allowlist | `receiver_not_allowlisted` | If `POLICY_ALLOWLIST` is configured, verifies `receiver_id` matches an entry. Empty allowlist disables the restriction. | Verified |
| 2. Memo Length | `memo_too_long` | Validates character count (Unicode scalars, not raw bytes) against `POLICY_MAX_MEMO_CHARS` (default 128). | Verified |
| 3. Memo Characters | `memo_bad_chars` | Rejects ASCII control characters, zero-width spaces/joiners (`U+200B`–`U+200F`, `U+2060`–`U+2064`, `U+FEFF`), and bidirectional overrides (`U+202A`–`U+202E`, `U+2066`–`U+2069`, `U+061C`). | Verified |
| 4. Amount Validity | `amount_invalid` | Enforces canonical positive base-unit integer string (digits only, no leading zeros, positive `u128`). Fails before downstream cap/mismatch checks. | Verified |
| 5. Amount Cap | `amount_over_cap` | If `POLICY_MAX_AMOUNT` is configured, flags any amount strictly greater than the threshold. | Verified |
| 6. User Request Amount Mismatch | `amount_mismatch_request` | Extracts standalone numbers and currency tags from `user_request`. Also parses natural fractions (`half`, `third`, `quarter`, `fourth`, `N%`, `N percent`). If user states an amount or fraction, payment must match. | Verified |
| 7. Invoice Amount Mismatch | `amount_mismatch_invoice` | When the user states no amount in `user_request`, scans invoice context items (`email`, `web`, `invoice`) for currency-tagged amounts. If present, payment must match. | Verified |

---

## 3. Reviewer Follow-Ups Resolution (PR #3)

Four specific reviewer follow-up considerations were identified during PR #3:

### Follow-up 1: Allowlist case-sensitivity and account whitespace
- **Analysis:** `PolicyConfig::from_vars` splits `POLICY_ALLOWLIST` on commas and trims leading/trailing whitespace (`.map(str::trim).filter(|s| !s.is_empty())`). NEAR account IDs are strictly lowercase alphanumeric with `.` and `_` / `-`.
- **Verdict & Resolution (closed in B4):** `.to_ascii_lowercase()` normalization in `PolicyConfig::from_vars` and case-insensitive `eq_ignore_ascii_case` matching in `policy::check` are now implemented and unit-tested in `checker/src/policy.rs`.

### Follow-up 2: Thousands separators and decimal fractions
- **Analysis:** `scan_amounts` properly handles comma thousands separators (e.g., `1,234.50 USDC` scales to `1234500000`). In `stated_fractions`, percentages support up to 6 decimal digits (scaled by `1_000_000`), e.g. `12.5 percent of 80 USDC` matches `10000000` base units.
- **Verdict:** Fractional arithmetic rounds half-up (`(v + den) / (2 * den)`) preventing rounding evasion. No edge cases found.

### Follow-up 3: Currency tag scope
- **Analysis:** Tags recognized in free text include `$` as a prefix, and `usdc`, `tusdc`, `usd`, `dollar`, `dollars` as suffixes.
- **Verdict:** Matches all current testnet and dry-run mock tokens (tUSDC with 6 decimals). When Sprint 2 adds multi-payee / multi-token registries (A4), tag detection can parameterize from `input.token_id`.

### Follow-up 4: Wasm32-wasip2 (OutLayer) fail-closed behavior
- **Analysis:** `PolicyConfig::from_env()` reads environment variables directly. OutLayer secrets are injected as environment variables inside the TEE guest. There is no file access required.
- **Verdict:** If any config variable is malformed (e.g. `POLICY_MAX_AMOUNT=abc`), `decide()` returns `CheckerError::Config` (exit code 2), guaranteeing fail-closed execution.

---

## 4. Test Evidence & Acceptance Criteria

1. **Unit tests in `checker/src/policy.rs`:**
   - `example_input_is_clean`: PASS
   - `fake_invoice_amount_inflation_is_flagged`: PASS (flagged with `amount_mismatch_request`)
   - `morse_lookalike_inflated_amount_is_flagged_against_invoice`: PASS
   - `benign_hosting_passes`: PASS
   - `benign_scenarios_all_pass`: PASS (all 30 benign scenarios verified clean)
   - `fraction_of_stated_amount_is_accepted`: PASS (half, third, quarter, 25%, 12.5%)
   - `user_amount_wins_over_invoice`: PASS
   - `invoice_amount_used_when_user_states_none`: PASS
   - `amount_validity_and_cap_edge`: PASS
   - `memo_rules_and_boundary`: PASS
   - `allowlist_hit_and_miss`: PASS
   - `config_from_vars`: PASS

2. **Integration in `checker/src/decide.rs`:**
   - `signals.policy` is filled when `POLICY_ENABLED=1`.
   - `signals.policy` is `null` when `POLICY_ENABLED=0`.
   - Frozen schema compatibility confirmed with `schemas/decision-record.schema.json`.

---

## 5. Sign-Off Readiness

All "Done when" acceptance criteria for Task B1 are met:
- [x] Unit tests pass across all scenarios.
- [x] `attack-fake-invoice-amount-inflation` is flagged.
- [x] Frozen `signals.policy` shape is populated.
- [x] 4 reviewer follow-up items evaluated and documented.

**Rc recommends B1 for formal sign-off by Jim.**
