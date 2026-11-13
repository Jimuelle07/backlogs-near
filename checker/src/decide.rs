use crate::counterparty::{self, CounterpartyConfig};
use crate::decision::{self, DecisionClient};
use crate::formats::*;
use crate::fusion::{self, FusionConfig, FusionMode};
use crate::injection::{self, InjectionConfig};
use crate::policy::{self, PolicyConfig};
use crate::provenance;
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

/// The checker pipeline: policy, injection and counterparty checks, the four Jev questions through
/// the `DecisionClient`, then `fusion::fuse` for outcome and reasons (`sdd.md §5`).
/// Configs come from the environment (`POLICY_*`, `INJECTION_*`/`CLASSIFIER_URL`,
/// `COUNTERPARTY_*`/`AGENT_PROFILE_*`, `FUSION_*`); a missing decision client (no keys) leaves
/// `signals.jev` null, which holds. With `FUSION_MODE=code_rules` the client is never built or
/// called and `signals.jev` stays null (evaluation baselines). With `FUSION_MODE=jev` and
/// `CASCADE_ENABLED` the order is policy, counterparty, Jev, and the classifier runs only when
/// Jev's `unusual > FUSION_HOLD_THRESHOLD`; a skipped classifier leaves `signals.injection` null.
/// When `DECISION_LOG_URL` is set the record is POSTed to the sink
/// (POST failure downgrades `allow` to `hold`).
pub fn decide(input_bytes: &[u8]) -> Result<(Verdict, DecisionRecord), CheckerError> {
    let policy_cfg = PolicyConfig::from_env().map_err(CheckerError::Config)?;
    let injection_cfg = InjectionConfig::from_env().map_err(CheckerError::Config)?;
    let counterparty_cfg = CounterpartyConfig::from_env().map_err(CheckerError::Config)?;
    let fusion_cfg = FusionConfig::from_env().map_err(CheckerError::Config)?;
    let sink_cfg = SinkConfig::from_env();
    let client = if fusion_cfg.mode == FusionMode::CodeRules {
        eprintln!("checker warning: FUSION_MODE=code_rules: Jev is not consulted (evaluation mode)");
        None
    } else {
        decision::client_from_env()
            .map_err(|e| eprintln!("checker warning: decision client unavailable: {e}"))
            .ok()
    };
    let (mut verdict, mut record) = decide_with_configs(
        input_bytes,
        &policy_cfg,
        &injection_cfg,
        &counterparty_cfg,
        &fusion_cfg,
        client.as_deref(),
    )?;
    sink::deliver_with_config(&mut verdict, &mut record, &sink_cfg)?;
    Ok((verdict, record))
}

pub fn decide_with(
    input_bytes: &[u8],
    policy_cfg: &PolicyConfig,
    client: Option<&dyn DecisionClient>,
) -> Result<(Verdict, DecisionRecord), CheckerError> {
    decide_with_configs(
        input_bytes,
        policy_cfg,
        &InjectionConfig::default(),
        &CounterpartyConfig::default(),
        &FusionConfig::default(),
        client,
    )
}

pub fn decide_with_configs(
    input_bytes: &[u8],
    policy_cfg: &PolicyConfig,
    injection_cfg: &InjectionConfig,
    counterparty_cfg: &CounterpartyConfig,
    fusion_cfg: &FusionConfig,
    client: Option<&dyn DecisionClient>,
) -> Result<(Verdict, DecisionRecord), CheckerError> {
    let input: CheckerInput =
        serde_json::from_slice(input_bytes).map_err(|e| CheckerError::Parse(e.to_string()))?;
    if input.format != INPUT_FORMAT {
        return Err(CheckerError::Format(input.format));
    }
    let version = env!("CARGO_PKG_VERSION").to_string();
    // Cascade (Jev mode only): the classifier runs after Jev, and only when Jev flags the payment.
    let cascade = fusion_cfg.mode == FusionMode::Jev && fusion_cfg.cascade;
    let injection_signal = if cascade {
        None
    } else {
        injection::check(&input, injection_cfg).map_err(CheckerError::Check)?.0
    };
    let (counterparty_signal, _cp_latency_ms) =
        counterparty::check(&input, counterparty_cfg).map_err(CheckerError::Check)?;
    let mut signals = Signals {
        policy: policy_cfg.enabled.then(|| {
            let mut p = policy::check(&input, policy_cfg);
            p.violations.extend(provenance::check(&input, &counterparty_cfg.profile.known_payees));
            p.ok = p.violations.is_empty();
            p
        }),
        injection: injection_signal,
        melon: None,
        counterparty: counterparty_signal,
        jev: None,
    };
    let fusion_cfg = &effective_fusion(fusion_cfg, counterparty_cfg);
    if fusion_cfg.mode == FusionMode::Jev {
        if let Some(c) = client {
            let jev = c
                .decide(
                    &fusion::jev_state(&input, &signals, fusion_cfg.reference_examples.as_ref()),
                    &decision::firewall_questions(),
                )
                .map_err(|e| e.to_string())
                .and_then(|d| fusion::jev_signal(&d));
            match jev {
                Ok(j) => signals.jev = Some(j),
                Err(e) => eprintln!("checker warning: Jev unavailable: {e}"),
            }
        }
    }
    if cascade && signals.jev.as_ref().is_some_and(|j| j.unusual > fusion_cfg.hold_threshold) {
        signals.injection = injection::check(&input, injection_cfg).map_err(CheckerError::Check)?.0;
    }
    let (outcome, reasons) = fusion::fuse(&signals, fusion_cfg);
    let record = DecisionRecord {
        format: RECORD_FORMAT.to_string(),
        input_sha256: sha256_hex(input_bytes),
        request_id: input.request_id.clone(),
        checker_version: version.clone(),
        outcome,
        reasons: reasons.clone(),
        signals,
    };
    let record_sha256 = sha256_hex(&record_bytes(&record)?);
    let verdict = Verdict {
        format: VERDICT_FORMAT.to_string(),
        request_id: input.request_id,
        receiver_id: input.receiver_id,
        token_id: input.token_id,
        amount: input.amount,
        outcome,
        reasons,
        record_sha256,
        checker_version: version,
    };
    Ok((verdict, record))
}

/// The fusion config in force for this agent: the per-agent hold threshold replaces the global one
/// once the profile shows at least `PER_AGENT_MIN_PAYMENTS` payments in the last 90 days.
pub fn effective_fusion(fusion_cfg: &FusionConfig, counterparty_cfg: &CounterpartyConfig) -> FusionConfig {
    FusionConfig {
        hold_threshold: match (fusion_cfg.agent_hold_threshold, counterparty_cfg.profile.payments_last_90d) {
            (Some(t), Some(n)) if n >= fusion::PER_AGENT_MIN_PAYMENTS => t,
            _ => fusion_cfg.hold_threshold,
        },
        ..fusion_cfg.clone()
    }
}

/// Re-fuse a stored `DecisionRecord`'s signals under the given configs: outcome and reasons only,
/// no checks run and no decision client built. Lets one recorded Jev run be scored at other thresholds.
pub fn refuse_with(
    record_bytes: &[u8],
    fusion_cfg: &FusionConfig,
    counterparty_cfg: &CounterpartyConfig,
) -> Result<(Outcome, Vec<ReasonCode>), CheckerError> {
    let record: DecisionRecord =
        serde_json::from_slice(record_bytes).map_err(|e| CheckerError::Parse(e.to_string()))?;
    Ok(fusion::fuse(&record.signals, &effective_fusion(fusion_cfg, counterparty_cfg)))
}

/// `refuse_with` under the configs from the environment (`FUSION_*`, `COUNTERPARTY_*`/`AGENT_PROFILE_*`).
pub fn refuse(record_bytes: &[u8]) -> Result<(Outcome, Vec<ReasonCode>), CheckerError> {
    let counterparty_cfg = CounterpartyConfig::from_env().map_err(CheckerError::Config)?;
    let fusion_cfg = FusionConfig::from_env().map_err(CheckerError::Config)?;
    refuse_with(record_bytes, &fusion_cfg, &counterparty_cfg)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::counterparty::AgentProfile;
    use crate::fusion::testing::FixedClient;

    fn counterparty_on() -> CounterpartyConfig {
        CounterpartyConfig {
            enabled: true,
            profile: AgentProfile::with_default_payees_in(None),
            ..CounterpartyConfig::default()
        }
    }

    fn decide_counterparty(
        input: &[u8],
        cfg: &CounterpartyConfig,
    ) -> (Verdict, DecisionRecord) {
        decide_with_configs(
            input,
            &PolicyConfig::default(),
            &InjectionConfig::default(),
            cfg,
            &FusionConfig::default(),
            Some(&FixedClient::benign()),
        )
        .unwrap()
    }

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
        let (v, _) =
            decide_with(INPUT.as_bytes(), &PolicyConfig::default(), Some(&FixedClient::benign())).unwrap();
        let i: CheckerInput = serde_json::from_str(INPUT).unwrap();
        assert_eq!(v.request_id, i.request_id);
        assert_eq!(v.receiver_id, i.receiver_id);
        assert_eq!(v.token_id, i.token_id);
        assert_eq!(v.amount, i.amount);
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(v.reasons, vec![ReasonCode::ChecksPassed]);
        assert_eq!(v.checker_version, "0.1.0");
    }

    #[test]
    fn record_hash_matches() {
        let (v, r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default(), None).unwrap();
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
        let (v, r) = decide_with(INPUT.as_bytes(), &cfg, None).unwrap();
        assert_eq!(r.signals, Signals::default());
        assert_eq!(v.record_sha256, sha256_hex(&serde_json::to_vec(&r).unwrap()));
        assert_eq!(v.outcome, Outcome::Hold);
    }

    #[test]
    fn policy_violation_with_normal_jev_holds() {
        let mut j: serde_json::Value = serde_json::from_str(INPUT).unwrap();
        j["amount"] = "180000000".into();
        j["user_request"] = "Pay the 18 USDC hosting bill.".into();
        let bytes = serde_json::to_vec(&j).unwrap();
        let (v, r) =
            decide_with(&bytes, &PolicyConfig::default(), Some(&FixedClient::benign())).unwrap();
        let p = r.signals.policy.unwrap();
        assert!(!p.ok);
        assert_eq!(p.violations, vec![crate::policy::V_AMOUNT_MISMATCH_REQUEST]);
        assert_eq!(v.outcome, Outcome::Hold);
        assert_eq!(v.reasons, vec![ReasonCode::PolicyViolation, ReasonCode::AmountMismatch]);
        assert!(serde_json::to_vec(&v).unwrap().len() <= 900);
    }

    #[test]
    fn jev_error_holds_with_check_unavailable() {
        let (v, r) =
            decide_with(INPUT.as_bytes(), &PolicyConfig::default(), Some(&FixedClient(Err(529)))).unwrap();
        assert_eq!(v.outcome, Outcome::Hold);
        assert_eq!(r.outcome, Outcome::Hold);
        assert_eq!(v.reasons[0], ReasonCode::CheckUnavailable);
        assert_eq!(r.signals.jev, None);
        assert_eq!(v.record_sha256, sha256_hex(&record_bytes(&r).unwrap()));
    }

    #[test]
    fn jev_answers_recorded() {
        let (_, r) =
            decide_with(INPUT.as_bytes(), &PolicyConfig::default(), Some(&FixedClient::benign())).unwrap();
        assert_eq!(
            r.signals.jev,
            Some(JevSignal {
                backend: JevBackend::Jev,
                model: "jev-latest".into(),
                unusual: 0.04,
                injection_driven: 0.01,
                receiver_risk: 0.02,
                label: "A".into(),
                label_probabilities: LabelProbabilities { a: 0.96, b: 0.03, c: 0.01 },
            })
        );
    }

    #[test]
    fn verdict_max_size() {
        let id = "a".repeat(64);
        let (mut v, _) = decide_with(INPUT.as_bytes(), &PolicyConfig::default(), None).unwrap();
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
        decide_with(INPUT.as_bytes(), &PolicyConfig::default(), None).unwrap();
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
        let (v, r) = decide_counterparty(INPUT.as_bytes(), &counterparty_on());
        assert_eq!(v.outcome, Outcome::Allow);
        let cp = r.signals.counterparty.expect("counterparty signal populated");
        assert_eq!(cp.lookalike_of, None);
        assert_eq!(cp.lookalike_distance, None);
        assert!(cp.prior_payments > 0);
        assert!(!cp.is_contract);
    }

    #[test]
    fn decide_detects_lookalike_receiver() {
        let mut input_val: serde_json::Value = serde_json::from_str(INPUT).unwrap();
        input_val["receiver_id"] = "hostc0.demo.testnet".into();
        let bytes = serde_json::to_vec(&input_val).unwrap();

        let (v, r) = decide_counterparty(&bytes, &counterparty_on());
        let cp = r.signals.counterparty.expect("counterparty signal populated");
        assert!(cp.lookalike_of.as_deref().unwrap_or("").contains("hostco"));
        assert_eq!(cp.lookalike_distance, Some(1));
        assert_eq!(cp.prior_payments, 0);
        assert!(v.reasons.contains(&ReasonCode::LookalikeReceiver));
    }

    #[test]
    fn decide_with_counterparty_disabled_yields_null() {
        let cp_cfg = CounterpartyConfig { enabled: false, ..CounterpartyConfig::default() };
        let (_v, r) = decide_with_configs(
            INPUT.as_bytes(),
            &PolicyConfig::default(),
            &InjectionConfig::default(),
            &cp_cfg,
            &FusionConfig::default(),
            None,
        )
        .unwrap();
        assert_eq!(r.signals.counterparty, None);
    }

    struct PanicClient;
    impl DecisionClient for PanicClient {
        fn decide(
            &self,
            _state: &serde_json::Value,
            _questions: &std::collections::BTreeMap<String, crate::decision::Question>,
        ) -> Result<crate::decision::Decision, crate::decision::DecisionError> {
            panic!("code_rules mode must not call the decision client");
        }
    }

    fn client_with_unusual(unusual: f64) -> FixedClient {
        let mut d = crate::fusion::testing::benign_decision();
        d.answers.insert("unusual".into(), crate::decision::Answer::Noul { noul: unusual });
        FixedClient(Ok(d))
    }

    /// A classifier that is enabled but unreachable: calling it makes `decide` return an error.
    fn unreachable_classifier() -> InjectionConfig {
        InjectionConfig {
            enabled: true,
            classifier_url: Some("http://127.0.0.1:9/score".into()),
            timeout: std::time::Duration::from_millis(500),
            ..InjectionConfig::default()
        }
    }

    fn decide_cascade(client: &dyn DecisionClient) -> Result<(Verdict, DecisionRecord), CheckerError> {
        decide_with_configs(
            INPUT.as_bytes(),
            &PolicyConfig::default(),
            &unreachable_classifier(),
            &CounterpartyConfig::default(),
            &FusionConfig { cascade: true, ..FusionConfig::default() },
            Some(client),
        )
    }

    #[test]
    fn cascade_skips_classifier_when_jev_is_low() {
        let (v, r) = decide_cascade(&client_with_unusual(0.04)).expect("classifier must not run");
        assert_eq!(r.signals.injection, None);
        assert!(r.signals.jev.is_some());
        assert_eq!(v.outcome, Outcome::Allow);
    }

    #[test]
    fn cascade_runs_classifier_when_jev_is_high() {
        let err = decide_cascade(&client_with_unusual(0.9)).expect_err("classifier attempted");
        assert!(matches!(&err, CheckerError::Check(m) if m.contains("injection classifier")), "{err}");
    }

    #[test]
    fn cascade_skips_classifier_without_jev() {
        let (v, r) = decide_cascade(&FixedClient(Err(529))).expect("classifier must not run");
        assert_eq!(r.signals.injection, None);
        assert_eq!(v.outcome, Outcome::Hold);
        assert_eq!(v.reasons[0], ReasonCode::CheckUnavailable);
    }

    #[test]
    fn no_cascade_runs_classifier_first() {
        let err = decide_with_configs(
            INPUT.as_bytes(),
            &PolicyConfig::default(),
            &unreachable_classifier(),
            &CounterpartyConfig::default(),
            &FusionConfig::default(),
            Some(&client_with_unusual(0.04)),
        )
        .expect_err("classifier runs before Jev without the cascade");
        assert!(matches!(err, CheckerError::Check(_)));
    }

    #[test]
    fn code_rules_never_calls_the_client() {
        let cfg = FusionConfig { mode: FusionMode::CodeRules, ..FusionConfig::default() };
        let (v, r) = decide_with_configs(
            INPUT.as_bytes(),
            &PolicyConfig::default(),
            &InjectionConfig::default(),
            &CounterpartyConfig::default(),
            &cfg,
            Some(&PanicClient),
        )
        .unwrap();
        assert_eq!(r.signals.jev, None);
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(v.reasons, vec![ReasonCode::ChecksPassed]);
    }

    #[test]
    fn agent_hold_threshold_applies_only_with_enough_payments() {
        let run = |payments: u32| {
            let cp = CounterpartyConfig {
                profile: AgentProfile {
                    payments_last_90d: Some(payments),
                    ..AgentProfile::with_default_payees_in(None)
                },
                ..CounterpartyConfig::default()
            };
            let fusion = FusionConfig {
                hold_threshold: 0.84,
                agent_hold_threshold: Some(0.70),
                ..FusionConfig::default()
            };
            decide_with_configs(
                INPUT.as_bytes(),
                &PolicyConfig::default(),
                &InjectionConfig::default(),
                &cp,
                &fusion,
                Some(&client_with_unusual(0.80)),
            )
            .unwrap()
            .0
            .outcome
        };
        assert_eq!(run(120), Outcome::Hold);
        assert_eq!(run(12), Outcome::Allow);
    }

    #[test]
    fn refuse_with_applies_the_given_hold_threshold() {
        let cp = CounterpartyConfig::default();
        let at = |hold_threshold: f64| {
            let cfg = FusionConfig { hold_threshold, ..FusionConfig::default() };
            refuse_with(FIXTURE_HOLD.as_bytes(), &cfg, &cp).unwrap()
        };
        assert_eq!(at(0.84).0, Outcome::Allow);
        assert_eq!(at(0.5).0, Outcome::Hold);
        assert!(refuse_with(b"{}", &FusionConfig::default(), &cp).is_err());
    }
}
