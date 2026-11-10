use crate::formats::*;
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
}

impl fmt::Display for CheckerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CheckerError::Parse(m) => write!(f, "invalid input: {m}"),
            CheckerError::Format(m) => write!(f, "unsupported format: {m}"),
            CheckerError::Serialize(m) => write!(f, "serialization failed: {m}"),
            CheckerError::Config(m) => write!(f, "invalid checker config: {m}"),
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

/// Verdict is still the stub allow (fusion is C3); `signals.policy` is the real policy check.
/// Policy config comes from the environment (`POLICY_*`), and when `DECISION_LOG_URL` is set
/// the record is POSTed to the sink (POST failure downgrades `allow` to `hold`).
pub fn decide(input_bytes: &[u8]) -> Result<(Verdict, DecisionRecord), CheckerError> {
    let cfg = PolicyConfig::from_env().map_err(CheckerError::Config)?;
    let sink_cfg = SinkConfig::from_env();
    let (mut verdict, mut record) = decide_with(input_bytes, &cfg)?;
    sink::deliver_with_config(&mut verdict, &mut record, &sink_cfg)?;
    Ok((verdict, record))
}

pub fn decide_with(
    input_bytes: &[u8],
    policy_cfg: &PolicyConfig,
) -> Result<(Verdict, DecisionRecord), CheckerError> {
    let input: CheckerInput =
        serde_json::from_slice(input_bytes).map_err(|e| CheckerError::Parse(e.to_string()))?;
    if input.format != INPUT_FORMAT {
        return Err(CheckerError::Format(input.format));
    }
    let version = env!("CARGO_PKG_VERSION").to_string();
    let reasons = vec![ReasonCode::StubAllow];
    let record = DecisionRecord {
        format: RECORD_FORMAT.to_string(),
        input_sha256: sha256_hex(input_bytes),
        request_id: input.request_id.clone(),
        checker_version: version.clone(),
        outcome: Outcome::Allow,
        reasons: reasons.clone(),
        signals: Signals {
            policy: policy_cfg.enabled.then(|| policy::check(&input, policy_cfg)),
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
}
