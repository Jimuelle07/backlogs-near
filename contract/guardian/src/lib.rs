//! Guardian: holds tUSDC, takes payment requests from the agent, yields until the checker
//! submits a verdict bound to the request, then pays / refuses / holds and writes a receipt.
pub mod types;
pub mod validate;

use near_contract_standards::fungible_token::core::ext_ft_core;
use near_sdk::json_types::{U128, U64};
use near_sdk::serde_json::{self, json};
use near_sdk::store::{IterableMap, LookupMap};
use near_sdk::{
    env, near, require, AccountId, BorshStorageKey, Gas, GasWeight, NearToken, PanicOnDefault,
    Promise, PromiseError, PromiseOrValue,
};

use types::*;

pub const MAX_CONTEXT_BYTES: usize = validate::MAX_CONTEXT_BYTES;
pub const MAX_PENDING: u32 = 16;
pub const CALLBACK_GAS: Gas = Gas::from_tgas(40);
pub const FT_TRANSFER_GAS: Gas = Gas::from_tgas(10);
pub const TRANSFER_DONE_GAS: Gas = Gas::from_tgas(5);
const MAX_LIST: u64 = 50;
pub const PER_PAYMENT_CAP_WHOLE: u128 = 200;
pub const DAILY_CAP_WHOLE: u128 = 500;
pub const NANOS_PER_DAY: u64 = 86_400_000_000_000;

#[derive(BorshStorageKey)]
#[near]
enum StorageKey {
    Pending,
    Receipts,
    Refs,
    Held,
}

#[derive(PanicOnDefault)]
#[near(contract_state)]
pub struct Guardian {
    owner_id: AccountId,
    agent_id: AccountId,
    token_id: AccountId,
    token_decimals: u8,
    checker_id: AccountId,
    next_request_id: u64,
    pending: IterableMap<u64, Pending>,
    receipts: IterableMap<u64, Receipt>,
    refs: LookupMap<String, u64>,
    held: IterableMap<u64, Held>,
    spend_day: u64,
    spent_today: u128,
}

fn emit(event: &str, data: serde_json::Value) {
    let e = json!({
        "standard": "payment_firewall",
        "version": "1.0.0",
        "event": event,
        "data": [data],
    });
    env::log_str(&format!("EVENT_JSON:{e}"));
}

#[near]
impl Guardian {
    #[init]
    pub fn new(
        owner_id: AccountId,
        agent_id: AccountId,
        token_id: AccountId,
        token_decimals: u8,
        checker_id: AccountId,
    ) -> Self {
        Self {
            owner_id,
            agent_id,
            token_id,
            token_decimals,
            checker_id,
            next_request_id: 1,
            pending: IterableMap::new(StorageKey::Pending),
            receipts: IterableMap::new(StorageKey::Receipts),
            refs: LookupMap::new(StorageKey::Refs),
            held: IterableMap::new(StorageKey::Held),
            spend_day: 0,
            spent_today: 0,
        }
    }

    fn unit(&self) -> u128 {
        10u128.pow(self.token_decimals as u32)
    }

    fn per_payment_cap(&self) -> u128 {
        PER_PAYMENT_CAP_WHOLE * self.unit()
    }

    fn daily_cap(&self) -> u128 {
        DAILY_CAP_WHOLE * self.unit()
    }

    /// Rolls the daily counter when the UTC day changed; returns today's index.
    fn roll_day(&mut self) -> u64 {
        let today = env::block_timestamp() / NANOS_PER_DAY;
        if today != self.spend_day {
            self.spend_day = today;
            self.spent_today = 0;
        }
        today
    }

    /// Releases a reservation made on `charged_day`; earlier days have already rolled off.
    fn unreserve(&mut self, charged_day: u64, amount: u128) {
        if charged_day == self.spend_day {
            self.spent_today = self.spent_today.saturating_sub(amount);
        }
    }

    /// NEP-141 receiver: only the owner can fund the Guardian; everyone else is refunded.
    pub fn ft_on_transfer(
        &mut self,
        sender_id: AccountId,
        amount: U128,
        #[allow(unused_variables)] msg: String,
    ) -> PromiseOrValue<U128> {
        require!(env::predecessor_account_id() == self.token_id, "Unsupported token");
        if sender_id == self.owner_id {
            PromiseOrValue::Value(U128(0))
        } else {
            PromiseOrValue::Value(amount)
        }
    }

    pub fn request_payment(
        &mut self,
        client_ref: String,
        receiver_id: AccountId,
        amount: U128,
        memo: String,
        user_request: String,
        context: Vec<ContextItem>,
    ) -> Promise {
        require!(
            env::predecessor_account_id() == self.agent_id,
            "Only the agent can request payments"
        );
        require!(amount.0 > 0, "Amount must be positive");
        let context_bytes = serde_json::to_vec(&context).unwrap_or_else(|_| env::abort()).len();
        require!(context_bytes <= MAX_CONTEXT_BYTES, "Context too large");
        require!(context.len() <= validate::MAX_CONTEXT_ITEMS, "Too many items");
        require!(!self.refs.contains_key(&client_ref), "Duplicate client_ref");
        require!(self.pending.len() < MAX_PENDING, "Too many pending requests");
        require!(validate::valid_client_ref(&client_ref), "Invalid client_ref");
        require!(validate::valid_memo(&memo), "Invalid memo");
        require!(validate::valid_user_request(&user_request), "Invalid user_request");
        require!(
            context.iter().all(|c| validate::valid_context_ref(&c.reference)),
            "Invalid context"
        );
        require!(
            receiver_id.as_str().len() >= 2 && receiver_id.as_str().len() <= 64,
            "Invalid receiver_id"
        );
        require!(amount.0 <= self.per_payment_cap(), "Amount exceeds per-payment cap");
        let day = self.roll_day();
        require!(self.spent_today + amount.0 <= self.daily_cap(), "Daily cap reached");
        self.spent_today += amount.0;

        let request_id = self.next_request_id;
        self.next_request_id += 1;
        let requested_block = env::block_height();

        let input = CheckerInput {
            format: CHECKER_INPUT_FORMAT.to_string(),
            request_id: U64(request_id),
            guardian_id: env::current_account_id(),
            agent_id: self.agent_id.clone(),
            token_id: self.token_id.clone(),
            token_decimals: self.token_decimals,
            receiver_id: receiver_id.clone(),
            amount,
            memo,
            user_request,
            context,
            block_height: U64(requested_block),
        };
        let checker_input = serde_json::to_string(&input).unwrap_or_else(|_| env::abort());
        let input_sha256 = hex::encode(env::sha256(checker_input.as_bytes()));

        let args = serde_json::to_vec(&json!({ "request_id": U64(request_id) }))
            .unwrap_or_else(|_| env::abort());
        let (promise, yield_id) =
            Promise::new_yield("on_verdict", args, CALLBACK_GAS, GasWeight(0));

        self.pending.insert(
            request_id,
            Pending {
                yield_id,
                client_ref: client_ref.clone(),
                receiver_id: receiver_id.clone(),
                amount,
                checker_input,
                input_sha256: input_sha256.clone(),
                requested_block,
                charged_day: day,
            },
        );
        self.refs.insert(client_ref.clone(), request_id);

        emit(
            "payment_requested",
            json!({
                "request_id": U64(request_id),
                "client_ref": client_ref,
                "receiver_id": receiver_id,
                "amount": amount,
                "input_sha256": input_sha256,
            }),
        );
        promise
    }

    /// Called by the checker (relayer / OutLayer). Validates the binding, then resumes the yield.
    pub fn submit_verdict(&mut self, request_id: U64, verdict: Verdict) {
        require!(
            env::predecessor_account_id() == self.checker_id,
            "Only the checker can submit verdicts"
        );
        let pending = self.pending.get(&request_id.0).unwrap_or_else(|| env::panic_str("Unknown request"));
        if let Err(field) = validate::binds(pending, &verdict, request_id, &self.token_id) {
            env::panic_str(&format!("Verdict does not match request: {field}"));
        }
        let bytes = serde_json::to_vec(&verdict).unwrap_or_else(|_| env::abort());
        if pending.yield_id.resume(bytes).is_err() {
            env::panic_str("Request already resolved");
        }
    }

    /// Yield callback. Never panics.
    #[private]
    pub fn on_verdict(
        &mut self,
        request_id: U64,
        #[callback_result] verdict: Result<Verdict, PromiseError>,
    ) -> PromiseOrValue<ReceiptStatus> {
        let id = request_id.0;
        let Some(pending) = self.pending.remove(&id) else {
            return PromiseOrValue::Value(ReceiptStatus::TimedOut);
        };
        let mut receipt = Receipt {
            request_id,
            client_ref: pending.client_ref,
            receiver_id: pending.receiver_id.clone(),
            amount: pending.amount,
            input_sha256: pending.input_sha256,
            outcome: None,
            reasons: vec![],
            record_sha256: None,
            checker_version: None,
            status: ReceiptStatus::TimedOut,
            requested_block: U64(pending.requested_block),
            decided_block: U64(env::block_height()),
        };
        let mut transfer = None;
        let mut release_at_ns: Option<U64> = None;
        match verdict {
            Ok(v) => {
                receipt.outcome = Some(v.outcome);
                receipt.reasons = v.reasons;
                receipt.record_sha256 = Some(v.record_sha256);
                receipt.checker_version = Some(v.checker_version);
                receipt.status = match v.outcome {
                    Outcome::Block => {
                        self.unreserve(pending.charged_day, pending.amount.0);
                        ReceiptStatus::Refused
                    }
                    Outcome::Hold => {
                        let at = env::block_timestamp()
                            + validate::hold_window_ns(pending.amount.0, self.token_decimals);
                        self.held.insert(
                            id,
                            Held {
                                receiver_id: pending.receiver_id.clone(),
                                amount: pending.amount,
                                release_at_ns: at,
                                charged_day: pending.charged_day,
                            },
                        );
                        release_at_ns = Some(U64(at));
                        ReceiptStatus::Held
                    }
                    Outcome::Allow => {
                        transfer = Some(self.pay(
                            request_id,
                            pending.receiver_id,
                            pending.amount,
                            pending.charged_day,
                        ));
                        ReceiptStatus::Paying
                    }
                };
            }
            Err(_) => self.unreserve(pending.charged_day, pending.amount.0),
        }
        let status = receipt.status;
        emit(
            "payment_decided",
            json!({
                "request_id": request_id,
                "outcome": receipt.outcome,
                "status": status,
                "record_sha256": receipt.record_sha256,
                "release_at_ns": release_at_ns,
            }),
        );
        self.receipts.insert(id, receipt);
        match transfer {
            Some(p) => PromiseOrValue::Promise(p),
            None => PromiseOrValue::Value(status),
        }
    }

    fn pay(
        &self,
        request_id: U64,
        receiver_id: AccountId,
        amount: U128,
        charged_day: u64,
    ) -> Promise {
        ext_ft_core::ext(self.token_id.clone())
            .with_attached_deposit(NearToken::from_yoctonear(1))
            .with_static_gas(FT_TRANSFER_GAS)
            .ft_transfer(
                receiver_id,
                amount,
                Some(format!("firewall request {}", request_id.0)),
            )
            .then(
                Self::ext(env::current_account_id())
                    .with_static_gas(TRANSFER_DONE_GAS)
                    .on_transfer_done(request_id, U64(charged_day), amount),
            )
    }

    #[private]
    pub fn on_transfer_done(
        &mut self,
        request_id: U64,
        charged_day: U64,
        amount: U128,
    ) -> ReceiptStatus {
        let status = if env::promise_result_checked(0, 0).is_ok() {
            ReceiptStatus::Paid
        } else {
            self.unreserve(charged_day.0, amount.0);
            ReceiptStatus::TransferFailed
        };
        if let Some(r) = self.receipts.get_mut(&request_id.0) {
            r.status = status;
        }
        status
    }

    /// Permissionless crank: pays out a hold once its window has passed.
    pub fn release_held(&mut self, request_id: U64) -> Promise {
        let id = request_id.0;
        let h = self.held.get(&id).unwrap_or_else(|| env::panic_str("Unknown hold"));
        require!(env::block_timestamp() >= h.release_at_ns, "Hold window not over");
        let h = self.held.remove(&id).unwrap_or_else(|| env::abort());
        if let Some(r) = self.receipts.get_mut(&id) {
            r.status = ReceiptStatus::Paying;
            r.decided_block = U64(env::block_height());
        }
        emit("hold_released", json!({ "request_id": request_id }));
        self.pay(request_id, h.receiver_id, h.amount, h.charged_day)
    }

    /// Owner or checker cancels a hold: receipt becomes `refused` (outcome stays `hold`).
    pub fn cancel_held(&mut self, request_id: U64) {
        let caller = env::predecessor_account_id();
        require!(
            caller == self.owner_id || caller == self.checker_id,
            "Only the owner or checker can cancel holds"
        );
        let id = request_id.0;
        let h = self.held.remove(&id).unwrap_or_else(|| env::panic_str("Unknown hold"));
        if let Some(r) = self.receipts.get_mut(&id) {
            r.status = ReceiptStatus::Refused;
        }
        self.unreserve(h.charged_day, h.amount.0);
        emit("hold_cancelled", json!({ "request_id": request_id }));
    }

    pub fn get_config(&self) -> Config {
        Config {
            owner_id: self.owner_id.clone(),
            agent_id: self.agent_id.clone(),
            token_id: self.token_id.clone(),
            token_decimals: self.token_decimals,
            checker_id: self.checker_id.clone(),
            per_payment_cap: U128(self.per_payment_cap()),
            daily_cap: U128(self.daily_cap()),
        }
    }

    pub fn get_daily_spent(&self) -> U128 {
        if env::block_timestamp() / NANOS_PER_DAY != self.spend_day {
            U128(0)
        } else {
            U128(self.spent_today)
        }
    }

    pub fn get_pending(&self, from_index: u64, limit: u64) -> Vec<PendingView> {
        self.pending
            .iter()
            .skip(from_index as usize)
            .take(limit.min(MAX_LIST) as usize)
            .map(|(id, p)| PendingView {
                request_id: U64(*id),
                client_ref: p.client_ref.clone(),
                checker_input: p.checker_input.clone(),
                input_sha256: p.input_sha256.clone(),
                requested_block: U64(p.requested_block),
            })
            .collect()
    }

    pub fn get_held(&self, from_index: u64, limit: u64) -> Vec<HeldView> {
        self.held
            .iter()
            .skip(from_index as usize)
            .take(limit.min(MAX_LIST) as usize)
            .map(|(id, h)| HeldView {
                request_id: U64(*id),
                receiver_id: h.receiver_id.clone(),
                amount: h.amount,
                release_at_ns: U64(h.release_at_ns),
            })
            .collect()
    }

    pub fn get_receipt(&self, request_id: U64) -> Option<Receipt> {
        self.receipts.get(&request_id.0).cloned()
    }

    pub fn get_receipt_by_ref(&self, client_ref: String) -> Option<Receipt> {
        self.refs.get(&client_ref).and_then(|id| self.receipts.get(id)).cloned()
    }

    pub fn list_receipts(&self, from_index: u64, limit: u64) -> Vec<Receipt> {
        self.receipts
            .iter()
            .skip(from_index as usize)
            .take(limit.min(MAX_LIST) as usize)
            .map(|(_, r)| r.clone())
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use near_sdk::test_utils::VMContextBuilder;
    use near_sdk::{testing_env, YieldId};

    const CHECKER_INPUT_EXAMPLE: &str = include_str!("../../../schemas/examples/checker-input.json");
    const VERDICT_EXAMPLE: &str = include_str!("../../../schemas/examples/verdict.json");
    const HASH: &str = "4065a20c2a9ecfa5bf74f9f6f3798eae85afc812f31cd28281412d7e1d262e5c";

    fn acct(s: &str) -> AccountId {
        s.parse().unwrap()
    }

    fn set_ctx(predecessor: &str) {
        set_ctx_at(predecessor, 0);
    }

    fn set_ctx_at(predecessor: &str, timestamp_ns: u64) {
        testing_env!(VMContextBuilder::new()
            .current_account_id(acct("guardian.testnet"))
            .predecessor_account_id(acct(predecessor))
            .block_height(7)
            .block_timestamp(timestamp_ns)
            .build());
    }

    fn new_guardian() -> Guardian {
        set_ctx("owner.testnet");
        Guardian::new(
            acct("owner.testnet"),
            acct("agent.testnet"),
            acct("tusdc.testnet"),
            6,
            acct("checker.testnet"),
        )
    }

    fn item(text: String) -> ContextItem {
        ContextItem {
            source: Source::Email,
            reference: "email:1".into(),
            trust: Trust::Untrusted,
            text,
        }
    }

    /// One context item whose serialized `context` array is exactly `bytes` long.
    fn ctx_of_bytes(bytes: usize) -> Vec<ContextItem> {
        let base = serde_json::to_vec(&vec![item(String::new())]).unwrap().len();
        let c = vec![item("a".repeat(bytes - base))];
        assert_eq!(serde_json::to_vec(&c).unwrap().len(), bytes);
        c
    }

    fn request(g: &mut Guardian, client_ref: &str, context: Vec<ContextItem>) -> Promise {
        set_ctx("agent.testnet");
        g.request_payment(
            client_ref.into(),
            acct("hostco.testnet"),
            U128(18_000_000),
            "INV-1".into(),
            "Pay the hosting invoice.".into(),
            context,
        )
    }

    fn verdict(outcome: Outcome) -> Verdict {
        Verdict {
            format: VERDICT_FORMAT.into(),
            request_id: U64(1),
            receiver_id: acct("hostco.testnet"),
            token_id: acct("tusdc.testnet"),
            amount: U128(18_000_000),
            outcome,
            reasons: vec![ReasonCode::StubAllow],
            record_sha256: HASH.into(),
            checker_version: "0.1.0".into(),
        }
    }

    fn dummy_pending() -> Pending {
        Pending {
            yield_id: near_sdk::borsh::from_slice::<YieldId>(&[0u8; 32]).unwrap(),
            client_ref: "r1".into(),
            receiver_id: acct("hostco.testnet"),
            amount: U128(18_000_000),
            checker_input: "{}".into(),
            input_sha256: HASH.into(),
            requested_block: 3,
            charged_day: 0,
        }
    }

    fn with_pending(g: &mut Guardian) {
        g.pending.insert(1, dummy_pending());
        g.refs.insert("r1".into(), 1);
        g.next_request_id = 2;
    }

    #[test]
    #[should_panic(expected = "Only the agent can request payments")]
    fn rp_only_agent() {
        let mut g = new_guardian();
        set_ctx("mallory.testnet");
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(1), "".into(), "x".into(), vec![],
        );
    }

    #[test]
    #[should_panic(expected = "Amount must be positive")]
    fn rp_zero_amount() {
        let mut g = new_guardian();
        set_ctx("agent.testnet");
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(0), "".into(), "x".into(), vec![],
        );
    }

    #[test]
    #[should_panic(expected = "Context too large")]
    fn rp_context_8193() {
        let mut g = new_guardian();
        let _ = request(&mut g, "a", ctx_of_bytes(8193));
    }

    #[test]
    fn rp_context_8192_ok() {
        let mut g = new_guardian();
        let _ = request(&mut g, "a", ctx_of_bytes(8192));
        assert_eq!(g.pending.len(), 1);
    }

    #[test]
    #[should_panic(expected = "Too many items")]
    fn rp_too_many_items() {
        let mut g = new_guardian();
        let _ = request(&mut g, "a", (0..9).map(|_| item("t".into())).collect());
    }

    #[test]
    #[should_panic(expected = "Duplicate client_ref")]
    fn rp_duplicate_ref() {
        let mut g = new_guardian();
        let _ = request(&mut g, "a", vec![]);
        let _ = request(&mut g, "a", vec![]);
    }

    #[test]
    #[should_panic(expected = "Too many pending requests")]
    fn rp_too_many_pending() {
        let mut g = new_guardian();
        for i in 0..=MAX_PENDING {
            let _ = request(&mut g, &format!("r{i}"), vec![]);
        }
    }

    #[test]
    #[should_panic(expected = "Invalid client_ref")]
    fn rp_invalid_ref() {
        let mut g = new_guardian();
        let _ = request(&mut g, "bad ref!", vec![]);
    }

    #[test]
    #[should_panic(expected = "Invalid memo")]
    fn rp_invalid_memo() {
        let mut g = new_guardian();
        set_ctx("agent.testnet");
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(1), "m".repeat(257), "x".into(), vec![],
        );
    }

    #[test]
    #[should_panic(expected = "Invalid user_request")]
    fn rp_invalid_user_request() {
        let mut g = new_guardian();
        set_ctx("agent.testnet");
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(1), "".into(), "".into(), vec![],
        );
    }

    #[test]
    fn checker_input_matches_request() {
        let mut g = new_guardian();
        let ctx = vec![item("hello".into())];
        let _ = request(&mut g, "ref-1", ctx.clone());
        let p = g.pending.get(&1).unwrap();
        let input: CheckerInput = serde_json::from_str(&p.checker_input).unwrap();
        assert_eq!(input.format, CHECKER_INPUT_FORMAT);
        assert_eq!(input.request_id, U64(1));
        assert_eq!(input.guardian_id, acct("guardian.testnet"));
        assert_eq!(input.agent_id, acct("agent.testnet"));
        assert_eq!(input.token_id, acct("tusdc.testnet"));
        assert_eq!(input.token_decimals, 6);
        assert_eq!(input.receiver_id, acct("hostco.testnet"));
        assert_eq!(input.amount, U128(18_000_000));
        assert_eq!(input.memo, "INV-1");
        assert_eq!(input.user_request, "Pay the hosting invoice.");
        assert_eq!(input.context, ctx);
        assert_eq!(input.block_height, U64(7));
        assert_eq!(p.input_sha256, hex::encode(env::sha256(p.checker_input.as_bytes())));
        assert_eq!(g.refs.get("ref-1"), Some(&1));
        assert_eq!(g.next_request_id, 2);
        let views = g.get_pending(0, 16);
        assert_eq!(views.len(), 1);
        assert_eq!(views[0].checker_input, p.checker_input);
    }

    #[test]
    fn schema_examples_parse() {
        let i: CheckerInput = serde_json::from_str(CHECKER_INPUT_EXAMPLE).unwrap();
        assert_eq!(i.request_id, U64(1));
        // field order of our serializer equals the schema example byte-for-byte
        assert_eq!(serde_json::to_string(&i).unwrap(), CHECKER_INPUT_EXAMPLE);
        let v: Verdict = serde_json::from_str(VERDICT_EXAMPLE).unwrap();
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(v.reasons, vec![ReasonCode::StubAllow]);
    }

    #[test]
    fn binds_rejects_each_field() {
        let p = dummy_pending();
        let tok = acct("tusdc.testnet");
        let ok = verdict(Outcome::Allow);
        assert_eq!(validate::binds(&p, &ok, U64(1), &tok), Ok(()));

        let mut v = ok.clone();
        v.format = "x".into();
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("format"));
        assert_eq!(validate::binds(&p, &ok, U64(2), &tok), Err("request_id"));
        let mut v = ok.clone();
        v.request_id = U64(2);
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("request_id"));
        let mut v = ok.clone();
        v.receiver_id = acct("hostc0.testnet");
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("receiver_id"));
        let mut v = ok.clone();
        v.token_id = acct("evil.testnet");
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("token_id"));
        let mut v = ok.clone();
        v.amount = U128(180_000_000);
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("amount"));
        let mut v = ok.clone();
        v.reasons = vec![];
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("reasons"));
        v.reasons = vec![ReasonCode::StubAllow; 7];
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("reasons"));
        let mut v = ok.clone();
        v.record_sha256 = HASH.to_uppercase();
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("record_sha256"));
        v.record_sha256 = "abc".into();
        assert_eq!(validate::binds(&p, &v, U64(1), &tok), Err("record_sha256"));
    }

    #[test]
    #[should_panic(expected = "Only the checker can submit verdicts")]
    fn submit_verdict_non_checker() {
        let mut g = new_guardian();
        with_pending(&mut g);
        set_ctx("mallory.testnet");
        g.submit_verdict(U64(1), verdict(Outcome::Allow));
    }

    #[test]
    #[should_panic(expected = "Unknown request")]
    fn submit_verdict_unknown() {
        let mut g = new_guardian();
        set_ctx("checker.testnet");
        g.submit_verdict(U64(9), verdict(Outcome::Allow));
    }

    #[test]
    #[should_panic(expected = "Verdict does not match request: amount")]
    fn submit_verdict_mismatch() {
        let mut g = new_guardian();
        with_pending(&mut g);
        set_ctx("checker.testnet");
        let mut v = verdict(Outcome::Allow);
        v.amount = U128(1);
        g.submit_verdict(U64(1), v);
    }

    fn run_on_verdict(
        outcome: Result<Verdict, PromiseError>,
    ) -> (Guardian, PromiseOrValue<ReceiptStatus>) {
        let mut g = new_guardian();
        with_pending(&mut g);
        set_ctx("guardian.testnet");
        let r = g.on_verdict(U64(1), outcome);
        (g, r)
    }

    fn value(r: PromiseOrValue<ReceiptStatus>) -> ReceiptStatus {
        match r {
            PromiseOrValue::Value(s) => s,
            PromiseOrValue::Promise(_) => panic!("expected value"),
        }
    }

    fn check_terminal(
        res: Result<Verdict, PromiseError>,
        status: ReceiptStatus,
        outcome: Option<Outcome>,
    ) {
        let (g, r) = run_on_verdict(res);
        assert_eq!(value(r), status);
        assert_eq!(g.pending.len(), 0);
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, status);
        assert_eq!(rec.outcome, outcome);
        assert_eq!(g.get_receipt_by_ref("r1".into()).unwrap(), rec);
        assert_eq!(g.list_receipts(0, 100).len(), 1);
    }

    #[test]
    fn on_verdict_block_is_refused() {
        check_terminal(Ok(verdict(Outcome::Block)), ReceiptStatus::Refused, Some(Outcome::Block));
    }

    #[test]
    fn on_verdict_hold_is_held() {
        check_terminal(Ok(verdict(Outcome::Hold)), ReceiptStatus::Held, Some(Outcome::Hold));
    }

    #[test]
    fn on_verdict_err_is_timed_out() {
        check_terminal(Err(PromiseError::Failed), ReceiptStatus::TimedOut, None);
    }

    #[test]
    fn on_verdict_allow_is_paying() {
        let (g, r) = run_on_verdict(Ok(verdict(Outcome::Allow)));
        assert!(matches!(r, PromiseOrValue::Promise(_)));
        assert_eq!(g.pending.len(), 0);
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::Paying);
        assert_eq!(rec.record_sha256.as_deref(), Some(HASH));
        assert_eq!(rec.reasons, vec![ReasonCode::StubAllow]);
    }

    #[test]
    fn on_verdict_missing_pending_does_not_panic() {
        let mut g = new_guardian();
        set_ctx("guardian.testnet");
        let r = g.on_verdict(U64(5), Err(PromiseError::Failed));
        assert_eq!(value(r), ReceiptStatus::TimedOut);
    }

    #[test]
    #[should_panic(expected = "Unsupported token")]
    fn ft_on_transfer_wrong_token() {
        let mut g = new_guardian();
        set_ctx("other.testnet");
        let _ = g.ft_on_transfer(acct("owner.testnet"), U128(5), "".into());
    }

    #[test]
    fn ft_on_transfer_refunds_non_owner() {
        let mut g = new_guardian();
        set_ctx("tusdc.testnet");
        match g.ft_on_transfer(acct("stranger.testnet"), U128(5), "".into()) {
            PromiseOrValue::Value(v) => assert_eq!(v, U128(5)),
            _ => panic!(),
        }
        match g.ft_on_transfer(acct("owner.testnet"), U128(5), "".into()) {
            PromiseOrValue::Value(v) => assert_eq!(v, U128(0)),
            _ => panic!(),
        }
    }

    fn request_amt(g: &mut Guardian, client_ref: &str, amount: u128, ts: u64) -> Promise {
        set_ctx_at("agent.testnet", ts);
        g.request_payment(
            client_ref.into(),
            acct("hostco.testnet"),
            U128(amount),
            "INV-1".into(),
            "Pay the hosting invoice.".into(),
            vec![],
        )
    }

    const T: u128 = 1_000_000;

    #[test]
    #[should_panic(expected = "Amount exceeds per-payment cap")]
    fn rp_per_payment_cap() {
        let mut g = new_guardian();
        let _ = request_amt(&mut g, "a", 200_000_001, 0);
    }

    #[test]
    fn rp_per_payment_cap_boundary_ok() {
        let mut g = new_guardian();
        let _ = request_amt(&mut g, "a", 200_000_000, 0);
        assert_eq!(g.pending.len(), 1);
        assert_eq!(g.get_daily_spent(), U128(200_000_000));
    }

    #[test]
    fn rp_daily_cap_and_rollover() {
        let mut g = new_guardian();
        let _ = request_amt(&mut g, "a", 200 * T, 0);
        let _ = request_amt(&mut g, "b", 200 * T, 0);
        let _ = request_amt(&mut g, "c", 100 * T, 0);
        set_ctx_at("agent.testnet", 0);
        assert_eq!(g.get_daily_spent(), U128(500_000_000));
        // next day: counter rolls off
        set_ctx_at("agent.testnet", NANOS_PER_DAY);
        assert_eq!(g.get_daily_spent(), U128(0));
        let _ = request_amt(&mut g, "d", 200 * T, NANOS_PER_DAY);
        assert_eq!(g.get_daily_spent(), U128(200_000_000));
    }

    #[test]
    #[should_panic(expected = "Daily cap reached")]
    fn rp_daily_cap_exceeded() {
        let mut g = new_guardian();
        let _ = request_amt(&mut g, "a", 200 * T, 0);
        let _ = request_amt(&mut g, "b", 200 * T, 0);
        let _ = request_amt(&mut g, "c", 100 * T, 0);
        let _ = request_amt(&mut g, "d", 1, 0);
    }

    #[test]
    fn block_unreserves() {
        let mut g = new_guardian();
        let _ = request(&mut g, "r1", vec![]);
        assert_eq!(g.get_daily_spent(), U128(18_000_000));
        set_ctx("guardian.testnet");
        let _ = g.on_verdict(U64(1), Ok(verdict(Outcome::Block)));
        assert_eq!(g.get_daily_spent(), U128(0));
    }

    #[test]
    fn timeout_unreserves() {
        let mut g = new_guardian();
        let _ = request(&mut g, "r1", vec![]);
        assert_eq!(g.get_daily_spent(), U128(18_000_000));
        set_ctx("guardian.testnet");
        let _ = g.on_verdict(U64(1), Err(PromiseError::Failed));
        assert_eq!(g.get_daily_spent(), U128(0));
    }

    fn hold_request(g: &mut Guardian) {
        let _ = request(g, "r1", vec![]);
        set_ctx_at("guardian.testnet", 1_000);
        let _ = g.on_verdict(U64(1), Ok(verdict(Outcome::Hold)));
    }

    #[test]
    fn hold_then_release() {
        let mut g = new_guardian();
        hold_request(&mut g);
        let held = g.get_held(0, 10);
        assert_eq!(held.len(), 1);
        assert_eq!(held[0].request_id, U64(1));
        assert_eq!(held[0].amount, U128(18_000_000));
        assert_eq!(held[0].release_at_ns, U64(1_000 + 600_000_000_000));
        assert_eq!(g.get_receipt(U64(1)).unwrap().status, ReceiptStatus::Held);
        // reservation stays while held
        assert_eq!(g.get_daily_spent(), U128(18_000_000));
        set_ctx_at("anyone.testnet", 1_000 + 600_000_000_000);
        let _p = g.release_held(U64(1));
        assert_eq!(g.get_receipt(U64(1)).unwrap().status, ReceiptStatus::Paying);
        assert!(g.get_held(0, 10).is_empty());
    }

    #[test]
    #[should_panic(expected = "Hold window not over")]
    fn release_before_window_panics() {
        let mut g = new_guardian();
        hold_request(&mut g);
        set_ctx_at("anyone.testnet", 1_000 + 599_999_999_999);
        let _ = g.release_held(U64(1));
    }

    #[test]
    fn cancel_held_owner_unreserves() {
        let mut g = new_guardian();
        hold_request(&mut g);
        set_ctx_at("owner.testnet", 2_000);
        g.cancel_held(U64(1));
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::Refused);
        assert_eq!(rec.outcome, Some(Outcome::Hold));
        assert_eq!(g.get_daily_spent(), U128(0));
        assert!(g.get_held(0, 10).is_empty());
    }

    #[test]
    #[should_panic(expected = "Only the owner or checker can cancel holds")]
    fn cancel_held_stranger_panics() {
        let mut g = new_guardian();
        hold_request(&mut g);
        set_ctx_at("mallory.testnet", 2_000);
        g.cancel_held(U64(1));
    }

    #[test]
    #[should_panic(expected = "Unknown hold")]
    fn release_unknown_panics() {
        let mut g = new_guardian();
        set_ctx("anyone.testnet");
        let _ = g.release_held(U64(9));
    }

    #[test]
    fn hold_window_boundaries() {
        let ten_min = 600_000_000_000;
        let one_h = 3_600_000_000_000;
        let six_h = 21_600_000_000_000;
        assert_eq!(validate::hold_window_ns(19_999_999, 6), ten_min);
        assert_eq!(validate::hold_window_ns(20_000_000, 6), one_h);
        assert_eq!(validate::hold_window_ns(100_000_000, 6), one_h);
        assert_eq!(validate::hold_window_ns(100_000_001, 6), six_h);
    }
}
