//! The only module that opens sockets: a blocking JSON POST with an optional bearer token.
//! Native builds use `ureq`; `wasm32-wasip2` uses `wasi-http-client`.
use std::fmt;
use std::time::Duration;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HttpResponse {
    pub status: u16,
    pub body: String,
}

#[derive(Debug)]
pub enum HttpError {
    Timeout,
    Transport(String),
}

impl fmt::Display for HttpError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            HttpError::Timeout => write!(f, "http timeout"),
            HttpError::Transport(e) => write!(f, "http transport error: {e}"),
        }
    }
}

impl std::error::Error for HttpError {}

/// POST `body` as JSON with `Authorization: Bearer {bearer}` (omitted when `bearer` is empty).
/// HTTP redirects are disabled (`max_redirects(0)`). Non-2xx statuses (including 3xx) are returned
/// as `Ok`; only transport failures and timeouts are errors.
///
/// Native: `timeout` bounds the whole request. WASI: only a connect timeout exists;
/// OutLayer's execution cap bounds the rest.
#[cfg(not(target_os = "wasi"))]
pub fn post_json(url: &str, bearer: &str, body: &str, timeout: Duration) -> Result<HttpResponse, HttpError> {
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(timeout))
        .max_redirects(0)
        .max_redirects_will_error(false)
        .http_status_as_error(false)
        .build()
        .into();
    let map_err = |e: ureq::Error| match e {
        ureq::Error::Timeout(_) => HttpError::Timeout,
        other => HttpError::Transport(other.to_string()),
    };
    let req = agent.post(url).header("Content-Type", "application/json");
    let req = if bearer.is_empty() {
        req
    } else {
        req.header("Authorization", format!("Bearer {bearer}"))
    };
    let mut resp = req.send(body).map_err(map_err)?;
    let status = resp.status().as_u16();
    let body = resp.body_mut().read_to_string().map_err(map_err)?;
    Ok(HttpResponse { status, body })
}

/// See the native variant. WASI has only a connect timeout; OutLayer's 60 s
/// execution cap bounds the rest of the request.
#[cfg(target_os = "wasi")]
pub fn post_json(url: &str, bearer: &str, body: &str, timeout: Duration) -> Result<HttpResponse, HttpError> {
    let req = wasi_http_client::Client::new()
        .post(url)
        .header("Content-Type", "application/json")
        .connect_timeout(timeout);
    let req = if bearer.is_empty() {
        req
    } else {
        req.header("Authorization", format!("Bearer {bearer}"))
    };
    let resp = req
        .body(body.as_bytes())
        .send()
        .map_err(|e| HttpError::Transport(e.to_string()))?;
    let status = resp.status();
    let bytes = resp.body().map_err(|e| HttpError::Transport(e.to_string()))?;
    Ok(HttpResponse { status, body: String::from_utf8_lossy(&bytes).into_owned() })
}

#[cfg(all(test, not(target_os = "wasi")))]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::thread;

    fn read_full_http_request(stream: &mut std::net::TcpStream) {
        let mut data = Vec::new();
        let mut buf = [0u8; 4096];
        loop {
            let n = stream.read(&mut buf).unwrap_or(0);
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
    }

    #[test]
    fn post_json_does_not_follow_redirects() {
        let target_listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let target_addr = target_listener.local_addr().unwrap();
        let target_hit = Arc::new(AtomicBool::new(false));
        let target_hit_clone = Arc::clone(&target_hit);
        target_listener.set_nonblocking(true).unwrap();

        let redirect_listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let redirect_addr = redirect_listener.local_addr().unwrap();
        let handle = thread::spawn(move || {
            let (mut stream, _) = redirect_listener.accept().unwrap();
            read_full_http_request(&mut stream);
            let resp = format!(
                "HTTP/1.1 302 Found\r\nLocation: http://{target_addr}/evil\r\nContent-Length: 11\r\nConnection: close\r\n\r\nredirecting"
            );
            stream.write_all(resp.as_bytes()).unwrap();
        });

        let res = post_json(
            &format!("http://{redirect_addr}/start"),
            "secret-bearer",
            r#"{"hello":"world"}"#,
            Duration::from_secs(3),
        )
        .unwrap();
        handle.join().unwrap();
        if target_listener.accept().is_ok() {
            target_hit_clone.store(true, Ordering::SeqCst);
        }

        assert_eq!(res.status, 302);
        assert_eq!(res.body, "redirecting");
        assert!(!target_hit.load(Ordering::SeqCst), "redirect target must never be contacted");
    }
}
