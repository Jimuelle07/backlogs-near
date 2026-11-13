//! Provenance rules (Jim, 2026-11-13): where did the receiver come from? Deterministic, no I/O, no AI.
//! They run as part of the policy check (`POLICY_ENABLED`) and add ids to `signals.policy.violations`:
//! `receiver_redirect`, `invoice_already_paid`, `untrusted_memory`, `obfuscated_context`.
use crate::counterparty::PayeeHistory;
use crate::formats::CheckerInput;

pub const V_RECEIVER_REDIRECT: &str = "receiver_redirect";
pub const V_INVOICE_ALREADY_PAID: &str = "invoice_already_paid";
pub const V_UNTRUSTED_MEMORY: &str = "untrusted_memory";
pub const V_OBFUSCATED_CONTEXT: &str = "obfuscated_context";

/// Run every rule; violation ids come back in the order of the constants above.
pub fn check(input: &CheckerInput, known_payees: &[PayeeHistory]) -> Vec<String> {
    let mut out = Vec::new();
    if receiver_redirect(input, known_payees) {
        out.push(V_RECEIVER_REDIRECT.to_string());
    }
    if invoice_already_paid(input) {
        out.push(V_INVOICE_ALREADY_PAID.to_string());
    }
    if input.context.iter().any(|c| c.source == "memory" && c.trust == "untrusted") {
        out.push(V_UNTRUSTED_MEMORY.to_string());
    }
    if input.context.iter().any(|c| obfuscated(&c.text)) {
        out.push(V_OBFUSCATED_CONTEXT.to_string());
    }
    out
}

/// Zero-width, bidi-control and similar invisible characters. U+200D is excluded (emoji joiner).
fn is_invisible(c: char) -> bool {
    matches!(c, '\u{200B}' | '\u{200C}' | '\u{2060}' | '\u{FEFF}' | '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}')
}

/// Account-like tokens of a text: lowercase, invisible chars dropped, split on every char outside
/// `[a-z0-9._@-]`, tokens with `@` skipped, edges trimmed of `.`, `-`, `_`, only tokens with a `.` kept.
fn account_tokens(text: &str) -> Vec<String> {
    let cleaned: String = text.to_lowercase().chars().filter(|c| !is_invisible(*c)).collect();
    cleaned
        .split(|c: char| !(c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '.' | '_' | '@' | '-')))
        .filter(|t| !t.contains('@'))
        .map(|t| t.trim_matches(|c| matches!(c, '.' | '-' | '_')))
        .filter(|t| t.contains('.'))
        .map(str::to_string)
        .collect()
}

/// Lowercase request, each run of chars outside `[a-z0-9]` collapsed to one space, padded with a space each side.
fn request_words(request: &str) -> String {
    let mut s = String::from(" ");
    let mut last_space = true;
    for c in request.to_lowercase().chars() {
        if c.is_ascii_lowercase() || c.is_ascii_digit() {
            s.push(c);
            last_space = false;
        } else if !last_space {
            s.push(' ');
            last_space = true;
        }
    }
    if !last_space {
        s.push(' ');
    }
    if s == " " {
        s.push(' ');
    }
    s
}

fn first_label(id: &str) -> &str {
    id.split('.').next().unwrap_or(id)
}

fn receiver_redirect(input: &CheckerInput, known_payees: &[PayeeHistory]) -> bool {
    let receiver = input.receiver_id.to_lowercase();
    let exact = known_payees.iter().any(|p| p.account_id.eq_ignore_ascii_case(&input.receiver_id));

    // (a) the request or a context item names a different known account.
    if !exact {
        let known: Vec<String> = known_payees
            .iter()
            .map(|p| p.account_id.to_lowercase())
            .filter(|id| id.contains('.') && *id != receiver)
            .collect();
        let texts = std::iter::once(input.user_request.as_str()).chain(input.context.iter().map(|c| c.text.as_str()));
        for text in texts {
            if account_tokens(text).iter().any(|t| known.contains(t)) {
                return true;
            }
        }
    }

    // (b) the request names a known payee and the receiver is not that payee.
    let words = request_words(&input.user_request);
    let mut named: Vec<String> = Vec::new();
    for p in known_payees {
        let label = first_label(&p.account_id).to_lowercase();
        if label.chars().count() < 4 {
            continue;
        }
        let spaced: String = label.chars().map(|c| if matches!(c, '-' | '_') { ' ' } else { c }).collect();
        let joined: String = label.chars().filter(|c| !matches!(c, '-' | '_')).collect();
        if words.contains(&format!(" {spaced} ")) || words.contains(&format!(" {joined} ")) {
            named.push(label);
        }
    }
    !named.is_empty() && !(exact && named.iter().any(|l| l == first_label(&receiver)))
}

/// Memo ids: maximal `[A-Za-z0-9-]` runs, trimmed of `-`, at least 4 chars, containing a digit, lowercased.
fn memo_ids(memo: &str) -> Vec<Vec<char>> {
    memo.split(|c: char| !(c.is_ascii_alphanumeric() || c == '-'))
        .map(|r| r.trim_matches('-'))
        .filter(|r| r.len() >= 4 && r.chars().any(|c| c.is_ascii_digit()))
        .map(|r| r.to_lowercase().chars().collect())
        .collect()
}

fn invoice_already_paid(input: &CheckerInput) -> bool {
    let ids = memo_ids(&input.memo);
    if ids.is_empty() {
        return false;
    }
    const NOT_PAID_YET: [&str; 7] = ["be", "not", "yet", "if", "when", "until", "unless"];
    for item in &input.context {
        let lower = item.text.to_lowercase();
        for line in lower.split('\n') {
            let line: Vec<char> = line.chars().collect();
            for id in &ids {
                if id.len() > line.len() {
                    continue;
                }
                for start in 0..=(line.len() - id.len()) {
                    if line[start..start + id.len()] != id[..] {
                        continue;
                    }
                    let end = start + id.len();
                    for p in end..line.len().saturating_sub(3) {
                        if matches!(line[p], '.' | ';') {
                            break;
                        }
                        if p - end > 24 {
                            break;
                        }
                        if line[p..p + 4] != ['p', 'a', 'i', 'd'] {
                            continue;
                        }
                        let word_before = p == 0 || !line[p - 1].is_alphanumeric();
                        let word_after = p + 4 >= line.len() || !line[p + 4].is_alphanumeric();
                        if !(word_before && word_after) {
                            continue;
                        }
                        if !NOT_PAID_YET.contains(&previous_word(&line[..p]).as_str()) {
                            return true;
                        }
                    }
                }
            }
        }
    }
    false
}

/// The last maximal alphanumeric run of `chars` (empty when none).
fn previous_word(chars: &[char]) -> String {
    let mut end = chars.len();
    while end > 0 && !chars[end - 1].is_alphanumeric() {
        end -= 1;
    }
    let mut start = end;
    while start > 0 && chars[start - 1].is_alphanumeric() {
        start -= 1;
    }
    chars[start..end].iter().collect()
}

fn is_latin(c: char) -> bool {
    c.is_ascii_alphabetic() || ('\u{00C0}'..='\u{024F}').contains(&c)
}

fn is_cyrillic_or_greek(c: char) -> bool {
    ('\u{0400}'..='\u{052F}').contains(&c) || ('\u{0370}'..='\u{03FF}').contains(&c)
}

/// An invisible char anywhere, or one alphabetic run that mixes Latin with Cyrillic or Greek letters.
fn obfuscated(text: &str) -> bool {
    if text.chars().any(is_invisible) {
        return true;
    }
    let (mut latin, mut other) = (false, false);
    for c in text.chars().chain(std::iter::once(' ')) {
        if c.is_alphabetic() {
            latin |= is_latin(c);
            other |= is_cyrillic_or_greek(c);
        } else {
            if latin && other {
                return true;
            }
            latin = false;
            other = false;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::counterparty::{find_lookalike, AgentProfile, LookalikeMatch};
    use crate::formats::ContextItem;
    use crate::policy::testing::{input, scenario_input};
    use std::path::{Path, PathBuf};

    fn payees() -> Vec<PayeeHistory> {
        AgentProfile::with_default_payees_in(None).known_payees
    }

    fn scenarios_dir() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../agent/scenarios")
    }

    fn json_files(dir: &Path) -> Vec<PathBuf> {
        let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
            .unwrap()
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().is_some_and(|e| e == "json"))
            .collect();
        v.sort();
        v
    }

    fn scenario(rel: &str) -> CheckerInput {
        let raw = std::fs::read_to_string(scenarios_dir().join(format!("{rel}.json"))).unwrap();
        scenario_input(&raw)
    }

    fn ctx(source: &str, trust: &str, text: &str) -> ContextItem {
        ContextItem { source: source.into(), reference: "x:1".into(), trust: trust.into(), text: text.into() }
    }

    fn with_context(memo: &str, text: &str) -> CheckerInput {
        let mut i = input();
        i.memo = memo.into();
        i.context = vec![ctx("email", "untrusted", text)];
        i
    }

    #[test]
    fn benign_scenarios_are_clean() {
        let payees = payees();
        let mut seen = 0;
        let mut dirs = vec![scenarios_dir(), scenarios_dir().join("external")];
        for dir in dirs.drain(..) {
            for path in json_files(&dir) {
                let raw = std::fs::read_to_string(&path).unwrap();
                let v: serde_json::Value = serde_json::from_str(&raw).unwrap();
                if v["label"] != "benign" {
                    continue;
                }
                seen += 1;
                let i = scenario_input(&raw);
                assert_eq!(check(&i, &payees), Vec::<String>::new(), "{}", path.display());
                let m = find_lookalike(&i.receiver_id, &payees, 2);
                assert!(
                    matches!(m, LookalikeMatch::Exact(_) | LookalikeMatch::Novel),
                    "{}: {m:?}",
                    path.display()
                );
            }
        }
        assert!(seen >= 250, "only {seen} benign scenarios");
    }

    #[test]
    fn named_cases() {
        let payees = payees();
        let cases: [(&str, &[&str]); 8] = [
            ("attack-fake-invoice-duplicate", &[V_INVOICE_ALREADY_PAID]),
            ("attack-memory-poisoning-gen-08", &[V_UNTRUSTED_MEMORY]),
            ("attack-memory-preference", &[V_RECEIVER_REDIRECT, V_UNTRUSTED_MEMORY]),
            ("attack-indirect-x-thread", &[V_RECEIVER_REDIRECT]),
            ("attack-homoglyph-text", &[V_OBFUSCATED_CONTEXT]),
            ("redteam/redteam-14", &[V_RECEIVER_REDIRECT]),
            ("external/ext-agentdojo-attack-001", &[V_RECEIVER_REDIRECT]),
            ("attack-fake-invoice-new-vendor", &[]),
        ];
        for (name, want) in cases {
            assert_eq!(check(&scenario(name), &payees), want, "{name}");
        }
    }

    #[test]
    fn unpaid_and_to_be_paid_do_not_fire_invoice_rule() {
        let payees = payees();
        for text in ["Invoice INV-2026-11 is unpaid", "INV-2026-11 is to be paid on Friday", "inv-2026-11: not paid yet"] {
            assert!(check(&with_context("INV-2026-11", text), &payees).is_empty(), "{text}");
        }
        assert_eq!(
            check(&with_context("INV-2026-11", "Note: INV-2026-11 was already paid last week"), &payees),
            vec![V_INVOICE_ALREADY_PAID]
        );
    }

    #[test]
    fn emoji_zwj_sequence_does_not_fire_obfuscation() {
        let i = with_context("x", "Thanks! \u{1F468}\u{200D}\u{1F469}\u{200D}\u{1F467}");
        assert!(check(&i, &payees()).is_empty());
        let i = with_context("x", "pay\u{200B}ment");
        assert_eq!(check(&i, &payees()), vec![V_OBFUSCATED_CONTEXT]);
    }

    #[test]
    fn short_payee_label_never_names() {
        let short = vec![PayeeHistory {
            account_id: "abc.demo.testnet".into(),
            prior_payments: 3,
            is_contract: None,
            account_age_days: None,
            code_hash: None,
        }];
        let mut i = input();
        i.user_request = "Pay the abc invoice.".into();
        i.receiver_id = "other.demo.testnet".into();
        assert!(check(&i, &short).is_empty());
    }

    #[test]
    fn named_payee_with_other_receiver_is_redirect() {
        let mut i = input();
        i.user_request = "Pay the HostCo invoice.".into();
        i.receiver_id = "cloudco.demo.testnet".into();
        i.context = vec![];
        assert_eq!(check(&i, &payees()), vec![V_RECEIVER_REDIRECT]);
        i.receiver_id = "hostco.demo.testnet".into();
        assert!(check(&i, &payees()).is_empty());
    }
}
