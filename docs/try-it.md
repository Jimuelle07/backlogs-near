# Try it

Moved from the README on 2026-11-13. Short form: [README Quick start](../README.md#quick-start). Steps 7–12 (evaluation, calibration, classifier, external set, benchmarks, dataset export) and configuration switches: [reference.md](reference.md#evaluation-and-benchmarks).

## Quick start (no keys)

Three commands, no keys and no funds:

```
cargo build -p checker --release
cd agent && uv sync
uv run firewall-demo --scenario benign-hosting --reset-spend
```

Expected: `verdict: hold reasons=check_unavailable…` and `action: held`. With no Jev key the checker fails closed and never allows a payment. With a Jev key the same command allows the payment; see step 4.

Numbered steps, each “do X → see Y”, run from the repo root unless a step says otherwise; steps 1–3 and 5 need no key, steps 4 and 6 need a TypeSafe Jev key.

## Offline, no keys

1. `cargo build -p checker --release` → `target/release/checker` (`.exe` on Windows) exists.
2. `cd agent && uv sync` → the Python environment is ready. Optional: `uv run pytest` runs the Python tests.
3. Offline dry-run, no keys. In `agent/`, run `uv run firewall-demo --scenario benign-hosting --reset-spend` → the lines below (`--reset-spend` clears the local dry-run daily spend, which is kept across runs like the contract):
   ```
   scenario: benign-hosting (benign)
   proposed: pay 18000000 units (18 tUSDC) to hostco.demo.testnet memo="INV-2026-11"
   verdict: hold reasons=check_unavailable… record=<64 hex>
   action: held
   held until <UTC time>
   record_file: data/decisions/dry-run/<request id>.json
   ```
   This is the fail-closed design, not a bug: with no `TYPESAFE_API_KEY` Jev cannot be called, and the checker never allows a payment without a Jev verdict. It returns `hold` with reason `check_unavailable` (more reasons may follow it) and the payment is not paid. The dry-run never waits for or releases the hold. The demo substitutes `OWNER_ACCOUNT_ID` (from `.env`) for the scenario namespace when it is set, otherwise `demo.testnet`, so `hostco.demo.testnet` above becomes `hostco.<OWNER_ACCOUNT_ID>`.

## With a Jev key

4. Dry-run with Jev. Put your key in `.env` at the repo root (`cp .env.example .env`, then set `TYPESAFE_API_KEY=`). Optional: `cd agent && uv run firewall-jev-ping` checks the key. Then in `agent/`:
   - `uv run firewall-demo --scenario benign-hosting --reset-spend` → `verdict: allow …` and `action: would_pay`.
   - `uv run firewall-demo --scenario attack-morse-lookalike --reset-spend` → `verdict: hold …` (`action: held`) or `verdict: block …` (`action: refused`); the receiver `hostc0.demo.testnet` is a lookalike of `hostco.demo.testnet`.
5. Open the file named on the `record_file:` line (e.g. `data/decisions/dry-run/2.json`) → the full decision record; `sha256sum <that file>` equals the `record=` value. The path is relative to the repository root, even though the command ran in `agent/`. Each dry-run gets the next request id, so earlier records are kept; the checker refuses to overwrite a record with different content.
6. Nightly end-to-end check, offline. In `agent/`, run `uv run firewall-nightly-e2e --mode dry-run -y` → one benign and one attack payment, then `Overall Status: SUCCESS` and exit code 0. It needs the Jev key from step 4. Without a key it prints `[FAIL] benign-hosting (benign)` with `Verdict: outcome=hold reasons=check_unavailable`, the attack payment still `[PASS]`, then `Overall Status: FAILURE` and exit code 1. Its scenario namespace follows `OWNER_ACCOUNT_ID` as in step 3. Details: [docs/build/nightly-e2e.md](build/nightly-e2e.md).
