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

from .config import DEFAULT_TESTNET_RPC, TOKEN_DECIMALS, Settings
from .formats import PaymentRequest, compact_json

VERDICT_FORMAT = "firewall.verdict.v1"
CHECKER_INPUT_FORMAT = "firewall.checker_input.v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_STATUS_BY_OUTCOME = {"allow": "would_pay", "hold": "held", "block": "refused"}
TGAS = 10**12


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
    """Dry-run guardian: same validation and CheckerInput as the contract, native checker."""

    def __init__(self, settings: Settings):
        self.s = settings

    @property
    def record_dir(self) -> Path:
        return self.s.checker_record_dir / "dry-run"

    def next_request_id(self) -> int:
        """Persisted counter: 1 + highest integer stem among existing records."""
        d = self.record_dir
        stems = [int(p.stem) for p in d.glob("*.json") if p.stem.isdigit()] if d.is_dir() else []
        return max(stems, default=0) + 1

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
        request_id = self.next_request_id()
        checker_input = self.build_checker_input(req, request_id)
        verdict = run_checker(
            self.s.checker_bin, compact_json(checker_input), self.record_dir
        )
        bad = binds(checker_input, verdict)
        if bad:
            raise ValueError(f"Verdict does not match request: {bad}")
        return Decision(
            outcome=verdict["outcome"],
            reasons=list(verdict["reasons"]),
            record_sha256=verdict["record_sha256"],
            status=_STATUS_BY_OUTCOME[verdict["outcome"]],
            record_path=self.record_dir / f"{request_id}.json",
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
            tx_hash = await acc.function_call(
                self.s.guardian_id, "request_payment", req.to_args(), gas=100 * TGAS, included=True
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
