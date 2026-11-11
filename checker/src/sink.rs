//! Off-chain DecisionRecord sink (A2): POSTs each serialized DecisionRecord to
//! `DECISION_LOG_URL`. If the POST fails, an `allow` outcome is downgraded to `hold`
//! (`sdd.md §7`).
use crate::decide::{record_bytes, sha256_hex, CheckerError};
use crate::formats::{DecisionRecord, Outcome, Verdict};
use crate::http::{self, HttpError};
use std::fmt;
use std::time::Duration;

pub const SINK_TIMEOUT: Duration = Duration::from_secs(3);

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SinkConfig {
    /// `DECISION_LOG_URL`. `None` when unset or empty (no HTTP POST).
    pub url: Option<String>,
}

impl SinkConfig {
    pub fn from_env() -> Self {
        Self::from_vars(|k| std::env::var(k).ok())
    }

    /// Variable lookup is injectable for tests; empty/whitespace values count as unset.
    pub fn from_vars(get: impl Fn(&str) -> Option<String>) -> Self {
        let url = get("DECISION_LOG_URL")
            .map(|v| v.trim().to_string())
            .filter(|v| !v.is_empty());
        Self { url }
    }
}

#[derive(Debug)]
pub enum SinkError {
    Http(HttpError),
    Status { status: u16, body: String },
}

impl fmt::Display for SinkError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SinkError::Http(e) => write!(f, "sink http: {e}"),
            SinkError::Status { status, body } => write!(f, "sink status {status}: {body}"),
        }
    }
}

impl std::error::Error for SinkError {}

impl From<HttpError> for SinkError {
    fn from(e: HttpError) -> Self {
        SinkError::Http(e)
    }
}

pub trait RecordSink {
    fn post(&self, record_json: &str) -> Result<(), SinkError>;
}

pub struct HttpRecordSink {
    pub url: String,
    pub timeout: Duration,
}

impl HttpRecordSink {
    pub fn new(url: impl Into<String>) -> Self {
        Self { url: url.into(), timeout: SINK_TIMEOUT }
    }
}

impl RecordSink for HttpRecordSink {
    fn post(&self, record_json: &str) -> Result<(), SinkError> {
        let resp = http::post_json(&self.url, "", record_json, self.timeout)?;
        if !(200..300).contains(&resp.status) {
            let body: String = resp.body.chars().take(300).collect();
            return Err(SinkError::Status { status: resp.status, body });
        }
        Ok(())
    }
}

/// POST `record` to `sink`. On failure, downgrades `allow` to `hold` on both `verdict` and
/// `record` and recomputes `verdict.record_sha256` so it matches the downgraded record.
pub fn deliver(
    verdict: &mut Verdict,
    record: &mut DecisionRecord,
    sink: &dyn RecordSink,
) -> Result<(), CheckerError> {
    let bytes = record_bytes(record)?;
    let json = String::from_utf8(bytes).map_err(|e| CheckerError::Serialize(e.to_string()))?;
    if let Err(e) = sink.post(&json) {
        eprintln!("checker warning: decision log POST failed: {e}");
        if verdict.outcome == Outcome::Allow {
            verdict.outcome = Outcome::Hold;
            record.outcome = Outcome::Hold;
            verdict.record_sha256 = sha256_hex(&record_bytes(record)?);
        }
    }
    Ok(())
}

/// Deliver using `SinkConfig`: no-op when `cfg.url` is `None`.
pub fn deliver_with_config(
    verdict: &mut Verdict,
    record: &mut DecisionRecord,
    cfg: &SinkConfig,
) -> Result<(), CheckerError> {
    if let Some(url) = &cfg.url {
        let sink = HttpRecordSink::new(url.clone());
        deliver(verdict, record, &sink)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::decide::decide_with;
    use crate::policy::PolicyConfig;
    use std::cell::RefCell;

    const INPUT: &str = include_str!("../../schemas/examples/checker-input.json");

    struct FakeSink {
        seen: RefCell<Vec<String>>,
        result: Result<(), u16>,
    }

    impl FakeSink {
        fn ok() -> Self {
            Self { seen: RefCell::new(Vec::new()), result: Ok(()) }
        }

        fn err_status(status: u16) -> Self {
            Self { seen: RefCell::new(Vec::new()), result: Err(status) }
        }
    }

    impl RecordSink for FakeSink {
        fn post(&self, record_json: &str) -> Result<(), SinkError> {
            self.seen.borrow_mut().push(record_json.to_string());
            match self.result {
                Ok(()) => Ok(()),
                Err(status) => Err(SinkError::Status { status, body: "error".into() }),
            }
        }
    }

    struct TransportErrSink( fn() -> HttpError );

    impl RecordSink for TransportErrSink {
        fn post(&self, _: &str) -> Result<(), SinkError> {
            Err(SinkError::Http((self.0)()))
        }
    }

    fn vars(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let owned: Vec<(String, String)> =
            pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
        move |k| owned.iter().find(|(n, _)| n == k).map(|(_, v)| v.clone())
    }

    #[test]
    fn config_from_vars() {
        assert_eq!(SinkConfig::from_vars(vars(&[])), SinkConfig { url: None });
        assert_eq!(
            SinkConfig::from_vars(vars(&[("DECISION_LOG_URL", "")])),
            SinkConfig { url: None }
        );
        assert_eq!(
            SinkConfig::from_vars(vars(&[("DECISION_LOG_URL", "   ")])),
            SinkConfig { url: None }
        );
        assert_eq!(
            SinkConfig::from_vars(vars(&[("DECISION_LOG_URL", " https://sink.example/log ")])),
            SinkConfig { url: Some("https://sink.example/log".into()) }
        );
    }

    #[test]
    fn disabled_sink_leaves_allow_unchanged() {
        let (mut v, mut r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let orig_sha = v.record_sha256.clone();
        deliver_with_config(&mut v, &mut r, &SinkConfig::default()).unwrap();
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(r.outcome, Outcome::Allow);
        assert_eq!(v.record_sha256, orig_sha);
    }

    #[test]
    fn post_success_preserves_allow_and_sends_exact_record_bytes() {
        let (mut v, mut r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let orig_sha = v.record_sha256.clone();
        let sink = FakeSink::ok();
        deliver(&mut v, &mut r, &sink).unwrap();
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(r.outcome, Outcome::Allow);
        assert_eq!(v.record_sha256, orig_sha);
        let seen = sink.seen.borrow();
        assert_eq!(seen.len(), 1);
        assert_eq!(sha256_hex(seen[0].as_bytes()), orig_sha);
        let parsed: DecisionRecord = serde_json::from_str(&seen[0]).unwrap();
        assert_eq!(parsed, r);
    }

    #[test]
    fn post_status_failure_downgrades_allow_to_hold() {
        let (mut v, mut r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let orig_sha = v.record_sha256.clone();
        let sink = FakeSink::err_status(500);
        deliver(&mut v, &mut r, &sink).unwrap();
        assert_eq!(v.outcome, Outcome::Hold);
        assert_eq!(r.outcome, Outcome::Hold);
        assert_ne!(v.record_sha256, orig_sha);
        assert_eq!(v.record_sha256, sha256_hex(&record_bytes(&r).unwrap()));
        assert!(serde_json::to_vec(&v).unwrap().len() <= 900);
    }

    #[test]
    fn post_transport_and_timeout_downgrade_allow_to_hold() {
        for err_fn in [
            (|| HttpError::Timeout) as fn() -> HttpError,
            || HttpError::Transport("connection refused".into()),
        ] {
            let (mut v, mut r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
            let sink = TransportErrSink(err_fn);
            deliver(&mut v, &mut r, &sink).unwrap();
            assert_eq!(v.outcome, Outcome::Hold);
            assert_eq!(r.outcome, Outcome::Hold);
            assert_eq!(v.record_sha256, sha256_hex(&record_bytes(&r).unwrap()));
        }
    }

    #[test]
    fn post_failure_preserves_hold_and_block() {
        for initial in [Outcome::Hold, Outcome::Block] {
            let (mut v, mut r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
            v.outcome = initial;
            r.outcome = initial;
            v.record_sha256 = sha256_hex(&record_bytes(&r).unwrap());
            let expected_sha = v.record_sha256.clone();
            let sink = FakeSink::err_status(503);
            deliver(&mut v, &mut r, &sink).unwrap();
            assert_eq!(v.outcome, initial);
            assert_eq!(r.outcome, initial);
            assert_eq!(v.record_sha256, expected_sha);
        }
    }

    #[cfg(not(target_os = "wasi"))]
    #[test]
    fn http_sink_against_local_server() {
        use std::io::{Read, Write};
        use std::net::TcpListener;
        use std::thread;

        // 1. 200 OK -> preserves Allow and receives exact DecisionRecord JSON.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            // Read until headers and the full Content-Length body have arrived;
            // the client may send headers and body in separate writes.
            let mut data = Vec::new();
            let mut buf = [0u8; 4096];
            loop {
                let n = stream.read(&mut buf).unwrap();
                if n == 0 {
                    break;
                }
                data.extend_from_slice(&buf[..n]);
                if let Some(end) = data.windows(4).position(|w| w == b"\r\n\r\n") {
                    let head = String::from_utf8_lossy(&data[..end]).to_ascii_lowercase();
                    let len = head
                        .lines()
                        .find_map(|l| l.strip_prefix("content-length:"))
                        .and_then(|v| v.trim().parse::<usize>().ok())
                        .unwrap_or(0);
                    if data.len() >= end + 4 + len {
                        break;
                    }
                }
            }
            let req = String::from_utf8_lossy(&data).into_owned();
            stream
                .write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
                .unwrap();
            req
        });
        let (mut v, mut r) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let cfg = SinkConfig { url: Some(format!("http://{addr}/decisions")) };
        deliver_with_config(&mut v, &mut r, &cfg).unwrap();
        let raw_req = handle.join().unwrap();
        let body = raw_req.split("\r\n\r\n").nth(1).unwrap_or("");
        assert_eq!(v.outcome, Outcome::Allow);
        assert_eq!(sha256_hex(body.as_bytes()), v.record_sha256);

        // 2. 500 error -> downgrades Allow to Hold.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut buf = [0u8; 4096];
            let _ = stream.read(&mut buf);
            stream
                .write_all(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 4\r\nConnection: close\r\n\r\nfail")
                .unwrap();
        });
        let (mut v2, mut r2) = decide_with(INPUT.as_bytes(), &PolicyConfig::default()).unwrap();
        let cfg2 = SinkConfig { url: Some(format!("http://{addr}/decisions")) };
        deliver_with_config(&mut v2, &mut r2, &cfg2).unwrap();
        handle.join().unwrap();
        assert_eq!(v2.outcome, Outcome::Hold);
        assert_eq!(r2.outcome, Outcome::Hold);
        assert_eq!(v2.record_sha256, sha256_hex(&record_bytes(&r2).unwrap()));
    }
}
