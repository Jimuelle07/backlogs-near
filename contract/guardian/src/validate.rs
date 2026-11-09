//! Pure validation helpers (no host calls).
use crate::types::{Pending, Verdict, VERDICT_FORMAT};
use near_sdk::json_types::U64;
use near_sdk::AccountId;

pub const MAX_CONTEXT_BYTES: usize = 8192;
pub const MAX_CONTEXT_ITEMS: usize = 8;
pub const MAX_MEMO_CHARS: usize = 256;
pub const MAX_USER_REQUEST_CHARS: usize = 1024;
pub const MAX_REF_CHARS: usize = 128;
pub const MAX_REASONS: usize = 6;

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
