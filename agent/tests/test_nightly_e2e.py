"""Unit tests for firewall-nightly-e2e runner (Sprint 1 task B2)."""

import dataclasses
import json
from unittest.mock import MagicMock, patch

import pytest

from firewall_agent import nightly_e2e
from firewall_agent.config import Settings
from firewall_agent.guardian import ContractRefusal, Decision
from firewall_agent.nightly_e2e import (
    DEFAULT_ATTACK_SCENARIO,
    DEFAULT_BENIGN_SCENARIO,
    NightlyReport,
    StepResult,
    main,
    preflight_check,
    run_nightly_e2e,
    run_scenario_step,
)


@pytest.fixture
def base_settings():
    return Settings(
        ns="demo.testnet",
        checker_bin=Settings.load().checker_bin,
        checker_record_dir=Settings.load().checker_record_dir,
        near_ai_api_key="",
        near_ai_base_url="https://cloud-api.near.ai/v1",
        agent_model="",
        typesafe_api_key="",
        near_network="testnet",
        near_rpc_url="",
        owner_account_id="",
        owner_private_key="",
        guardian_id="guardian-v2.jimuelle-firewall.testnet",
        token_id="tusdc.demo.testnet",
        agent_account_id="agent-v2.jimuelle-firewall.testnet",
        agent_private_key="ed25519:testkey",
        checker_account_id="",
        checker_private_key="",
    )


class MockGuardian:
    def __init__(self, outcome="allow", status="paid", reasons=None, should_panic=False):
        self.outcome = outcome
        self.status = status
        self.reasons = reasons or ["stub_allow"]
        self.should_panic = should_panic
        self.calls = []

    def request_payment(self, req):
        self.calls.append(req)
        if self.should_panic:
            raise ContractRefusal("Daily cap reached")
        return Decision(
            outcome=self.outcome,
            reasons=list(self.reasons),
            record_sha256="aa" * 32,
            status=self.status,
            detail="request_id=1",
        )


def test_preflight_check_testnet_missing_keys(base_settings):
    bad = dataclasses.replace(
        base_settings,
        guardian_id="",
        agent_account_id="",
        agent_private_key="",
    )
    errors = preflight_check(bad, mode="testnet")
    assert len(errors) == 3
    assert any("GUARDIAN_ID" in e for e in errors)
    assert any("AGENT_ACCOUNT_ID" in e for e in errors)
    assert any("AGENT_PRIVATE_KEY" in e for e in errors)


def test_preflight_check_testnet_complete(base_settings):
    errors = preflight_check(base_settings, mode="testnet")
    assert errors == []


def test_preflight_check_dry_run_ignores_keys(base_settings):
    bad = dataclasses.replace(
        base_settings,
        guardian_id="",
        agent_account_id="",
        agent_private_key="",
    )
    assert preflight_check(bad, mode="dry-run") == []


def test_run_scenario_step_benign_success(base_settings):
    mock_g = MockGuardian(outcome="allow", status="paid", reasons=["stub_allow"])
    res = run_scenario_step(
        DEFAULT_BENIGN_SCENARIO,
        step_title="benign_test",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert res.passed
    assert res.outcome == "allow"
    assert res.status == "paid"
    assert res.scenario == DEFAULT_BENIGN_SCENARIO
    assert len(mock_g.calls) == 1


def test_run_scenario_step_attack_stub_allow(base_settings):
    mock_g = MockGuardian(outcome="allow", status="paid", reasons=["stub_allow"])
    res = run_scenario_step(
        DEFAULT_ATTACK_SCENARIO,
        step_title="attack_test",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert res.passed
    assert res.outcome == "allow"
    assert res.status == "paid"
    assert res.scenario == DEFAULT_ATTACK_SCENARIO


def test_run_scenario_step_attack_blocked(base_settings):
    mock_g = MockGuardian(outcome="block", status="refused", reasons=["policy_violation"])
    res = run_scenario_step(
        DEFAULT_ATTACK_SCENARIO,
        step_title="attack_test",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert res.passed
    assert res.outcome == "block"
    assert res.status == "refused"


def test_run_scenario_step_contract_refusal(base_settings):
    mock_g = MockGuardian(should_panic=True)
    # Benign panicked -> fail
    res_b = run_scenario_step(
        DEFAULT_BENIGN_SCENARIO,
        step_title="benign_panic",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert not res_b.passed
    assert res_b.error == "Daily cap reached"

    # Attack panicked -> safe refusal counts as passed
    res_a = run_scenario_step(
        DEFAULT_ATTACK_SCENARIO,
        step_title="attack_panic",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert res_a.passed
    assert res_a.status == "refused_by_contract"


def test_run_nightly_e2e_full_pass(base_settings):
    mock_g = MockGuardian(outcome="allow", status="paid")
    report = run_nightly_e2e(
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
        interactive=False,
    )
    assert report.all_passed
    assert report.benign is not None and report.benign.passed
    assert report.attack is not None and report.attack.passed
    assert report.guardian_id == base_settings.guardian_id
    assert report.duration_total_s >= 0.0


def test_run_nightly_e2e_interactive_abort(base_settings, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    report = run_nightly_e2e(
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: MockGuardian(),
        interactive=True,
    )
    assert not report.all_passed
    assert report.benign is None


def test_run_nightly_e2e_interactive_confirm(base_settings, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    mock_g = MockGuardian(outcome="allow", status="paid")
    report = run_nightly_e2e(
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
        interactive=True,
    )
    assert report.all_passed
    assert report.benign is not None and report.benign.passed


def test_main_cli_dry_run(monkeypatch):
    mock_g = MockGuardian(outcome="allow", status="would_pay")
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y"])
    assert code == 0


def test_main_cli_json_output(monkeypatch, capsys):
    mock_g = MockGuardian(outcome="allow", status="would_pay")
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y", "--json"])
    assert code == 0
    captured = capsys.readouterr().out
    assert '"all_passed": true' in captured
    assert '"benign":' in captured
    assert '"attack":' in captured


def test_main_cli_failure_exit_code(monkeypatch):
    mock_g = MockGuardian(outcome="block", status="refused")
    # Benign blocked is a failure
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y"])
    assert code == 1
