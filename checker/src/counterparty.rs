//! Counterparty signals (B3): account age, is-contract, code-hash change,
//! prior payments, and lookalike distance over NEAR RPC and agent profile history.
//! Output is the frozen `signals.counterparty` shape.
use crate::formats::{CheckerInput, CounterpartySignal, ReasonCode};
use crate::http;
use serde::{Deserialize, Serialize};
use std::time::Duration;

pub const DEFAULT_MAX_LOOKALIKE_DISTANCE: u32 = 2;
pub const DEFAULT_TIMEOUT_MS: u64 = 2000;
/// Largest accepted `COUNTERPARTY_TIMEOUT_MS`; the 30 s OutLayer budget is fitted to it (sdd §4).
pub const MAX_TIMEOUT_MS: u64 = 2000;
pub const NEAR_NO_CODE_HASH: &str = "11111111111111111111111111111111";

/// History entry for a known payee in the agent's behavior profile.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PayeeHistory {
    pub account_id: String,
    #[serde(default = "default_prior_payments")]
    pub prior_payments: u64,
    #[serde(default)]
    pub is_contract: Option<bool>,
    #[serde(default)]
    pub account_age_days: Option<f64>,
    /// NEAR code hash recorded for this payee; an RPC hash that differs sets `code_changed_recently`.
    #[serde(default)]
    pub code_hash: Option<String>,
}

fn default_prior_payments() -> u64 {
    1
}

/// Agent behavior profile tracking payment history and known counterparties.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct AgentProfile {
    #[serde(default)]
    pub payments_last_90d: Option<u32>,
    #[serde(default)]
    pub typical_amount_units: Option<Vec<u128>>,
    #[serde(default)]
    pub known_payees: Vec<PayeeHistory>,
}

impl AgentProfile {
    /// Populate default benign payees used across scenarios and benchmarks. With `namespace`
    /// (`COUNTERPARTY_NAMESPACE`, e.g. `jimuelle-firewall.testnet`) the profile also contains
    /// `<base>.<namespace>` for every default base name (first label, de-duplicated), with the same
    /// history fields as the default entries.
    pub fn with_default_payees_in(namespace: Option<&str>) -> Self {
        let default_names = [
            "hostco",
            "hostco.demo.testnet",
            "hostco.testnet",
            "cloudco",
            "cloudco.demo.testnet",
            "cloudco.testnet",
            "supplier-acme",
            "supplier-acme.demo.testnet",
            "supplier-acme.testnet",
            "designer-ana",
            "designer-ana.demo.testnet",
            "designer-ana.testnet",
            "domainreg",
            "domainreg.demo.testnet",
            "domainreg.testnet",
            "fastcdn.demo.testnet",
            "adnetwork.demo.testnet",
            "email-saas.demo.testnet",
            "office-realty.demo.testnet",
            "utility-power.demo.testnet",
            "contractor-bob.demo.testnet",
            "devops-pro.demo.testnet",
            "translator-lee.demo.testnet",
        ];
        let mut names: Vec<String> = default_names.iter().map(|n| (*n).to_string()).collect();
        if let Some(ns) = namespace {
            for name in default_names {
                let base = name.split('.').next().unwrap_or(name);
                let qualified = format!("{base}.{ns}");
                if !names.contains(&qualified) {
                    names.push(qualified);
                }
            }
        }
        let known_payees = names
            .into_iter()
            .map(|account_id| PayeeHistory {
                account_id,
                prior_payments: 5,
                is_contract: Some(false),
                account_age_days: Some(180.0),
                code_hash: None,
            })
            .collect();

        Self {
            payments_last_90d: Some(12),
            typical_amount_units: Some(vec![15000000, 22000000]),
            known_payees,
        }
    }

    /// Flexible parser supporting multiple profile shapes:
    /// - `{"known_payees": ["hostco", ...]}` (list of strings or payee objects)
    /// - `{"known_payees": {"hostco": 5}}` (map of payee -> payment count)
    /// - `["hostco", "cloudco"]` (bare list of strings or payee objects)
    pub fn from_json_str(s: &str) -> Result<Self, String> {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum PayeeItem {
            Name(String),
            Detailed(PayeeHistory),
        }

        #[derive(Deserialize)]
        #[serde(untagged)]
        enum ProfilePayload {
            Standard {
                #[serde(default)]
                payments_last_90d: Option<u32>,
                #[serde(default)]
                typical_amount_units: Option<Vec<u128>>,
                #[serde(default)]
                known_payees: Vec<PayeeItem>,
            },
            MapShape {
                #[serde(default)]
                payments_last_90d: Option<u32>,
                #[serde(default)]
                typical_amount_units: Option<Vec<u128>>,
                known_payees: std::collections::BTreeMap<String, u64>,
            },
            BareList(Vec<PayeeItem>),
        }

        let parsed: ProfilePayload = serde_json::from_str(s)
            .map_err(|e| format!("failed to parse agent profile JSON: {e}"))?;

        match parsed {
            ProfilePayload::Standard {
                payments_last_90d,
                typical_amount_units,
                known_payees,
            } => {
                let payees = known_payees
                    .into_iter()
                    .map(|item| match item {
                        PayeeItem::Name(name) => PayeeHistory {
                            account_id: name,
                            prior_payments: 1,
                            is_contract: None,
                            account_age_days: None,
                            code_hash: None,
                        },
                        PayeeItem::Detailed(d) => d,
                    })
                    .collect();
                Ok(Self {
                    payments_last_90d,
                    typical_amount_units,
                    known_payees: payees,
                })
            }
            ProfilePayload::MapShape {
                payments_last_90d,
                typical_amount_units,
                known_payees,
            } => {
                let payees = known_payees
                    .into_iter()
                    .map(|(account_id, prior_payments)| PayeeHistory {
                        account_id,
                        prior_payments,
                        is_contract: None,
                        account_age_days: None,
                        code_hash: None,
                    })
                    .collect();
                Ok(Self {
                    payments_last_90d,
                    typical_amount_units,
                    known_payees: payees,
                })
            }
            ProfilePayload::BareList(items) => {
                let payees = items
                    .into_iter()
                    .map(|item| match item {
                        PayeeItem::Name(name) => PayeeHistory {
                            account_id: name,
                            prior_payments: 1,
                            is_contract: None,
                            account_age_days: None,
                            code_hash: None,
                        },
                        PayeeItem::Detailed(d) => d,
                    })
                    .collect();
                Ok(Self {
                    payments_last_90d: None,
                    typical_amount_units: None,
                    known_payees: payees,
                })
            }
        }
    }
}

/// Checker configuration for counterparty and lookalike signals.
#[derive(Debug, Clone, PartialEq)]
pub struct CounterpartyConfig {
    /// `COUNTERPARTY_ENABLED` (default true when parsed from environment).
    pub enabled: bool,
    /// `COUNTERPARTY_RPC_URL` (NEAR JSON-RPC endpoint); unset = no RPC query.
    pub rpc_url: Option<String>,
    /// `COUNTERPARTY_TIMEOUT_MS`, default 2000 ms (fits the 30 s OutLayer budget).
    pub timeout: Duration,
    /// `COUNTERPARTY_MAX_LOOKALIKE_DISTANCE`, default 2.
    pub max_lookalike_distance: u32,
    /// Agent behavioral profile containing known payee history.
    pub profile: AgentProfile,
}

impl Default for CounterpartyConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            rpc_url: None,
            timeout: Duration::from_millis(DEFAULT_TIMEOUT_MS),
            max_lookalike_distance: DEFAULT_MAX_LOOKALIKE_DISTANCE,
            profile: AgentProfile::default(),
        }
    }
}

impl CounterpartyConfig {
    pub fn from_env() -> Result<Self, String> {
        Self::from_vars(|k| std::env::var(k).ok())
    }

    pub fn from_vars(get: impl Fn(&str) -> Option<String>) -> Result<Self, String> {
        let var = |k: &str| get(k).map(|v| v.trim().to_string()).filter(|v| !v.is_empty());

        let enabled_explicit = if let Some(v) = var("COUNTERPARTY_ENABLED") {
            Some(match v.to_ascii_lowercase().as_str() {
                "1" | "true" | "on" | "yes" => true,
                "0" | "false" | "off" | "no" => false,
                _ => return Err(format!("COUNTERPARTY_ENABLED: expected 1/0/true/false/on/off, got {v:?}")),
            })
        } else {
            None
        };

        // When not explicitly configured, enabled defaults to true in from_vars/from_env
        let enabled = enabled_explicit.unwrap_or(true);

        let rpc_url = match var("COUNTERPARTY_RPC_URL") {
            None => None,
            Some(u) => Some(crate::decision::validate_https_base_url(&u).map_err(|_| {
                format!("COUNTERPARTY_RPC_URL: expected an https:// URL with a host, got {u:?}")
            })?),
        };

        let timeout = if let Some(v) = var("COUNTERPARTY_TIMEOUT_MS") {
            let ms: u64 = v
                .parse()
                .map_err(|e| format!("COUNTERPARTY_TIMEOUT_MS: {e}"))?;
            if ms > MAX_TIMEOUT_MS {
                return Err(format!(
                    "COUNTERPARTY_TIMEOUT_MS: max {MAX_TIMEOUT_MS} (30 s OutLayer budget), got {ms}"
                ));
            }
            Duration::from_millis(ms)
        } else {
            Duration::from_millis(DEFAULT_TIMEOUT_MS)
        };

        let max_lookalike_distance = if let Some(v) = var("COUNTERPARTY_MAX_LOOKALIKE_DISTANCE") {
            v.parse::<u32>()
                .map_err(|e| format!("COUNTERPARTY_MAX_LOOKALIKE_DISTANCE: {e}"))?
        } else {
            DEFAULT_MAX_LOOKALIKE_DISTANCE
        };

        // Load profile: from AGENT_PROFILE_JSON, AGENT_PROFILE_PATH, COUNTERPARTY_KNOWN_PAYEES, or default payees
        let profile = if let Some(json_str) = var("AGENT_PROFILE_JSON") {
            AgentProfile::from_json_str(&json_str)?
        } else if let Some(path) = var("AGENT_PROFILE_PATH") {
            let content = std::fs::read_to_string(&path)
                .map_err(|e| format!("AGENT_PROFILE_PATH ({path}): {e}"))?;
            AgentProfile::from_json_str(&content)?
        } else if let Some(known_payees_str) = var("COUNTERPARTY_KNOWN_PAYEES") {
            let payees = known_payees_str
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(|s| PayeeHistory {
                    account_id: s.to_string(),
                    prior_payments: 1,
                    is_contract: None,
                    account_age_days: None,
                    code_hash: None,
                })
                .collect();
            AgentProfile {
                known_payees: payees,
                ..AgentProfile::default()
            }
        } else {
            let namespace = var("COUNTERPARTY_NAMESPACE");
            if let Some(ns) = &namespace {
                if ns.starts_with('.') || ns.ends_with('.') || ns.chars().any(char::is_whitespace) {
                    return Err(format!(
                        "COUNTERPARTY_NAMESPACE: expected an account suffix like jimuelle-firewall.testnet (no leading dot), got {ns:?}"
                    ));
                }
            }
            AgentProfile::with_default_payees_in(namespace.as_deref())
        };

        Ok(Self {
            enabled,
            rpc_url,
            timeout,
            max_lookalike_distance,
            profile,
        })
    }
}

/// Damerau-Levenshtein distance (optimal string alignment distance).
/// Accounts for deletions, insertions, substitutions, and adjacent transpositions.
pub fn damerau_levenshtein(s: &str, t: &str) -> u32 {
    let s_lower = s.to_ascii_lowercase();
    let t_lower = t.to_ascii_lowercase();

    let s_chars: Vec<char> = s_lower.chars().collect();
    let t_chars: Vec<char> = t_lower.chars().collect();

    let m = s_chars.len();
    let n = t_chars.len();

    if m == 0 {
        return n as u32;
    }
    if n == 0 {
        return m as u32;
    }

    let mut d = vec![vec![0u32; n + 1]; m + 1];

    for i in 0..=m {
        d[i][0] = i as u32;
    }
    for j in 0..=n {
        d[0][j] = j as u32;
    }

    for i in 1..=m {
        for j in 1..=n {
            let cost = if s_chars[i - 1] == t_chars[j - 1] { 0 } else { 1 };
            let mut val = (d[i - 1][j] + 1) // deletion
                .min(d[i][j - 1] + 1) // insertion
                .min(d[i - 1][j - 1] + cost); // substitution

            // Adjacent transposition
            if i > 1
                && j > 1
                && s_chars[i - 1] == t_chars[j - 2]
                && s_chars[i - 2] == t_chars[j - 1]
            {
                val = val.min(d[i - 2][j - 2] + 1);
            }

            d[i][j] = val;
        }
    }

    d[m][n]
}

/// Compute effective distance between a candidate receiver and a known payee account.
/// Accommodates NEAR subaccount scoping (`prefix.suffix`) so that:
/// - Exact (case-insensitive) matches return 0
/// - Both qualified with the same suffix -> full string distance
/// - Both qualified, different suffixes -> `min(full, prefix + 1)`
/// - Exactly one side qualified (e.g. `hostc0` vs `hostco.demo.testnet`, or `hostco.evil.testnet`
///   vs bare `hostco`) -> prefix distance + 1, never 0: a qualified account id never matches a
///   bare profile name exactly (Jim, 2026-11-12)
pub fn payee_distance(candidate: &str, payee: &str) -> u32 {
    if candidate.eq_ignore_ascii_case(payee) {
        return 0;
    }

    let full_dist = damerau_levenshtein(candidate, payee);

    let c_prefix = candidate.split('.').next().unwrap_or(candidate);
    let p_prefix = payee.split('.').next().unwrap_or(payee);

    // If both have no dots
    if c_prefix == candidate && p_prefix == payee {
        return full_dist;
    }

    let prefix_dist = damerau_levenshtein(c_prefix, p_prefix);

    let c_has_dot = candidate.contains('.');
    let p_has_dot = payee.contains('.');

    if c_has_dot && p_has_dot {
        let c_suffix = candidate.find('.').map(|i| &candidate[i..]);
        let p_suffix = payee.find('.').map(|i| &payee[i..]);
        if c_suffix == p_suffix {
            full_dist
        } else {
            full_dist.min(prefix_dist + 1)
        }
    } else {
        // Exactly one side is qualified: never an exact match.
        prefix_dist + 1
    }
}

#[derive(Debug, PartialEq)]
pub enum LookalikeMatch<'a> {
    Exact(&'a PayeeHistory),
    Lookalike {
        payee: &'a PayeeHistory,
        distance: u32,
    },
    Novel,
}

/// Find closest known payee and determine if candidate receiver is an exact match,
/// a lookalike attack, or a novel/unknown counterparty.
pub fn find_lookalike<'a>(
    receiver_id: &str,
    payees: &'a [PayeeHistory],
    max_lookalike_distance: u32,
) -> LookalikeMatch<'a> {
    let mut exact: Option<&'a PayeeHistory> = None;
    let mut closest_lookalike: Option<(&'a PayeeHistory, u32)> = None;

    for payee in payees {
        let dist = payee_distance(receiver_id, &payee.account_id);
        if dist == 0 {
            exact = Some(payee);
            break;
        }

        if dist <= max_lookalike_distance {
            match closest_lookalike {
                None => closest_lookalike = Some((payee, dist)),
                Some((prev_payee, prev_dist)) => {
                    if dist < prev_dist
                        || (dist == prev_dist && payee.prior_payments > prev_payee.prior_payments)
                    {
                        closest_lookalike = Some((payee, dist));
                    }
                }
            }
        }
    }

    if let Some(payee) = exact {
        LookalikeMatch::Exact(payee)
    } else if let Some((payee, distance)) = closest_lookalike {
        LookalikeMatch::Lookalike { payee, distance }
    } else {
        LookalikeMatch::Novel
    }
}

/// The part of a `view_account` response the checker uses.
#[derive(Debug, PartialEq, Eq)]
pub struct RpcAccountView {
    pub code_hash: String,
}

/// Parse a JSON-RPC `query`/`view_account` response body. An RPC error (top-level `error`, or a
/// `result.error` string such as an unknown account) or a missing `code_hash` is an `Err`.
fn parse_view_account(body: &serde_json::Value) -> Result<RpcAccountView, String> {
    if let Some(err) = body.get("error").filter(|e| !e.is_null()) {
        return Err(format!("RPC error response: {err}"));
    }
    let result = body.get("result").ok_or("RPC response has no result")?;
    if let Some(err) = result.get("error").filter(|e| !e.is_null()) {
        return Err(format!("RPC query error: {err}"));
    }
    let code_hash = result
        .get("code_hash")
        .and_then(|v| v.as_str())
        .filter(|h| !h.is_empty())
        .ok_or("view_account result has no code_hash")?;
    Ok(RpcAccountView { code_hash: code_hash.to_string() })
}

fn query_rpc_account(
    rpc_url: &str,
    account_id: &str,
    timeout: Duration,
) -> Result<RpcAccountView, String> {
    let req = serde_json::json!({
        "jsonrpc": "2.0",
        "id": "checker-counterparty",
        "method": "query",
        "params": {
            "request_type": "view_account",
            "finality": "optimistic",
            "account_id": account_id
        }
    });

    let body = serde_json::to_string(&req).map_err(|e| e.to_string())?;
    let resp = http::post_json(rpc_url, "", &body, timeout)
        .map_err(|e| format!("RPC query failed: {e}"))?;

    if resp.status < 200 || resp.status >= 300 {
        return Err(format!("RPC HTTP status {}: {}", resp.status, resp.body));
    }

    let parsed: serde_json::Value = serde_json::from_str(&resp.body)
        .map_err(|e| format!("failed to parse RPC response: {e}"))?;
    parse_view_account(&parsed)
}

/// Helper function to classify counterparty reasons from the signal.
pub fn counterparty_reasons(signal: &CounterpartySignal) -> Vec<ReasonCode> {
    let mut reasons = Vec::new();
    if signal.lookalike_of.is_some() {
        reasons.push(ReasonCode::LookalikeReceiver);
    } else if signal.prior_payments == 0 {
        reasons.push(ReasonCode::NewReceiver);
    }
    if let Some(age) = signal.account_age_days {
        if age < 7.0 {
            reasons.push(ReasonCode::YoungAccount);
        }
    }
    if signal.code_changed_recently {
        reasons.push(ReasonCode::ContractCodeChanged);
    }
    reasons
}

/// Execute counterparty check: evaluates lookalike distance, payment history,
/// and live or mock NEAR RPC signals (contract status, account age, code changes).
pub fn check(
    input: &CheckerInput,
    config: &CounterpartyConfig,
) -> Result<(Option<CounterpartySignal>, u64), String> {
    if !config.enabled {
        return Ok((None, 0));
    }

    let start = std::time::Instant::now();

    // 1. Lookalike & prior payment detection from profile
    let lookalike_match = find_lookalike(
        &input.receiver_id,
        &config.profile.known_payees,
        config.max_lookalike_distance,
    );

    let (prior_payments, lookalike_of, lookalike_distance) = match &lookalike_match {
        LookalikeMatch::Exact(payee) => (payee.prior_payments.max(1), None, None),
        LookalikeMatch::Lookalike { payee, distance } => {
            (0, Some(payee.account_id.clone()), Some(*distance))
        }
        LookalikeMatch::Novel => (0, None, None),
    };

    // 2. Account metadata defaults from the profile entry (age comes from the profile only:
    // `view_account` carries no creation block).
    let mut is_contract = false;
    let mut code_changed_recently = false;
    let mut account_age_days = None;
    let mut profile_code_hash: Option<&str> = None;

    if let LookalikeMatch::Exact(payee) = &lookalike_match {
        if let Some(ic) = payee.is_contract {
            is_contract = ic;
        }
        account_age_days = payee.account_age_days;
        profile_code_hash = payee.code_hash.as_deref();
    }

    // 3. NEAR RPC query if configured
    if let Some(rpc_url) = &config.rpc_url {
        match query_rpc_account(rpc_url, &input.receiver_id, config.timeout) {
            Ok(view) => {
                is_contract = view.code_hash != NEAR_NO_CODE_HASH;
                code_changed_recently = profile_code_hash.is_some_and(|h| h != view.code_hash);
            }
            Err(e) => eprintln!("checker warning: counterparty RPC failed: {e}"),
        }
    }

    let elapsed_ms = start.elapsed().as_millis() as u64;

    let signal = CounterpartySignal {
        account_age_days,
        is_contract,
        code_changed_recently,
        prior_payments,
        lookalike_of,
        lookalike_distance,
    };

    Ok((Some(signal), elapsed_ms))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_damerau_levenshtein_cases() {
        assert_eq!(damerau_levenshtein("hostco", "hostco"), 0);
        assert_eq!(damerau_levenshtein("hostc0", "hostco"), 1);
        assert_eq!(damerau_levenshtein("cl0udco", "cloudco"), 1);
        assert_eq!(damerau_levenshtein("supplier-acme1", "supplier-acme"), 1);
        assert_eq!(damerau_levenshtein("domianreg", "domainreg"), 1);
        assert_eq!(damerau_levenshtein("designer_ana", "designer-ana"), 1);
        assert_eq!(damerau_levenshtein("h0stco", "hostco"), 1);
        assert_eq!(damerau_levenshtein("completely-different", "hostco"), 18);
    }

    #[test]
    fn test_hostc0_flagged_as_lookalike_of_hostco() {
        // Criterion: `hostc0` flagged as lookalike of `hostco`
        let payees = vec![PayeeHistory {
            account_id: "hostco".to_string(),
            prior_payments: 5,
            is_contract: Some(false),
            account_age_days: Some(120.0),
            code_hash: None,
        }];

        let match_res = find_lookalike("hostc0", &payees, 2);
        match match_res {
            LookalikeMatch::Lookalike { payee, distance } => {
                assert_eq!(payee.account_id, "hostco");
                assert_eq!(distance, 1);
            }
            _ => panic!("expected hostc0 to be flagged as lookalike of hostco"),
        }
    }

    #[test]
    fn test_all_six_attack_scenarios() {
        let attacks = [
            ("hostc0.demo.testnet", "hostco.demo.testnet"),
            ("cl0udco.demo.testnet", "cloudco.demo.testnet"),
            ("supplier-acme1.demo.testnet", "supplier-acme.demo.testnet"),
            ("domianreg.demo.testnet", "domainreg.demo.testnet"),
            ("designer_ana.demo.testnet", "designer-ana.demo.testnet"),
            ("h0stco.demo.testnet", "hostco.demo.testnet"),
        ];

        for (attacker, legit) in attacks {
            let payees = vec![PayeeHistory {
                account_id: legit.to_string(),
                prior_payments: 3,
                is_contract: None,
                account_age_days: None,
                code_hash: None,
            }];
            let m = find_lookalike(attacker, &payees, 2);
            match m {
                LookalikeMatch::Lookalike { payee, distance } => {
                    assert_eq!(payee.account_id, legit);
                    assert_eq!(distance, 1, "failed for attacker {attacker} vs {legit}");
                }
                _ => panic!("expected lookalike for attacker {attacker} vs {legit}"),
            }
        }
    }

    #[test]
    fn test_benign_exact_match() {
        let profile = AgentProfile::with_default_payees_in(None);
        let m = find_lookalike("hostco.demo.testnet", &profile.known_payees, 2);
        match m {
            LookalikeMatch::Exact(p) => {
                assert!(p.account_id.contains("hostco"));
                assert!(p.prior_payments > 0);
            }
            _ => panic!("expected exact match for benign payee"),
        }
    }

    #[test]
    fn test_novel_payee_not_lookalike() {
        let profile = AgentProfile::with_default_payees_in(None);
        let m = find_lookalike("brand-new-contractor-999.testnet", &profile.known_payees, 2);
        assert_eq!(m, LookalikeMatch::Novel);
    }

    fn lookalike_distance_of(receiver: &str, profile: &AgentProfile) -> Option<(String, u32)> {
        match find_lookalike(receiver, &profile.known_payees, 2) {
            LookalikeMatch::Lookalike { payee, distance } => Some((payee.account_id.clone(), distance)),
            LookalikeMatch::Exact(_) => panic!("{receiver} unexpectedly exact"),
            LookalikeMatch::Novel => None,
        }
    }

    #[test]
    fn test_qualified_candidate_never_exact_vs_bare_payee() {
        assert_eq!(payee_distance("hostco.evil.testnet", "hostco"), 1);
        assert_eq!(payee_distance("hostco", "hostco.evil.testnet"), 1);
        let bare = vec![PayeeHistory {
            account_id: "hostco".to_string(),
            prior_payments: 5,
            is_contract: None,
            account_age_days: None,
            code_hash: None,
        }];
        match find_lookalike("hostco.evil.testnet", &bare, 2) {
            LookalikeMatch::Lookalike { payee, distance } => {
                assert_eq!(payee.account_id, "hostco");
                assert_eq!(distance, 1);
            }
            other => panic!("expected lookalike, got {other:?}"),
        }
        // Bare vs bare is unchanged.
        assert_eq!(payee_distance("hostc0", "hostco"), 1);
    }

    #[test]
    fn test_default_profile_qualified_receiver_without_namespace() {
        let profile = AgentProfile::with_default_payees_in(None);
        // Not a default member: lookalike of the bare name (distance 1).
        assert_eq!(
            lookalike_distance_of("hostco.evil.testnet", &profile),
            Some(("hostco".to_string(), 1))
        );
        assert_eq!(lookalike_distance_of("hostc0", &profile), Some(("hostco".to_string(), 1)));
        // Without COUNTERPARTY_NAMESPACE the live receiver is a lookalike of bare `hostco`.
        assert_eq!(
            lookalike_distance_of("hostco.jimuelle-firewall.testnet", &profile),
            Some(("hostco".to_string(), 1))
        );
    }

    #[test]
    fn test_counterparty_namespace_adds_qualified_default_payees() {
        let ns = "jimuelle-firewall.testnet";
        let profile = AgentProfile::with_default_payees_in(Some(ns));
        match find_lookalike("hostco.jimuelle-firewall.testnet", &profile.known_payees, 2) {
            LookalikeMatch::Exact(p) => {
                assert_eq!(p.prior_payments, 5);
                assert_eq!(p.account_age_days, Some(180.0));
            }
            other => panic!("expected exact, got {other:?}"),
        }
        let (payee, distance) = lookalike_distance_of("hostc0.jimuelle-firewall.testnet", &profile).unwrap();
        assert_eq!(payee, "hostco.jimuelle-firewall.testnet");
        assert_eq!(distance, 1);
        // The qualified attacker name is still not a member.
        assert!(lookalike_distance_of("hostco.evil.testnet", &profile).is_some());
        // De-duplicated: demo.testnet adds no repeated `hostco.demo.testnet`.
        let demo = AgentProfile::with_default_payees_in(Some("demo.testnet"));
        let count = demo.known_payees.iter().filter(|p| p.account_id == "hostco.demo.testnet").count();
        assert_eq!(count, 1);
    }

    #[test]
    fn test_counterparty_namespace_from_vars() {
        let with_ns = |k: &str| match k {
            "COUNTERPARTY_NAMESPACE" => Some("jimuelle-firewall.testnet".to_string()),
            _ => None,
        };
        let cfg = CounterpartyConfig::from_vars(with_ns).unwrap();
        assert!(cfg
            .profile
            .known_payees
            .iter()
            .any(|p| p.account_id == "hostco.jimuelle-firewall.testnet"));
        let empty = |k: &str| match k {
            "COUNTERPARTY_NAMESPACE" => Some("  ".to_string()),
            _ => None,
        };
        let cfg = CounterpartyConfig::from_vars(empty).unwrap();
        assert_eq!(cfg.profile, AgentProfile::with_default_payees_in(None));
        let bad = |k: &str| match k {
            "COUNTERPARTY_NAMESPACE" => Some(".testnet".to_string()),
            _ => None,
        };
        assert!(CounterpartyConfig::from_vars(bad).is_err());
        // An explicit profile wins; the namespace is ignored.
        let explicit = |k: &str| match k {
            "COUNTERPARTY_NAMESPACE" => Some("jimuelle-firewall.testnet".to_string()),
            "COUNTERPARTY_KNOWN_PAYEES" => Some("payee1.near".to_string()),
            _ => None,
        };
        assert_eq!(CounterpartyConfig::from_vars(explicit).unwrap().profile.known_payees.len(), 1);
    }

    #[test]
    fn test_counterparty_timeout_maximum() {
        let with = |ms: &'static str| {
            move |k: &str| match k {
                "COUNTERPARTY_TIMEOUT_MS" => Some(ms.to_string()),
                _ => None,
            }
        };
        assert_eq!(
            CounterpartyConfig::from_vars(with("2001")).unwrap_err(),
            "COUNTERPARTY_TIMEOUT_MS: max 2000 (30 s OutLayer budget), got 2001"
        );
        assert_eq!(
            CounterpartyConfig::from_vars(with("2000")).unwrap().timeout,
            Duration::from_millis(2000)
        );
    }

    #[test]
    fn test_counterparty_config_from_vars() {
        let vars = |k: &str| match k {
            "COUNTERPARTY_ENABLED" => Some("1".to_string()),
            "COUNTERPARTY_MAX_LOOKALIKE_DISTANCE" => Some("3".to_string()),
            "COUNTERPARTY_TIMEOUT_MS" => Some("1500".to_string()),
            "COUNTERPARTY_KNOWN_PAYEES" => Some("payee1.near,payee2.near".to_string()),
            _ => None,
        };

        let cfg = CounterpartyConfig::from_vars(vars).unwrap();
        assert!(cfg.enabled);
        assert_eq!(cfg.max_lookalike_distance, 3);
        assert_eq!(cfg.timeout, Duration::from_millis(1500));
        assert_eq!(cfg.profile.known_payees.len(), 2);
        assert_eq!(cfg.profile.known_payees[0].account_id, "payee1.near");
        assert_eq!(cfg.profile.known_payees[1].account_id, "payee2.near");
    }

    #[test]
    fn test_counterparty_config_invalid_vars() {
        let vars_bad_bool = |k: &str| match k {
            "COUNTERPARTY_ENABLED" => Some("maybe".to_string()),
            _ => None,
        };
        assert!(CounterpartyConfig::from_vars(vars_bad_bool).is_err());

        let vars_bad_dist = |k: &str| match k {
            "COUNTERPARTY_MAX_LOOKALIKE_DISTANCE" => Some("not-a-number".to_string()),
            _ => None,
        };
        assert!(CounterpartyConfig::from_vars(vars_bad_dist).is_err());
    }

    #[test]
    fn test_profile_json_parsing_shapes() {
        let shape1 = r#"{"payments_last_90d": 5, "known_payees": ["hostco.testnet"]}"#;
        let p1 = AgentProfile::from_json_str(shape1).unwrap();
        assert_eq!(p1.known_payees.len(), 1);
        assert_eq!(p1.known_payees[0].account_id, "hostco.testnet");

        let shape2 = r#"["hostco.testnet", "cloudco.testnet"]"#;
        let p2 = AgentProfile::from_json_str(shape2).unwrap();
        assert_eq!(p2.known_payees.len(), 2);

        let shape3 = r#"{"known_payees": {"hostco.testnet": 10}}"#;
        let p3 = AgentProfile::from_json_str(shape3).unwrap();
        assert_eq!(p3.known_payees.len(), 1);
        assert_eq!(p3.known_payees[0].prior_payments, 10);
    }

    #[test]
    fn test_check_execution_lookalike() {
        let mut cfg = CounterpartyConfig::default();
        cfg.enabled = true;
        cfg.profile = AgentProfile {
            known_payees: vec![PayeeHistory {
                account_id: "hostco".to_string(),
                prior_payments: 10,
                is_contract: Some(false),
                account_age_days: Some(300.0),
                code_hash: None,
            }],
            ..AgentProfile::default()
        };

        let input = CheckerInput {
            format: crate::formats::INPUT_FORMAT.to_string(),
            request_id: "req-1".to_string(),
            guardian_id: "guardian.testnet".to_string(),
            agent_id: "agent.testnet".to_string(),
            token_id: "tusdc.testnet".to_string(),
            token_decimals: 6,
            receiver_id: "hostc0".to_string(),
            amount: "18000000".to_string(),
            memo: "INV-1".to_string(),
            user_request: "pay hostco".to_string(),
            context: vec![],
            block_height: "100000".to_string(),
        };

        let (signal_opt, _) = check(&input, &cfg).unwrap();
        let signal = signal_opt.expect("signal should be present");
        assert_eq!(signal.lookalike_of.as_deref(), Some("hostco"));
        assert_eq!(signal.lookalike_distance, Some(1));
        assert_eq!(signal.prior_payments, 0);

        let reasons = counterparty_reasons(&signal);
        assert_eq!(reasons, vec![ReasonCode::LookalikeReceiver]);
    }

    #[test]
    fn test_check_execution_exact_match() {
        let mut cfg = CounterpartyConfig::default();
        cfg.enabled = true;
        cfg.profile = AgentProfile {
            known_payees: vec![PayeeHistory {
                account_id: "hostco.demo.testnet".to_string(),
                prior_payments: 7,
                is_contract: Some(false),
                account_age_days: Some(90.0),
                code_hash: None,
            }],
            ..AgentProfile::default()
        };

        let input = CheckerInput {
            format: crate::formats::INPUT_FORMAT.to_string(),
            request_id: "req-2".to_string(),
            guardian_id: "guardian.testnet".to_string(),
            agent_id: "agent.testnet".to_string(),
            token_id: "tusdc.testnet".to_string(),
            token_decimals: 6,
            receiver_id: "hostco.demo.testnet".to_string(),
            amount: "18000000".to_string(),
            memo: "INV-1".to_string(),
            user_request: "pay hostco".to_string(),
            context: vec![],
            block_height: "100000".to_string(),
        };

        let (signal_opt, _) = check(&input, &cfg).unwrap();
        let signal = signal_opt.expect("signal should be present");
        assert_eq!(signal.lookalike_of, None);
        assert_eq!(signal.lookalike_distance, None);
        assert_eq!(signal.prior_payments, 7);
        assert_eq!(signal.is_contract, false);
        assert_eq!(signal.account_age_days, Some(90.0));

        let reasons = counterparty_reasons(&signal);
        assert!(reasons.is_empty());
    }

    #[test]
    fn test_frozen_schema_json_shape() {
        let signal = CounterpartySignal {
            account_age_days: Some(2.1),
            is_contract: false,
            code_changed_recently: false,
            prior_payments: 0,
            lookalike_of: Some("hostco.testnet".to_string()),
            lookalike_distance: Some(1),
        };

        let json = serde_json::to_string(&signal).unwrap();
        assert!(json.contains(r#""account_age_days":2.1"#));
        assert!(json.contains(r#""is_contract":false"#));
        assert!(json.contains(r#""code_changed_recently":false"#));
        assert!(json.contains(r#""prior_payments":0"#));
        assert!(json.contains(r#""lookalike_of":"hostco.testnet""#));
        assert!(json.contains(r#""lookalike_distance":1"#));
    }

    fn input_for(receiver: &str) -> CheckerInput {
        CheckerInput {
            format: crate::formats::INPUT_FORMAT.to_string(),
            request_id: "req-rpc".to_string(),
            guardian_id: "guardian.testnet".to_string(),
            agent_id: "agent.testnet".to_string(),
            token_id: "tusdc.testnet".to_string(),
            token_decimals: 6,
            receiver_id: receiver.to_string(),
            amount: "18000000".to_string(),
            memo: "INV-1".to_string(),
            user_request: "pay hostco".to_string(),
            context: vec![],
            block_height: "100000".to_string(),
        }
    }

    /// Serve one HTTP response with a JSON body on a local port; returns the URL.
    fn serve_once(body: String) -> String {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}/", listener.local_addr().unwrap());
        std::thread::spawn(move || {
            let (mut s, _) = listener.accept().unwrap();
            let mut buf = Vec::new();
            let mut chunk = [0u8; 1024];
            loop {
                let n = s.read(&mut chunk).unwrap();
                buf.extend_from_slice(&chunk[..n]);
                if let Some(pos) = buf.windows(4).position(|w| w == b"\r\n\r\n") {
                    let head = String::from_utf8_lossy(&buf[..pos]).to_ascii_lowercase();
                    let len = head
                        .lines()
                        .find_map(|l| l.strip_prefix("content-length:"))
                        .and_then(|v| v.trim().parse::<usize>().ok())
                        .unwrap_or(0);
                    if buf.len() >= pos + 4 + len {
                        break;
                    }
                }
                if n == 0 {
                    break;
                }
            }
            let resp = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            s.write_all(resp.as_bytes()).unwrap();
        });
        url
    }

    fn view_body(code_hash: &str) -> String {
        serde_json::json!({
            "jsonrpc": "2.0",
            "id": "checker-counterparty",
            "result": {"amount": "1", "code_hash": code_hash, "block_height": 123456789u64}
        })
        .to_string()
    }

    fn rpc_cfg(url: String, profile_code_hash: Option<&str>) -> CounterpartyConfig {
        CounterpartyConfig {
            enabled: true,
            rpc_url: Some(url),
            profile: AgentProfile {
                known_payees: vec![PayeeHistory {
                    account_id: "hostco.demo.testnet".to_string(),
                    prior_payments: 5,
                    is_contract: Some(true),
                    account_age_days: Some(90.0),
                    code_hash: profile_code_hash.map(str::to_string),
                }],
                ..AgentProfile::default()
            },
            ..CounterpartyConfig::default()
        }
    }

    #[test]
    fn code_changed_recently_only_on_profile_code_hash_mismatch() {
        let input = input_for("hostco.demo.testnet");

        let changed = rpc_cfg(serve_once(view_body("NEWHASH")), Some("OLDHASH"));
        let s = check(&input, &changed).unwrap().0.unwrap();
        assert!(s.code_changed_recently);
        assert!(s.is_contract);
        assert_eq!(s.account_age_days, Some(90.0), "age comes from the profile only");

        let same = rpc_cfg(serve_once(view_body("OLDHASH")), Some("OLDHASH"));
        assert!(!check(&input, &same).unwrap().0.unwrap().code_changed_recently);

        let no_profile_hash = rpc_cfg(serve_once(view_body("NEWHASH")), None);
        assert!(!check(&input, &no_profile_hash).unwrap().0.unwrap().code_changed_recently);

        // A lookalike is not an exact profile match, so there is nothing to compare against.
        let lookalike = rpc_cfg(serve_once(view_body("NEWHASH")), Some("OLDHASH"));
        let s = check(&input_for("hostc0.demo.testnet"), &lookalike).unwrap().0.unwrap();
        assert!(!s.code_changed_recently);
    }

    #[test]
    fn plain_account_rpc_sets_is_contract_false_and_no_age() {
        let cfg = CounterpartyConfig {
            enabled: true,
            rpc_url: Some(serve_once(view_body(NEAR_NO_CODE_HASH))),
            ..CounterpartyConfig::default()
        };
        let s = check(&input_for("brand-new.testnet"), &cfg).unwrap().0.unwrap();
        assert!(!s.is_contract);
        assert!(!s.code_changed_recently);
        assert_eq!(s.account_age_days, None, "view_account block_height is not the creation block");
    }

    #[test]
    fn rpc_failure_keeps_profile_values() {
        let mut cfg = rpc_cfg("http://127.0.0.1:9/".to_string(), Some("OLDHASH"));
        cfg.timeout = Duration::from_millis(500);
        let s = check(&input_for("hostco.demo.testnet"), &cfg).unwrap().0.unwrap();
        assert!(s.is_contract, "profile is_contract kept");
        assert!(!s.code_changed_recently);
        assert_eq!(s.account_age_days, Some(90.0));
        assert_eq!(s.prior_payments, 5);
    }

    #[test]
    fn parse_view_account_contract_plain_and_error() {
        let contract = serde_json::json!({"result": {"code_hash": "9xYabc", "amount": "5"}});
        assert_eq!(parse_view_account(&contract).unwrap().code_hash, "9xYabc");

        let plain = serde_json::json!({"result": {"code_hash": NEAR_NO_CODE_HASH, "amount": "5"}});
        assert_eq!(parse_view_account(&plain).unwrap().code_hash, NEAR_NO_CODE_HASH);

        let rpc_error = serde_json::json!({"error": {"name": "HANDLER_ERROR", "cause": {"name": "UNKNOWN_ACCOUNT"}}});
        assert!(parse_view_account(&rpc_error).unwrap_err().contains("RPC error"));

        let query_error = serde_json::json!({"result": {"error": "account foo does not exist while viewing"}});
        assert!(parse_view_account(&query_error).unwrap_err().contains("does not exist"));

        let no_hash = serde_json::json!({"result": {"amount": "5"}});
        assert!(parse_view_account(&no_hash).unwrap_err().contains("code_hash"));
        assert!(parse_view_account(&serde_json::json!({})).is_err());
    }

    #[test]
    fn rpc_url_must_be_https() {
        let with = |u: &'static str| {
            CounterpartyConfig::from_vars(move |k| (k == "COUNTERPARTY_RPC_URL").then(|| u.to_string()))
        };
        assert!(with("http://rpc.testnet.near.org").unwrap_err().starts_with("COUNTERPARTY_RPC_URL"));
        assert!(with("https://").is_err());
        assert_eq!(
            with("https://test.rpc.fastnear.com/").unwrap().rpc_url.as_deref(),
            Some("https://test.rpc.fastnear.com")
        );
        assert_eq!(CounterpartyConfig::from_vars(|_| None).unwrap().timeout, Duration::from_millis(2000));
    }
}
