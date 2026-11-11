"""Guardian clients: LocalGuardian (dry-run, mirrors the contract) and TestnetGuardian (py-near)."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import DEFAULT_TESTNET_RPC, TOKEN_DECIMALS, Settings
from .formats import PaymentRequest, compact_json

VERDICT_FORMAT = "firewall.verdict.v1"
CHECKER_INPUT_FORMAT = "firewall.checker_input.v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_STATUS_BY_OUTCOME = {"allow": "would_pay", "hold": "held", "block": "refused"}
TGAS = 10**12

# Hard limits: mirror contract/guardian/src/lib.rs (PER_PAYMENT_CAP_WHOLE, DAILY_CAP_WHOLE,
# NANOS_PER_DAY) and contract/guardian/src/validate.rs (hold_window_ns).
PER_PAYMENT_CAP_WHOLE = 200
DAILY_CAP_WHOLE = 500
NANOS_PER_DAY = 86_400_000_000_000


def hold_window_ns(amount: int, decimals: int) -> int:
    """Hold window by amount: <20 tokens 10 min, <=100 tokens 1 h, otherwise 6 h."""
    unit = 10**decimals
    if amount < 20 * unit:
        return 600_000_000_000
    if amount <= 100 * unit:
        return 3_600_000_000_000
    return 21_600_000_000_000


_PANIC_PREFIX = "Smart contract panicked: "


class ContractRefusal(Exception):
    """The Guardian contract rejected request_payment (panic); no receipt exists for it."""


def _failure_message(status: dict) -> str:
    """Message for a `{"Failure": ...}` status; never empty, never raises."""
    try:
        err = status["Failure"]["ActionError"]["kind"]["FunctionCallError"]["ExecutionError"]
        if isinstance(err, str) and err:
            return err.removeprefix(_PANIC_PREFIX)
    except (KeyError, TypeError):
        pass
    try:
        return f"transaction failed: {json.dumps(status['Failure'], separators=(',', ':'))}"
    except (KeyError, TypeError, ValueError):
        return "transaction failed (unrecognised failure status)"


def contract_failure(tx: dict) -> str | None:
    """Failure message of the request_payment receipt in a raw EXPERIMENTAL_tx_status result.

    None means success, not executed yet, or an unparseable response. The call's receipt is
    transaction_outcome.outcome.receipt_ids[0], matched in receipts_outcome by "id"; later receipts
    (ft_transfer, callbacks) and the transaction-level status do not decide refusal.
    """
    try:
        rid = tx["transaction_outcome"]["outcome"]["receipt_ids"][0]
        for ro in tx["receipts_outcome"]:
            if ro["id"] == rid:
                status = ro["outcome"]["status"]
                return _failure_message(status) if "Failure" in status else None
    except (KeyError, IndexError, TypeError):
        return None
    return None


@dataclass
class Decision:
    outcome: str | None
    reasons: list[str]
    record_sha256: str | None
    status: str
    detail: str = ""
    record_path: Path | None = None
    release_at_ns: int | None = None
    tx_hash: str | None = None
    balance_before: int | None = None
    balance_after: int | None = None


def binds(checker_input: dict, verdict: dict) -> str | None:
    """Mirror of the contract's validate::binds. Returns the first mismatched field, or None."""
    if verdict.get("format") != VERDICT_FORMAT:
        return "format"
    for f in ("request_id", "receiver_id", "token_id", "amount"):
        if verdict.get(f) != checker_input[f]:
            return f
    if verdict.get("outcome") not in _STATUS_BY_OUTCOME:
        return "outcome"
    reasons = verdict.get("reasons")
    if not isinstance(reasons, list) or not (1 <= len(reasons) <= 6):
        return "reasons"
    rec = verdict.get("record_sha256")
    if not isinstance(rec, str) or not _HEX64.fullmatch(rec):
        return "record_sha256"
    return None


def run_checker(checker_bin, input_bytes: bytes, record_dir) -> dict:
    """Run the native checker on exact stdin bytes; return the parsed verdict."""
    if not checker_bin.is_file():
        raise SystemExit(
            f"checker binary not found at {checker_bin}; run: cargo build -p checker --release"
        )
    env = dict(os.environ)
    env["CHECKER_RECORD_DIR"] = str(record_dir)
    proc = subprocess.run([str(checker_bin)], input=input_bytes, capture_output=True, env=env)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise SystemExit(f"checker exited {proc.returncode}: {err}")
    return json.loads(proc.stdout.decode("utf-8"))


class LocalGuardian:
    """Dry-run guardian: same validation, caps and CheckerInput as the contract, native checker.

    Mirrors the contract's hard limits: per-payment cap, daily cap (reserved at request time,
    released on `block`, kept for `allow`/`hold`) persisted in `<record_dir>/state.json`.
    A `hold` verdict yields status `held` with `release_at_ns`; dry-run never waits and never
    auto-releases or cancels the hold. State is single-process (no file lock).
    """

    def __init__(self, settings: Settings, now_ns: Callable[[], int] | None = None):
        self.s = settings
        self.now_ns = now_ns or (lambda: time.time_ns())

    @property
    def record_dir(self) -> Path:
        return self.s.checker_record_dir / "dry-run"

    @property
    def state_path(self) -> Path:
        return self.record_dir / "state.json"

    def next_request_id(self) -> int:
        """Persisted counter: 1 + highest integer stem among existing records."""
        d = self.record_dir
        stems = [int(p.stem) for p in d.glob("*.json") if p.stem.isdigit()] if d.is_dir() else []
        return max(stems, default=0) + 1

    def _load_state(self, today: int) -> dict:
        """Daily spend state, rolled forward to `today` (mirror of the contract's roll_day).

        Only a missing file is a fresh state; anything unreadable or malformed fails closed.
        A clock that moved back keeps the stored day and spend.
        """
        corrupt = ContractRefusal("dry-run state.json is corrupt; rerun with --reset-spend")
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"spend_day": today, "spent_today": 0}
        except (OSError, ValueError):
            raise corrupt from None
        if not isinstance(raw, dict):
            raise corrupt
        day, spent = raw.get("spend_day"), raw.get("spent_today")
        if type(day) is not int or type(spent) is not int or day < 0 or spent < 0:
            raise corrupt
        if today > day:
            return {"spend_day": today, "spent_today": 0}
        return {"spend_day": day, "spent_today": spent}

    def reset_spend(self) -> None:
        """Dry-run only: forget today's spend (demo convenience; the contract has no such call)."""
        self.state_path.unlink(missing_ok=True)

    def _save_state(self, state: dict) -> None:
        self.record_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name("state.json.tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def build_checker_input(self, req: PaymentRequest, request_id: int) -> dict:
        ns = self.s.ns
        return {
            "format": CHECKER_INPUT_FORMAT,
            "request_id": str(request_id),
            "guardian_id": f"guardian.{ns}",
            "agent_id": f"agent.{ns}",
            "token_id": f"tusdc.{ns}",
            "token_decimals": TOKEN_DECIMALS,
            "receiver_id": req.receiver_id,
            "amount": str(req.amount),
            "memo": req.memo,
            "user_request": req.user_request,
            "context": req.context_dicts(),
            "block_height": "0",
        }

    def request_payment(self, req: PaymentRequest) -> Decision:
        req.validate()
        now = self.now_ns()
        unit = 10**TOKEN_DECIMALS
        if req.amount > PER_PAYMENT_CAP_WHOLE * unit:
            raise ContractRefusal("Amount exceeds per-payment cap")
        state = self._load_state(now // NANOS_PER_DAY)
        if state["spent_today"] + req.amount > DAILY_CAP_WHOLE * unit:
            raise ContractRefusal("Daily cap reached")
        state["spent_today"] += req.amount
        self._save_state(state)

        try:
            request_id = self.next_request_id()
            checker_input = self.build_checker_input(req, request_id)
            verdict = run_checker(
                self.s.checker_bin, compact_json(checker_input), self.record_dir
            )
            bad = binds(checker_input, verdict)
            if bad:
                raise ValueError(f"Verdict does not match request: {bad}")
        except BaseException:
            state["spent_today"] -= req.amount
            self._save_state(state)
            raise
        release_at_ns = None
        if verdict["outcome"] == "block":
            state["spent_today"] -= req.amount
            self._save_state(state)
        elif verdict["outcome"] == "hold":
            release_at_ns = now + hold_window_ns(req.amount, TOKEN_DECIMALS)
        return Decision(
            outcome=verdict["outcome"],
            reasons=list(verdict["reasons"]),
            record_sha256=verdict["record_sha256"],
            status=_STATUS_BY_OUTCOME[verdict["outcome"]],
            record_path=self.record_dir / f"{request_id}.json",
            release_at_ns=release_at_ns,
        )


class TestnetGuardian:
    """Calls the deployed Guardian as the agent (function-call key). Signs testnet txs: human-gated."""

    __test__ = False  # not a pytest class

    POLL_SECONDS = 2
    TIMEOUT_SECONDS = 300
    TX_STATUS_TIMEOUT_SECONDS = 5

    def __init__(self, settings: Settings):
        self.s = settings
        for name in ("guardian_id", "agent_account_id", "agent_private_key"):
            if not getattr(self.s, name):
                raise SystemExit(f"{name.upper()} not set (run firewall-setup-testnet first)")

    def request_payment(self, req: PaymentRequest) -> Decision:
        req.validate()
        return asyncio.run(self._run(req))

    async def _tx_refusal(self, acc, tx_hash: str) -> str | None:
        """Failure message of the request_payment receipt, or None (success, not executed yet, or query failed).

        Never blocks long: EXPERIMENTAL_tx_status waits for all receipts, and the yield's receipts only
        finish after the verdict, so each query is time-boxed and errors are retried by the caller.
        """
        try:
            tx = await asyncio.wait_for(
                acc._provider.json_rpc(
                    "EXPERIMENTAL_tx_status",
                    {
                        "tx_hash": tx_hash,
                        "sender_account_id": self.s.agent_account_id,
                        "wait_until": "INCLUDED_FINAL",
                    },
                ),
                self.TX_STATUS_TIMEOUT_SECONDS,
            )
        except Exception:
            return None
        return contract_failure(tx)

    async def _run(self, req: PaymentRequest) -> Decision:
        try:
            from py_near.account import Account
        except ImportError:
            raise SystemExit("py-near not installed; run: uv sync --extra testnet")
        rpc = self.s.near_rpc_url or DEFAULT_TESTNET_RPC
        acc = Account(self.s.agent_account_id, self.s.agent_private_key, rpc_addr=rpc)
        await acc.startup()
        try:
            # included=True returns the hash once the tx is included; it never reports a contract panic.
            # OutLayer checker mode needs ~160 TGas (request_execution 100 + callback 40); relayer mode is unaffected.
            tx_hash = await acc.function_call(
                self.s.guardian_id, "request_payment", req.to_args(), gas=200 * TGAS, included=True
            )
            accepted = False
            deadline = time.monotonic() + self.TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                res = await acc.view_function(
                    self.s.guardian_id, "get_receipt_by_ref", {"client_ref": req.client_ref}
                )
                receipt = res.result
                if receipt:
                    accepted = True
                    if receipt.get("status") != "paying":
                        return self._decision(req, receipt)
                if not accepted:
                    pend = await acc.view_function(
                        self.s.guardian_id, "get_pending", {"from_index": 0, "limit": 50}
                    )
                    accepted = any(p.get("client_ref") == req.client_ref for p in pend.result or [])
                if not accepted:
                    failure = await self._tx_refusal(acc, tx_hash)
                    if failure is not None:
                        raise ContractRefusal(failure)
                await asyncio.sleep(self.POLL_SECONDS)
            what = "no verdict yet" if accepted else "request was never accepted by the contract"
            print(
                f"timed out after {self.TIMEOUT_SECONDS}s waiting for {req.client_ref}: {what} (tx {tx_hash})",
                file=sys.stderr,
            )
            raise SystemExit(1)
        finally:
            await acc.shutdown()

    @staticmethod
    def _decision(req: PaymentRequest, receipt: dict) -> Decision:
        if receipt.get("receiver_id") != req.receiver_id or str(receipt.get("amount")) != str(req.amount):
            print(
                f"receipt for {req.client_ref} does not match the request: "
                f"receiver_id={receipt.get('receiver_id')} amount={receipt.get('amount')}, "
                f"expected {req.receiver_id} / {req.amount}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return Decision(
            outcome=receipt.get("outcome"),
            reasons=list(receipt.get("reasons") or []),
            record_sha256=receipt.get("record_sha256"),
            status=receipt["status"],
            detail=f"request_id={receipt.get('request_id')}",
        )


STORAGE_DEPOSIT_YOCTO = 10**24 * 125 // 100_000  # 0.00125 NEAR (NEP-145 minimum)


def _extract_tx_hash(tx_res) -> str:
    """Best-effort transaction hash extraction across py-near return shapes."""
    if isinstance(tx_res, str):
        return tx_res
    tx = getattr(tx_res, "transaction", None)
    if tx is not None and getattr(tx, "hash", None):
        return str(tx.hash)
    if isinstance(tx_res, dict):
        return str(tx_res.get("transaction", {}).get("hash") or tx_res.get("tx_hash") or "")
    return str(tx_res or "")


class UnprotectedLocalAgent:
    """Dry-run plain agent for demo step 3 (A5): no Guardian, no checker, no caps or escrow."""

    def __init__(self, settings: Settings | None = None):
        self.s = settings

    def reset_spend(self) -> None:
        """No-op in unprotected mode (no daily cap state exists)."""

    def request_payment(self, req: PaymentRequest) -> Decision:
        req.validate()
        return Decision(
            outcome=None,
            reasons=["unprotected_no_guardian"],
            record_sha256=None,
            status="would_pay_unprotected",
            detail="plain agent with full-access key (no Guardian)",
        )


class UnprotectedTestnetAgent:
    """Testnet plain agent for demo step 3 (A5): holds a full-access key and calls NEP-141
    `ft_transfer` directly on `TOKEN_ID` without the Guardian. Human-gated (signs testnet txs).
    """

    __test__ = False  # not a pytest class

    def __init__(self, settings: Settings):
        self.s = settings
        self.payer_id = settings.unprotected_agent_account_id or settings.owner_account_id
        self.payer_key = settings.unprotected_agent_private_key or settings.owner_private_key
        if not self.s.token_id:
            raise SystemExit("TOKEN_ID not set (run firewall-setup-testnet first)")
        if not (self.payer_id and self.payer_key):
            raise SystemExit(
                "UNPROTECTED_AGENT_ACCOUNT_ID/UNPROTECTED_AGENT_PRIVATE_KEY "
                "(or OWNER_ACCOUNT_ID/OWNER_PRIVATE_KEY) not set (run firewall-setup-testnet first)"
            )

    def request_payment(self, req: PaymentRequest) -> Decision:
        req.validate()
        return asyncio.run(self._run(req))

    async def _run(self, req: PaymentRequest) -> Decision:
        try:
            from py_near.account import Account
        except ImportError:
            raise SystemExit("py-near not installed; run: uv sync --extra testnet")
        rpc = self.s.near_rpc_url or DEFAULT_TESTNET_RPC
        acc = Account(self.payer_id, self.payer_key, rpc_addr=rpc)
        await acc.startup()
        try:
            bal_before_res = await acc.view_function(
                self.s.token_id, "ft_balance_of", {"account_id": self.payer_id}
            )
            before = int(bal_before_res.result or 0)
            if before < req.amount:
                raise ContractRefusal(
                    f"Insufficient tUSDC balance on {self.payer_id}: have {before}, need {req.amount}"
                )

            sb = await acc.view_function(
                self.s.token_id, "storage_balance_of", {"account_id": req.receiver_id}
            )
            if not sb.result:
                await acc.function_call(
                    self.s.token_id,
                    "storage_deposit",
                    {"account_id": req.receiver_id, "registration_only": True},
                    gas=30 * TGAS,
                    amount=STORAGE_DEPOSIT_YOCTO,
                )

            tx_res = await acc.function_call(
                self.s.token_id,
                "ft_transfer",
                {
                    "receiver_id": req.receiver_id,
                    "amount": str(req.amount),
                    "memo": req.memo or None,
                },
                gas=30 * TGAS,
                amount=1,
            )
            status = getattr(tx_res, "status", None)
            if isinstance(status, dict) and "Failure" in status:
                raise ContractRefusal(_failure_message(status))
            tx_hash = _extract_tx_hash(tx_res)

            bal_after_res = await acc.view_function(
                self.s.token_id, "ft_balance_of", {"account_id": self.payer_id}
            )
            after = int(bal_after_res.result or 0)

            return Decision(
                outcome=None,
                reasons=["unprotected_no_guardian"],
                record_sha256=None,
                status="paid_unprotected",
                detail=f"tx={tx_hash}" if tx_hash else "paid directly without Guardian",
                tx_hash=tx_hash or None,
                balance_before=before,
                balance_after=after,
            )
        finally:
            await acc.shutdown()
