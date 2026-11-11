//! Wire types mirroring `schemas/`. Field order = schema order.
use serde::{Deserialize, Serialize};

pub const INPUT_FORMAT: &str = "firewall.checker_input.v1";
pub const VERDICT_FORMAT: &str = "firewall.verdict.v1";
pub const RECORD_FORMAT: &str = "firewall.decision_record.v1";

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContextItem {
    pub source: String,
    #[serde(rename = "ref")]
    pub reference: String,
    pub trust: String,
    pub text: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CheckerInput {
    pub format: String,
    pub request_id: String,
    pub guardian_id: String,
    pub agent_id: String,
    pub token_id: String,
    pub token_decimals: u8,
    pub receiver_id: String,
    pub amount: String,
    pub memo: String,
    pub user_request: String,
    pub context: Vec<ContextItem>,
    pub block_height: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Allow,
    Hold,
    Block,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReasonCode {
    StubAllow,
    PolicyViolation,
    InjectionHigh,
    MelonMatch,
    LookalikeReceiver,
    NewReceiver,
    YoungAccount,
    ContractCodeChanged,
    UnusualForAgent,
    JevInjectionDriven,
    JevReceiverRisk,
    AmountMismatch,
    CheckUnavailable,
    ChecksPassed,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Verdict {
    pub format: String,
    pub request_id: String,
    pub receiver_id: String,
    pub token_id: String,
    pub amount: String,
    pub outcome: Outcome,
    pub reasons: Vec<ReasonCode>,
    pub record_sha256: String,
    pub checker_version: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PolicySignal {
    pub ok: bool,
    pub violations: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InjectionItem {
    #[serde(rename = "ref")]
    pub reference: String,
    pub score: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InjectionSignal {
    pub max_score: f64,
    pub per_item: Vec<InjectionItem>,
    pub model: String,
    pub model_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MelonSignal {
    pub masked_call_matches: bool,
    pub llm_model: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CounterpartySignal {
    pub account_age_days: Option<f64>,
    pub is_contract: bool,
    pub code_changed_recently: bool,
    pub prior_payments: u64,
    pub lookalike_of: Option<String>,
    pub lookalike_distance: Option<u32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum JevBackend {
    Jev,
    Llm,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LabelProbabilities {
    #[serde(rename = "A")]
    pub a: f64,
    #[serde(rename = "B")]
    pub b: f64,
    #[serde(rename = "C")]
    pub c: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JevSignal {
    pub backend: JevBackend,
    pub model: String,
    pub unusual: f64,
    pub injection_driven: f64,
    pub receiver_risk: f64,
    pub label: String,
    pub label_probabilities: LabelProbabilities,
}

/// Every key is always serialized; `None` -> explicit `null`.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Signals {
    pub policy: Option<PolicySignal>,
    pub injection: Option<InjectionSignal>,
    pub melon: Option<MelonSignal>,
    pub counterparty: Option<CounterpartySignal>,
    pub jev: Option<JevSignal>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DecisionRecord {
    pub format: String,
    pub input_sha256: String,
    pub request_id: String,
    pub checker_version: String,
    pub outcome: Outcome,
    pub reasons: Vec<ReasonCode>,
    pub signals: Signals,
}
