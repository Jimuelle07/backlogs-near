"""Unit tests for Task A5: Unprotected-agent mode for demo step 3."""

from __future__ import annotations

import dataclasses
import sys
import types
from types import SimpleNamespace

import pytest

from firewall_agent import demo as demo_mod
from firewall_agent.agent import propose_payment
from firewall_agent.config import Settings
from firewall_agent.guardian import (
    STORAGE_DEPOSIT_YOCTO,
    TGAS,
    ContractRefusal,
    UnprotectedLocalAgent,
    UnprotectedTestnetAgent,
)
from firewall_agent.llm import ScriptedLLM
from firewall_agent.scenarios import load_scenario


@pytest.fixture
def base_settings(tmp_path):
    return Settings(
        ns="demo.testnet",
        checker_bin=tmp_path / "no-checker-needed",
        checker_record_dir=tmp_path / "decisions",
        near_ai_api_key="",
        near_ai_base_url="https://cloud-api.near.ai/v1",
        agent_model="",
        typesafe_api_key="",
        near_network="testnet",
        near_rpc_url="https://test.rpc.fastnear.com",
        owner_account_id="owner.demo.testnet",
        owner_private_key="ed25519:ownerkey",
        guardian_id="guardian-v2.demo.testnet",
        token_id="tusdc.demo.testnet",
        agent_account_id="agent-v2.demo.testnet",
        agent_private_key="ed25519:agentfckey",
        checker_account_id="checker.demo.testnet",
        checker_private_key="ed25519:checkerkey",
        unprotected_agent_account_id="unprotected.demo.testnet",
        unprotected_agent_private_key="ed25519:unprotectedfullkey",
    )


def _attack_request(ns: str = "demo.testnet"):
    scenario = load_scenario("attack-morse-lookalike", ns)
    req = propose_payment(scenario, ScriptedLLM(scenario), "attack-morse-lookalike-1")
    assert req is not None
    return req


def test_unprotected_local_agent_pays_attack_without_checker_or_caps(base_settings):
    req = _attack_request(base_settings.ns)
    # Even if amount exceeds the 200 tUSDC Guardian cap, a plain agent without Guardian has no cap.
    inflated = dataclasses.replace(req, amount=950_000_000)
    agent = UnprotectedLocalAgent(base_settings)
    d = agent.request_payment(inflated)
    assert d.outcome is None
    assert d.reasons == ["unprotected_no_guardian"]
    assert d.record_sha256 is None
    assert d.status == "would_pay_unprotected"


def test_unprotected_testnet_agent_requires_token_and_payer_keys(base_settings):
    no_token = dataclasses.replace(base_settings, token_id="")
    with pytest.raises(SystemExit, match="TOKEN_ID"):
        UnprotectedTestnetAgent(no_token)

    no_keys = dataclasses.replace(
        base_settings,
        unprotected_agent_account_id="",
        unprotected_agent_private_key="",
        owner_account_id="",
        owner_private_key="",
    )
    with pytest.raises(SystemExit, match="UNPROTECTED_AGENT_ACCOUNT_ID"):
        UnprotectedTestnetAgent(no_keys)


def test_unprotected_testnet_agent_falls_back_to_owner_account(base_settings):
    fallback = dataclasses.replace(
        base_settings,
        unprotected_agent_account_id="",
        unprotected_agent_private_key="",
    )
    agent = UnprotectedTestnetAgent(fallback)
    assert agent.payer_id == "owner.demo.testnet"
    assert agent.payer_key == "ed25519:ownerkey"


def _install_fake_py_near(monkeypatch, account_cls):
    py_near_mod = types.ModuleType("py_near")
    acc_mod = types.ModuleType("py_near.account")
    acc_mod.Account = account_cls
    py_near_mod.account = acc_mod
    monkeypatch.setitem(sys.modules, "py_near", py_near_mod)
    monkeypatch.setitem(sys.modules, "py_near.account", acc_mod)


def test_unprotected_testnet_agent_pays_attack_and_balance_drops(base_settings, monkeypatch):
    calls = []

    class FakeAccount:
        def __init__(self, account_id, private_key, rpc_addr=None):
            self.account_id = account_id
            self.private_key = private_key
            self.rpc_addr = rpc_addr
            self.balance = 500_000_000  # 500 tUSDC
            self.started = False
            self.closed = False

        async def startup(self):
            self.started = True

        async def shutdown(self):
            self.closed = True

        async def view_function(self, contract_id, method_name, args):
            calls.append(("view", contract_id, method_name, args))
            if method_name == "ft_balance_of":
                return SimpleNamespace(result=str(self.balance))
            if method_name == "storage_balance_of":
                return SimpleNamespace(result={"total": "1250000000000000000000"})
            raise AssertionError(f"unexpected view {method_name}")

        async def function_call(self, contract_id, method_name, args, gas=0, amount=0):
            calls.append(("call", contract_id, method_name, args, gas, amount))
            if method_name == "ft_transfer":
                self.balance -= int(args["amount"])
                return SimpleNamespace(
                    transaction=SimpleNamespace(hash="9xAttackTxHashTestnet111"),
                    status={"SuccessValue": ""},
                )
            raise AssertionError(f"unexpected call {method_name}")

    _install_fake_py_near(monkeypatch, FakeAccount)
    req = _attack_request(base_settings.ns)
    agent = UnprotectedTestnetAgent(base_settings)
    d = agent.request_payment(req)

    assert d.outcome is None
    assert d.reasons == ["unprotected_no_guardian"]
    assert d.record_sha256 is None
    assert d.status == "paid_unprotected"
    assert d.tx_hash == "9xAttackTxHashTestnet111"
    assert d.balance_before == 500_000_000
    assert d.balance_after == 320_000_000
    assert (
        "call",
        "tusdc.demo.testnet",
        "ft_transfer",
        {
            "receiver_id": "hostc0.demo.testnet",
            "amount": "180000000",
            "memo": "INV-2026-11",
        },
        30 * TGAS,
        1,
    ) in calls


def test_unprotected_testnet_agent_registers_unregistered_receiver(base_settings, monkeypatch):
    calls = []

    class FakeAccountUnregistered:
        def __init__(self, account_id, private_key, rpc_addr=None):
            self.balance = 200_000_000

        async def startup(self):
            pass

        async def shutdown(self):
            pass

        async def view_function(self, contract_id, method_name, args):
            if method_name == "ft_balance_of":
                return SimpleNamespace(result=str(self.balance))
            if method_name == "storage_balance_of":
                return SimpleNamespace(result=None)
            raise AssertionError(f"unexpected view {method_name}")

        async def function_call(self, contract_id, method_name, args, gas=0, amount=0):
            calls.append((method_name, args, gas, amount))
            if method_name == "ft_transfer":
                self.balance -= int(args["amount"])
            return "tx-unreg-123"

    _install_fake_py_near(monkeypatch, FakeAccountUnregistered)
    req = _attack_request(base_settings.ns)
    d = UnprotectedTestnetAgent(base_settings).request_payment(req)

    assert d.status == "paid_unprotected"
    assert d.balance_before == 200_000_000
    assert d.balance_after == 20_000_000
    assert calls[0] == (
        "storage_deposit",
        {"account_id": "hostc0.demo.testnet", "registration_only": True},
        30 * TGAS,
        STORAGE_DEPOSIT_YOCTO,
    )
    assert calls[1][0] == "ft_transfer"


def test_unprotected_testnet_agent_insufficient_balance_raises(base_settings, monkeypatch):
    class FakeAccountLowBalance:
        def __init__(self, account_id, private_key, rpc_addr=None):
            pass

        async def startup(self):
            pass

        async def shutdown(self):
            pass

        async def view_function(self, contract_id, method_name, args):
            return SimpleNamespace(result="10000000")  # only 10 tUSDC

    _install_fake_py_near(monkeypatch, FakeAccountLowBalance)
    req = _attack_request(base_settings.ns)
    with pytest.raises(ContractRefusal, match="Insufficient tUSDC balance"):
        UnprotectedTestnetAgent(base_settings).request_payment(req)


def test_demo_cli_unprotected_dry_run_and_testnet(base_settings, monkeypatch, capsys):
    monkeypatch.setattr(demo_mod.Settings, "load", classmethod(lambda cls: base_settings))

    # 1. Dry-run with --unprotected (does not need checker binary).
    rc = demo_mod.main(["--scenario", "attack-morse-lookalike", "--mode", "dry-run", "--unprotected"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scenario: attack-morse-lookalike (attack)" in out
    assert "proposed: pay 180000000 units (180 tUSDC) to hostc0.demo.testnet" in out
    assert "verdict: None reasons=unprotected_no_guardian record=None" in out
    assert "action: would_pay_unprotected" in out

    # 2. Testnet with --mode unprotected (and --mode testnet --unprotected).
    class FakeAccount:
        def __init__(self, account_id, private_key, rpc_addr=None):
            self.balance = 500_000_000

        async def startup(self):
            pass

        async def shutdown(self):
            pass

        async def view_function(self, contract_id, method_name, args):
            if method_name == "ft_balance_of":
                return SimpleNamespace(result=str(self.balance))
            return SimpleNamespace(result={"total": "1"})

        async def function_call(self, contract_id, method_name, args, gas=0, amount=0):
            if method_name == "ft_transfer":
                self.balance -= int(args["amount"])
            return "TxStep3AttackPaid"

    _install_fake_py_near(monkeypatch, FakeAccount)
    for cli_args in [
        ["--scenario", "attack-morse-lookalike", "--mode", "unprotected"],
        ["--scenario", "attack-morse-lookalike", "--mode", "testnet", "--unprotected"],
    ]:
        rc = demo_mod.main(cli_args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "action: paid_unprotected" in out
        assert "tx_hash: TxStep3AttackPaid" in out
        assert "balance: 500000000 -> 320000000 units (500 -> 320 tUSDC)" in out
