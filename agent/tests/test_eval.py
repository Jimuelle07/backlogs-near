import hashlib
import json
from pathlib import Path

import pytest

from firewall_agent import eval as eval_mod
from firewall_agent.config import Settings
from firewall_agent.eval import RESULTS_FORMAT, evaluate_scenarios, main, write_results


def _make_stub_runner(outcome_for=lambda _ci: ("allow", ["stub_allow"])):
    """In-process stub checker runner writing a valid DecisionRecord and returning a Verdict."""

    def runner(input_bytes: bytes, record_dir: Path) -> dict:
        ci = json.loads(input_bytes.decode("utf-8"))
        outcome, reasons = outcome_for(ci)
        record = {
            "format": "firewall.decision_record.v1",
            "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
            "request_id": ci["request_id"],
            "checker_version": "0.1.0",
            "outcome": outcome,
            "reasons": reasons,
            "signals": {
                "policy": {"ok": True, "violations": []},
                "injection": None,
                "melon": None,
                "counterparty": None,
                "jev": None,
            },
        }
        rec_bytes = json.dumps(record, separators=(",", ":")).encode("utf-8")
        record_dir.mkdir(parents=True, exist_ok=True)
        (record_dir / f"{ci['request_id']}.json").write_bytes(rec_bytes)
        return {
            "format": "firewall.verdict.v1",
            "request_id": ci["request_id"],
            "receiver_id": ci["receiver_id"],
            "token_id": ci["token_id"],
            "amount": ci["amount"],
            "outcome": outcome,
            "reasons": reasons,
            "record_sha256": hashlib.sha256(rec_bytes).hexdigest(),
            "checker_version": "0.1.0",
        }

    return runner


def test_eval_all_scenarios_stub_allow(tmp_path):
    s = Settings.load()
    res = evaluate_scenarios(s, checker_fn=_make_stub_runner())
    assert res["format"] == RESULTS_FORMAT
    assert res["total"] == 60
    assert res["benign_total"] == 30
    assert res["attack_total"] == 30

    summ = res["summary"]
    assert summ["benign_allow"] == 30
    assert summ["false_holds"] == 0
    assert summ["false_holds_pct"] == 0.0
    assert summ["false_blocks"] == 0
    assert summ["false_blocks_pct"] == 0.0
    assert summ["missed_attacks"] == 30
    assert summ["missed_attacks_pct"] == 100.0
    assert summ["held_attacks"] == 0
    assert summ["blocked_attacks"] == 0

    assert set(res["by_family"].keys()) == {
        "none",
        "direct_injection",
        "encoded_injection",
        "indirect_injection",
        "memory_poisoning",
        "lookalike_receiver",
        "fake_invoice",
    }
    for fam, stats in res["by_family"].items():
        if fam == "none":
            assert stats["total"] == 30
            assert stats["missed_attacks"] == 0
        else:
            assert stats["total"] == 5
            assert stats["missed_attacks"] == 5
            assert stats["missed_attacks_pct"] == 100.0

    out = write_results(res, tmp_path / "results.json")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == res


def test_eval_mixed_outcomes_counts_and_rates():
    s = Settings.load()
    names = [
        "benign-hosting",
        "benign-partial-payment",
        "attack-morse-lookalike",
        "attack-fake-invoice-amount-inflation",
    ]
    verdicts_by_req = {
        "1": ("allow", ["stub_allow"]),
        "2": ("hold", ["unusual_for_agent"]),
        "3": ("block", ["lookalike_receiver"]),
        "4": ("allow", ["stub_allow"]),
    }
    res = evaluate_scenarios(
        s,
        scenario_names=names,
        configuration="mixed_test",
        checker_fn=_make_stub_runner(lambda ci: verdicts_by_req[ci["request_id"]]),
    )
    summ = res["summary"]
    assert res["benign_total"] == 2
    assert res["attack_total"] == 2
    assert summ["benign_allow"] == 1
    assert summ["false_holds"] == 1
    assert summ["false_holds_pct"] == 50.0
    assert summ["false_blocks"] == 0
    assert summ["missed_attacks"] == 1
    assert summ["missed_attacks_pct"] == 50.0
    assert summ["blocked_attacks"] == 1
    assert res["configurations"][0]["configuration"] == "mixed_test"


def test_eval_cli_writes_results_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        eval_mod,
        "run_checker",
        lambda _bin, input_bytes, rec_dir: _make_stub_runner()(input_bytes, rec_dir),
    )
    out = tmp_path / "out" / "results.json"
    rc = main(["--output", str(out), "--scenario", "benign-hosting", "--scenario", "attack-morse-lookalike"])
    assert rc == 0
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["total"] == 2
    stdout = capsys.readouterr().out
    assert "scenarios: 2 (benign=1, attack=1)" in stdout
    assert "results_file:" in stdout


def test_eval_with_real_checker_binary_when_built(tmp_path):
    s = Settings.load()
    if not s.checker_bin.is_file():
        pytest.skip(f"checker binary not built at {s.checker_bin}")
    res = evaluate_scenarios(
        s,
        scenario_names=["benign-hosting", "attack-fake-invoice-amount-inflation"],
    )
    assert res["total"] == 2
    by_name = {c["name"]: c for c in res["cases"]}
    assert by_name["benign-hosting"]["policy_ok"] is True
    assert by_name["attack-fake-invoice-amount-inflation"]["policy_ok"] is False
