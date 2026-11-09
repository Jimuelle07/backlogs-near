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
    Promise, PromiseError, PromiseOrValue, YieldId,
};

use types::*;

pub const MAX_CONTEXT_BYTES: usize = validate::MAX_CONTEXT_BYTES;
pub const MAX_PENDING: u32 = 16;
pub const CALLBACK_GAS: Gas = Gas::from_tgas(40);
/// Gas attached to OutLayer's `request_execution`. The docs attach 100 TGas and say its
/// settlement callback takes 50 TGas from it.
pub const OUTLAYER_REQUEST_GAS: Gas = Gas::from_tgas(100);
pub const FT_TRANSFER_GAS: Gas = Gas::from_tgas(10);
pub const TRANSFER_DONE_GAS: Gas = Gas::from_tgas(5);
const MAX_LIST: u64 = 50;
pub const PER_PAYMENT_CAP_WHOLE: u128 = 200;
pub const DAILY_CAP_WHOLE: u128 = 500;
pub const NANOS_PER_DAY: u64 = 86_400_000_000_000;
/// Cap on the NEAR deposit per OutLayer request (enforced by `valid_mode`).
pub const MAX_OUTLAYER_DEPOSIT: NearToken = validate::MAX_OUTLAYER_DEPOSIT;
/// Balance the Guardian must keep above `deposit_yocto` (and its storage stake) per OutLayer request.
pub const OUTLAYER_BALANCE_MARGIN: NearToken = NearToken::from_millinear(50);
/// Blocks after which an unanswered OutLayer request may be cleared by the owner. Beyond the
/// 200-block yield window, so a cleared request can no longer receive a legitimate callback.
pub const OUTLAYER_STUCK_BLOCKS: u64 = 300;
/// Memory limit sent with every OutLayer request (the CLI's on-chain default). Without it
/// `request_execution` emits `max_memory_mb: null`; every completed testnet job we saw sets it.
pub const OUTLAYER_MAX_MEMORY_MB: u64 = 128;

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

/// Raw storage key of the checker mode. Kept outside the borsh root state so that the `Guardian`
/// layout of an already-deployed contract is untouched; absent = `Relayer`. All collection
/// prefixes (`StorageKey`) are a single byte 0..=3 and the root key is `STATE`, so none collide.
const MODE_KEY: &[u8] = b"checker_mode";
/// Raw storage key prefix marking a request that was sent to OutLayer.
const OUTLAYER_REQ_PREFIX: &[u8] = b"outlayer_req:";
/// Raw storage key of the daily OutLayer request counter: borsh `(day_index, count)`.
const OUTLAYER_DAY_KEY: &[u8] = b"outlayer_day";

fn today() -> u64 {
    env::block_timestamp() / NANOS_PER_DAY
}

/// The persisted `(day_index, count)` counter, if any request was ever counted.
fn outlayer_counter() -> Option<(u64, u64)> {
    env::storage_read(OUTLAYER_DAY_KEY)
        .and_then(|b| near_sdk::borsh::from_slice::<(u64, u64)>(&b).ok())
}

/// OutLayer requests already made today (0 when the stored day is not today).
fn outlayer_used_today() -> u64 {
    outlayer_counter().filter(|(day, _)| *day == today()).map_or(0, |(_, count)| count)
}

fn count_outlayer_request() {
    let bytes = near_sdk::borsh::to_vec(&(today(), outlayer_used_today() + 1))
        .unwrap_or_else(|_| env::abort());
    env::storage_write(OUTLAYER_DAY_KEY, &bytes);
}

/// Rough per-request storage overhead beyond `checker_input` (pending/receipt/ref records).
const OUTLAYER_STORAGE_OVERHEAD_BYTES: u128 = 600;

/// Panics unless the daily budget has room and the balance covers the deposit, the margin and
/// the storage this request will add.
fn require_outlayer_capacity(deposit_yocto: u128, max_per_day: u64, checker_input_len: usize) {
    require!(outlayer_used_today() < max_per_day, "OutLayer daily request budget reached");
    let byte_cost = env::storage_byte_cost().as_yoctonear();
    let spendable = env::account_balance()
        .as_yoctonear()
        .saturating_sub(env::storage_usage() as u128 * byte_cost);
    let request_storage = (checker_input_len as u128 + OUTLAYER_STORAGE_OVERHEAD_BYTES) * byte_cost;
    let required = deposit_yocto
        .saturating_add(OUTLAYER_BALANCE_MARGIN.as_yoctonear())
        .saturating_add(request_storage);
    require!(spendable >= required, "Guardian balance too low for the OutLayer deposit");
}

/// Absent key = `Relayer`; a present but undecodable value is a hard error, never a silent
/// fallback to relayer mode.
fn stored_mode() -> CheckerMode {
    match env::storage_read(MODE_KEY) {
        None => CheckerMode::Relayer,
        Some(b) => near_sdk::borsh::from_slice::<CheckerMode>(&b)
            .unwrap_or_else(|_| env::panic_str("Corrupt checker mode")),
    }
}

fn outlayer_req_key(id: u64) -> Vec<u8> {
    let mut k = OUTLAYER_REQ_PREFIX.to_vec();
    k.extend_from_slice(&id.to_le_bytes());
    k
}

fn mark_outlayer(id: u64) {
    env::storage_write(&outlayer_req_key(id), &[1]);
}

fn is_outlayer(id: u64) -> bool {
    env::storage_has_key(&outlayer_req_key(id))
}

/// Removes the marker; true when it was present.
fn take_outlayer_marker(id: u64) -> bool {
    env::storage_remove(&outlayer_req_key(id))
}

/// OutLayer requests have no Guardian yield; `Pending` still carries one, so store an inert id.
/// `submit_verdict` refuses OutLayer requests before it could ever resume it.
fn placeholder_yield_id() -> YieldId {
    near_sdk::borsh::from_slice::<YieldId>(&[0u8; 32]).unwrap_or_else(|_| env::abort())
}

/// `request_execution` args for an OutLayer-mode request.
fn outlayer_request_args(checker_input: &str, mode: &CheckerMode) -> serde_json::Value {
    let CheckerMode::OutLayer {
        project_id,
        version_key,
        secrets_ref,
        max_instructions,
        max_execution_seconds,
        ..
    } = mode
    else {
        env::abort()
    };
    json!({
        "source": { "Project": { "project_id": project_id, "version_key": version_key } },
        "resource_limits": {
            "max_instructions": max_instructions.0,
            "max_memory_mb": OUTLAYER_MAX_MEMORY_MB,
            "max_execution_seconds": max_execution_seconds.0,
        },
        "input_data": checker_input,
        "secrets_ref": secrets_ref,
        "response_format": "Text",
    })
}

/// `outlayer.request_execution(...)` paid from the Guardian's balance, then `on_outlayer_verdict`.
fn outlayer_promise(request_id: u64, checker_input: &str, mode: &CheckerMode) -> Promise {
    let CheckerMode::OutLayer { outlayer_id, deposit_yocto, .. } = mode else {
        env::abort()
    };
    let args = serde_json::to_vec(&outlayer_request_args(checker_input, mode)).unwrap_or_else(|_| env::abort());
    Promise::new(outlayer_id.clone())
        .function_call(
            "request_execution".to_string(),
            args,
            NearToken::from_yoctonear(deposit_yocto.0),
            OUTLAYER_REQUEST_GAS,
        )
        .then(
            Guardian::ext(env::current_account_id())
                .with_static_gas(CALLBACK_GAS)
                .on_outlayer_verdict(U64(request_id)),
        )
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
        let mode = stored_mode();
        let request_id = self.next_request_id;
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

        // Everything above is read-only: a rejected OutLayer request writes nothing.
        if let CheckerMode::OutLayer { deposit_yocto, max_requests_per_day, .. } = &mode {
            require_outlayer_capacity(deposit_yocto.0, max_requests_per_day.0, checker_input.len());
        }
        let day = self.roll_day();
        require!(self.spent_today + amount.0 <= self.daily_cap(), "Daily cap reached");
        self.spent_today += amount.0;
        self.next_request_id += 1;

        let (promise, yield_id) = match &mode {
            CheckerMode::Relayer => {
                let args = serde_json::to_vec(&json!({ "request_id": U64(request_id) }))
                    .unwrap_or_else(|_| env::abort());
                Promise::new_yield("on_verdict", args, CALLBACK_GAS, GasWeight(0))
            }
            CheckerMode::OutLayer { .. } => {
                (outlayer_promise(request_id, &checker_input, &mode), placeholder_yield_id())
            }
        };
        if matches!(mode, CheckerMode::OutLayer { .. }) {
            mark_outlayer(request_id);
            count_outlayer_request();
        }
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
        require!(!is_outlayer(request_id.0), "Request is decided by OutLayer");
        let pending = self.pending.get(&request_id.0).unwrap_or_else(|| env::panic_str("Unknown request"));
        if let Err(field) = validate::binds(pending, &verdict, request_id, &self.token_id) {
            env::panic_str(&format!("Verdict does not match request: {field}"));
        }
        let bytes = serde_json::to_vec(&verdict).unwrap_or_else(|_| env::abort());
        if pending.yield_id.resume(bytes).is_err() {
            env::panic_str("Request already resolved");
        }
    }

    /// Yield callback (relayer mode). Never panics.
    #[private]
    pub fn on_verdict(
        &mut self,
        request_id: U64,
        #[callback_result] verdict: Result<Verdict, PromiseError>,
    ) -> PromiseOrValue<ReceiptStatus> {
        let Some(pending) = self.pending.remove(&request_id.0) else {
            return PromiseOrValue::Value(ReceiptStatus::TimedOut);
        };
        self.settle(request_id, pending, verdict.ok())
    }

    /// OutLayer callback (OutLayer mode). Reads the execution result, binds the verdict to the
    /// pending request, then settles exactly as `on_verdict` does. Never panics and fails closed:
    /// any OutLayer failure, unparsable/oversized/unbound output leaves no outcome, no transfer
    /// and no reservation (receipt `timed_out`) and emits `checker_failed`.
    #[private]
    pub fn on_outlayer_verdict(&mut self, request_id: U64) -> PromiseOrValue<ReceiptStatus> {
        let id = request_id.0;
        if !take_outlayer_marker(id) {
            // Not an OutLayer request (or already handled): nothing to decide.
            return PromiseOrValue::Value(ReceiptStatus::TimedOut);
        }
        let Some(pending) = self.pending.remove(&id) else {
            return PromiseOrValue::Value(ReceiptStatus::TimedOut);
        };
        let verdict = match env::promise_result_checked(0, validate::MAX_OUTLAYER_RESULT_BYTES) {
            Err(PromiseError::Failed) => Err("outlayer_failed".to_string()),
            Err(_) => Err("oversized".to_string()),
            Ok(bytes) => validate::parse_outlayer_output(&bytes)
                .map_err(|e| e.to_string())
                .and_then(|v| {
                    validate::binds(&pending, &v, request_id, &self.token_id)
                        .map(|_| v)
                        .map_err(|field| format!("unbound_{field}"))
                }),
        };
        match verdict {
            Ok(v) => self.settle(request_id, pending, Some(v)),
            Err(reason) => {
                emit("checker_failed", json!({ "request_id": request_id, "reason": reason }));
                self.settle(request_id, pending, None)
            }
        }
    }

    /// Shared outcome logic for both checker modes. `None` = no usable verdict (timed out):
    /// no outcome, no transfer, reservation released.
    fn settle(
        &mut self,
        request_id: U64,
        pending: Pending,
        verdict: Option<Verdict>,
    ) -> PromiseOrValue<ReceiptStatus> {
        let id = request_id.0;
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
            Some(v) => {
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
            None => self.unreserve(pending.charged_day, pending.amount.0),
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

    /// Owner only. `Relayer` (default) or `OutLayer { .. }`. Requests already in flight keep the
    /// mode they were made under.
    pub fn set_checker_mode(&mut self, mode: CheckerMode) {
        require!(
            env::predecessor_account_id() == self.owner_id,
            "Only the owner can set the checker mode"
        );
        if let Err(field) = validate::valid_mode(&mode) {
            env::panic_str(&format!("Invalid checker mode: {field}"));
        }
        match &mode {
            CheckerMode::Relayer => {
                env::storage_remove(MODE_KEY);
            }
            m => {
                let bytes = near_sdk::borsh::to_vec(m).unwrap_or_else(|_| env::abort());
                env::storage_write(MODE_KEY, &bytes);
            }
        }
        emit("checker_mode_set", json!({ "mode": mode }));
    }

    /// Owner only. Clears an OutLayer request that never got a callback (older than
    /// `OUTLAYER_STUCK_BLOCKS`): fails it closed like a failed callback. The daily request budget
    /// is not refunded.
    pub fn clear_stuck_outlayer(&mut self, request_id: U64) {
        require!(
            env::predecessor_account_id() == self.owner_id,
            "Only the owner can clear stuck requests"
        );
        let id = request_id.0;
        require!(is_outlayer(id), "Unknown OutLayer request");
        let requested_block = self
            .pending
            .get(&id)
            .unwrap_or_else(|| env::panic_str("Unknown OutLayer request"))
            .requested_block;
        require!(
            env::block_height() >= requested_block.saturating_add(OUTLAYER_STUCK_BLOCKS),
            "Request is not stuck"
        );
        take_outlayer_marker(id);
        let pending = self.pending.remove(&id).unwrap_or_else(|| env::abort());
        emit("checker_failed", json!({ "request_id": request_id, "reason": "stuck_cleared" }));
        let _ = self.settle(request_id, pending, None);
    }

    pub fn get_outlayer_usage(&self) -> Option<OutlayerUsage> {
        let counter = outlayer_counter();
        let max_per_day = match stored_mode() {
            CheckerMode::Relayer if counter.is_none() => return None,
            CheckerMode::Relayer => U64(0),
            CheckerMode::OutLayer { max_requests_per_day, .. } => max_requests_per_day,
        };
        Some(OutlayerUsage { day: U64(today()), used: U64(outlayer_used_today()), max_per_day })
    }

    pub fn get_checker_mode(&self) -> CheckerMode {
        stored_mode()
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
            .filter(|(id, _)| !is_outlayer(**id))
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
    use near_sdk::{testing_env, PromiseResult, YieldId};

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

    // ---- checker mode ----

    fn ol_mode() -> CheckerMode {
        ol_mode_max(100)
    }

    fn ol_mode_max(max_requests_per_day: u64) -> CheckerMode {
        CheckerMode::OutLayer {
            outlayer_id: acct("outlayer.testnet"),
            project_id: "owner.testnet/checker".into(),
            version_key: None,
            secrets_ref: None,
            deposit_yocto: U128(50_000_000_000_000_000_000_000),
            max_instructions: U64(1_000_000_000),
            max_execution_seconds: U64(30),
            max_requests_per_day: U64(max_requests_per_day),
        }
    }

    /// Every completed OutLayer testnet job we saw sets all three limits; the one request that
    /// omitted `max_memory_mb` (emitted as null) got no job.
    #[test]
    fn outlayer_request_args_set_every_limit() {
        let args = outlayer_request_args("{}", &ol_mode());
        let limits = &args["resource_limits"];
        for (field, cap) in [
            ("max_instructions", 500_000_000_000u64),
            ("max_memory_mb", 4096),
            ("max_execution_seconds", 180),
        ] {
            let v = limits[field].as_u64().unwrap_or_else(|| panic!("{field} missing or not a number"));
            assert!((1..=cap).contains(&v), "{field} = {v} outside 1..={cap}");
        }
        assert_eq!(limits["max_memory_mb"], json!(OUTLAYER_MAX_MEMORY_MB));
        assert_eq!(args["response_format"], json!("Text"));
        assert_eq!(args["input_data"], json!("{}"));
    }

    /// New Guardian in OutLayer mode with one request (id 1, client_ref "r1") in flight.
    fn ol_guardian() -> Guardian {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        g.set_checker_mode(ol_mode());
        let _ = request(&mut g, "r1", vec![]);
        g
    }

    fn text_result(v: &Verdict) -> PromiseResult {
        let line = format!("{}\n", serde_json::to_string(v).unwrap());
        PromiseResult::Successful(serde_json::to_vec(&line).unwrap())
    }

    fn deliver(g: &mut Guardian, result: PromiseResult) -> PromiseOrValue<ReceiptStatus> {
        testing_env!(
            VMContextBuilder::new()
                .current_account_id(acct("guardian.testnet"))
                .predecessor_account_id(acct("guardian.testnet"))
                .block_height(9)
                .build(),
            near_sdk::test_vm_config(),
            near_sdk::RuntimeFeesConfig::test(),
            Default::default(),
            vec![result]
        );
        g.on_outlayer_verdict(U64(1))
    }

    /// Fail-closed expectations: timed out, no outcome, no transfer, reservation released.
    fn assert_failed_closed(g: &Guardian, r: PromiseOrValue<ReceiptStatus>, reason: &str) {
        assert_eq!(value(r), ReceiptStatus::TimedOut);
        assert_eq!(g.pending.len(), 0);
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::TimedOut);
        assert_eq!(rec.outcome, None);
        assert_eq!(rec.record_sha256, None);
        assert_eq!(g.get_daily_spent(), U128(0));
        let logs = near_sdk::test_utils::get_logs().join("\n");
        assert!(logs.contains("checker_failed"), "logs: {logs}");
        assert!(logs.contains(reason), "expected reason {reason} in logs: {logs}");
        assert!(!is_outlayer(1));
    }

    #[test]
    fn mode_default_is_relayer() {
        let g = new_guardian();
        assert_eq!(g.get_checker_mode(), CheckerMode::Relayer);
    }

    #[test]
    #[should_panic(expected = "Only the owner can set the checker mode")]
    fn mode_set_owner_only() {
        let mut g = new_guardian();
        set_ctx("mallory.testnet");
        g.set_checker_mode(ol_mode());
    }

    #[test]
    #[should_panic(expected = "Only the owner can set the checker mode")]
    fn mode_set_checker_cannot() {
        let mut g = new_guardian();
        set_ctx("checker.testnet");
        g.set_checker_mode(CheckerMode::Relayer);
    }

    #[test]
    fn mode_roundtrip_and_back_to_relayer() {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        g.set_checker_mode(ol_mode());
        assert_eq!(g.get_checker_mode(), ol_mode());
        g.set_checker_mode(CheckerMode::Relayer);
        assert_eq!(g.get_checker_mode(), CheckerMode::Relayer);
        assert!(env::storage_read(MODE_KEY).is_none());
    }

    #[test]
    fn mode_json_shape() {
        let v = serde_json::to_value(ol_mode()).unwrap();
        assert_eq!(v["outlayer"]["project_id"], "owner.testnet/checker");
        assert_eq!(serde_json::to_value(CheckerMode::Relayer).unwrap(), "relayer");
        let back: CheckerMode = serde_json::from_value(v).unwrap();
        assert_eq!(back, ol_mode());
    }

    #[test]
    #[should_panic(expected = "Invalid checker mode: project_id")]
    fn mode_rejects_bad_project_id() {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        let CheckerMode::OutLayer { outlayer_id, deposit_yocto, max_instructions, max_execution_seconds, .. } = ol_mode() else { unreachable!() };
        g.set_checker_mode(CheckerMode::OutLayer {
            outlayer_id,
            project_id: "no-slash".into(),
            version_key: None,
            secrets_ref: None,
            deposit_yocto,
            max_instructions,
            max_execution_seconds,
            max_requests_per_day: U64(100),
        });
    }

    #[test]
    #[should_panic(expected = "Invalid checker mode: deposit_yocto")]
    fn mode_rejects_zero_deposit() {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        let CheckerMode::OutLayer { outlayer_id, project_id, max_instructions, max_execution_seconds, .. } = ol_mode() else { unreachable!() };
        g.set_checker_mode(CheckerMode::OutLayer {
            outlayer_id,
            project_id,
            version_key: None,
            secrets_ref: None,
            deposit_yocto: U128(0),
            max_instructions,
            max_execution_seconds,
            max_requests_per_day: U64(100),
        });
    }

    #[test]
    fn ol_request_reserves_and_marks() {
        let g = ol_guardian();
        assert_eq!(g.pending.len(), 1);
        assert!(is_outlayer(1));
        assert_eq!(g.get_daily_spent(), U128(18_000_000));
    }

    #[test]
    #[should_panic(expected = "Amount exceeds per-payment cap")]
    fn ol_request_keeps_caps() {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        g.set_checker_mode(ol_mode());
        set_ctx("agent.testnet");
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(201_000_000), "".into(), "x".into(), vec![],
        );
    }

    #[test]
    #[should_panic(expected = "Guardian balance too low for the OutLayer deposit")]
    fn ol_request_needs_balance() {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        g.set_checker_mode(ol_mode());
        testing_env!(VMContextBuilder::new()
            .current_account_id(acct("guardian.testnet"))
            .predecessor_account_id(acct("agent.testnet"))
            .account_balance(NearToken::from_millinear(1))
            .build());
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(1), "".into(), "x".into(), vec![],
        );
    }

    #[test]
    #[should_panic(expected = "Request is decided by OutLayer")]
    fn ol_submit_verdict_panics() {
        let mut g = ol_guardian();
        set_ctx("checker.testnet");
        g.submit_verdict(U64(1), verdict(Outcome::Allow));
    }

    #[test]
    fn ol_callback_allow_is_paying() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, text_result(&verdict(Outcome::Allow)));
        assert!(matches!(r, PromiseOrValue::Promise(_)));
        assert_eq!(g.pending.len(), 0);
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::Paying);
        assert_eq!(rec.outcome, Some(Outcome::Allow));
        assert_eq!(rec.record_sha256.as_deref(), Some(HASH));
        assert!(!is_outlayer(1));
    }

    #[test]
    fn ol_callback_json_object_result_is_accepted() {
        let mut g = ol_guardian();
        let bytes = serde_json::to_vec(&verdict(Outcome::Allow)).unwrap();
        let r = deliver(&mut g, PromiseResult::Successful(bytes));
        assert!(matches!(r, PromiseOrValue::Promise(_)));
    }

    #[test]
    fn ol_callback_hold_is_held() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, text_result(&verdict(Outcome::Hold)));
        assert_eq!(value(r), ReceiptStatus::Held);
        assert_eq!(g.pending.len(), 0);
        assert_eq!(g.get_held(0, 10).len(), 1);
        // The reservation stays charged while the hold is escrowed.
        assert_eq!(g.get_daily_spent(), U128(18_000_000));
        assert_eq!(g.get_receipt(U64(1)).unwrap().outcome, Some(Outcome::Hold));
    }

    #[test]
    fn ol_callback_block_is_refused_and_unreserved() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, text_result(&verdict(Outcome::Block)));
        assert_eq!(value(r), ReceiptStatus::Refused);
        assert_eq!(g.get_daily_spent(), U128(0));
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::Refused);
        assert_eq!(rec.outcome, Some(Outcome::Block));
        assert!(g.get_held(0, 10).is_empty());
    }

    #[test]
    fn ol_callback_malformed_json_fails_closed() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, PromiseResult::Successful(b"not json".to_vec()));
        assert_failed_closed(&g, r, "bad_result_json");
    }

    #[test]
    fn ol_callback_text_that_is_not_a_verdict_fails_closed() {
        let mut g = ol_guardian();
        let bytes = serde_json::to_vec("hello world").unwrap();
        let r = deliver(&mut g, PromiseResult::Successful(bytes));
        assert_failed_closed(&g, r, "bad_verdict");
    }

    #[test]
    fn ol_callback_null_fails_closed() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, PromiseResult::Successful(b"null".to_vec()));
        assert_failed_closed(&g, r, "null_result");
    }

    #[test]
    fn ol_callback_oversize_verdict_fails_closed() {
        let mut g = ol_guardian();
        let mut v = verdict(Outcome::Allow);
        v.checker_version = "x".repeat(900);
        let r = deliver(&mut g, text_result(&v));
        assert_failed_closed(&g, r, "oversized");
    }

    #[test]
    fn ol_callback_oversize_result_fails_closed() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, PromiseResult::Successful(vec![b' '; 3000]));
        assert_failed_closed(&g, r, "oversized");
    }

    #[test]
    fn ol_callback_binding_mismatch_fails_closed() {
        let mut g = ol_guardian();
        let mut v = verdict(Outcome::Allow);
        v.amount = U128(1);
        let r = deliver(&mut g, text_result(&v));
        assert_failed_closed(&g, r, "unbound_amount");
    }

    #[test]
    fn ol_callback_wrong_request_id_fails_closed() {
        let mut g = ol_guardian();
        let mut v = verdict(Outcome::Allow);
        v.request_id = U64(2);
        let r = deliver(&mut g, text_result(&v));
        assert_failed_closed(&g, r, "unbound_request_id");
    }

    #[test]
    fn ol_callback_promise_failure_fails_closed() {
        let mut g = ol_guardian();
        let r = deliver(&mut g, PromiseResult::Failed);
        assert_failed_closed(&g, r, "outlayer_failed");
    }

    #[test]
    fn ol_callback_without_marker_is_a_noop() {
        // A relayer-mode request must not be decidable through the OutLayer callback.
        let mut g = new_guardian();
        with_pending(&mut g);
        let r = deliver(&mut g, text_result(&verdict(Outcome::Allow)));
        assert_eq!(value(r), ReceiptStatus::TimedOut);
        assert_eq!(g.pending.len(), 1);
        assert!(g.get_receipt(U64(1)).is_none());
    }

    #[test]
    fn relayer_request_is_not_marked() {
        let mut g = new_guardian();
        let _ = request(&mut g, "r1", vec![]);
        assert!(!is_outlayer(1));
    }

    // ---- OutLayer hardening ----

    const DEPOSIT: u128 = 50_000_000_000_000_000_000_000;

    fn request_at(g: &mut Guardian, client_ref: &str, ts: u64) -> Promise {
        set_ctx_at("agent.testnet", ts);
        g.request_payment(
            client_ref.into(),
            acct("hostco.testnet"),
            U128(18_000_000),
            "".into(),
            "Pay.".into(),
            vec![],
        )
    }

    fn ol_guardian_with_max(max: u64) -> Guardian {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        g.set_checker_mode(ol_mode_max(max));
        g
    }

    fn usage_at(g: &Guardian, ts: u64) -> Option<OutlayerUsage> {
        set_ctx_at("anyone.testnet", ts);
        g.get_outlayer_usage()
    }

    fn set_ctx_block(predecessor: &str, block: u64) {
        testing_env!(VMContextBuilder::new()
            .current_account_id(acct("guardian.testnet"))
            .predecessor_account_id(acct(predecessor))
            .block_height(block)
            .build());
    }

    /// Extra balance that covers the storage of a small request but not of a max-size one.
    const STORAGE_SLACK: u128 = 30_000_000_000_000_000_000_000;

    /// OutLayer request with an exact spendable balance (storage stake pinned to zero).
    fn ol_request_with_balance(balance_yocto: u128, context: Vec<ContextItem>) {
        let mut g = ol_guardian_with_max(10);
        testing_env!(VMContextBuilder::new()
            .current_account_id(acct("guardian.testnet"))
            .predecessor_account_id(acct("agent.testnet"))
            .storage_usage(0)
            .account_balance(NearToken::from_yoctonear(balance_yocto))
            .build());
        let _ = g.request_payment(
            "a".into(), acct("hostco.testnet"), U128(1), "".into(), "x".into(), context,
        );
        assert_eq!(g.pending.len(), 1);
    }

    #[test]
    fn ol_budget_counts_requests() {
        let mut g = ol_guardian_with_max(2);
        let _ = request_at(&mut g, "r1", 0);
        let _ = request_at(&mut g, "r2", 0);
        assert_eq!(g.pending.len(), 2);
        let used = usage_at(&g, 0).unwrap();
        assert_eq!((used.day, used.used, used.max_per_day), (U64(0), U64(2), U64(2)));
    }

    #[test]
    #[should_panic(expected = "OutLayer daily request budget reached")]
    fn ol_budget_third_request_panics() {
        let mut g = ol_guardian_with_max(2);
        let _ = request_at(&mut g, "r1", 0);
        let _ = request_at(&mut g, "r2", 0);
        let _ = request_at(&mut g, "r3", 0);
    }

    #[test]
    fn ol_budget_panic_leaves_no_state() {
        let mut g = ol_guardian_with_max(1);
        let _ = request_at(&mut g, "r1", 0);
        let spent = g.get_daily_spent();
        let next = g.next_request_id;
        let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _ = request_at(&mut g, "r2", 0);
        }));
        assert!(r.is_err());
        assert_eq!(g.get_daily_spent(), spent);
        assert_eq!(g.next_request_id, next);
        assert_eq!(g.pending.len(), 1);
        assert!(!is_outlayer(next));
        let counter = near_sdk::borsh::from_slice::<(u64, u64)>(
            &env::storage_read(OUTLAYER_DAY_KEY).unwrap(),
        )
        .unwrap();
        assert_eq!(counter, (0, 1));
    }

    #[test]
    fn ol_budget_not_refunded_on_failed_callback() {
        let mut g = ol_guardian_with_max(5);
        let _ = request_at(&mut g, "r1", 0);
        let r = deliver(&mut g, PromiseResult::Failed);
        assert_eq!(value(r), ReceiptStatus::TimedOut);
        assert_eq!(usage_at(&g, 0).unwrap().used, U64(1));
    }

    #[test]
    fn ol_budget_not_refunded_on_block() {
        let mut g = ol_guardian_with_max(5);
        let _ = request_at(&mut g, "r1", 0);
        let r = deliver(&mut g, text_result(&verdict(Outcome::Block)));
        assert_eq!(value(r), ReceiptStatus::Refused);
        assert_eq!(usage_at(&g, 0).unwrap().used, U64(1));
    }

    #[test]
    #[should_panic(expected = "OutLayer daily request budget reached")]
    fn ol_budget_still_exhausted_after_failed_callback() {
        let mut g = ol_guardian_with_max(1);
        let _ = request_at(&mut g, "r1", 0);
        let _ = deliver(&mut g, PromiseResult::Failed);
        let _ = request_at(&mut g, "r2", 0);
    }

    #[test]
    fn ol_budget_resets_next_utc_day() {
        let mut g = ol_guardian_with_max(1);
        let _ = request_at(&mut g, "r1", 0);
        let _ = request_at(&mut g, "r2", NANOS_PER_DAY);
        let u = usage_at(&g, NANOS_PER_DAY).unwrap();
        assert_eq!((u.day, u.used), (U64(1), U64(1)));
        // Viewed on a later day with no requests yet: used reads as 0.
        let u = usage_at(&g, 3 * NANOS_PER_DAY).unwrap();
        assert_eq!((u.day, u.used, u.max_per_day), (U64(3), U64(0), U64(1)));
    }

    #[test]
    fn ol_usage_is_none_in_relayer_mode() {
        let g = new_guardian();
        assert_eq!(usage_at(&g, 0), None);
    }

    #[test]
    #[should_panic(expected = "Guardian balance too low for the OutLayer deposit")]
    fn ol_balance_exactly_deposit_panics() {
        ol_request_with_balance(DEPOSIT, vec![]);
    }

    #[test]
    #[should_panic(expected = "Guardian balance too low for the OutLayer deposit")]
    fn ol_balance_one_yocto_short_of_margin_panics() {
        ol_request_with_balance(DEPOSIT + OUTLAYER_BALANCE_MARGIN.as_yoctonear() - 1, vec![]);
    }

    #[test]
    #[should_panic(expected = "Guardian balance too low for the OutLayer deposit")]
    fn ol_balance_margin_without_storage_panics() {
        ol_request_with_balance(DEPOSIT + OUTLAYER_BALANCE_MARGIN.as_yoctonear(), vec![]);
    }

    #[test]
    fn ol_balance_deposit_margin_and_storage_passes() {
        ol_request_with_balance(DEPOSIT + OUTLAYER_BALANCE_MARGIN.as_yoctonear() + STORAGE_SLACK, vec![]);
    }

    #[test]
    #[should_panic(expected = "Guardian balance too low for the OutLayer deposit")]
    fn ol_balance_small_request_fits_but_max_context_does_not() {
        // Passes for a small request (previous test), fails for a max-size context.
        ol_request_with_balance(
            DEPOSIT + OUTLAYER_BALANCE_MARGIN.as_yoctonear() + STORAGE_SLACK,
            ctx_of_bytes(MAX_CONTEXT_BYTES),
        );
    }

    #[test]
    fn ol_balance_max_context_passes_with_enough_storage_balance() {
        ol_request_with_balance(
            DEPOSIT + OUTLAYER_BALANCE_MARGIN.as_yoctonear() + 20 * STORAGE_SLACK,
            ctx_of_bytes(MAX_CONTEXT_BYTES),
        );
    }

    #[test]
    #[should_panic(expected = "Corrupt checker mode")]
    fn corrupt_checker_mode_panics_instead_of_relayer() {
        let g = new_guardian();
        env::storage_write(MODE_KEY, &[0xff, 0xff, 0xff]);
        let _ = g.get_checker_mode();
    }

    #[test]
    fn ol_usage_persists_after_switching_to_relayer() {
        let mut g = ol_guardian_with_max(3);
        let _ = request_at(&mut g, "r1", 0);
        set_ctx("owner.testnet");
        g.set_checker_mode(CheckerMode::Relayer);
        let u = usage_at(&g, 0).unwrap();
        assert_eq!((u.used, u.max_per_day), (U64(1), U64(0)));
    }

    fn mode_with(outlayer_id: &str, deposit_yocto: u128, max_requests_per_day: u64) -> CheckerMode {
        CheckerMode::OutLayer {
            outlayer_id: acct(outlayer_id),
            project_id: "owner.testnet/checker".into(),
            version_key: None,
            secrets_ref: None,
            deposit_yocto: U128(deposit_yocto),
            max_instructions: U64(1_000_000_000),
            max_execution_seconds: U64(30),
            max_requests_per_day: U64(max_requests_per_day),
        }
    }

    #[test]
    fn valid_mode_accepts_known_outlayer_ids() {
        assert_eq!(validate::valid_mode(&mode_with("outlayer.testnet", DEPOSIT, 100)), Ok(()));
        assert_eq!(validate::valid_mode(&mode_with("outlayer.near", DEPOSIT, 100)), Ok(()));
    }

    #[test]
    fn valid_mode_rejects_other_outlayer_id() {
        assert_eq!(
            validate::valid_mode(&mode_with("evil.testnet", DEPOSIT, 100)),
            Err("outlayer_id")
        );
    }

    #[test]
    fn valid_mode_deposit_bound() {
        let one_near = MAX_OUTLAYER_DEPOSIT.as_yoctonear();
        assert_eq!(validate::valid_mode(&mode_with("outlayer.testnet", one_near, 100)), Ok(()));
        assert_eq!(
            validate::valid_mode(&mode_with("outlayer.testnet", one_near + 1, 100)),
            Err("deposit_yocto")
        );
    }

    #[test]
    fn valid_mode_request_budget_bounds() {
        for ok in [1, 1000] {
            assert_eq!(validate::valid_mode(&mode_with("outlayer.testnet", DEPOSIT, ok)), Ok(()));
        }
        for bad in [0, 1001] {
            assert_eq!(
                validate::valid_mode(&mode_with("outlayer.testnet", DEPOSIT, bad)),
                Err("max_requests_per_day")
            );
        }
    }

    #[test]
    #[should_panic(expected = "Invalid checker mode: outlayer_id")]
    fn set_checker_mode_rejects_other_outlayer_id() {
        let mut g = new_guardian();
        set_ctx("owner.testnet");
        g.set_checker_mode(mode_with("evil.testnet", DEPOSIT, 100));
    }

    #[test]
    fn get_pending_hides_outlayer_requests() {
        let g = ol_guardian();
        assert_eq!(g.pending.len(), 1);
        assert!(g.get_pending(0, 50).is_empty());
    }

    #[test]
    fn get_pending_lists_relayer_requests() {
        let mut g = new_guardian();
        let _ = request(&mut g, "r1", vec![]);
        let list = g.get_pending(0, 50);
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].request_id, U64(1));
    }

    #[test]
    fn get_pending_mixed_modes_lists_only_relayer() {
        let mut g = new_guardian();
        let _ = request(&mut g, "r1", vec![]);
        set_ctx("owner.testnet");
        g.set_checker_mode(ol_mode());
        let _ = request(&mut g, "r2", vec![]);
        assert_eq!(g.pending.len(), 2);
        let list = g.get_pending(0, 50);
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].request_id, U64(1));
    }

    #[test]
    #[should_panic(expected = "Request is not stuck")]
    fn clear_stuck_before_300_blocks_panics() {
        let mut g = ol_guardian();
        set_ctx_block("owner.testnet", 7 + OUTLAYER_STUCK_BLOCKS - 1);
        g.clear_stuck_outlayer(U64(1));
    }

    #[test]
    #[should_panic(expected = "Only the owner can clear stuck requests")]
    fn clear_stuck_stranger_panics() {
        let mut g = ol_guardian();
        set_ctx_block("mallory.testnet", 7 + OUTLAYER_STUCK_BLOCKS);
        g.clear_stuck_outlayer(U64(1));
    }

    #[test]
    #[should_panic(expected = "Only the owner can clear stuck requests")]
    fn clear_stuck_agent_panics() {
        let mut g = ol_guardian();
        set_ctx_block("agent.testnet", 7 + OUTLAYER_STUCK_BLOCKS);
        g.clear_stuck_outlayer(U64(1));
    }

    #[test]
    #[should_panic(expected = "Unknown OutLayer request")]
    fn clear_stuck_unknown_id_panics() {
        let mut g = ol_guardian();
        set_ctx_block("owner.testnet", 7 + OUTLAYER_STUCK_BLOCKS);
        g.clear_stuck_outlayer(U64(99));
    }

    #[test]
    #[should_panic(expected = "Unknown OutLayer request")]
    fn clear_stuck_relayer_request_panics() {
        let mut g = new_guardian();
        let _ = request(&mut g, "r1", vec![]);
        set_ctx_block("owner.testnet", 7 + OUTLAYER_STUCK_BLOCKS);
        g.clear_stuck_outlayer(U64(1));
    }

    #[test]
    fn clear_stuck_after_300_blocks_fails_closed() {
        let mut g = ol_guardian();
        assert_eq!(g.get_daily_spent(), U128(18_000_000));
        set_ctx_block("owner.testnet", 7 + OUTLAYER_STUCK_BLOCKS);
        g.clear_stuck_outlayer(U64(1));
        let logs = near_sdk::test_utils::get_logs().join("\n");
        assert!(logs.contains("checker_failed") && logs.contains("stuck_cleared"), "logs: {logs}");
        assert_eq!(g.pending.len(), 0);
        assert!(!is_outlayer(1));
        assert_eq!(g.get_daily_spent(), U128(0));
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::TimedOut);
        assert_eq!(rec.outcome, None);
        assert_eq!(rec.record_sha256, None);
        // The daily budget is not refunded by clearing.
        assert_eq!(usage_at(&g, 0).unwrap().used, U64(1));

        // A late callback for the cleared id is a no-op and cannot pay.
        let r = deliver(&mut g, text_result(&verdict(Outcome::Allow)));
        assert_eq!(value(r), ReceiptStatus::TimedOut);
        let rec = g.get_receipt(U64(1)).unwrap();
        assert_eq!(rec.status, ReceiptStatus::TimedOut);
        assert_eq!(rec.outcome, None);
    }
}
