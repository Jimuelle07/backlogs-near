//! Pure validation helpers (no host calls).
use crate::types::{CheckerMode, Pending, Verdict, VERDICT_FORMAT};
use near_sdk::json_types::U64;
use near_sdk::serde_json::{self, Value};
use near_sdk::AccountId;
use near_sdk::NearToken;

pub const MAX_CONTEXT_BYTES: usize = 8192;
pub const MAX_CONTEXT_ITEMS: usize = 8;
pub const MAX_MEMO_CHARS: usize = 256;
pub const MAX_USER_REQUEST_CHARS: usize = 1024;
pub const MAX_REF_CHARS: usize = 128;
pub const MAX_REASONS: usize = 6;
/// OutLayer hands the guest's stdout back to the contract; it must stay within this.
pub const MAX_VERDICT_BYTES: usize = 900;
/// Upper bound on the promise result read from OutLayer (a JSON-escaped 900-byte string fits).
pub const MAX_OUTLAYER_RESULT_BYTES: usize = 2048;
/// OutLayer hard caps (contract README `get_max_limits`).
pub const OUTLAYER_MAX_INSTRUCTIONS: u64 = 500_000_000_000;
pub const OUTLAYER_MAX_SECONDS: u64 = 180;
pub const MAX_PROJECT_ID_BYTES: usize = 128;
/// Largest NEAR deposit the owner may attach to one OutLayer request.
pub const MAX_OUTLAYER_DEPOSIT: NearToken = NearToken::from_near(1);
/// Upper bound of `max_requests_per_day`.
pub const MAX_REQUESTS_PER_DAY_LIMIT: u64 = 1000;

/// `^[A-Za-z0-9_-]{1,64}$`
pub fn valid_client_ref(s: &str) -> bool {
    (1..=64).contains(&s.len())
        && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

pub fn valid_memo(s: &str) -> bool {
    s.chars().count() <= MAX_MEMO_CHARS
}

pub fn valid_user_request(s: &str) -> bool {
    (1..=MAX_USER_REQUEST_CHARS).contains(&s.chars().count())
}

pub fn valid_context_ref(s: &str) -> bool {
    (1..=MAX_REF_CHARS).contains(&s.chars().count())
}

/// `^[0-9a-f]{64}$`
pub fn is_lower_hex_64(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// Hold window by amount: <20 tokens 10 min, <=100 tokens 1 h, otherwise 6 h.
pub fn hold_window_ns(amount: u128, decimals: u8) -> u64 {
    let unit = 10u128.pow(decimals as u32);
    if amount < 20 * unit {
        600_000_000_000
    } else if amount <= 100 * unit {
        3_600_000_000_000
    } else {
        21_600_000_000_000
    }
}

/// Per-payee budget after a paid transfer of `paid`: never shrinks, grows to twice the payment,
/// capped at `cap` (the per-payment cap).
pub fn grown_budget(budget: u128, paid: u128, cap: u128) -> u128 {
    budget.max(paid.saturating_mul(2)).min(cap)
}

/// Checks that `verdict` binds exactly the pending request. Err carries the offending field.
pub fn binds(
    pending: &Pending,
    verdict: &Verdict,
    request_id: U64,
    token_id: &AccountId,
) -> Result<(), &'static str> {
    if verdict.format != VERDICT_FORMAT {
        return Err("format");
    }
    if verdict.request_id != request_id {
        return Err("request_id");
    }
    if verdict.receiver_id != pending.receiver_id {
        return Err("receiver_id");
    }
    if &verdict.token_id != token_id {
        return Err("token_id");
    }
    if verdict.amount != pending.amount {
        return Err("amount");
    }
    if verdict.reasons.is_empty() || verdict.reasons.len() > MAX_REASONS {
        return Err("reasons");
    }
    if !is_lower_hex_64(&verdict.record_sha256) {
        return Err("record_sha256");
    }
    Ok(())
}

/// Parses what OutLayer returned for a `Text` run (a JSON string holding the guest's stdout) or a
/// `Json` run (the JSON object). Err carries a short, static reason; never panics.
pub fn parse_outlayer_output(bytes: &[u8]) -> Result<Verdict, &'static str> {
    let value: Value = serde_json::from_slice(bytes).map_err(|_| "bad_result_json")?;
    let text = match value {
        Value::Null => return Err("null_result"),
        Value::String(s) => s,
        v @ Value::Object(_) => v.to_string(),
        _ => return Err("bad_result_shape"),
    };
    if text.len() > MAX_VERDICT_BYTES {
        return Err("oversized");
    }
    serde_json::from_str(&text).map_err(|_| "bad_verdict")
}

/// `^[A-Za-z0-9_-]{1,64}$`, the rule OutLayer applies to a secrets profile.
fn valid_profile(s: &str) -> bool {
    valid_client_ref(s)
}

/// `<owner>/<name>`: non-empty owner, name 1-64 bytes of `[A-Za-z0-9_-]` (OutLayer project rules;
/// a name may contain `/` only for nested projects, which the Guardian does not accept).
fn valid_project_id(s: &str) -> bool {
    if s.len() > MAX_PROJECT_ID_BYTES {
        return false;
    }
    match s.split_once('/') {
        Some((owner, name)) => owner.parse::<AccountId>().is_ok() && valid_client_ref(name),
        None => false,
    }
}

/// Checks an owner-supplied mode before it is stored. Err carries the offending field.
pub fn valid_mode(mode: &CheckerMode) -> Result<(), &'static str> {
    let CheckerMode::OutLayer {
        outlayer_id,
        project_id,
        version_key,
        secrets_ref,
        deposit_yocto,
        max_instructions,
        max_execution_seconds,
        max_requests_per_day,
    } = mode
    else {
        return Ok(());
    };
    if !matches!(outlayer_id.as_str(), "outlayer.testnet" | "outlayer.near") {
        return Err("outlayer_id");
    }
    if !valid_project_id(project_id) {
        return Err("project_id");
    }
    if version_key.as_deref().is_some_and(|k| !is_lower_hex_64(k)) {
        return Err("version_key");
    }
    if secrets_ref.as_ref().is_some_and(|s| !valid_profile(&s.profile)) {
        return Err("secrets_ref.profile");
    }
    if deposit_yocto.0 == 0 || deposit_yocto.0 > MAX_OUTLAYER_DEPOSIT.as_yoctonear() {
        return Err("deposit_yocto");
    }
    if !(1..=OUTLAYER_MAX_INSTRUCTIONS).contains(&max_instructions.0) {
        return Err("max_instructions");
    }
    if !(1..=OUTLAYER_MAX_SECONDS).contains(&max_execution_seconds.0) {
        return Err("max_execution_seconds");
    }
    if !(1..=MAX_REQUESTS_PER_DAY_LIMIT).contains(&max_requests_per_day.0) {
        return Err("max_requests_per_day");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::grown_budget;

    const T: u128 = 1_000_000;

    #[test]
    fn grown_budget_doubles_caps_and_never_shrinks() {
        assert_eq!(grown_budget(20 * T, 18 * T, 200 * T), 36 * T);
        assert_eq!(grown_budget(20 * T, 5 * T, 200 * T), 20 * T);
        assert_eq!(grown_budget(36 * T, 150 * T, 200 * T), 200 * T);
        assert_eq!(grown_budget(200 * T, 1, 200 * T), 200 * T);
        assert_eq!(grown_budget(20 * T, u128::MAX, 200 * T), 200 * T);
    }
}
