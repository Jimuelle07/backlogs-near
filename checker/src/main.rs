use checker::decide;

use std::io::{Read, Write};
use std::process::exit;

fn main() {
    #[cfg(not(target_os = "wasi"))]
    if std::env::args().nth(1).as_deref() == Some("--refuse") {
        refuse_stdin();
    }
    let mut input = Vec::new();
    if let Err(e) = std::io::stdin().read_to_end(&mut input) {
        eprintln!("checker error: cannot read stdin: {e}");
        exit(2);
    }
    let (verdict, record) = match decide::decide(&input) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("checker error: {e}");
            exit(2);
        }
    };
    let line = match serde_json::to_vec(&verdict) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("checker error: {e}");
            exit(2);
        }
    };
    if line.len() > 900 {
        eprintln!("verdict exceeds 900 bytes");
        exit(3);
    }
    #[cfg(not(target_os = "wasi"))]
    if let Ok(dir) = std::env::var("CHECKER_RECORD_DIR") {
        if !dir.is_empty() {
            let res = decide::record_bytes(&record).map_err(|e| e.to_string()).and_then(|bytes| {
                std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
                let path = std::path::Path::new(&dir).join(format!("{}.json", verdict.request_id));
                write_record_once(&path, &bytes)
            });
            if let Err(e) = res {
                eprintln!("checker error: cannot write record: {e}");
                exit(2);
            }
        }
    }
    #[cfg(target_os = "wasi")]
    let _ = &record;
    // OutLayer takes stdout as the whole Verdict and caps it at 900 bytes: no trailing newline there.
    #[cfg(not(target_os = "wasi"))]
    let line = {
        let mut l = line;
        l.push(b'\n');
        l
    };
    let mut out = std::io::stdout();
    if out.write_all(&line).and_then(|_| out.flush()).is_err() {
        exit(2);
    }
}

/// `checker --refuse`: re-fuse a DecisionRecord from stdin under the env configs and print
/// `{"outcome":...,"reasons":[...]}`. Never returns.
#[cfg(not(target_os = "wasi"))]
fn refuse_stdin() -> ! {
    let mut input = Vec::new();
    if let Err(e) = std::io::stdin().read_to_end(&mut input) {
        eprintln!("checker error: cannot read stdin: {e}");
        exit(2);
    }
    let (outcome, reasons) = match decide::refuse(&input) {
        Ok(x) => x,
        Err(e) => {
            eprintln!("checker error: {e}");
            exit(2);
        }
    };
    let line = match serde_json::to_string(&serde_json::json!({"outcome": outcome, "reasons": reasons})) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("checker error: {e}");
            exit(2);
        }
    };
    let mut out = std::io::stdout();
    if writeln!(out, "{line}").and_then(|_| out.flush()).is_err() {
        exit(2);
    }
    exit(0);
}

/// The record file is the owner's decision log: never replace an existing
/// record with different bytes. Re-running on identical input is a no-op.
#[cfg(not(target_os = "wasi"))]
fn write_record_once(path: &std::path::Path, bytes: &[u8]) -> Result<(), String> {
    use std::fs::OpenOptions;
    match OpenOptions::new().write(true).create_new(true).open(path) {
        Ok(mut f) => f.write_all(bytes).map_err(|e| e.to_string()),
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
            let existing = std::fs::read(path).map_err(|e| e.to_string())?;
            if existing == bytes {
                Ok(())
            } else {
                Err(format!("record {} exists with different content", path.display()))
            }
        }
        Err(e) => Err(e.to_string()),
    }
}
