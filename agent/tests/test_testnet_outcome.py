"""Testnet refusal handling and per-run client_ref. No network; py-near is stubbed."""

import asyncio
import dataclasses
import re
import sys
import types
from types import SimpleNamespace as NS

import pytest

from firewall_agent import demo
from firewall_agent.demo import make_client_ref
from firewall_agent.formats import PaymentRequest
from firewall_agent.guardian import ContractRefusal, TestnetGuardian, contract_failure
from firewall_agent.scenarios import list_scenarios

CLIENT_REF_RULE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # contract validate::valid_client_ref


def _panic(msg):
    return {
        "Failure": {
            "ActionError": {
                "index": 0,
                "kind": {"FunctionCallError": {"ExecutionError": f"Smart contract panicked: {msg}"}},
            }
        }
    }


def _tx(call_status, extra=(), rid="r1"):
    """Raw EXPERIMENTAL_tx_status result."""
    receipts = [{"id": rid, "outcome": {"status": call_status}}]
    receipts += [{"id": i, "outcome": {"status": s}} for i, s in extra]
    return {
        "status": {"Failure": "tx level, ignored"},
        "transaction_outcome": {"outcome": {"receipt_ids": [rid]}},
        "receipts_outcome": receipts,
    }


# --- pure parsing -----------------------------------------------------------


def test_success():
    assert contract_failure(_tx({"SuccessReceiptId": "abc"})) is None


def test_duplicate_client_ref():
    assert contract_failure(_tx(_panic("Duplicate client_ref"))) == "Duplicate client_ref"


def test_per_payment_cap():
    assert contract_failure(_tx(_panic("Amount exceeds per-payment cap"))) == "Amount exceeds per-payment cap"


def test_unexpected_failure_shape_is_generic_not_success():
    msg = contract_failure(_tx({"Failure": {"weird": 1}}))
    assert msg and "transaction failed" in msg


def test_receipt_not_yet_known():
    tx = {"transaction_outcome": {"outcome": {"receipt_ids": ["r1"]}}, "receipts_outcome": []}
    assert contract_failure(tx) is None


def test_garbage_response_is_not_a_failure():
    assert contract_failure({}) is None
    assert contract_failure(None) is None


def test_later_receipt_failure_and_tx_level_status_ignored():
    tx = _tx({"SuccessReceiptId": "r2"}, extra=[("r2", _panic("boom"))])
    assert contract_failure(tx) is None


# --- TestnetGuardian._run against a stub account ----------------------------

REQ = PaymentRequest(
    client_ref="ref-1", receiver_id="hostco.demo.testnet", amount=18_000_000, memo="m", user_request="u"
)


class FakeAccount:
    """views: dict method -> list of results popped in order (last one repeats)."""

    instances: list = []
    views: dict = {}
    tx_status = None  # callable -> dict, or exception instance to raise

    def __init__(self, *a, **kw):
        FakeAccount.instances.append(self)
        self.rpc_calls = 0
        self.closed = False
        self._provider = self

    async def startup(self):
        pass

    async def shutdown(self):
        self.closed = True

    async def function_call(self, *a, **kw):
        assert kw.get("included") is True
        return "HASH"

    async def view_function(self, contract, method, args):
        seq = FakeAccount.views[method]
        return NS(result=seq.pop(0) if len(seq) > 1 else seq[0])

    async def json_rpc(self, method, params):
        assert method == "EXPERIMENTAL_tx_status"
        assert params["tx_hash"] == "HASH" and params["wait_until"] == "INCLUDED_FINAL"
        self.rpc_calls += 1
        r = FakeAccount.tx_status
        if isinstance(r, BaseException):
            raise r
        if callable(r):
            return await r()
        return r


@pytest.fixture
def guardian(monkeypatch):
    mod = types.ModuleType("py_near.account")
    mod.Account = FakeAccount
    monkeypatch.setitem(sys.modules, "py_near", types.ModuleType("py_near"))
    monkeypatch.setitem(sys.modules, "py_near.account", mod)
    FakeAccount.instances = []
    FakeAccount.views = {"get_receipt_by_ref": [None], "get_pending": [[]]}
    FakeAccount.tx_status = None
    monkeypatch.setattr(TestnetGuardian, "POLL_SECONDS", 0.01)
    monkeypatch.setattr(TestnetGuardian, "TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(TestnetGuardian, "TX_STATUS_TIMEOUT_SECONDS", 0.05)
    s = dataclasses.replace(
        __import__("firewall_agent.config", fromlist=["Settings"]).Settings.load(),
        guardian_id="g.testnet",
        agent_account_id="a.testnet",
        agent_private_key="ed25519:x",
    )
    return TestnetGuardian(s)


def _run(g, req=REQ):
    return asyncio.run(g._run(req))


PAID = {
    "status": "paid",
    "outcome": "allow",
    "reasons": ["stub_allow"],
    "record_sha256": "ab" * 32,
    "request_id": "7",
    "receiver_id": REQ.receiver_id,
    "amount": str(REQ.amount),
}


def test_refusal_via_tx_status(guardian):
    FakeAccount.tx_status = _tx(_panic("Duplicate client_ref"))
    with pytest.raises(ContractRefusal, match="^Duplicate client_ref$"):
        _run(guardian)
    assert FakeAccount.instances[0].closed


def test_accepted_via_pending_then_paid(guardian):
    FakeAccount.views = {
        "get_receipt_by_ref": [None, None, PAID],
        "get_pending": [[{"client_ref": "ref-1"}]],
    }
    FakeAccount.tx_status = _tx(_panic("must not be consulted"))
    d = _run(guardian)
    assert d.status == "paid" and d.outcome == "allow" and d.reasons == ["stub_allow"]
    assert FakeAccount.instances[0].rpc_calls == 0


def test_tx_status_hangs_or_errors_while_accepted(guardian):
    async def hang():
        await asyncio.sleep(10)

    for failing in (hang, RuntimeError("rpc down")):
        FakeAccount.views = {"get_receipt_by_ref": [None, PAID], "get_pending": [[]]}
        FakeAccount.tx_status = failing
        # not yet accepted at first poll: tx_status fails/times out, loop retries, receipt shows up
        assert _run(guardian).status == "paid"


def test_receipt_mismatch_exits_1(guardian, capsys):
    FakeAccount.views = {"get_receipt_by_ref": [{**PAID, "amount": "1"}]}
    with pytest.raises(SystemExit) as e:
        _run(guardian)
    assert e.value.code == 1
    assert "does not match" in capsys.readouterr().err


def test_never_accepted_exits_1(guardian, capsys):
    FakeAccount.tx_status = _tx({"SuccessReceiptId": "r2"})
    with pytest.raises(SystemExit) as e:
        _run(guardian)
    assert e.value.code == 1
    assert "never accepted" in capsys.readouterr().err


def test_accepted_without_verdict_exits_1(guardian, capsys):
    FakeAccount.views = {"get_receipt_by_ref": [{**PAID, "status": "paying"}]}
    with pytest.raises(SystemExit) as e:
        _run(guardian)
    assert e.value.code == 1
    assert "no verdict" in capsys.readouterr().err


# --- demo -------------------------------------------------------------------


def test_demo_prints_refusal_and_returns_1(monkeypatch, capsys):
    class Refusing:
        def __init__(self, s):
            pass

        def request_payment(self, req):
            raise ContractRefusal("Duplicate client_ref")

    monkeypatch.setattr(demo, "TestnetGuardian", Refusing)
    assert demo.main(["--scenario", "benign-hosting", "--mode", "testnet"]) == 1
    assert "refused by contract: Duplicate client_ref" in capsys.readouterr().out


def test_testnet_client_refs_unique_and_valid():
    a = make_client_ref("benign-hosting", "testnet", now_ns=1_800_000_000_000_000_000)
    b = make_client_ref("benign-hosting", "testnet", now_ns=1_800_000_001_000_000_000)
    assert a != b
    assert make_client_ref("benign-hosting", "testnet") != make_client_ref("benign-hosting", "dry-run")
    for name in list_scenarios():
        assert CLIENT_REF_RULE.match(make_client_ref(name, "testnet")), name
    assert CLIENT_REF_RULE.match(make_client_ref("x" * 100, "testnet"))


def test_dry_run_client_ref_stable():
    assert make_client_ref("benign-hosting", "dry-run") == "benign-hosting-1"
