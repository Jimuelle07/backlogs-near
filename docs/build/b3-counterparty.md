# B3 Counterparty Signals: Architecture, Implementation & Verification

Author: **Rc** (Backend Lane B, Sprint 2)  
Lead: **Jim** (Backend Lead)  
Task: **B3** (Counterparty signals: is-contract and code-hash change over RPC, account age and prior payments from the agent profile, lookalike distance; output `signals.counterparty`)  
Implementation: `checker/src/counterparty.rs`, `checker/src/decide.rs`, `checker/src/lib.rs`  
Done When: `hostc0` flagged as lookalike of `hostco`; frozen `signals.counterparty` in `schemas/decision-record.schema.json` populated; unit tests  
Status: **Complete — Ready for Review & Sign-off**

---

## 1. Executive Summary

Task B3 delivers the counterparty signals detector for the Attested Payment Firewall checker (`checker/src/counterparty.rs`).

The counterparty detector guards autonomous agents against payee substitution and lookalike impersonation attacks (such as zero-for-oh typosquatting, character transpositions, underscore substitutions, and suffix insertions). It evaluates proposed transactions against the agent's historical behavioral profile and optionally queries NEAR JSON-RPC (or an OutLayer-attested RPC proxy) for the receiver's `code_hash` (`is_contract`, `code_changed_recently`). `account_age_days` comes only from the agent profile.

The output conforms strictly to the frozen `signals.counterparty` schema in `schemas/decision-record.schema.json` and `checker/src/formats.rs::CounterpartySignal`.

---

## 2. Architecture & Detector Components

### 2.1 Lookalike Detection with Damerau-Levenshtein Metric

Attackers impersonating known payees employ common typographic variations:
- **Character substitution**: e.g., `hostc0` vs `hostco`, `cl0udco` vs `cloudco`, `h0stco` vs `hostco`.
- **Adjacent character transposition**: e.g., `domianreg` vs `domainreg` (`ia` ↔ `ai`).
- **Character insertion / suffixing**: e.g., `supplier-acme1` vs `supplier-acme`.
- **Character replacement**: e.g., `designer_ana` vs `designer-ana` (`_` ↔ `-`).

Standard Levenshtein treats adjacent transpositions as two operations (one deletion + one insertion = cost 2). We implement **Damerau-Levenshtein distance (optimal string alignment)**, which recognizes adjacent transpositions as a single edit operation (cost 1).

**Confusable skeleton.** NEAR account ids allow only `a-z 0-9 - _ .`, so the lookalike surface is ASCII confusables, not Unicode homoglyphs (e.g. `cl0udc0x` vs `cloudco`, edit distance 3 without the skeleton). `ascii_skeleton` lowercases ASCII, then makes one left-to-right pass: the two-character sequences `rn`→`m` and `vv`→`w`; the single characters `0`→`o`, `1`→`l`, `i`→`l`, `3`→`e`, `4`→`a`, `5`→`s`, `7`→`t`, `8`→`b`, `9`→`g`, `_`→`-`; every other character is kept. `payee_distance` computes `raw` (the distance defined below); if `raw == 0` it returns 0, otherwise it returns `raw.min(skel.max(1))`, where `skel` is the same distance between the two skeletons. A confusable variant is therefore never an exact match, and its distance is at least 1. `find_lookalike` and `COUNTERPARTY_MAX_LOOKALIKE_DISTANCE` are unchanged except for the tie-break: among payees at the same distance, the one with the smaller raw distance wins, then the one with more prior payments.

### 2.2 NEAR Subaccount & Suffix Scoping

NEAR accounts use hierarchical dot notation (e.g., `hostco.demo.testnet`, `hostco.testnet`, `hostco`). The distance calculation accounts for network namespaces:
1. Exact match (`candidate == payee`) returns `0`.
2. Matching domain suffixes (e.g. `hostc0.demo.testnet` vs `hostco.demo.testnet`) compares subaccount prefixes directly (`full_dist == 1`).
3. Both qualified, different suffixes: `min(full_dist, prefix_dist + 1)`, preventing cross-namespace spoofing.
4. Exactly one side qualified (contains a dot), e.g. bare `hostco` vs `hostco.evil.testnet`: `prefix_dist + 1`, never 0. A qualified account id never matches a bare profile name exactly, so `hostco.evil.testnet` is a lookalike (distance 1) of bare `hostco`, not a known payee (Jim, 2026-11-12). Both bare: plain distance (`hostc0` vs `hostco` is 1).
5. `COUNTERPARTY_NAMESPACE` (optional, an account suffix such as `jimuelle-firewall.testnet`, no leading dot): when set, the built-in default profile also contains `<base>.<ns>` for every default payee base name (first label, de-duplicated) with the same history fields, so `hostco.<ns>` is an exact known payee and `hostc0.<ns>` a lookalike. Without it, `hostco.jimuelle-firewall.testnet` is a lookalike of bare `hostco`. Ignored when an explicit profile (`AGENT_PROFILE_JSON`, `AGENT_PROFILE_PATH`, `COUNTERPARTY_KNOWN_PAYEES`) is set. The agent's own checker runs (dry-run `LocalGuardian`, `firewall-relayer`) set it to the scenario namespace; `firewall-eval` does not (it evaluates in `demo.testnet`, whose names are default members).

### 2.3 Lookalike Match Logic & Thresholds

For candidate `receiver_id` tested against `known_payees` with threshold `max_lookalike_distance` (default 2):
- **Distance = 0 (Exact Match)**: Known payee. `lookalike_of: None`, `lookalike_distance: None`, `prior_payments: payee.prior_payments` ($\ge 1$).
- **$1 \le \text{Distance} \le \text{max\_lookalike\_distance}$**: Lookalike attack detected! `lookalike_of: Some(closest_payee)`, `lookalike_distance: Some(dist)`, `prior_payments: 0`.
- **$\text{Distance} > \text{max\_lookalike\_distance}$**: Novel receiver. `lookalike_of: None`, `lookalike_distance: None`, `prior_payments: 0`.

### 2.4 Agent Behavioral Profile

The agent profile (`AgentProfile`) tracks:
- `known_payees: Vec<PayeeHistory>`: List of known accounts with historical interaction counts (`prior_payments`) and optional `is_contract`, `account_age_days` and `code_hash` (the code hash recorded for that payee).
- `payments_last_90d`: Count of recent successful payments (for fusion scoring in C3).
- `typical_amount_units`: Distribution of past payment sizes in base units.

The parser supports:
1. `AGENT_PROFILE_JSON`: Raw JSON string with `known_payees`, map shapes, or bare lists.
2. `AGENT_PROFILE_PATH`: Path to a JSON profile file on disk.
3. `COUNTERPARTY_KNOWN_PAYEES`: Comma-separated list of known payee account names.
4. `AgentProfile::with_default_payees_in(ns)`: Pre-populated benchmark payees from the benign scenarios (`hostco`, `cloudco`, `supplier-acme`, `designer-ana`, `domainreg`, etc.), plus the `<base>.<ns>` names when `COUNTERPARTY_NAMESPACE` is set.

### 2.5 NEAR JSON-RPC Querying

When `COUNTERPARTY_RPC_URL` is configured (the checker does not read `NEAR_RPC_URL`; the URL must be HTTPS, otherwise config parsing fails):
- Performs an HTTP `POST` to the RPC endpoint with `{"jsonrpc": "2.0", "method": "query", "params": {"request_type": "view_account", "finality": "optimistic", "account_id": receiver_id}}`.
- Only `result.code_hash` is read from the response. Plain user accounts (EOAs) have `code_hash == "11111111111111111111111111111111"`; any other code hash sets `is_contract: true`.
- `code_changed_recently` is `true` only when the receiver exactly matches a profile payee whose `code_hash` is set and the RPC `code_hash` differs from it. Lookalikes, unknown receivers and payees without a profile `code_hash` stay `false`.
- `account_age_days` is never derived from RPC (`view_account` carries no creation block). It is the matched profile payee's `account_age_days`, else `null`.
- If RPC is disabled, the check skips it. If the RPC call fails, the checker prints `checker warning: counterparty RPC failed: …` to stderr and keeps the profile-derived signals; the run does not fail.

---

## 3. Configuration Specification

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `COUNTERPARTY_ENABLED` | bool | `true` | Enables or disables counterparty check |
| `COUNTERPARTY_RPC_URL` | string | unset | NEAR JSON-RPC URL (HTTPS only); unset = no RPC query |
| `COUNTERPARTY_TIMEOUT_MS` | integer | `2000` | HTTP timeout for RPC calls in milliseconds; maximum 2000 (30 s OutLayer budget), a larger value is a config error |
| `COUNTERPARTY_MAX_LOOKALIKE_DISTANCE` | integer | `2` | Maximum edit distance to flag as a lookalike |
| `COUNTERPARTY_KNOWN_PAYEES` | string | unset | Comma-separated list of known payee account IDs |
| `COUNTERPARTY_NAMESPACE` | string | unset | Account suffix (no leading dot) that adds `<base>.<ns>` for each default payee; default profile only |
| `AGENT_PROFILE_JSON` | string | unset | Inlined JSON string of agent behavioral profile |
| `AGENT_PROFILE_PATH` | string | unset | Path to JSON file containing agent profile |

---

## 4. Acceptance Criteria & Test Evidence

### 4.1 Done When Criterion: `hostc0` Flagged as Lookalike of `hostco`

Verified by unit test `test_hostc0_flagged_as_lookalike_of_hostco`:
```rust
let match_res = find_lookalike("hostc0", &payees, 2);
// Result: LookalikeMatch::Lookalike { payee: "hostco", distance: 1 }
```

### 4.2 Coverage Across All 6 Lookalike Attack Scenarios

Verified by unit test `test_all_six_attack_scenarios`:
| Scenario File | Candidate Receiver | Known Target Payee | Distance | Match Classification |
| --- | --- | --- | --- | --- |
| `attack-morse-lookalike.json` | `hostc0.demo.testnet` | `hostco.demo.testnet` | 1 | `lookalike_of: "hostco.demo.testnet"` |
| `attack-lookalike-cloudco.json` | `cl0udco.demo.testnet` | `cloudco.demo.testnet` | 1 | `lookalike_of: "cloudco.demo.testnet"` |
| `attack-lookalike-suffix.json` | `supplier-acme1.demo.testnet` | `supplier-acme.demo.testnet` | 1 | `lookalike_of: "supplier-acme.demo.testnet"` |
| `attack-lookalike-transposed.json` | `domianreg.demo.testnet` | `domainreg.demo.testnet` | 1 | `lookalike_of: "domainreg.demo.testnet"` |
| `attack-lookalike-underscore.json` | `designer_ana.demo.testnet` | `designer-ana.demo.testnet` | 1 | `lookalike_of: "designer-ana.demo.testnet"` |
| `attack-lookalike-history-poison.json` | `h0stco.demo.testnet` | `hostco.demo.testnet` | 1 | `lookalike_of: "hostco.demo.testnet"` |

### 4.3 Schema Conformity

Frozen schema in `schemas/decision-record.schema.json`:
```json
"Counterparty": {
  "type": "object", "additionalProperties": false,
  "required": ["account_age_days", "is_contract", "code_changed_recently", "prior_payments", "lookalike_of", "lookalike_distance"],
  "properties": {
    "account_age_days": {"type": ["number", "null"]},
    "is_contract": {"type": "boolean"},
    "code_changed_recently": {"type": "boolean"},
    "prior_payments": {"type": "integer", "minimum": 0},
    "lookalike_of": {"type": ["string", "null"]},
    "lookalike_distance": {"type": ["integer", "null"], "minimum": 0}
  }
}
```
All fields serialize strictly according to spec.

### 4.4 Test Execution Summary

- `pytest tests/test_schemas.py tests/test_formats.py`: **87 passed in 0.23s**
- `pytest tests/test_nightly_e2e.py`: **13 passed in 0.05s**
- `pytest tests/test_eval.py`: **3 passed, 1 skipped in 94.9s**
- Rust unit tests in `counterparty.rs` and `decide.rs`:
  - `test_damerau_levenshtein_cases`
  - `test_hostc0_flagged_as_lookalike_of_hostco`
  - `test_all_six_attack_scenarios`
  - `test_benign_exact_match`
  - `test_novel_payee_not_lookalike`
  - `test_counterparty_config_from_vars`
  - `test_counterparty_config_invalid_vars`
  - `test_profile_json_parsing_shapes`
  - `test_check_execution_lookalike`
  - `test_check_execution_exact_match`
  - `test_frozen_schema_json_shape`
  - `decide_populates_counterparty_signal`
  - `decide_detects_lookalike_receiver`
  - `decide_with_counterparty_disabled_yields_null`

---

## 5. Integration with C3 Jev Fusion

In `checker/src/counterparty.rs`, `counterparty_reasons` maps signals directly to the frozen `ReasonCode` enum:
- `lookalike_of.is_some()` $\rightarrow$ `ReasonCode::LookalikeReceiver`
- `prior_payments == 0` $\rightarrow$ `ReasonCode::NewReceiver`
- `account_age_days < 7.0` $\rightarrow$ `ReasonCode::YoungAccount`
- `code_changed_recently == true` $\rightarrow$ `ReasonCode::ContractCodeChanged`

This enables task **C3** (Jev fusion in `decide()`, owned by paticolcol & Jim) to immediately consume real counterparty signals alongside policy and injection detector outputs.
