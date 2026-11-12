//! Counterparty signals (B3): account age, is-contract, code-hash change,
//! prior payments, and lookalike distance over NEAR RPC and agent profile history.
//! Output is the frozen `signals.counterparty` shape.
use crate::formats::{CheckerInput, CounterpartySignal, ReasonCode};
use crate::http;
use serde::{Deserialize, Serialize};
use std::time::Duration;

pub const DEFAULT_MAX_LOOKALIKE_DISTANCE: u32 = 2;
pub const DEFAULT_TIMEOUT_MS: u64 = 5000;
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
    /// Populate default benign payees used across scenarios and benchmarks.
    pub fn with_default_payees() -> Self {
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
        let known_payees = default_names
            .iter()
            .map(|name| PayeeHistory {
                account_id: (*name).to_string(),
                prior_payments: 5,
                is_contract: Some(false),
                account_age_days: Some(180.0),
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
    /// `COUNTERPARTY_TIMEOUT_MS`, default 5000 ms.
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

        let rpc_url = var("COUNTERPARTY_RPC_URL");

        let timeout = if let Some(v) = var("COUNTERPARTY_TIMEOUT_MS") {
            let ms: u64 = v
                .parse()
                .map_err(|e| format!("COUNTERPARTY_TIMEOUT_MS: {e}"))?;
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
                })
                .collect();
            AgentProfile {
                known_payees: payees,
                ..AgentProfile::default()
            }
        } else {
            AgentProfile::with_default_payees()
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
/// - Exact matches return 0
/// - Suffixes match -> full string distance
/// - Unqualified candidate `hostc0` vs `hostco.demo.testnet` compares prefixes
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
        // One has a dot and the other is a base name (e.g. hostc0 vs hostco.demo.testnet)
        prefix_dist
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

#[derive(Debug, Deserialize)]
struct NearRpcResponse {
    result: Option<NearAccountView>,
    #[allow(dead_code)]
    error: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct NearAccountView {
    #[serde(default)]
    pub code_hash: Option<String>,
    #[serde(default)]
    pub block_height: Option<u64>,
    #[serde(default)]
    pub account_age_days: Option<f64>,
    #[serde(default)]
    pub code_changed_recently: Option<bool>,
    #[serde(default)]
    pub is_contract: Option<bool>,
}

fn query_rpc_account(
    rpc_url: &str,
    account_id: &str,
    timeout: Duration,
) -> Result<NearAccountView, String> {
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

    let parsed: NearRpcResponse = serde_json::from_str(&resp.body)
        .map_err(|e| format!("failed to parse RPC response: {e}"))?;

    if let Some(view) = parsed.result {
        Ok(view)
    } else {
        Err(format!("RPC error response: {:?}", parsed.error))
    }
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

    // 2. Account metadata defaults
    let mut is_contract = false;
    let mut code_changed_recently = false;
    let mut account_age_days = None;

    if let LookalikeMatch::Exact(payee) = &lookalike_match {
        if let Some(ic) = payee.is_contract {
            is_contract = ic;
        }
        if let Some(age) = payee.account_age_days {
            account_age_days = Some(age);
        }
    }

    // 3. NEAR RPC query if configured
    if let Some(ref rpc_url) = config.rpc_url {
        match query_rpc_account(rpc_url, &input.receiver_id, config.timeout) {
            Ok(view) => {
                if let Some(ic) = view.is_contract {
                    is_contract = ic;
                } else if let Some(ref code_hash) = view.code_hash {
                    is_contract = code_hash != NEAR_NO_CODE_HASH && !code_hash.is_empty();
                }

                if let Some(cc) = view.code_changed_recently {
                    code_changed_recently = cc;
                }

                if let Some(age) = view.account_age_days {
                    account_age_days = Some(age);
                } else if let Some(bh) = view.block_height {
                    if let Ok(curr) = input.block_height.parse::<u64>() {
                        if curr > bh {
                            account_age_days = Some((curr - bh) as f64 / 86400.0);
                        }
                    }
                }
            }
            Err(_e) => {
                // RPC query failure falls back gracefully without failing closed
            }
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
        let profile = AgentProfile::with_default_payees();
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
        let profile = AgentProfile::with_default_payees();
        let m = find_lookalike("brand-new-contractor-999.testnet", &profile.known_payees, 2);
        assert_eq!(m, LookalikeMatch::Novel);
    }

    #[test]
    fn test_counterparty_config_from_vars() {
        let vars = |k: &str| match k {
            "COUNTERPARTY_ENABLED" => Some("1".to_string()),
            "COUNTERPARTY_MAX_LOOKALIKE_DISTANCE" => Some("3".to_string()),
            "COUNTERPARTY_TIMEOUT_MS" => Some("2500".to_string()),
            "COUNTERPARTY_KNOWN_PAYEES" => Some("payee1.near,payee2.near".to_string()),
            _ => None,
        };

        let cfg = CounterpartyConfig::from_vars(vars).unwrap();
        assert!(cfg.enabled);
        assert_eq!(cfg.max_lookalike_distance, 3);
        assert_eq!(cfg.timeout, Duration::from_millis(2500));
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
}
