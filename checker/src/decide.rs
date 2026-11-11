use crate::counterparty::{self, CounterpartyConfig};
use crate::formats::*;
use crate::injection::{self, InjectionConfig};
use crate::policy::{self, PolicyConfig};
use crate::sink::{self, SinkConfig};
use sha2::{Digest, Sha256};
use std::fmt;

#[derive(Debug)]
pub enum CheckerError {
    Parse(String),
    Format(String),
    Serialize(String),
    Config(String),
    Check(String),
}

impl fmt::Display for CheckerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CheckerError::Parse(m) => write!(f, "invalid input: {m}"),
            CheckerError::Format(m) => write!(f, "unsupported format: {m}"),
            CheckerError::Serialize(m) => write!(f, "serialization failed: {m}"),
            CheckerError::Config(m) => write!(f, "invalid checker config: {m}"),
            CheckerError::Check(m) => write!(f, "check execution failed: {m}"),
        }
    }
}

impl std::error::Error for CheckerError {}

pub(crate) fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

/// Serialize a record exactly as it is hashed and (natively) written to disk.
pub fn record_bytes(record: &DecisionRecord) -> Result<Vec<u8>, CheckerError> {
    serde_json::to_vec(record).map_err(|e| CheckerError::Serialize(e.to_string()))
}

/// Verdict is still the stub allow (fusion is C3); `signals.policy`, `signals.injection` and `signals.counterparty` are real checks.
/// Policy config comes from the environment (`POLICY_*`), injection config from (`INJECTION_*`, `CLASSIFIER_URL`),
/// counterparty config from (`COUNTERPARTY_*`, `AGENT_PROFILE_*`),
/// and when `DECISION_LOG_URL` is set the record is POSTed to the sink (POST failure downgrades `allow` to `hold`).
pub fn decide(input_bytes: &[u8]) -> Result<(Verdict, DecisionRecord), CheckerError> {
    let policy_cfg = PolicyConfig::from_env().map_err(CheckerError::Config)?;
    let injection_cfg = InjectionConfig::from_env().map_err(CheckerError::Config)?;
    let counterparty_cfg = CounterpartyConfig::from_env().map_err(CheckerError::Config)?;
    let sink_cfg = SinkConfig::from_env();
    let (mut verdict, mut record) =
        decide_with_configs(input_bytes, &policy_cfg, &injection_cfg, &counterparty_cfg)?;
    sink::deliver_with_config(&mut verdict, &mut record, &sink_cfg)?;
    Ok((verdict, record))
}

pub fn decide_with(
    input_bytes: &[u8],
    policy_cfg: &PolicyConfig,
) -> Result<(Verdict, DecisionRecord), CheckerError> {
    decide_with_configs(
        input_bytes,
        policy_cfg,
        &InjectionConfig::default(),
        &CounterpartyConfig::default(),
    )
}

pub fn decide_with_configs(
    input_bytes: &[u8],
    policy_cfg: &PolicyConfig,
    injection_cfg: &InjectionConfig,
    counterparty_cfg: &CounterpartyConfig,
) -> Result<(Verdict, DecisionRecord), CheckerError> {
    let input: CheckerInput =
        serde_json::from_slice(input_bytes).map_err(|e| CheckerError::Parse(e.to_string()))?;
    if input.format != INPUT_FORMAT {
        return Err(CheckerError::Format(input.format));
    }
    let version = env!("CARGO_PKG_VERSION").to_string();
    let reasons = vec![ReasonCode::StubAllow];
    let (injection_signal, _latency_ms) =
        injection::check(&input, injection_cfg).map_err(CheckerError::Check)?;
    let (counterparty_signal, _cp_latency_ms) =
        counterparty::check(&input, counterparty_cfg).map_err(CheckerError::Check)?;
    let record = DecisionRecord {
        format: RECORD_FORMAT.to_string(),
        input_sha256: sha256_hex(input_bytes),
        request_id: input.request_id.clone(),
        checker_version: version.clone(),
        outcome: Outcome::Allow,
        reasons: reasons.clone(),
        signals: Signals {
            policy: policy_cfg.enabled.then(|| policy::check(&input, policy_cfg)),
            injection: injection_signal,
            counterparty: counterparty_signal,
            ..Signals::default()
        },
    };
    let record_sha256 = sha256_hex(&record_bytes(&record)?);
    let verdict = Verdict {
        format: VERDICT_FORMAT.to_string(),
        request_id: input.request_id,
        receiver_id: input.receiver_id,
        token_id: input.token_id,
        amount: input.amount,
        outcome: Outcome::Allow,
        reasons,
        record_sha256,
        checker_version: version,
    };
    Ok((verdict, record))
}

#[cfg(test)]
mod tests {
    use super::*;

    const INPUT: &str = include_str!("../../schemas/examples/checker-input.json");
    const VERDICT: &str = include_str!("../../schemas/examples/verdict.json");
    const RECORD: &str = include_str!("../../schemas/examples/decision-record.json");

    const FIXTURE_BENIGN: &str = include_str!("../../schemas/fixtures/decision-record-benign.json");
    const FIXTURE_INJECTION: &str = include_str!("../../schemas/fixtures/decision-record-attack-injection.json");
    const FIXTURE_LOOKALIKE: &str = include_str!("../../schemas/fixtures/decision-record-attack-lookalike.json");
    const FIXTURE_POLICY: &str = include_str!("../../schemas/fixtures/decision-record-attack-policy-violation.json");
    const FIXTURE_HOLD: &str = include_str!("../../schemas/fixtures/decision-record-hold-unusual.json");

    #[test]
    fn verdict_binds_input() {
        let (v, _) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let i: CheckerInput = serde_json::from_str(INPUT).unwrap();
        assert_eq!(v.request_id, i.request_id);
        assert_eq!(v.receiver_id, i.receiver_id);
        assert_eq!(v.token_id, i.token_id);
        assert_eq!(v.amount, i.amount);
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(v.reasons, vec![ReasonCode::StubAllow]);
        assert_eq!(v.checker_version, "0.1.0");
    }

    #[test]
    fn record_hash_matches() {
        let (v, r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let bytes = serde_json::to_vec(&r).unwrap();
        assert_eq!(v.record_sha256, sha256_hex(&bytes));
        assert_eq!(r.input_sha256, sha256_hex(INPUT.as_bytes()));
        let s = String::from_utf8(bytes).unwrap();
        assert!(s.contains(
            r#""signals":{"policy":{"ok":true,"violations":[]},"injection":null,"melon":null,"counterparty":null,"jev":null}"#
        ));
    }

    #[test]
    fn disabled_policy_switch_yields_null_signal() {
        let cfg = PolicyConfig { enabled: false, ..PolicyConfig::default() };
        let (v, r) = decide_with(INPUT.as_bytes(), &cfg).unwrap();
        assert_eq!(r.signals, Signals::default());
        assert_eq!(v.record_sha256, sha256_hex(&serde_json::to_vec(&r).unwrap()));
        assert_eq!(v.outcome, Outcome::Allow);
    }

    #[test]
    fn flagged_policy_does_not_change_verdict() {
        let mut j: serde_json::Value = serde_json::from_str(INPUT).unwrap();
        j["amount"] = "180000000".into();
        j["user_request"] = "Pay the 18 USDC hosting bill.".into();
        let bytes = serde_json::to_vec(&j).unwrap();
        let (v, r) = decide_with(&bytes, &PolicyConfig::default()).unwrap();
        let p = r.signals.policy.unwrap();
        assert!(!p.ok);
        assert_eq!(p.violations, vec![crate::policy::V_AMOUNT_MISMATCH_REQUEST]);
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(v.reasons, vec![ReasonCode::StubAllow]);
        assert!(serde_json::to_vec(&v).unwrap().len() <= 900);
    }

    #[test]
    fn verdict_max_size() {
        let id = "a".repeat(64);
        let (mut v, _) = decide(INPUT.as_bytes()).unwrap();
        v.request_id = u64::MAX.to_string();
        v.receiver_id = id.clone();
        v.token_id = id;
        v.amount = "9".repeat(39);
        v.reasons = vec![ReasonCode::CheckUnavailable; 6];
        v.record_sha256 = "f".repeat(64);
        assert!(serde_json::to_vec(&v).unwrap().len() <= 900);
    }

    #[test]
    fn rejects_bad_format_and_unknown_field() {
        let mut j: serde_json::Value = serde_json::from_str(INPUT).unwrap();
        j["format"] = "firewall.checker_input.v2".into();
        assert!(matches!(
            decide(&serde_json::to_vec(&j).unwrap()),
            Err(CheckerError::Format(_))
        ));
        let mut j: serde_json::Value = serde_json::from_str(INPUT).unwrap();
        j["extra"] = 1.into();
        assert!(matches!(
            decide(&serde_json::to_vec(&j).unwrap()),
            Err(CheckerError::Parse(_))
        ));
        assert!(decide(b"{}").is_err());
    }

    #[test]
    fn examples_parse() {
        decide(INPUT.as_bytes()).unwrap();
        let v: Verdict = serde_json::from_str(VERDICT).unwrap();
        assert_eq!(v.outcome, Outcome::Allow);
        let r: DecisionRecord = serde_json::from_str(RECORD).unwrap();
        assert_eq!(
            r.signals.policy,
            Some(PolicySignal { ok: true, violations: vec![] })
        );
        assert_eq!(r.signals.injection, None);
    }

    #[test]
    fn fixtures_parse() {
        let b: DecisionRecord = serde_json::from_str(FIXTURE_BENIGN).unwrap();
        assert_eq!(b.outcome, Outcome::Allow);
        assert!(b.signals.policy.as_ref().unwrap().ok);
        assert!(b.signals.injection.as_ref().unwrap().max_score < 0.1);
        assert_eq!(b.signals.jev.as_ref().unwrap().backend, JevBackend::Jev);

        let inj: DecisionRecord = serde_json::from_str(FIXTURE_INJECTION).unwrap();
        assert_eq!(inj.outcome, Outcome::Block);
        assert!(inj.signals.injection.as_ref().unwrap().max_score > 0.9);
        assert!(inj.signals.melon.as_ref().unwrap().masked_call_matches);
        assert_eq!(inj.reasons, vec![ReasonCode::InjectionHigh, ReasonCode::JevInjectionDriven]);

        let look: DecisionRecord = serde_json::from_str(FIXTURE_LOOKALIKE).unwrap();
        assert_eq!(look.outcome, Outcome::Block);
        assert_eq!(look.signals.counterparty.as_ref().unwrap().lookalike_of.as_deref(), Some("hostco.testnet"));

        let pol: DecisionRecord = serde_json::from_str(FIXTURE_POLICY).unwrap();
        assert_eq!(pol.outcome, Outcome::Block);
        assert!(!pol.signals.policy.as_ref().unwrap().ok);

        let h: DecisionRecord = serde_json::from_str(FIXTURE_HOLD).unwrap();
        assert_eq!(h.outcome, Outcome::Hold);
        assert_eq!(h.reasons, vec![ReasonCode::UnusualForAgent]);
    }

    #[test]
    fn decide_populates_counterparty_signal() {
        let (v, r) = decide(INPUT.as_bytes()).unwrap();
        assert_eq!(v.outcome, Outcome::Allow);
        let cp = r.signals.counterparty.expect("counterparty signal populated");
        assert_eq!(cp.lookalike_of, None);
        assert_eq!(cp.lookalike_distance, None);
        assert!(cp.prior_payments > 0);
        assert_eq!(cp.is_contract, false);
    }

    #[test]
    fn decide_detects_lookalike_receiver() {
        let mut input_val: serde_json::Value = serde_json::from_str(INPUT).unwrap();
        input_val["receiver_id"] = "hostc0.demo.testnet".into();
        let bytes = serde_json::to_vec(&input_val).unwrap();

        let (_v, r) = decide(&bytes).unwrap();
        let cp = r.signals.counterparty.expect("counterparty signal populated");
        assert!(cp.lookalike_of.as_deref().unwrap_or("").contains("hostco"));
        assert_eq!(cp.lookalike_distance, Some(1));
        assert_eq!(cp.prior_payments, 0);
    }

    #[test]
    fn decide_with_counterparty_disabled_yields_null() {
        let cp_cfg = CounterpartyConfig {
            enabled: false,
            ..CounterpartyConfig::default()
        };
        let (_v, r) = decide_with_configs(
            INPUT.as_bytes(),
            &PolicyConfig::default(),
            &InjectionConfig::default(),
            &cp_cfg,
        )
        .unwrap();
        assert_eq!(r.signals.counterparty, None);
    }
}
