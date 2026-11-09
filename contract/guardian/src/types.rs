//! Wire types mirroring `schemas/`. Field order is the schema order.
use near_sdk::json_types::{U128, U64};
use near_sdk::{near, AccountId, YieldId};

pub const CHECKER_INPUT_FORMAT: &str = "firewall.checker_input.v1";
pub const VERDICT_FORMAT: &str = "firewall.verdict.v1";

#[near(serializers = [json, borsh])]
#[derive(Clone, Debug, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Source {
    Email,
    XReply,
    Web,
    Memory,
    Tool,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Debug, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Trust {
    Trusted,
    Untrusted,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Debug, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ContextItem {
    pub source: Source,
    #[serde(rename = "ref")]
    pub reference: String,
    pub trust: Trust,
    pub text: String,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Debug, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CheckerInput {
    pub format: String,
    pub request_id: U64,
    pub guardian_id: AccountId,
    pub agent_id: AccountId,
    pub token_id: AccountId,
    pub token_decimals: u8,
    pub receiver_id: AccountId,
    pub amount: U128,
    pub memo: String,
    pub user_request: String,
    pub context: Vec<ContextItem>,
    pub block_height: U64,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Allow,
    Hold,
    Block,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
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
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Debug, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Verdict {
    pub format: String,
    pub request_id: U64,
    pub receiver_id: AccountId,
    pub token_id: AccountId,
    pub amount: U128,
    pub outcome: Outcome,
    pub reasons: Vec<ReasonCode>,
    pub record_sha256: String,
    pub checker_version: String,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ReceiptStatus {
    Paying,
    Paid,
    TransferFailed,
    Refused,
    Held,
    TimedOut,
}

#[near(serializers = [json, borsh])]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Receipt {
    pub request_id: U64,
    pub client_ref: String,
    pub receiver_id: AccountId,
    pub amount: U128,
    pub input_sha256: String,
    pub outcome: Option<Outcome>,
    pub reasons: Vec<ReasonCode>,
    pub record_sha256: Option<String>,
    pub checker_version: Option<String>,
    pub status: ReceiptStatus,
    pub requested_block: U64,
    pub decided_block: U64,
}

/// Stored per in-flight request (borsh only).
#[near(serializers = [borsh])]
pub struct Pending {
    pub yield_id: YieldId,
    pub client_ref: String,
    pub receiver_id: AccountId,
    pub amount: U128,
    pub checker_input: String,
    pub input_sha256: String,
    pub requested_block: u64,
    /// UTC day index the daily-cap reservation was charged to.
    pub charged_day: u64,
}

#[near(serializers = [json])]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PendingView {
    pub request_id: U64,
    pub client_ref: String,
    pub checker_input: String,
    pub input_sha256: String,
    pub requested_block: U64,
}

#[near(serializers = [json])]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Config {
    pub owner_id: AccountId,
    pub agent_id: AccountId,
    pub token_id: AccountId,
    pub token_decimals: u8,
    pub checker_id: AccountId,
    pub per_payment_cap: U128,
    pub daily_cap: U128,
}

/// Escrowed payment awaiting its release window (borsh only).
#[near(serializers = [borsh])]
pub struct Held {
    pub receiver_id: AccountId,
    pub amount: U128,
    pub release_at_ns: u64,
    pub charged_day: u64,
}

#[near(serializers = [json])]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HeldView {
    pub request_id: U64,
    pub receiver_id: AccountId,
    pub amount: U128,
    pub release_at_ns: U64,
}
