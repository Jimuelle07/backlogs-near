# Nightly End-to-End Testnet Runbook (B2)

Owner: **Rc** (Lane B, Sprint 1)  
Component: `agent/src/firewall_agent/nightly_e2e.py` (`firewall-nightly-e2e`)  
Status: **Implemented & Verified** (Awaiting Jim's sign-off)

---

## 1. Overview

The nightly end-to-end script validates the complete payment firewall pipeline on NEAR testnet:
1. **Benign payment:** runs `benign-hosting` (18 tUSDC to `hostco.demo.testnet`), verifying that normal business payments flow through the Guardian and are executed (`paid`).
2. **Attack payment:** runs `attack-morse-lookalike` (180 tUSDC to lookalike `hostc0.demo.testnet`), verifying that attack scenarios are processed through the Guardian without crashing or stalling. In Sprint 1 (under the OutLayer stub checker), the verdict is `allow` (`stub_allow`); starting in Sprint 2 (C3 fusion), this will transition to `block` or `hold`.

### Human-only policy compliance

In accordance with [AGENTS.md §4](../../AGENTS.md#4-human-only-actions), **agents do not sign testnet transactions or spend tokens autonomously**. The nightly script enforces an interactive human confirmation prompt before any transaction is submitted, showing target accounts, transaction details, and signer keys. For automated CI environments with dedicated testnet accounts, the `-y` / `--non-interactive` flag may be used.

---

## 2. Invocation

Run from the repo root or `agent/` directory:

```bash
# Recommended: via repository root helper script
./scripts/nightly-e2e.sh

# Or Windows PowerShell
powershell -File scripts\nightly-e2e.ps1

# Or via uv from agent/
cd agent && uv run firewall-nightly-e2e

# Offline dry-run verification
cd agent && uv run firewall-nightly-e2e --mode dry-run -y

# Emit machine-readable JSON summary
cd agent && uv run firewall-nightly-e2e --json
```

### CLI Options

| Flag | Choices / Default | Description |
| --- | --- | --- |
| `--mode` | `testnet` (default), `dry-run` | Target network environment |
| `--benign-scenario` | `benign-hosting` (default) | Scenario to execute for benign payment |
| `--attack-scenario` | `attack-morse-lookalike` (default) | Scenario to execute for attack payment |
| `--llm` | `scripted` (default), `near-ai` | LLM used for payment proposal extraction |
| `-y`, `--yes`, `--non-interactive` | Flag | Skip human confirmation prompt |
| `--json` | Flag | Output full JSON report at conclusion |

---

## 3. Expected Output

### A. Testnet Execution (Human runs it)

```text
========================================================================
  ATTESTED PAYMENT FIREWALL - NIGHTLY END-TO-END TEST (B2)
  Time (UTC): 2026-11-10T23:45:00Z
  Mode:       TESTNET
  Guardian:   guardian-v2.jimuelle-firewall.testnet
  Agent:      agent-v2.jimuelle-firewall.testnet
  Benign:     benign-hosting
  Attack:     attack-morse-lookalike
========================================================================

[HUMAN CONFIRMATION REQUIRED (AGENTS.md §4)]
  This script will submit 2 transactions to NEAR testnet:
    1. Benign payment: benign-hosting
    2. Attack payment: attack-morse-lookalike
  Signer account:   agent-v2.jimuelle-firewall.testnet
  Target contract:  guardian-v2.jimuelle-firewall.testnet

Proceed with testnet execution? [y/N]: y

>>> [1/2] Executing Benign Payment: benign-hosting ...
    [PASS] benign-hosting (benign) in 14.2s
           Proposed: 18 tUSDC -> hostco.demo.testnet (memo: "INV-2026-11")
           Verdict:  outcome=allow reasons=stub_allow
           Status:   paid
           Record:   7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069

>>> [2/2] Executing Attack Payment: attack-morse-lookalike ...
    [PASS] attack-morse-lookalike (attack) in 12.8s
           Proposed: 180 tUSDC -> hostc0.demo.testnet (memo: "INV-2026-12")
           Verdict:  outcome=allow reasons=stub_allow
           Status:   paid
           Record:   e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

========================================================================
  NIGHTLY RUN SUMMARY
========================================================================
  1. Benign (benign-hosting): PASS
  2. Attack (attack-morse-lookalike): PASS
  Total Duration: 27.0s
  Overall Status: SUCCESS
========================================================================
```

*(Note: In Sprint 1, OutLayer checker mode returns `stub_allow` on both payments as recorded in SDD §6. When C3 Jev fusion lands in Sprint 2, the attack payment outcome transitions to `block` / `refused` or `hold` / `held`).*

### B. Dry-run Execution (Offline verification)

```text
========================================================================
  ATTESTED PAYMENT FIREWALL - NIGHTLY END-TO-END TEST (B2)
  Time (UTC): 2026-11-10T23:50:00Z
  Mode:       DRY-RUN
  Guardian:   guardian.demo.testnet
  Agent:      agent.demo.testnet
  Benign:     benign-hosting
  Attack:     attack-morse-lookalike
========================================================================

>>> [1/2] Executing Benign Payment: benign-hosting ...
    [PASS] benign-hosting (benign) in 0.05s
           Proposed: 18 tUSDC -> hostco.demo.testnet (memo: "INV-2026-11")
           Verdict:  outcome=allow reasons=stub_allow
           Status:   would_pay
           Record:   3bfb7d8d0859422df595b8719cdbcaefc80882e367abefce8c6bc62ffb77714f

>>> [2/2] Executing Attack Payment: attack-morse-lookalike ...
    [PASS] attack-morse-lookalike (attack) in 0.04s
           Proposed: 180 tUSDC -> hostc0.demo.testnet (memo: "INV-2026-12")
           Verdict:  outcome=allow reasons=stub_allow
           Status:   would_pay
           Record:   d62d2958564db801b69f8c65f02bc0f71aa55490bf9e45be989ff1ea9bb7bc78

========================================================================
  NIGHTLY RUN SUMMARY
========================================================================
  1. Benign (benign-hosting): PASS
  2. Attack (attack-morse-lookalike): PASS
  Total Duration: 0.1s
  Overall Status: SUCCESS
========================================================================
```

### C. JSON Output (`--json`)

```json
{
  "timestamp_utc": "2026-11-10T23:50:00Z",
  "mode": "testnet",
  "guardian_id": "guardian-v2.jimuelle-firewall.testnet",
  "agent_id": "agent-v2.jimuelle-firewall.testnet",
  "benign": {
    "step_name": "1_benign",
    "scenario": "benign-hosting",
    "label": "benign",
    "client_ref": "benign-hosting-1762818600000000000",
    "receiver_id": "hostco.demo.testnet",
    "amount": 18000000,
    "amount_display": "18 tUSDC",
    "memo": "INV-2026-11",
    "outcome": "allow",
    "reasons": ["stub_allow"],
    "status": "paid",
    "record_sha256": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    "detail": "request_id=14923",
    "passed": true,
    "duration_s": 14.2,
    "error": null
  },
  "attack": {
    "step_name": "2_attack",
    "scenario": "attack-morse-lookalike",
    "label": "attack",
    "client_ref": "attack-morse-lookalike-1762818615000000000",
    "receiver_id": "hostc0.demo.testnet",
    "amount": 180000000,
    "amount_display": "180 tUSDC",
    "memo": "INV-2026-12",
    "outcome": "allow",
    "reasons": ["stub_allow"],
    "status": "paid",
    "record_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "detail": "request_id=14924",
    "passed": true,
    "duration_s": 12.8,
    "error": null
  },
  "all_passed": true,
  "duration_total_s": 27.0
}
```

---

## 4. Verification & Testing

Unit tests for the runner are located at `agent/tests/test_nightly_e2e.py` and cover:
- Preflight credential validation
- Scenario step execution with stub and contract refusal handling
- Interactive prompt confirmation vs abort
- CLI argument parsing and exit codes
- JSON output structure

Run the unit tests via:
```bash
cd agent && uv run pytest tests/test_nightly_e2e.py
```
