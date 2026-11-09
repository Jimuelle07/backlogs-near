//! Deterministic policy rules (B1): receiver allowlist, memo sanity, amount sanity, and
//! "the amount must match what the user asked for or what the invoice states".
//! Output is the frozen `signals.policy` shape `{ok, violations[]}`; no I/O, no AI.
use crate::formats::{CheckerInput, PolicySignal};

pub const V_RECEIVER_NOT_ALLOWLISTED: &str = "receiver_not_allowlisted";
pub const V_MEMO_TOO_LONG: &str = "memo_too_long";
pub const V_MEMO_BAD_CHARS: &str = "memo_bad_chars";
pub const V_AMOUNT_INVALID: &str = "amount_invalid";
pub const V_AMOUNT_OVER_CAP: &str = "amount_over_cap";
pub const V_AMOUNT_MISMATCH_REQUEST: &str = "amount_mismatch_request";
pub const V_AMOUNT_MISMATCH_INVOICE: &str = "amount_mismatch_invoice";

pub const DEFAULT_MAX_MEMO_CHARS: usize = 128;

/// Checker config for the policy check. Thresholds live here, never in prompts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyConfig {
    /// `POLICY_ENABLED` (default on). Off: `signals.policy` is `null`.
    pub enabled: bool,
    /// `POLICY_ALLOWLIST`, comma-separated account ids. Empty = no allowlist rule.
    pub allowlist: Vec<String>,
    /// `POLICY_MAX_AMOUNT`, token base units. `None` = no cap rule.
    pub max_amount: Option<u128>,
    /// `POLICY_MAX_MEMO_CHARS`, default 128.
    pub max_memo_chars: usize,
}

impl Default for PolicyConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            allowlist: Vec::new(),
            max_amount: None,
            max_memo_chars: DEFAULT_MAX_MEMO_CHARS,
        }
    }
}

impl PolicyConfig {
    pub fn from_env() -> Result<Self, String> {
        Self::from_vars(|k| std::env::var(k).ok())
    }

    /// Variable lookup is injectable for tests; empty values count as unset.
    /// A malformed value is an error (the checker fails closed), never a silent default.
    pub fn from_vars(get: impl Fn(&str) -> Option<String>) -> Result<Self, String> {
        let var = |k: &str| get(k).map(|v| v.trim().to_string()).filter(|v| !v.is_empty());
        let mut cfg = Self::default();
        if let Some(v) = var("POLICY_ENABLED") {
            cfg.enabled = match v.to_ascii_lowercase().as_str() {
                "1" | "true" | "on" | "yes" => true,
                "0" | "false" | "off" | "no" => false,
                _ => return Err(format!("POLICY_ENABLED: expected 1/0/true/false/on/off, got {v:?}")),
            };
        }
        if let Some(v) = var("POLICY_ALLOWLIST") {
            cfg.allowlist = v
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect();
        }
        if let Some(v) = var("POLICY_MAX_AMOUNT") {
            match parse_base_units(&v) {
                Some(n) if n > 0 => cfg.max_amount = Some(n),
                _ => return Err(format!("POLICY_MAX_AMOUNT: expected positive integer base units, got {v:?}")),
            }
        }
        if let Some(v) = var("POLICY_MAX_MEMO_CHARS") {
            cfg.max_memo_chars = v
                .parse()
                .map_err(|_| format!("POLICY_MAX_MEMO_CHARS: expected integer, got {v:?}"))?;
        }
        Ok(cfg)
    }
}

/// Run every rule. Does not consult `cfg.enabled`; the caller decides whether to run it.
pub fn check(input: &CheckerInput, cfg: &PolicyConfig) -> PolicySignal {
    let mut violations: Vec<String> = Vec::new();
    let mut add = |id: &str| violations.push(id.to_string());

    if !cfg.allowlist.is_empty() && !cfg.allowlist.iter().any(|a| a == &input.receiver_id) {
        add(V_RECEIVER_NOT_ALLOWLISTED);
    }

    if input.memo.chars().count() > cfg.max_memo_chars {
        add(V_MEMO_TOO_LONG);
    }
    if input.memo.chars().any(is_bad_memo_char) {
        add(V_MEMO_BAD_CHARS);
    }

    match parse_base_units(&input.amount).filter(|n| *n > 0) {
        None => add(V_AMOUNT_INVALID),
        Some(amount) => {
            if cfg.max_amount.is_some_and(|cap| amount > cap) {
                add(V_AMOUNT_OVER_CAP);
            }
            let decimals = input.token_decimals;
            // The user's own words win over invoice text: an attacker controls the invoice.
            let asked = scan_amounts(&input.user_request, decimals);
            if !asked.is_empty() {
                let derived = fraction_amounts(&input.user_request, &asked);
                // A stated fraction replaces the bare numbers: "half of 95" must not accept 95.
                let fractional = !stated_fractions(&input.user_request).is_empty();
                let stated = !fractional && asked.iter().any(|s| s.units == Some(amount));
                if !stated && !derived.contains(&amount) {
                    add(V_AMOUNT_MISMATCH_REQUEST);
                }
            } else {
                let invoiced: Vec<Stated> = input
                    .context
                    .iter()
                    .flat_map(|c| scan_amounts(&c.text, decimals))
                    .filter(|s| s.tagged)
                    .collect();
                if !invoiced.is_empty() && !invoiced.iter().any(|s| s.units == Some(amount)) {
                    add(V_AMOUNT_MISMATCH_INVOICE);
                }
            }
        }
    }

    PolicySignal { ok: violations.is_empty(), violations }
}

/// Control characters, zero-width characters and bidi controls: invisible or reordering text in a memo.
fn is_bad_memo_char(c: char) -> bool {
    c.is_control()
        || matches!(
            c,
            '\u{200B}'..='\u{200F}' // zero-width space/joiners, LRM, RLM
                | '\u{202A}'..='\u{202E}' // bidi embeddings/overrides
                | '\u{2060}'..='\u{2064}' // word joiner, invisible operators
                | '\u{2066}'..='\u{2069}' // bidi isolates
                | '\u{061C}'
                | '\u{FEFF}'
        )
}

/// Canonical decimal base-unit string (digits only, no leading zeros) -> u128.
fn parse_base_units(s: &str) -> Option<u128> {
    if s.is_empty() || !s.bytes().all(|b| b.is_ascii_digit()) || (s.len() > 1 && s.starts_with('0')) {
        return None;
    }
    s.parse().ok()
}

/// Fractions the user request itself states, as (numerator, denominator): half, third, quarter/fourth,
/// `N%`, `N percent`. Only ever called on the user request; invoice text is untrusted.
fn stated_fractions(text: &str) -> Vec<(u128, u128)> {
    const PCT_SCALE: u128 = 1_000_000; // percent values keep up to 6 fractional digits
    let lower = text.to_ascii_lowercase();
    let mut out = Vec::new();
    for w in lower.split(|ch: char| !ch.is_ascii_alphanumeric()) {
        match w {
            "half" => out.push((1, 2)),
            "third" => out.push((1, 3)),
            "quarter" | "fourth" => out.push((1, 4)),
            _ => {}
        }
    }
    let mut marks: Vec<usize> = lower.match_indices('%').map(|(p, _)| p).collect();
    for (p, _) in lower.match_indices("percent") {
        let before = lower[..p].chars().next_back();
        let after = lower[p + 7..].chars().next();
        if !before.is_some_and(|ch| ch.is_ascii_alphabetic()) && !after.is_some_and(|ch| ch.is_ascii_alphabetic()) {
            marks.push(p);
        }
    }
    for p in marks {
        let num: String = lower[..p].trim_end_matches(' ').chars().rev().take_while(|ch| ch.is_ascii_digit() || *ch == '.').collect();
        let num: String = num.chars().rev().collect();
        let (int, frac) = num.split_once('.').unwrap_or((num.as_str(), ""));
        if int.is_empty() {
            continue;
        }
        if let Some(n) = to_units(int, frac, 6) {
            out.push((n, 100 * PCT_SCALE));
        }
    }
    out
}

/// Base-unit amounts the user's stated fractions of their stated amounts produce, rounded half-up
/// at base-unit precision.
fn fraction_amounts(user_request: &str, asked: &[Stated]) -> Vec<u128> {
    let mut out = Vec::new();
    for (num, den) in stated_fractions(user_request) {
        for units in asked.iter().filter_map(|s| s.units) {
            let scaled = units.checked_mul(num).and_then(|v| v.checked_mul(2)).and_then(|v| v.checked_add(den));
            if let Some(v) = scaled {
                out.push(v / (2 * den));
            }
        }
    }
    out
}

/// An amount found in free text, scaled to base units (`None`: not representable at this precision).
#[derive(Debug, Clone, PartialEq, Eq)]
struct Stated {
    units: Option<u128>,
    /// Followed by a currency word (usdc, tusdc, usd, dollar[s]) or preceded by `$`.
    tagged: bool,
}

/// Decimal digits `int[.frac]` -> base units. `None` on excess precision or overflow.
fn to_units(int: &str, frac: &str, decimals: u8) -> Option<u128> {
    if frac.len() > decimals as usize {
        return None;
    }
    let scale = 10u128.checked_pow(decimals as u32)?;
    let whole: u128 = int.parse().ok()?;
    let frac_units: u128 = if frac.is_empty() {
        0
    } else {
        let f: u128 = frac.parse().ok()?;
        f.checked_mul(10u128.checked_pow((decimals as usize - frac.len()) as u32)?)?
    };
    whole.checked_mul(scale)?.checked_add(frac_units)
}

/// Find decimal amounts in `text`. A number counts only when it stands alone (not part of an
/// identifier like `INV-2026-11` or `v1.2`). With a currency tag it is always an amount; without one
/// it is returned untagged, and the caller decides whether bare numbers matter.
fn scan_amounts(text: &str, decimals: u8) -> Vec<Stated> {
    let c: Vec<char> = text.chars().collect();
    let mut out = Vec::new();
    let mut i = 0;
    while i < c.len() {
        if !c[i].is_ascii_digit() {
            i += 1;
            continue;
        }
        let start = i;
        let mut int = String::new();
        while i < c.len() {
            if c[i].is_ascii_digit() {
                int.push(c[i]);
                i += 1;
            } else if c[i] == ','
                && i + 4 <= c.len()
                && c[i + 1..i + 4].iter().all(|d| d.is_ascii_digit())
                && !c.get(i + 4).is_some_and(|d| d.is_ascii_digit())
            {
                i += 1; // thousands separator
            } else {
                break;
            }
        }
        let mut frac = String::new();
        if i + 1 < c.len() && c[i] == '.' && c[i + 1].is_ascii_digit() {
            i += 1;
            while i < c.len() && c[i].is_ascii_digit() {
                frac.push(c[i]);
                i += 1;
            }
        }
        let standalone = start == 0 || !(c[start - 1].is_alphanumeric() || matches!(c[start - 1], '_' | '-' | '.' | '/'));
        let mut j = i;
        while j < c.len() && c[j] == ' ' {
            j += 1;
        }
        let word: String = c[j..].iter().take_while(|ch| ch.is_ascii_alphabetic()).collect::<String>().to_ascii_lowercase();
        let dollar = (start > 0 && c[start - 1] == '$') || (start > 1 && c[start - 1] == ' ' && c[start - 2] == '$');
        let tagged = dollar || matches!(word.as_str(), "usdc" | "tusdc" | "usd" | "dollar" | "dollars");
        let glued_letter = c.get(i).is_some_and(|ch| ch.is_alphabetic());
        if standalone && (tagged || !glued_letter) {
            out.push(Stated { units: to_units(&int, &frac, decimals), tagged });
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::formats::ContextItem;

    fn input() -> CheckerInput {
        serde_json::from_str(include_str!("../../schemas/examples/checker-input.json")).unwrap()
    }

    fn with(f: impl FnOnce(&mut CheckerInput)) -> CheckerInput {
        let mut i = input();
        f(&mut i);
        i
    }

    fn ctx(text: &str) -> ContextItem {
        ContextItem { source: "email".into(), reference: "email:x".into(), trust: "untrusted".into(), text: text.into() }
    }

    fn ids(i: &CheckerInput, cfg: &PolicyConfig) -> Vec<String> {
        check(i, cfg).violations
    }

    /// Scenario file -> CheckerInput the way the agent builds it (6 decimals, {NS} = demo.testnet).
    fn scenario_input(raw: &str) -> CheckerInput {
        let raw = raw.replace("{NS}", "demo.testnet");
        let s: serde_json::Value = serde_json::from_str(&raw).unwrap();
        let args = &s["scripted_tool_call"]["arguments"];
        let amount = args["amount"].as_str().unwrap();
        let (int, frac) = amount.split_once('.').unwrap_or((amount, ""));
        let mut i = input();
        i.receiver_id = args["receiver_id"].as_str().unwrap().into();
        i.amount = to_units(int, frac, i.token_decimals).unwrap().to_string();
        i.memo = args["memo"].as_str().unwrap().into();
        i.user_request = s["user_request"].as_str().unwrap().into();
        i.context = s["inbox"]
            .as_array()
            .unwrap()
            .iter()
            .map(|c| ContextItem {
                source: c["source"].as_str().unwrap().into(),
                reference: c["ref"].as_str().unwrap().into(),
                trust: c["trust"].as_str().unwrap().into(),
                text: c["text"].as_str().unwrap().into(),
            })
            .collect();
        i
    }

    #[test]
    fn example_input_is_clean() {
        let s = check(&input(), &PolicyConfig::default());
        assert!(s.ok);
        assert!(s.violations.is_empty());
    }

    #[test]
    fn fake_invoice_amount_inflation_is_flagged() {
        let i = scenario_input(include_str!("../../agent/scenarios/attack-fake-invoice-amount-inflation.json"));
        assert_eq!(i.amount, "180000000");
        let s = check(&i, &PolicyConfig::default());
        assert!(!s.ok);
        assert_eq!(s.violations, vec![V_AMOUNT_MISMATCH_REQUEST]);
    }

    #[test]
    fn morse_lookalike_inflated_amount_is_flagged_against_invoice() {
        let i = scenario_input(include_str!("../../agent/scenarios/attack-morse-lookalike.json"));
        assert_eq!(ids(&i, &PolicyConfig::default()), vec![V_AMOUNT_MISMATCH_INVOICE]);
    }

    #[test]
    fn benign_hosting_passes() {
        let i = scenario_input(include_str!("../../agent/scenarios/benign-hosting.json"));
        assert_eq!(check(&i, &PolicyConfig::default()), PolicySignal { ok: true, violations: vec![] });
    }

    #[test]
    fn benign_scenarios_all_pass() {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../agent/scenarios");
        let mut n = 0;
        for e in std::fs::read_dir(dir).unwrap() {
            let p = e.unwrap().path();
            let name = p.file_name().unwrap().to_string_lossy().to_string();
            if !name.starts_with("benign-") || !name.ends_with(".json") {
                continue;
            }
            n += 1;
            let v = ids(&scenario_input(&std::fs::read_to_string(&p).unwrap()), &PolicyConfig::default());
            assert!(v.is_empty(), "{name}: {v:?}");
        }
        assert!(n >= 20);
    }

    #[test]
    fn fraction_of_stated_amount_is_accepted() {
        let req = |text: &str, amount: &str| {
            with(|i| {
                i.user_request = text.into();
                i.amount = amount.into();
            })
        };
        let cfg = PolicyConfig::default();
        assert!(ids(&req("Pay half of the 95 USDC invoice", "47500000"), &cfg).is_empty());
        assert!(ids(&req("Pay a third of 10 USDC", "3333333"), &cfg).is_empty());
        assert!(ids(&req("Pay a quarter of 10 USDC", "2500000"), &cfg).is_empty());
        assert!(ids(&req("Pay 25% of 80 USDC", "20000000"), &cfg).is_empty());
        assert_eq!(ids(&req("Pay 25% of 80 USDC", "80000000"), &cfg), vec![V_AMOUNT_MISMATCH_REQUEST]);
        assert!(ids(&req("Pay 12.5 percent of 80 USDC", "10000000"), &cfg).is_empty());
        assert!(ids(&req("Pay half of 0.000001 USDC", "1"), &cfg).is_empty()); // 0.5 rounds half-up to 1
        // Fraction-derived amount that differs from the payment is still flagged.
        for amount in ["95000000", "60000000", "47500001"] {
            assert_eq!(ids(&req("Pay half of the 95 USDC invoice", amount), &cfg), vec![V_AMOUNT_MISMATCH_REQUEST], "{amount}");
        }
        // Fractions come from the user request only: invoice text saying "half" does not help.
        let i = with(|i| {
            i.user_request = "Pay the 95 USDC invoice".into();
            i.context = vec![ctx("pay half now, 50% off")];
            i.amount = "47500000".into();
        });
        assert_eq!(ids(&i, &cfg), vec![V_AMOUNT_MISMATCH_REQUEST]);
    }

    #[test]
    fn user_amount_wins_over_invoice() {
        // Invoice says 180, user said 18: paying 180 is flagged, paying 18 is not.
        let base = |amount: &str| {
            with(|i| {
                i.user_request = "Pay the 18 USDC hosting bill.".into();
                i.context = vec![ctx("amount due 180.00 USDC")];
                i.amount = amount.into();
            })
        };
        assert_eq!(ids(&base("180000000"), &PolicyConfig::default()), vec![V_AMOUNT_MISMATCH_REQUEST]);
        assert!(ids(&base("18000000"), &PolicyConfig::default()).is_empty());
    }

    #[test]
    fn invoice_amount_used_when_user_states_none() {
        let i = with(|i| {
            i.context = vec![ctx("Invoice INV-2026-11, amount due 18.00 USDC"), ctx("older: $12.5")];
            i.amount = "12500000".into();
        });
        assert!(ids(&i, &PolicyConfig::default()).is_empty());
        let i = with(|i| i.amount = "18000001".into());
        assert_eq!(ids(&i, &PolicyConfig::default()), vec![V_AMOUNT_MISMATCH_INVOICE]);
    }

    #[test]
    fn no_stated_amount_means_no_mismatch() {
        let i = with(|i| {
            i.context = vec![ctx("Invoice INV-2026-11, ref 2026")];
            i.amount = "5".into();
        });
        assert!(ids(&i, &PolicyConfig::default()).is_empty());
    }

    #[test]
    fn decimals_scaling() {
        assert_eq!(to_units("18", "", 6), Some(18_000_000));
        assert_eq!(to_units("18", "00", 6), Some(18_000_000));
        assert_eq!(to_units("0", "000001", 6), Some(1));
        assert_eq!(to_units("0", "0000001", 6), None);
        assert_eq!(to_units("18", "5", 0), None);
        assert_eq!(to_units("18", "", 0), Some(18));
        assert_eq!(to_units("340282366920938463463374607431768211455", "", 6), None);
        // "18 tUSDC" vs 18000000 at 6 decimals, 18 at 0 decimals, 18e18 at 18 decimals
        let i = with(|i| i.user_request = "Send 18 tUSDC to HostCo".into());
        assert!(ids(&i, &PolicyConfig::default()).is_empty());
        let i = with(|i| {
            i.user_request = "Send 18 tUSDC to HostCo".into();
            i.token_decimals = 18;
            i.amount = "18000000000000000000".into();
        });
        assert!(ids(&i, &PolicyConfig::default()).is_empty());
        let i = with(|i| {
            i.user_request = "Send 18 tUSDC to HostCo".into();
            i.token_decimals = 18;
        });
        assert_eq!(ids(&i, &PolicyConfig::default()), vec![V_AMOUNT_MISMATCH_REQUEST]);
        let i = with(|i| {
            i.user_request = "Send 18.5 USDC".into();
            i.amount = "18500000".into();
        });
        assert!(ids(&i, &PolicyConfig::default()).is_empty());
    }

    #[test]
    fn scanner_ignores_identifiers_and_reads_separators() {
        let s = scan_amounts("INV-2026-11 v1.2 ref_7 x9 USDC", 6);
        assert!(s.is_empty(), "{s:?}");
        let s = scan_amounts("total 1,234.50 USDC.", 6);
        assert_eq!(s, vec![Stated { units: Some(1_234_500_000), tagged: true }]);
        let s = scan_amounts("pay 7 now, 18USDC and $3", 6);
        assert_eq!(
            s,
            vec![
                Stated { units: Some(7_000_000), tagged: false },
                Stated { units: Some(18_000_000), tagged: true },
                Stated { units: Some(3_000_000), tagged: true },
            ]
        );
    }

    #[test]
    fn amount_validity_and_cap_edge() {
        let cfg = PolicyConfig { max_amount: Some(18_000_000), ..Default::default() };
        assert!(ids(&input(), &cfg).is_empty()); // exactly at the cap
        let over = with(|i| i.amount = "18000001".into());
        let v = ids(&over, &cfg);
        assert!(v.contains(&V_AMOUNT_OVER_CAP.to_string()));
        for bad in ["0", "", "-5", "1.5", "007", "1e6", " 5", "999999999999999999999999999999999999999999"] {
            let i = with(|i| i.amount = bad.into());
            assert_eq!(ids(&i, &PolicyConfig::default()), vec![V_AMOUNT_INVALID], "{bad:?}");
        }
    }

    #[test]
    fn memo_rules_and_boundary() {
        let cfg = PolicyConfig::default();
        let at = with(|i| i.memo = "a".repeat(128));
        assert!(ids(&at, &cfg).is_empty());
        let over = with(|i| i.memo = "a".repeat(129));
        assert_eq!(ids(&over, &cfg), vec![V_MEMO_TOO_LONG]);
        // length counts chars, not bytes
        let uni = with(|i| i.memo = "é".repeat(128));
        assert!(ids(&uni, &cfg).is_empty());
        let small = PolicyConfig { max_memo_chars: 4, ..Default::default() };
        assert!(ids(&with(|i| i.memo = "abcd".into()), &small).is_empty());
        assert_eq!(ids(&with(|i| i.memo = "abcde".into()), &small), vec![V_MEMO_TOO_LONG]);
        for bad in ["a\u{0}b", "a\nb", "a\u{200B}b", "a\u{202E}b", "a\u{2066}b", "\u{FEFF}a", "a\u{7f}"] {
            assert_eq!(ids(&with(|i| i.memo = bad.into()), &cfg), vec![V_MEMO_BAD_CHARS], "{bad:?}");
        }
        assert!(ids(&with(|i| i.memo = "KIM-20 – Übersetzung".into()), &cfg).is_empty());
        assert!(ids(&with(|i| i.memo = String::new()), &cfg).is_empty());
    }

    #[test]
    fn allowlist_hit_and_miss() {
        let cfg = PolicyConfig { allowlist: vec!["hostco.demo.testnet".into(), "other.testnet".into()], ..Default::default() };
        assert!(ids(&input(), &cfg).is_empty());
        let miss = with(|i| i.receiver_id = "hostc0.demo.testnet".into());
        assert_eq!(ids(&miss, &cfg), vec![V_RECEIVER_NOT_ALLOWLISTED]);
        // empty allowlist = rule off
        assert!(ids(&miss, &PolicyConfig::default()).is_empty());
    }

    #[test]
    fn multiple_violations_accumulate_in_rule_order() {
        let cfg = PolicyConfig { allowlist: vec!["x.testnet".into()], ..Default::default() };
        let i = with(|i| {
            i.memo = "a\u{200B}".repeat(100);
            i.amount = "0".into();
        });
        assert_eq!(ids(&i, &cfg), vec![V_RECEIVER_NOT_ALLOWLISTED, V_MEMO_TOO_LONG, V_MEMO_BAD_CHARS, V_AMOUNT_INVALID]);
    }

    fn vars(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let owned: Vec<(String, String)> = pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
        move |k| owned.iter().find(|(n, _)| n == k).map(|(_, v)| v.clone())
    }

    #[test]
    fn config_from_vars() {
        assert_eq!(PolicyConfig::from_vars(vars(&[])).unwrap(), PolicyConfig::default());
        assert_eq!(PolicyConfig::from_vars(vars(&[("POLICY_ENABLED", ""), ("POLICY_ALLOWLIST", " ")])).unwrap(), PolicyConfig::default());
        for off in ["0", "false", "OFF", "no"] {
            let get = move |k: &str| (k == "POLICY_ENABLED").then(|| off.to_string());
            assert!(!PolicyConfig::from_vars(get).unwrap().enabled, "{off}");
        }
        let cfg = PolicyConfig::from_vars(vars(&[
            ("POLICY_ENABLED", "true"),
            ("POLICY_ALLOWLIST", "a.testnet, b.testnet,,"),
            ("POLICY_MAX_AMOUNT", "50000000"),
            ("POLICY_MAX_MEMO_CHARS", "64"),
        ]))
        .unwrap();
        assert!(cfg.enabled);
        assert_eq!(cfg.allowlist, vec!["a.testnet", "b.testnet"]);
        assert_eq!(cfg.max_amount, Some(50_000_000));
        assert_eq!(cfg.max_memo_chars, 64);
        for bad in [
            &[("POLICY_ENABLED", "maybe")][..],
            &[("POLICY_MAX_AMOUNT", "0")],
            &[("POLICY_MAX_AMOUNT", "18.5")],
            &[("POLICY_MAX_MEMO_CHARS", "-1")],
        ] {
            assert!(PolicyConfig::from_vars(vars(bad)).is_err());
        }
    }
}
