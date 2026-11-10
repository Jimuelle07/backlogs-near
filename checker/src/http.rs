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
/// Non-2xx statuses are returned as `Ok`; only transport failures and timeouts are errors.
///
/// Native: `timeout` bounds the whole request. WASI: only a connect timeout exists;
/// OutLayer's 60 s execution cap bounds the rest.
#[cfg(not(target_os = "wasi"))]
pub fn post_json(url: &str, bearer: &str, body: &str, timeout: Duration) -> Result<HttpResponse, HttpError> {
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(timeout))
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
