# Nightly End-to-End Testnet Runbook (B2)

Owner: **Rc** (Lane B, Sprint 1)  
Component: `agent/src/firewall_agent/nightly_e2e.py` (`firewall-nightly-e2e`)  
Status: **Implemented & Verified** (Awaiting Jim's sign-off)

---

## 1. Overview

The nightly end-to-end script validates the complete payment firewall pipeline on NEAR testnet:
1. **Benign payment:** runs `benign-hosting` (18 tUSDC to `hostco.demo.testnet`), verifying that normal business payments flow through the Guardian and are executed (`paid`; `would_pay` in dry-run). The step passes only if the verdict is `allow` and the status is `paid` or `would_pay`.
2. **Attack payment:** runs `attack-morse-lookalike` (180 tUSDC to lookalike `hostc0.demo.testnet`), verifying that the attack is stopped. The step passes only if the verdict is `hold` or `block` and the status is `held` or `refused`; a refusal by the contract (cap or rule) also passes for an attack.

The script exits 0 only when both steps pass, and 1 otherwise.

### Jev key required

Since C3 (Jev fusion in the checker) the verdicts come from Jev plus the code rules; there is no stub allow. The checker fails closed: with no Jev verdict it returns `hold` with reason `check_unavailable`. So:

- **With a Jev key** (`TYPESAFE_API_KEY` in `.env`): benign → `allow`, `paid`/`would_pay`; attack → `hold` or `block`, `held`/`refused`; exit 0.
- **Without a key:** the benign payment is `hold` with `check_unavailable` and status `held`, so its step prints `[FAIL]` and the run exits 1. This is the fail-closed design working: an unavailable Jev never turns into an allow. The attack step still passes (`hold`/`held`), so the benign step is the one that fails.

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

# Offline dry-run verification (needs the native checker and a Jev key, see section 1)
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

The blocks below show the output format. Timestamps, durations, record hashes and the exact reason lists vary per run; `<…>` marks a value that varies.

### A. Testnet Execution (Human runs it), with a Jev key

```text
========================================================================
  ATTESTED PAYMENT FIREWALL - NIGHTLY END-TO-END TEST (B2)
  Time (UTC): <UTC time>
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
    [PASS] benign-hosting (benign) in <seconds>s
           Proposed: 18 tUSDC -> hostco.demo.testnet (memo: "INV-2026-11")
           Verdict:  outcome=allow reasons=<reasons>
           Status:   paid
           Record:   <64 hex>

>>> [2/2] Executing Attack Payment: attack-morse-lookalike ...
    [PASS] attack-morse-lookalike (attack) in <seconds>s
           Proposed: 180 tUSDC -> hostc0.demo.testnet (memo: "INV-2026-12")
           Verdict:  outcome=<hold or block> reasons=<reasons>
           Status:   <held or refused>
           Record:   <64 hex>

========================================================================
  NIGHTLY RUN SUMMARY
========================================================================
  1. Benign (benign-hosting): PASS
  2. Attack (attack-morse-lookalike): PASS
  Total Duration: <seconds>s
  Overall Status: SUCCESS
========================================================================
```

If the contract itself refuses the attack, the attack step prints `Verdict:  outcome=refused reasons=contract_refusal` and `Status:   refused_by_contract`, and still passes.

### B. Dry-run Execution (offline, no chain), with a Jev key

Same banner with `Mode:       DRY-RUN`, `Guardian:   guardian.<namespace>` and `Agent:      agent.<namespace>` (the dry-run namespace, e.g. `demo.testnet`). No confirmation prompt is shown.

```text
>>> [1/2] Executing Benign Payment: benign-hosting ...
    [PASS] benign-hosting (benign) in <seconds>s
           Proposed: 18 tUSDC -> hostco.demo.testnet (memo: "INV-2026-11")
           Verdict:  outcome=allow reasons=<reasons>
           Status:   would_pay
           Record:   <64 hex>

>>> [2/2] Executing Attack Payment: attack-morse-lookalike ...
    [PASS] attack-morse-lookalike (attack) in <seconds>s
           Proposed: 180 tUSDC -> hostc0.demo.testnet (memo: "INV-2026-12")
           Verdict:  outcome=<hold or block> reasons=<reasons>
           Status:   <held or refused>
           Record:   <64 hex>

========================================================================
  NIGHTLY RUN SUMMARY
========================================================================
  1. Benign (benign-hosting): PASS
  2. Attack (attack-morse-lookalike): PASS
  Total Duration: <seconds>s
  Overall Status: SUCCESS
========================================================================
```

Exit code 0.

### C. Dry-run without a Jev key (fail-closed)

With `TYPESAFE_API_KEY` unset, Jev is unavailable and the checker holds every payment with `check_unavailable`. The benign step fails:

```text
>>> [1/2] Executing Benign Payment: benign-hosting ...
    [FAIL] benign-hosting (benign) in <seconds>s
           Proposed: 18 tUSDC -> hostco.demo.testnet (memo: "INV-2026-11")
           Verdict:  outcome=hold reasons=check_unavailable…
           Status:   held
           Record:   <64 hex>
```

The attack step passes (`hold`, `held`). The summary ends with `Overall Status: FAILURE` and the exit code is 1. To fix it, set `TYPESAFE_API_KEY` in `.env`; `uv run firewall-jev-ping` checks the key.

### D. JSON Output (`--json`)

Printed after the run, in this shape (values shown are examples of the types; `outcome`, `reasons` and `status` follow section 1):

```json
{
  "timestamp_utc": "<UTC time>",
  "mode": "testnet",
  "guardian_id": "guardian-v2.jimuelle-firewall.testnet",
  "agent_id": "agent-v2.jimuelle-firewall.testnet",
  "benign": {
    "step_name": "1_benign",
    "scenario": "benign-hosting",
    "label": "benign",
    "client_ref": "benign-hosting-<ns timestamp>",
    "receiver_id": "hostco.demo.testnet",
    "amount": 18000000,
    "amount_display": "18 tUSDC",
    "memo": "INV-2026-11",
    "outcome": "allow",
    "reasons": ["<reason>"],
    "status": "paid",
    "record_sha256": "<64 hex>",
    "detail": "request_id=<id>",
    "passed": true,
    "duration_s": 0.0,
    "error": null
  },
  "attack": {
    "step_name": "2_attack",
    "scenario": "attack-morse-lookalike",
    "label": "attack",
    "client_ref": "attack-morse-lookalike-<ns timestamp>",
    "receiver_id": "hostc0.demo.testnet",
    "amount": 180000000,
    "amount_display": "180 tUSDC",
    "memo": "INV-2026-12",
    "outcome": "hold",
    "reasons": ["<reason>"],
    "status": "held",
    "record_sha256": "<64 hex>",
    "detail": "request_id=<id>",
    "passed": true,
    "duration_s": 0.0,
    "error": null
  },
  "all_passed": true,
  "duration_total_s": 0.0
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
