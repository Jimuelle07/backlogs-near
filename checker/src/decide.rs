use crate::formats::*;
use sha2::{Digest, Sha256};
use std::fmt;

#[derive(Debug)]
pub enum CheckerError {
    Parse(String),
    Format(String),
    Serialize(String),
}

impl fmt::Display for CheckerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CheckerError::Parse(m) => write!(f, "invalid input: {m}"),
            CheckerError::Format(m) => write!(f, "unsupported format: {m}"),
            CheckerError::Serialize(m) => write!(f, "serialization failed: {m}"),
        }
    }
}

impl std::error::Error for CheckerError {}

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

/// Serialize a record exactly as it is hashed and (natively) written to disk.
pub fn record_bytes(record: &DecisionRecord) -> Result<Vec<u8>, CheckerError> {
    serde_json::to_vec(record).map_err(|e| CheckerError::Serialize(e.to_string()))
}

/// Stub: hard-coded allow. Tue/Wed checks replace the body.
pub fn decide(input_bytes: &[u8]) -> Result<(Verdict, DecisionRecord), CheckerError> {
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
        signals: Signals::default(),
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
        let (v, _) = decide(INPUT.as_bytes()).unwrap();
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
        let (v, r) = decide(INPUT.as_bytes()).unwrap();
        let bytes = serde_json::to_vec(&r).unwrap();
        assert_eq!(v.record_sha256, sha256_hex(&bytes));
        assert_eq!(r.input_sha256, sha256_hex(INPUT.as_bytes()));
        let s = String::from_utf8(bytes).unwrap();
        assert!(s.contains(
            r#""signals":{"policy":null,"injection":null,"melon":null,"counterparty":null,"jev":null}"#
        ));
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
        assert_eq!(r.signals, Signals::default());
    }
}
