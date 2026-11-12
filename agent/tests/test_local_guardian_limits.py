import dataclasses
import json

import pytest

from firewall_agent import demo
from firewall_agent import guardian as guardian_mod
from firewall_agent.config import TOKEN_DECIMALS, Settings
from firewall_agent.formats import PaymentRequest
from firewall_agent.guardian import ContractRefusal, LocalGuardian

UNIT = 10**TOKEN_DECIMALS
DAY = 86_400_000_000_000
MIN = 60 * 10**9
T0 = 20_000 * DAY + 5 * MIN  # arbitrary UTC day, shortly after midnight


@pytest.fixture
def settings(tmp_path):
    s = Settings.load()
    if not s.checker_bin.is_file():
        pytest.fail(f"checker binary not found at {s.checker_bin}; run: cargo build -p checker --release")
    return dataclasses.replace(s, checker_record_dir=tmp_path / "decisions")


def _req(s, amount, ref="ref-1"):
    return PaymentRequest(
        client_ref=ref,
        receiver_id=f"cdnfast.{s.ns}",
        amount=amount,
        memo="INV-1",
        user_request="Pay the bill.",
    )


def _fake_checker(monkeypatch, outcome):
    def fake(checker_bin, input_bytes, record_dir, counterparty_namespace=None):
        ci = json.loads(input_bytes)
        record_dir.mkdir(parents=True, exist_ok=True)
        (record_dir / f"{ci['request_id']}.json").write_text("{}")
        return {
            "format": guardian_mod.VERDICT_FORMAT,
            "request_id": ci["request_id"],
            "receiver_id": ci["receiver_id"],
            "token_id": ci["token_id"],
            "amount": ci["amount"],
            "outcome": outcome,
            "reasons": ["test"],
            "record_sha256": "0" * 64,
        }

    monkeypatch.setattr(guardian_mod, "run_checker", fake)


def _guardian(s, clock):
    return LocalGuardian(s, now_ns=lambda: clock[0])


def _records(s):
    d = s.checker_record_dir / "dry-run"
    return sorted(p.name for p in d.glob("[0-9]*.json")) if d.is_dir() else []


def test_per_payment_cap_boundary(settings, tmp_path, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    clock = [T0]
    # 200 tUSDC is above a new payee's 20 tUSDC budget: accepted under the cap, escrowed.
    assert _guardian(settings, clock).request_payment(_req(settings, 200 * UNIT)).status == "held"
    assert _records(settings) == ["1.json"]

    other = dataclasses.replace(settings, checker_record_dir=tmp_path / "other")
    with pytest.raises(ContractRefusal, match="^Amount exceeds per-payment cap$"):
        _guardian(other, clock).request_payment(_req(other, 200 * UNIT + 1))
    assert _records(other) == []


def test_refusal_writes_nothing_and_keeps_next_id(settings):
    clock = [T0]
    g = _guardian(settings, clock)
    g.request_payment(_req(settings, 10 * UNIT))
    before = g.next_request_id()
    with pytest.raises(ContractRefusal, match="Amount exceeds per-payment cap"):
        g.request_payment(_req(settings, 200 * UNIT + 1, "ref-2"))
    assert g.next_request_id() == before == 2
    assert _records(settings) == ["1.json"]


def test_daily_cap_and_day_roll(settings, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    clock = [T0]
    g = _guardian(settings, clock)
    for amt in (200, 200, 100):
        g.request_payment(_req(settings, amt * UNIT))
    with pytest.raises(ContractRefusal, match="^Daily cap reached$"):
        g.request_payment(_req(settings, 1))
    assert g.next_request_id() == 4

    # state persists across guardian instances
    with pytest.raises(ContractRefusal, match="Daily cap reached"):
        _guardian(settings, clock).request_payment(_req(settings, 1))

    clock[0] = T0 + DAY
    assert _guardian(settings, clock).request_payment(_req(settings, 200 * UNIT)).status == "held"


def test_block_releases_reservation(settings, monkeypatch):
    _fake_checker(monkeypatch, "block")
    clock = [T0]
    g = _guardian(settings, clock)
    for _ in range(3):
        d = g.request_payment(_req(settings, 200 * UNIT))
        assert d.status == "refused" and d.release_at_ns is None
    state = json.loads(g.state_path.read_text())
    assert state == {"spend_day": T0 // DAY, "spent_today": 0, "payee_budgets": {}}


@pytest.mark.parametrize(
    "amount,window",
    [
        (20 * UNIT - 1, 10 * MIN),
        (20 * UNIT, 60 * MIN),
        (100 * UNIT, 60 * MIN),
        (100 * UNIT + 1, 360 * MIN),
    ],
)
def test_hold_keeps_reservation_and_sets_release(settings, monkeypatch, amount, window):
    _fake_checker(monkeypatch, "hold")
    clock = [T0]
    g = _guardian(settings, clock)
    d = g.request_payment(_req(settings, amount))
    assert d.status == "held"
    assert d.release_at_ns == T0 + window
    assert json.loads(g.state_path.read_text())["spent_today"] == amount


def test_allow_keeps_reservation(settings, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    g = _guardian(settings, [T0])
    g.request_payment(_req(settings, 7 * UNIT))
    assert json.loads(g.state_path.read_text())["spent_today"] == 7 * UNIT


def test_allow_above_payee_budget_is_held(settings, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    g = _guardian(settings, [T0])
    d = g.request_payment(_req(settings, 20 * UNIT + 1))
    assert (d.outcome, d.status) == ("allow", "held")
    assert d.release_at_ns == T0 + 60 * MIN
    state = json.loads(g.state_path.read_text())
    assert state["spent_today"] == 20 * UNIT + 1
    assert state["payee_budgets"] == {}


def test_allow_within_payee_budget_grows_it(settings, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    clock = [T0]
    g = _guardian(settings, clock)
    receiver = _req(settings, 1).receiver_id
    d = g.request_payment(_req(settings, 18 * UNIT))
    assert (d.status, d.release_at_ns) == ("would_pay", None)
    assert json.loads(g.state_path.read_text())["payee_budgets"] == {receiver: 36 * UNIT}
    # The budget survives the day roll and now covers 36 tUSDC.
    clock[0] = T0 + DAY
    assert g.request_payment(_req(settings, 36 * UNIT, "ref-2")).status == "would_pay"
    assert json.loads(g.state_path.read_text())["payee_budgets"] == {receiver: 72 * UNIT}


def test_demo_prints_contract_refusal(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHECKER_RECORD_DIR", str(tmp_path / "decisions"))
    rc = demo.main(["--scenario", "attack-direct-drain-cap"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "refused by contract: Amount exceeds per-payment cap" in out
    assert not (tmp_path / "decisions" / "dry-run").exists()


def test_demo_prints_held_until(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHECKER_RECORD_DIR", str(tmp_path / "decisions"))
    _fake_checker(monkeypatch, "hold")
    monkeypatch.setattr(guardian_mod.time, "time_ns", lambda: T0)
    rc = demo.main(["--scenario", "benign-hosting"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "action: held" in out
    assert "held until 2024-10-04T00:15:00Z" in out


def _seed_full_day(tmp_path, monkeypatch):
    monkeypatch.setenv("CHECKER_RECORD_DIR", str(tmp_path / "decisions"))
    monkeypatch.setattr(guardian_mod.time, "time_ns", lambda: T0)
    d = tmp_path / "decisions" / "dry-run"
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps({"spend_day": T0 // DAY, "spent_today": 500 * UNIT}))


HINT = "rerun with --reset-spend"


def test_demo_daily_cap_hint_and_reset(tmp_path, monkeypatch, capsys):
    _seed_full_day(tmp_path, monkeypatch)
    _fake_checker(monkeypatch, "allow")
    assert demo.main(["--scenario", "benign-hosting"]) == 1
    out = capsys.readouterr().out
    assert "refused by contract: Daily cap reached" in out
    assert HINT in out

    assert demo.main(["--scenario", "benign-hosting", "--reset-spend"]) == 0
    out = capsys.readouterr().out
    assert "action: would_pay" in out
    assert HINT not in out


def test_demo_no_hint_on_per_payment_refusal(tmp_path, monkeypatch, capsys):
    _seed_full_day(tmp_path, monkeypatch)
    assert demo.main(["--scenario", "attack-direct-drain-cap"]) == 1
    out = capsys.readouterr().out
    assert "Amount exceeds per-payment cap" in out
    assert HINT not in out


def test_demo_testnet_ignores_reset_and_no_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHECKER_RECORD_DIR", str(tmp_path / "decisions"))

    class FakeTestnet:
        def __init__(self, settings):
            pass

        def request_payment(self, req):
            raise ContractRefusal("Daily cap reached")

    monkeypatch.setattr(demo, "TestnetGuardian", FakeTestnet)
    assert demo.main(["--scenario", "benign-hosting", "--mode", "testnet", "--reset-spend"]) == 1
    out = capsys.readouterr().out
    assert "--reset-spend only applies to dry-run" in out
    assert "refused by contract: Daily cap reached" in out
    assert HINT not in out


def _spent(g):
    return json.loads(g.state_path.read_text())["spent_today"]


def test_checker_failure_rolls_back(settings, monkeypatch):
    g = _guardian(settings, [T0])
    _fake_checker(monkeypatch, "allow")
    g.request_payment(_req(settings, 10 * UNIT))

    def boom(*a, **kw):
        raise SystemExit("checker exited 1")

    monkeypatch.setattr(guardian_mod, "run_checker", boom)
    with pytest.raises(SystemExit):
        g.request_payment(_req(settings, 50 * UNIT, "ref-2"))
    assert _spent(g) == 10 * UNIT


def test_mismatched_verdict_rolls_back(settings, monkeypatch):
    g = _guardian(settings, [T0])
    _fake_checker(monkeypatch, "allow")
    g.request_payment(_req(settings, 10 * UNIT))
    good = guardian_mod.run_checker

    def bad_id(*a, **kw):
        v = good(*a, **kw)
        v["request_id"] = "999"
        return v

    monkeypatch.setattr(guardian_mod, "run_checker", bad_id)
    with pytest.raises(ValueError, match="request_id"):
        g.request_payment(_req(settings, 50 * UNIT, "ref-2"))
    assert _spent(g) == 10 * UNIT


CORRUPT = [
    "not json{",
    "[]",
    json.dumps({"spend_day": 1}),
    json.dumps({"spend_day": 1, "spent_today": -1}),
    json.dumps({"spend_day": -1, "spent_today": 0}),
    json.dumps({"spend_day": 1, "spent_today": 1.5}),
    json.dumps({"spend_day": 1, "spent_today": True}),
    json.dumps({"spend_day": "1", "spent_today": 0}),
    json.dumps({"spend_day": 1, "spent_today": 0, "payee_budgets": []}),
    json.dumps({"spend_day": 1, "spent_today": 0, "payee_budgets": {"a.testnet": -1}}),
    json.dumps({"spend_day": 1, "spent_today": 0, "payee_budgets": {"a.testnet": "5"}}),
]


@pytest.mark.parametrize("content", CORRUPT)
def test_corrupt_state_fails_closed_and_reset_recovers(settings, monkeypatch, content):
    _fake_checker(monkeypatch, "allow")
    g = _guardian(settings, [T0])
    g.record_dir.mkdir(parents=True)
    g.state_path.write_text(content)
    with pytest.raises(ContractRefusal, match="state.json is corrupt; rerun with --reset-spend"):
        g.request_payment(_req(settings, UNIT))
    assert g.state_path.read_text() == content
    assert _records(settings) == []

    g.reset_spend()
    assert g.request_payment(_req(settings, UNIT)).status == "would_pay"


def test_demo_corrupt_state_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHECKER_RECORD_DIR", str(tmp_path / "decisions"))
    d = tmp_path / "decisions" / "dry-run"
    d.mkdir(parents=True)
    (d / "state.json").write_text("garbage")
    assert demo.main(["--scenario", "benign-hosting"]) == 1
    assert "dry-run state.json is corrupt; rerun with --reset-spend" in capsys.readouterr().out


def test_clock_moved_back_keeps_spend(settings, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    clock = [T0]
    g = _guardian(settings, clock)
    for _ in range(2):
        g.request_payment(_req(settings, 200 * UNIT))
    clock[0] = T0 - DAY
    with pytest.raises(ContractRefusal, match="Daily cap reached"):
        g.request_payment(_req(settings, 101 * UNIT))
    assert json.loads(g.state_path.read_text()) == {
        "spend_day": T0 // DAY,
        "spent_today": 400 * UNIT,
        "payee_budgets": {},
    }


def test_grooming_stopped_by_daily_cap(settings, monkeypatch):
    # An always-allow checker plus a growing schedule to one new payee: the budget keeps doubling,
    # but the daily cap still bounds cumulative spend.
    _fake_checker(monkeypatch, "allow")
    g = _guardian(settings, [T0])
    for i, amt in enumerate((18, 36, 72, 144, 200), start=1):
        d = g.request_payment(_req(settings, amt * UNIT, f"ref-{i}"))
        assert d.status == "would_pay"
    assert _spent(g) == 470 * UNIT
    with pytest.raises(ContractRefusal, match="^Daily cap reached$"):
        g.request_payment(_req(settings, 200 * UNIT, "ref-6"))
    assert _spent(g) <= 500 * UNIT
    assert _spent(g) == 470 * UNIT


def test_replayed_verdict_does_not_bind_larger_amount(settings):
    g = _guardian(settings, [T0])
    small = g.build_checker_input(_req(settings, 12 * UNIT), 7)
    large = g.build_checker_input(_req(settings, 120 * UNIT), 7)
    verdict = {
        "format": guardian_mod.VERDICT_FORMAT,
        "request_id": small["request_id"],
        "receiver_id": small["receiver_id"],
        "token_id": small["token_id"],
        "amount": small["amount"],
        "outcome": "allow",
        "reasons": ["test"],
        "record_sha256": "0" * 64,
    }
    assert guardian_mod.binds(small, verdict) is None
    assert guardian_mod.binds(large, verdict) == "amount"


def _capture_env(monkeypatch):
    seen = {}

    def fake_run(cmd, input, capture_output, env):
        seen["env"] = env
        return type("P", (), {"returncode": 0, "stdout": b"{}", "stderr": b""})()

    monkeypatch.setattr(guardian_mod.subprocess, "run", fake_run)
    return seen


def test_run_checker_sets_namespace_env(tmp_path, monkeypatch):
    exe = tmp_path / "checker"
    exe.write_text("")
    monkeypatch.setenv("COUNTERPARTY_NAMESPACE", "inherited.testnet")
    seen = _capture_env(monkeypatch)
    guardian_mod.run_checker(exe, b"{}", tmp_path, counterparty_namespace="ns.testnet")
    assert seen["env"]["COUNTERPARTY_NAMESPACE"] == "ns.testnet"


def test_run_checker_none_leaves_inherited_env(tmp_path, monkeypatch):
    exe = tmp_path / "checker"
    exe.write_text("")
    seen = _capture_env(monkeypatch)
    monkeypatch.delenv("COUNTERPARTY_NAMESPACE", raising=False)
    guardian_mod.run_checker(exe, b"{}", tmp_path)
    assert "COUNTERPARTY_NAMESPACE" not in seen["env"]
    monkeypatch.setenv("COUNTERPARTY_NAMESPACE", "inherited.testnet")
    guardian_mod.run_checker(exe, b"{}", tmp_path, counterparty_namespace=None)
    assert seen["env"]["COUNTERPARTY_NAMESPACE"] == "inherited.testnet"


def test_local_guardian_passes_scenario_namespace(settings, monkeypatch):
    _fake_checker(monkeypatch, "allow")
    inner = guardian_mod.run_checker
    calls = []

    def spy(*a, **kw):
        calls.append(kw.get("counterparty_namespace"))
        return inner(*a, **kw)

    monkeypatch.setattr(guardian_mod, "run_checker", spy)
    _guardian(settings, [T0]).request_payment(_req(settings, 10 * UNIT))
    assert calls == [settings.ns]
