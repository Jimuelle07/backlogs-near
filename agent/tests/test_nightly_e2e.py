"""Unit tests for firewall-nightly-e2e runner (Sprint 1 task B2)."""

import dataclasses
import json
from unittest.mock import MagicMock, patch

import pytest

from firewall_agent import nightly_e2e
from firewall_agent.config import Settings
from firewall_agent.guardian import ContractRefusal, Decision, PollTimeout
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
        owner_account_id="jimuelle-firewall.testnet",
        owner_private_key="ed25519:ownerkey",
        guardian_id="guardian-v2.jimuelle-firewall.testnet",
        token_id="tusdc.demo.testnet",
        agent_account_id="agent-v2.jimuelle-firewall.testnet",
        agent_private_key="ed25519:testkey",
        checker_account_id="",
        checker_private_key="",
    )


ALLOW_THEN_BLOCK = [
    ("allow", "paid", ["checks_passed"]),
    ("block", "refused", ["injection_high", "lookalike_receiver"]),
]
DRY_ALLOW_THEN_BLOCK = [("allow", "would_pay", ["checks_passed"]), ALLOW_THEN_BLOCK[1]]


class MockGuardian:
    """Deterministic stand-in for TestnetGuardian/LocalGuardian: request_payment plus the view/owner helpers."""

    def __init__(
        self,
        outcome="allow",
        status="paid",
        reasons=None,
        should_panic=False,
        sequence=None,
        panic_message="Daily cap reached",
        raises=None,
        balance_skew=0,
        cancel_error=None,
        cancel_leaves_held=False,
        checker_mode="relayer",
        usage=None,
        guardian_balance=1_000_000_000,
        payee_budget=20_000_000,
        sent_then_timeout=None,
        ref_visible_at_end=None,
        reread_error=None,
        sent_then_raise=None,
        sent_status="held",
        hide_request_id=None,
    ):
        self.sent_then_raise: dict[int, BaseException] = sent_then_raise or {}
        self.sent_status = sent_status
        self.hide_request_id: set[int] = hide_request_id or set()
        self.outcome = outcome
        self.status = status
        self.reasons = reasons or ["checks_passed"]
        self.should_panic = should_panic
        self.panic_message = panic_message
        # sequence[i] = (outcome, status, reasons) returned by the i-th request_payment call
        self.sequence: list[tuple[str, str, list[str]]] | None = sequence
        self.raises: dict[int, BaseException] = raises or {}  # call index -> exception
        self.balance_skew = balance_skew
        self.cancel_error = cancel_error
        self.cancel_leaves_held = cancel_leaves_held
        self.checker_mode = checker_mode
        self.usage = usage
        self.guardian_balance = guardian_balance
        self.payee_budget = payee_budget
        self.calls = []
        self.cancelled: list[str] = []
        self.balances: dict[str, int] = {}
        self.held: list[dict] = []
        self.receipts: dict[str, dict] = {}
        self.last_tx_hash = None
        self.by_ref: dict[str, dict] = {}
        self.sent_then_timeout: set[int] = sent_then_timeout or set()
        self.ref_visible_at_end: set[int] = ref_visible_at_end or set()
        self.reread_error = reread_error

    def request_payment(self, req):
        self.calls.append(req)
        idx = len(self.calls) - 1
        if idx in self.sent_then_timeout:
            # The tx landed and the request is held on chain, but the poll never saw the receipt.
            rid = str(len(self.calls))
            receipt = {"request_id": rid, "status": self.sent_status, "client_ref": req.client_ref}
            self.receipts[rid] = receipt
            if self.sent_status == "held":
                self.held.append({"request_id": rid, "receiver_id": req.receiver_id, "amount": str(req.amount)})
            if idx in self.ref_visible_at_end:
                self.by_ref[req.client_ref] = receipt
            raise self.sent_then_raise.get(idx, PollTimeout(1))
        if idx in self.raises:
            raise self.raises[idx]
        if self.should_panic:
            raise ContractRefusal(self.panic_message)
        if self.sequence is not None:
            outcome, status, reasons = self.sequence[idx]
        else:
            outcome, status, reasons = self.outcome, self.status, self.reasons
        rid = str(len(self.calls))
        self.last_tx_hash = f"tx{rid}"
        if status == "paid":
            self.balances[req.receiver_id] = self.balances.get(req.receiver_id, 0) + req.amount + self.balance_skew
        if status == "held":
            self.held.append({"request_id": rid, "receiver_id": req.receiver_id, "amount": str(req.amount)})
        self.receipts[rid] = {"request_id": rid, "status": status}
        if idx in self.ref_visible_at_end:
            self.by_ref[req.client_ref] = self.receipts[rid]
        return Decision(
            outcome=outcome,
            reasons=list(reasons),
            record_sha256="aa" * 32,
            status=status,
            detail="" if idx in self.hide_request_id else f"request_id={rid}",
        )

    def cancel_held(self, request_id):
        if self.cancel_error:
            raise RuntimeError(self.cancel_error)
        self.cancelled.append(str(request_id))
        if not self.cancel_leaves_held:
            self.held = [h for h in self.held if h["request_id"] != str(request_id)]
        self.receipts[str(request_id)]["status"] = "refused"
        return f"canceltx{request_id}"

    def view(self, method, args=None, contract=None):
        args = args or {}
        if method == "get_checker_mode":
            return self.checker_mode
        if method == "get_outlayer_usage":
            return self.usage
        if method == "get_payee_budget":
            return str(self.payee_budget)
        if method == "ft_balance_of":
            if args["account_id"].startswith("guardian"):
                return str(self.guardian_balance)
            return str(self.balances.get(args["account_id"], 0))
        if method == "get_receipt":
            if self.cancelled and self.reread_error:
                raise RuntimeError(self.reread_error)
            return self.receipts.get(str(args["request_id"]))
        if method == "get_receipt_by_ref":
            return self.by_ref.get(args["client_ref"])
        if method == "get_held":
            return self.held[args["from_index"] : args["from_index"] + args["limit"]]
        raise AssertionError(f"unexpected view {method}")


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


def test_run_scenario_step_attack_allowed_fails(base_settings):
    mock_g = MockGuardian(outcome="allow", status="paid", reasons=["checks_passed"])
    res = run_scenario_step(
        DEFAULT_ATTACK_SCENARIO,
        step_title="attack_test",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert not res.passed
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
    assert res_b.message == "Daily cap reached"

    # Attack refused by the daily cap -> the checker never judged it: inconclusive, FAIL
    res_a = run_scenario_step(
        DEFAULT_ATTACK_SCENARIO,
        step_title="attack_panic",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert not res_a.passed
    assert res_a.status == "inconclusive"


def test_run_nightly_e2e_full_pass(base_settings):
    mock_g = MockGuardian(sequence=ALLOW_THEN_BLOCK)
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
    mock_g = MockGuardian(sequence=ALLOW_THEN_BLOCK)
    report = run_nightly_e2e(
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
        interactive=True,
    )
    assert report.all_passed
    assert report.benign is not None and report.benign.passed


def test_main_cli_dry_run(monkeypatch):
    mock_g = MockGuardian(sequence=DRY_ALLOW_THEN_BLOCK)
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y"])
    assert code == 0


def test_main_cli_json_output(monkeypatch, capsys):
    mock_g = MockGuardian(sequence=DRY_ALLOW_THEN_BLOCK)
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y", "--json"])
    assert code == 0
    captured = capsys.readouterr().out
    assert '"all_passed": true' in captured
    assert '"steps":' in captured
    assert '"label": "benign"' in captured
    assert '"label": "attack"' in captured


def test_main_cli_failure_exit_code(monkeypatch):
    mock_g = MockGuardian(outcome="block", status="refused")
    # Benign blocked is a failure
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y"])
    assert code == 1


# ---- multi-scenario runner, cancel, preflight, report ----

HELD_ATTACK = ("hold", "held", ["lookalike_receiver"])
BENIGN_PAID = ("allow", "paid", ["checks_passed"])


def _run(settings, mock, scenarios=None, **kw):
    return run_nightly_e2e(
        settings=settings,
        mode="testnet",
        guardian_factory=lambda _s: mock,
        interactive=False,
        scenarios=scenarios,
        **kw,
    )


def test_multi_scenario_order_and_labels(base_settings):
    mock_g = MockGuardian(
        sequence=[BENIGN_PAID, ("block", "refused", ["policy_violation"]), BENIGN_PAID]
    )
    report = _run(base_settings, mock_g, ["benign-hosting", "attack-morse-lookalike", "benign-cdn"])
    assert [s.scenario for s in report.steps] == ["benign-hosting", "attack-morse-lookalike", "benign-cdn"]
    assert [s.label for s in report.steps] == ["benign", "attack", "benign"]
    assert [r.receiver_id for r in mock_g.calls] == [s.receiver_id for s in report.steps]
    assert report.counts == {
        "benign": {"passed": 2, "failed": 0},
        "attack": {"passed": 1, "failed": 0},
    }
    assert report.all_passed


def test_cli_scenario_flag_repeat_and_comma(monkeypatch):
    mock_g = MockGuardian(
        sequence=[
            ("allow", "would_pay", ["checks_passed"]),
            ("block", "refused", ["policy_violation"]),
            ("allow", "would_pay", ["checks_passed"]),
        ]
    )
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y", "--scenario", "benign-hosting,attack-morse-lookalike", "--scenario", "benign-cdn"])
    assert code == 0
    assert len(mock_g.calls) == 3


def test_held_attack_is_cancelled_and_passes(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK])
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert atk.passed
    assert atk.status == "refused"
    assert atk.cancel_tx == "canceltx2"
    assert atk.note == "hold_cancelled"
    assert mock_g.cancelled == ["2"]
    assert report.leftover_held == []
    assert report.all_passed


def test_cancel_failure_fails_step_with_command(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], cancel_error="rpc down")
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert not atk.passed
    assert "near contract call-function as-transaction guardian-v2.jimuelle-firewall.testnet cancel_held" in atk.message
    assert '{"request_id":"2"}' in atk.message
    assert "sign-as jimuelle-firewall.testnet" in atk.message
    assert not report.all_passed
    assert [h["request_id"] for h in report.leftover_held] == ["2"]


def test_attack_without_owner_key_is_preflight_error(base_settings):
    no_owner = dataclasses.replace(base_settings, owner_private_key="")
    errors = preflight_check(no_owner, mode="testnet", has_attack=True)
    assert any("attack steps need OWNER_ACCOUNT_ID and OWNER_PRIVATE_KEY to cancel holds" in e for e in errors)
    assert preflight_check(no_owner, mode="testnet", has_attack=False) == []
    mock_g = MockGuardian()
    report = _run(no_owner, mock_g, None)
    assert not report.all_passed
    assert report.steps == []
    assert mock_g.calls == []


def test_benign_check_unavailable_fails(base_settings):
    mock_g = MockGuardian(sequence=[("hold", "held", ["check_unavailable"]), HELD_ATTACK])
    report = _run(base_settings, mock_g)
    b = report.benign
    assert not b.passed
    assert "checker did not get a Jev answer" in b.message
    assert mock_g.cancelled == ["2"]  # only the attack hold is cancelled, never the benign one
    assert not report.all_passed


def test_attack_check_unavailable_fails_but_is_cancelled(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, ("hold", "held", ["check_unavailable"])])
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert not atk.passed
    assert "checker did not get a Jev answer" in atk.message
    assert atk.cancel_tx == "canceltx2"
    assert report.leftover_held == []


def test_benign_payee_budget_escrow_passes_not_cancelled(base_settings):
    mock_g = MockGuardian(sequence=[("allow", "held", ["checks_passed"]), ("block", "refused", ["x"])])
    report = _run(base_settings, mock_g)
    b = report.benign
    assert b.passed
    assert b.note == "payee_budget_hold"
    assert b.status == "held"
    assert mock_g.cancelled == []
    assert report.all_passed


def test_benign_paid_balance_delta_recorded(base_settings):
    mock_g = MockGuardian(sequence=ALLOW_THEN_BLOCK)
    report = _run(base_settings, mock_g)
    assert report.benign.balance_delta == report.benign.amount == 18_000_000
    assert report.benign.tx_hash == "tx1"


def test_benign_paid_wrong_balance_delta_fails(base_settings):
    mock_g = MockGuardian(sequence=ALLOW_THEN_BLOCK, balance_skew=-1)
    report = _run(base_settings, mock_g)
    b = report.benign
    assert not b.passed
    assert b.balance_delta == 18_000_000 - 1
    assert "expected 18000000" in b.message
    assert not report.all_passed


def test_attack_per_payment_cap_refusal_passes(base_settings):
    mock_g = MockGuardian(should_panic=True, panic_message="Amount exceeds per-payment cap")
    res = run_scenario_step(
        "attack-direct-drain-cap",
        step_title="a",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert res.passed
    assert res.status == "refused_by_contract"


def test_attack_duplicate_ref_refusal_inconclusive(base_settings):
    mock_g = MockGuardian(should_panic=True, panic_message="Duplicate client_ref")
    res = run_scenario_step(
        DEFAULT_ATTACK_SCENARIO,
        step_title="a",
        settings=base_settings,
        mode="testnet",
        guardian_factory=lambda _s: mock_g,
    )
    assert not res.passed
    assert res.status == "inconclusive"


def test_timeout_in_one_step_continues_and_report_written(monkeypatch, tmp_path):
    mock_g = MockGuardian(
        sequence=[None, ("block", "refused", ["policy_violation"])],
        raises={0: PollTimeout(1)},
    )
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    out = tmp_path / "nested" / "dir" / "report.json"
    code = main(["--mode", "dry-run", "-y", "--report", str(out)])
    assert code == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    first, second = data["steps"]
    assert first["status"] == "timed_out"
    assert not first["passed"]
    assert first["client_ref"] in first["message"]
    assert second["passed"] and second["status"] == "refused"
    assert data["all_passed"] is False


STEP_FIELDS = {
    "scenario", "label", "family", "receiver_id", "amount", "client_ref", "request_id", "outcome",
    "reasons", "status", "tx_hash", "cancel_tx", "balance_delta", "note", "passed", "message", "duration_s",
}


def test_report_file_has_all_fields(base_settings, monkeypatch, tmp_path):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], usage={"day": "20000", "max_per_day": "50", "used": "3"})
    mock_g.checker_mode = {"outlayer": {"version_key": "abc123"}}
    monkeypatch.setattr(nightly_e2e.Settings, "load", classmethod(lambda cls: base_settings))
    monkeypatch.setattr(nightly_e2e, "TestnetGuardian", lambda _s: mock_g)
    out = tmp_path / "r" / "report.json"
    code = main(["--mode", "testnet", "-y", "--report", str(out)])
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    for key in ("started_at", "finished_at", "mode", "guardian_id", "preflight", "all_passed", "counts", "steps"):
        assert key in data
    assert data["mode"] == "testnet"
    assert data["counts"] == {"benign": {"passed": 1, "failed": 0}, "attack": {"passed": 1, "failed": 0}}
    for step in data["steps"]:
        assert STEP_FIELDS <= set(step)
    pre = data["preflight"]
    assert pre["checker_mode"] == "outlayer" and pre["version_key"] == "abc123"
    assert pre["outlayer_usage_before"]["used"] == 3 and pre["outlayer_usage_after"]["used"] == 3
    assert pre["guardian_balance"] == 1_000_000_000


def test_leftover_held_attack_after_run_exit_1(base_settings, monkeypatch):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], cancel_leaves_held=True)
    monkeypatch.setattr(nightly_e2e.Settings, "load", classmethod(lambda cls: base_settings))
    monkeypatch.setattr(nightly_e2e, "TestnetGuardian", lambda _s: mock_g)
    assert main(["--mode", "testnet", "-y"]) == 1


def test_preflight_errors_outlayer_budget_and_balance(base_settings):
    low_usage = MockGuardian(
        checker_mode={"outlayer": {"version_key": "k"}}, usage={"day": "1", "max_per_day": "50", "used": "49"}
    )
    report = _run(base_settings, low_usage, None)
    assert not report.all_passed and report.steps == []
    assert low_usage.calls == []

    poor = MockGuardian(guardian_balance=1_000_000)
    report = _run(base_settings, poor, None)
    assert not report.all_passed and poor.calls == []


def test_preflight_payee_budget_warning(base_settings, capsys):
    mock_g = MockGuardian(sequence=[("allow", "held", ["checks_passed"]), ("block", "refused", ["x"])], payee_budget=1_000_000)
    report = _run(base_settings, mock_g, None)
    assert report.preflight["warnings"]
    assert "WARNING" in capsys.readouterr().out
    assert report.all_passed


# ---- timed-out attacks, cancel bookkeeping, report always written ----


def test_timed_out_attack_resolved_at_end_and_cancelled(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, None], sent_then_timeout={1}, ref_visible_at_end={1})
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert atk.request_id == "2"
    assert mock_g.cancelled == ["2"]
    assert atk.cancel_tx == "canceltx2"
    assert atk.status == "refused"
    assert atk.note == "hold_cancelled_after_timeout"
    assert not atk.passed  # the verdict was never observed, so the run still fails
    assert report.leftover_held == []
    assert not report.all_passed


def test_timed_out_attack_unresolved_fails_run_with_ref_and_command(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, None], sent_then_timeout={1})
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert not atk.passed and not report.all_passed
    assert atk.request_id is None
    assert atk.client_ref in atk.message
    assert (
        "near contract call-function as-read-only guardian-v2.jimuelle-firewall.testnet get_receipt_by_ref "
        f"json-args '{{\"client_ref\":\"{atk.client_ref}\"}}' network-config testnet now"
    ) in atk.message
    assert "get_held" in atk.message and "hold window" in atk.message
    assert mock_g.cancelled == []


def test_cancel_sent_but_reread_fails_is_unverified_without_cancel_command(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], reread_error="rpc flaky")
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert not atk.passed and not report.all_passed
    assert atk.cancel_tx == "canceltx2"
    assert "cancel sent (tx canceltx2), status unverified" in atk.message
    assert "near contract call-function" not in atk.message
    assert "cancel_held" not in atk.message


def test_unknown_scenario_exits_1_with_message(monkeypatch, capsys):
    mock_g = MockGuardian()
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    code = main(["--mode", "dry-run", "-y", "--scenario", "no-such-scenario"])
    assert code == 1
    assert "no-such-scenario" in capsys.readouterr().err
    assert mock_g.calls == []


def test_exception_mid_loop_still_writes_report(monkeypatch, tmp_path):
    mock_g = MockGuardian(sequence=DRY_ALLOW_THEN_BLOCK)
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)
    real = nightly_e2e.run_scenario_step
    calls = []

    def flaky(*a, **kw):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("boom")
        return real(*a, **kw)

    monkeypatch.setattr(nightly_e2e, "run_scenario_step", flaky)
    out = tmp_path / "report.json"
    code = main(["--mode", "dry-run", "-y", "--report", str(out)])
    assert code == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["steps"]) == 2  # the in-flight step stays registered
    assert data["steps"][1]["status"] == "error"
    assert data["all_passed"] is False
    assert "boom" in data["preflight"]["run_error"]


def test_keyboard_interrupt_writes_report_then_reraises(monkeypatch, tmp_path):
    mock_g = MockGuardian(sequence=DRY_ALLOW_THEN_BLOCK)
    monkeypatch.setattr(nightly_e2e, "LocalGuardian", lambda _s: mock_g)

    def interrupted(*a, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(nightly_e2e, "run_scenario_step", interrupted)
    out = tmp_path / "report.json"
    with pytest.raises(KeyboardInterrupt):
        main(["--mode", "dry-run", "-y", "--report", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["all_passed"] is False and "interrupted" in data["preflight"]["run_error"]


# ---- in-flight steps survive Ctrl-C / exceptions; unparsable ids; pending resolution ----


def test_keyboard_interrupt_in_attack_poll_is_resolved_cancelled_and_reraised(base_settings, tmp_path):
    mock_g = MockGuardian(
        sequence=[BENIGN_PAID, None],
        sent_then_timeout={1},
        sent_then_raise={1: KeyboardInterrupt()},
        ref_visible_at_end={1},
    )
    out = tmp_path / "report.json"
    with pytest.raises(KeyboardInterrupt):
        _run(base_settings, mock_g, report_path=str(out))
    assert mock_g.cancelled == ["2"]
    data = json.loads(out.read_text(encoding="utf-8"))
    atk = data["steps"][1]
    assert atk["label"] == "attack" and atk["request_id"] == "2"
    assert atk["status"] == "refused" and atk["passed"] is False
    assert data["leftover_held"] == [] and data["all_passed"] is False
    assert "interrupted" in data["preflight"]["run_error"]
    # the ref registered before sending is the ref used on chain
    assert atk["client_ref"] == mock_g.calls[1].client_ref


def test_generic_exception_in_attack_poll_fails_run_and_cancels(base_settings, tmp_path):
    mock_g = MockGuardian(
        sequence=[BENIGN_PAID, None],
        sent_then_timeout={1},
        sent_then_raise={1: RuntimeError("rpc exploded")},
        ref_visible_at_end={1},
    )
    out = tmp_path / "report.json"
    report = _run(base_settings, mock_g, report_path=str(out))
    assert mock_g.cancelled == ["2"]
    assert not report.all_passed
    assert report.attack.request_id == "2" and report.attack.status == "refused"
    assert report.leftover_held == []
    assert json.loads(out.read_text(encoding="utf-8"))["steps"][1]["client_ref"] == mock_g.calls[1].client_ref


def test_exception_escaping_run_scenario_step_after_send_cancels_attack(base_settings, monkeypatch):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], ref_visible_at_end={1})
    real = nightly_e2e.run_scenario_step

    def send_then_die(*a, **kw):
        res = real(*a, **kw)
        if res.label == "attack":
            raise KeyboardInterrupt  # step result lost after the request was sent and held
        return res

    monkeypatch.setattr(nightly_e2e, "run_scenario_step", send_then_die)
    with pytest.raises(KeyboardInterrupt):
        _run(base_settings, mock_g)
    # real step already cancelled it; nothing remains held
    assert mock_g.held == []


def test_timed_out_attack_resolved_pending_gives_cancel_command_and_get_held(base_settings):
    mock_g = MockGuardian(
        sequence=[BENIGN_PAID, None], sent_then_timeout={1}, ref_visible_at_end={1}, sent_status="pending"
    )
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert not atk.passed and not report.all_passed
    assert atk.request_id == "2"
    assert mock_g.cancelled == []
    assert "cancel_held" in atk.message and '"request_id":"2"' in atk.message
    assert "get_held" in atk.message


def test_held_attack_with_unparsable_request_id_is_resolved_by_ref_and_cancelled(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], hide_request_id={1}, ref_visible_at_end={1})
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert mock_g.cancelled == ["2"]
    assert atk.request_id == "2" and atk.status == "refused" and atk.cancel_tx == "canceltx2"
    assert not atk.passed and not report.all_passed
    assert report.leftover_held == []


def test_held_attack_with_unparsable_request_id_unresolved_names_lookup_command(base_settings):
    mock_g = MockGuardian(sequence=[BENIGN_PAID, HELD_ATTACK], hide_request_id={1})
    report = _run(base_settings, mock_g)
    atk = report.attack
    assert not atk.passed and not report.all_passed
    assert atk.request_id is None and mock_g.cancelled == []
    assert "get_receipt_by_ref" in atk.message and atk.client_ref in atk.message
