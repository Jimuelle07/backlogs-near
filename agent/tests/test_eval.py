import hashlib
import json
from pathlib import Path

import pytest

from firewall_agent import eval as eval_mod
from firewall_agent.config import Settings
from firewall_agent.scenarios import list_scenarios, load_scenario
from firewall_agent.eval import (
    EVAL_CONFIGURATIONS,
    RESULTS_FORMAT,
    evaluate_scenarios,
    main,
    run_all_configurations,
    write_results,
)


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
    loaded_scenarios = [load_scenario(n, s.ns) for n in list_scenarios()]
    n_benign = sum(1 for sc in loaded_scenarios if sc.label == "benign")
    n_attack = sum(1 for sc in loaded_scenarios if sc.label == "attack")
    n_attack_per_family: dict[str, int] = {}
    for sc in loaded_scenarios:
        if sc.label == "attack":
            n_attack_per_family[sc.family] = n_attack_per_family.get(sc.family, 0) + 1
    assert n_benign > 0 and n_attack > 0
    res = evaluate_scenarios(s, checker_fn=_make_stub_runner())
    assert res["format"] == RESULTS_FORMAT
    assert res["total"] == n_benign + n_attack
    assert res["benign_total"] == n_benign
    assert res["attack_total"] == n_attack

    summ = res["summary"]
    assert summ["benign_allow"] == n_benign
    assert summ["false_holds"] == 0
    assert summ["false_holds_pct"] == 0.0
    assert summ["false_blocks"] == 0
    assert summ["false_blocks_pct"] == 0.0
    assert summ["missed_attacks"] == n_attack
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
            assert stats["total"] == n_benign
            assert stats["missed_attacks"] == 0
        else:
            assert stats["total"] == n_attack_per_family[fam]
            assert stats["missed_attacks"] == n_attack_per_family[fam]
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


# ---------------------------------------------------------------------------
# C4 — Multi-configuration run
# ---------------------------------------------------------------------------


def test_run_all_configurations_produces_multiple_rows(tmp_path):
    """C4: run_all_configurations returns one config row per preset."""
    s = Settings.load()
    # Use stub runner so this test is fast and offline.
    combined = run_all_configurations(
        s,
        configurations=[
            ("cfg_a", {"JEV_ENABLED": "false"}),
            ("cfg_b", {"JEV_ENABLED": "false"}),
        ],
        checker_fn=_make_stub_runner(),
        output_path=tmp_path / "results.json",
    )
    assert combined["format"] == RESULTS_FORMAT
    assert len(combined["configurations"]) == 2
    labels = [r["configuration"] for r in combined["configurations"]]
    assert labels == ["cfg_a", "cfg_b"]
    assert (tmp_path / "results.json").is_file()


def test_run_all_configurations_default_presets(tmp_path):
    """C4: default EVAL_CONFIGURATIONS has the expected configuration labels."""
    labels = [label for label, _ in EVAL_CONFIGURATIONS]
    assert "no_defense" in labels
    assert "jev_fusion_all_signals" in labels
    assert "jev_fusion_conformal" in labels


def test_eval_cli_all_configurations(tmp_path, monkeypatch, capsys):
    """C4: --all-configurations CLI flag runs all presets and prints summary."""
    monkeypatch.setattr(
        eval_mod,
        "run_checker",
        lambda _bin, input_bytes, rec_dir: _make_stub_runner()(input_bytes, rec_dir),
    )
    out = tmp_path / "results.json"
    # Monkeypatch run_all_configurations to use our stub runner for speed.
    original_run_all = eval_mod.run_all_configurations

    def _patched_run_all(settings, configurations=None, checker_fn=None, output_path=None, **_kw):
        return original_run_all(
            settings,
            configurations=[("no_defense", {}), ("jev_fusion_all_signals", {"POLICY_ENABLED": "true"})],
            checker_fn=_make_stub_runner(),
            output_path=output_path or out,
        )

    monkeypatch.setattr(eval_mod, "run_all_configurations", _patched_run_all)
    rc = main(["--all-configurations", "--output", str(out)])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "configurations:" in stdout


def test_eval_configurations_are_the_seven_presets_in_order():
    labels = [label for label, _ in EVAL_CONFIGURATIONS]
    assert labels == [
        "no_defense",
        "policy_only",
        "classifier_only",
        "code_rules_all_signals",
        "jev_fusion_all_signals",
        "jev_fusion_conformal",
        "jev_fusion_conformal_cascade",
    ]
    switches = {
        "FUSION_MODE",
        "CASCADE_ENABLED",
        "POLICY_ENABLED",
        "INJECTION_ENABLED",
        "COUNTERPARTY_ENABLED",
    }
    by_label = dict(EVAL_CONFIGURATIONS)
    for label, env in EVAL_CONFIGURATIONS:
        assert switches <= set(env), label
    assert by_label["jev_fusion_all_signals"]["FUSION_HOLD_THRESHOLD"] == "0.5"
    assert "FUSION_HOLD_THRESHOLD" not in by_label["jev_fusion_conformal"]
    assert by_label["jev_fusion_conformal_cascade"]["CASCADE_ENABLED"] == "true"
    assert by_label["no_defense"]["FUSION_MODE"] == "code_rules"
    assert by_label["jev_fusion_conformal"]["FUSION_MODE"] == "jev"


def test_preset_removes_exported_hold_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("FUSION_HOLD_THRESHOLD", "0.9")
    seen: dict[str, str | None] = {}
    stub = _make_stub_runner()

    def runner(input_bytes, record_dir):
        import os

        seen.setdefault("threshold", os.environ.get("FUSION_HOLD_THRESHOLD"))
        return stub(input_bytes, record_dir)

    import os

    run_all_configurations(
        Settings.load(),
        configurations=[c for c in EVAL_CONFIGURATIONS if c[0] == "jev_fusion_conformal"],
        checker_fn=runner,
        output_path=tmp_path / "results.json",
    )
    assert seen["threshold"] is None
    assert os.environ["FUSION_HOLD_THRESHOLD"] == "0.9"


def _env_probe_runner(names, seen, raises=False):
    """Stub checker that records the named env vars on every call (optionally then raises)."""
    import os

    stub = _make_stub_runner()

    def runner(input_bytes, record_dir):
        seen.append({n: os.environ.get(n) for n in names})
        if raises:
            raise RuntimeError("boom")
        return stub(input_bytes, record_dir)

    return runner


def _run_preset(tmp_path, runner, label="jev_fusion_conformal", configurations=None, **kw):
    return run_all_configurations(
        Settings.load(),
        configurations=configurations or [c for c in EVAL_CONFIGURATIONS if c[0] == label],
        checker_fn=runner,
        output_path=tmp_path / "results.json",
        scenario_names=["benign-hosting"],
        **kw,
    )


def test_preset_removes_exported_reference_examples(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("JEV_REFERENCE_EXAMPLES_JSON", '{"x": 1}')
    seen: list[dict] = []
    _run_preset(tmp_path, _env_probe_runner(["JEV_REFERENCE_EXAMPLES_JSON"], seen))
    assert seen and all(s["JEV_REFERENCE_EXAMPLES_JSON"] is None for s in seen)
    assert os.environ["JEV_REFERENCE_EXAMPLES_JSON"] == '{"x": 1}'


def test_preset_reference_examples_override_restored(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("JEV_REFERENCE_EXAMPLES_JSON", "X")
    base = dict(EVAL_CONFIGURATIONS)["jev_fusion_conformal"]
    cfgs = [("with_refs", {**base, "JEV_REFERENCE_EXAMPLES_JSON": "Y"})]
    seen: list[dict] = []
    _run_preset(tmp_path, _env_probe_runner(["JEV_REFERENCE_EXAMPLES_JSON"], seen), configurations=cfgs)
    assert seen and all(s["JEV_REFERENCE_EXAMPLES_JSON"] == "Y" for s in seen)
    assert os.environ["JEV_REFERENCE_EXAMPLES_JSON"] == "X"


def test_set_profile_path_clears_exported_profile_json(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("AGENT_PROFILE_JSON", '{"p": 1}')
    monkeypatch.setenv("AGENT_PROFILE_PATH", "old.json")
    monkeypatch.setitem(eval_mod.SCENARIO_SET_ENV, "main", {"AGENT_PROFILE_PATH": "set.json"})
    seen: list[dict] = []
    _run_preset(tmp_path, _env_probe_runner(["AGENT_PROFILE_JSON", "AGENT_PROFILE_PATH"], seen))
    assert seen
    assert all(s == {"AGENT_PROFILE_JSON": None, "AGENT_PROFILE_PATH": "set.json"} for s in seen)
    assert os.environ["AGENT_PROFILE_JSON"] == '{"p": 1}'
    assert os.environ["AGENT_PROFILE_PATH"] == "old.json"


def test_set_profile_path_restores_unset_profile_path(tmp_path, monkeypatch):
    import os

    monkeypatch.delenv("AGENT_PROFILE_PATH", raising=False)
    monkeypatch.setitem(eval_mod.SCENARIO_SET_ENV, "main", {"AGENT_PROFILE_PATH": "set.json"})
    _run_preset(tmp_path, _env_probe_runner([], []))
    assert "AGENT_PROFILE_PATH" not in os.environ


def test_set_without_env_passes_profile_json_through(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_PROFILE_JSON", '{"p": 1}')
    monkeypatch.delitem(eval_mod.SCENARIO_SET_ENV, "main", raising=False)
    seen: list[dict] = []
    _run_preset(tmp_path, _env_probe_runner(["AGENT_PROFILE_JSON"], seen))
    assert seen and all(s["AGENT_PROFILE_JSON"] == '{"p": 1}' for s in seen)


def test_agent_hold_threshold_passes_through(tmp_path, monkeypatch):
    monkeypatch.setenv("FUSION_AGENT_HOLD_THRESHOLD", "0.7")
    seen: list[dict] = []
    _run_preset(tmp_path, _env_probe_runner(["FUSION_AGENT_HOLD_THRESHOLD"], seen))
    assert seen and all(s["FUSION_AGENT_HOLD_THRESHOLD"] == "0.7" for s in seen)


def test_env_restored_when_run_raises(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("JEV_REFERENCE_EXAMPLES_JSON", "X")
    monkeypatch.setenv("AGENT_PROFILE_JSON", '{"p": 1}')
    monkeypatch.delenv("AGENT_PROFILE_PATH", raising=False)
    monkeypatch.setitem(eval_mod.SCENARIO_SET_ENV, "main", {"AGENT_PROFILE_PATH": "set.json"})
    seen: list[dict] = []
    with pytest.raises(Exception):
        _run_preset(
            tmp_path,
            _env_probe_runner(["JEV_REFERENCE_EXAMPLES_JSON", "AGENT_PROFILE_JSON", "AGENT_PROFILE_PATH"], seen, raises=True),
        )
    assert seen == [
        {"JEV_REFERENCE_EXAMPLES_JSON": None, "AGENT_PROFILE_JSON": None, "AGENT_PROFILE_PATH": "set.json"}
    ]
    assert os.environ["JEV_REFERENCE_EXAMPLES_JSON"] == "X"
    assert os.environ["AGENT_PROFILE_JSON"] == '{"p": 1}'
    assert "AGENT_PROFILE_PATH" not in os.environ


def test_cascade_skipped_classifier_is_reported(monkeypatch):
    monkeypatch.setenv("CASCADE_ENABLED", "true")
    monkeypatch.setenv("INJECTION_ENABLED", "true")
    res = evaluate_scenarios(
        Settings.load(),
        scenario_names=["benign-hosting", "attack-morse-lookalike"],
        checker_fn=_make_stub_runner(),
    )
    assert [c["cascade_path"] for c in res["cases"]] == ["classifier_skipped"] * 2
    assert all(c["classifier_called"] is False for c in res["cases"])
    row = res["configurations"][0]
    assert row["classifier_calls_per_payment"] == 0
    assert row["latency_by_path"]["classifier_skipped"]["count"] == 2
    assert "classifier_run" not in row["latency_by_path"]


def test_cascade_path_null_when_classifier_disabled(monkeypatch):
    monkeypatch.setenv("CASCADE_ENABLED", "true")
    monkeypatch.setenv("INJECTION_ENABLED", "false")
    res = evaluate_scenarios(
        Settings.load(),
        scenario_names=["benign-hosting", "attack-morse-lookalike"],
        checker_fn=_make_stub_runner(),
    )
    assert [c["cascade_path"] for c in res["cases"]] == [None, None]
    assert "latency_by_path" not in res["configurations"][0]


def test_failed_jev_call_counts_as_attempted(monkeypatch):
    monkeypatch.setenv("FUSION_MODE", "jev")
    monkeypatch.delenv("CASCADE_ENABLED", raising=False)
    stub = _make_stub_runner(lambda _ci: ("hold", ["check_unavailable"]))
    res = evaluate_scenarios(
        Settings.load(),
        scenario_names=["benign-hosting", "attack-morse-lookalike"],
        checker_fn=stub,
    )
    assert all(c["jev_called"] is True for c in res["cases"])
    assert res["configurations"][0]["jev_calls_per_payment"] == 1.0
    assert eval_mod.JEV_FAILED_CAVEAT in res["caveats"]
    assert eval_mod.JEV_FAILED_CAVEAT == "Jev calls that failed (check_unavailable) count as attempted calls."


def test_check_unavailable_in_code_rules_mode_is_not_a_jev_call(monkeypatch):
    monkeypatch.setenv("FUSION_MODE", "code_rules")
    stub = _make_stub_runner(lambda _ci: ("hold", ["check_unavailable"]))
    res = evaluate_scenarios(Settings.load(), scenario_names=["benign-hosting"], checker_fn=stub)
    assert res["cases"][0]["jev_called"] is False
    assert eval_mod.JEV_FAILED_CAVEAT not in res["caveats"]


def test_no_cascade_path_and_unpriced_cost_caveat(monkeypatch):
    monkeypatch.delenv("CASCADE_ENABLED", raising=False)
    monkeypatch.delenv("EVAL_JEV_USD_PER_CALL", raising=False)
    monkeypatch.delenv("EVAL_CLASSIFIER_USD_PER_CALL", raising=False)
    res = evaluate_scenarios(
        Settings.load(), scenario_names=["benign-hosting"], checker_fn=_make_stub_runner()
    )
    assert res["cases"][0]["cascade_path"] is None
    assert "latency_by_path" not in res["configurations"][0]
    assert res["configurations"][0]["cost_per_payment_usd"] == 0.0
    assert eval_mod.UNPRICED_CAVEAT in res["caveats"]
    assert eval_mod.MELON_CAVEAT in res["caveats"]
    assert res["scenario_set"] == "main"


def test_eval_namespace_does_not_leak_owner_account(monkeypatch):
    monkeypatch.setenv("OWNER_ACCOUNT_ID", "someone-else.testnet")
    settings = Settings.load()
    assert settings.ns == "someone-else.testnet"
    seen: list[str] = []
    inner = _make_stub_runner()

    def runner(input_bytes, record_dir):
        seen.append(json.loads(input_bytes.decode("utf-8"))["receiver_id"])
        return inner(input_bytes, record_dir)

    evaluate_scenarios(settings, checker_fn=runner)
    assert seen
    for receiver in seen:
        assert "someone-else" not in receiver
        assert "." not in receiver or receiver.endswith(".demo.testnet"), receiver


def test_cost_per_payment_uses_call_counts_and_prices(monkeypatch):
    monkeypatch.setenv("EVAL_JEV_USD_PER_CALL", "0.01")
    monkeypatch.setenv("EVAL_CLASSIFIER_USD_PER_CALL", "0.002")
    res = evaluate_scenarios(
        Settings.load(), scenario_names=["benign-hosting"], checker_fn=_make_stub_runner()
    )
    # The stub writes jev: null and injection: null, so no calls are counted.
    assert res["configurations"][0]["jev_calls_per_payment"] == 0
    assert res["configurations"][0]["cost_per_payment_usd"] == 0.0
    assert eval_mod.UNPRICED_CAVEAT not in res["caveats"]


def test_apply_calibration_writes_q_hat_and_rotation(tmp_path):
    cases = [
        {"name": f"b{i}", "label": "benign", "family": "none", "outcome": "allow", "jev_unusual": i / 100}
        for i in range(40)
    ] + [
        {"name": "a0", "label": "attack", "family": "fake_invoice", "outcome": "block"},
    ]
    calib = tmp_path / "calib.json"
    calib.write_text(json.dumps({"cases": cases}), encoding="utf-8")
    results: dict = {}
    eval_mod.apply_calibration(results, calib)
    assert isinstance(results["q_hat"], float)
    rows = {r["family"]: r for r in results["unseen_family_rotation"]}
    assert rows["fake_invoice"]["detected"] == 1
    assert rows["all"]["total"] == 1


# ---------------------------------------------------------------------------
# Step 3 / Step 5 — per-case signals, --record-dir, --refuse-from
# ---------------------------------------------------------------------------

JEV_SIGNAL = {
    "backend": "jev",
    "model": "jev-latest",
    "unusual": 0.4,
    "injection_driven": 0.7,
    "receiver_risk": 0.25,
    "label": "B",
    "label_probabilities": {"A": 0.2, "B": 0.7, "C": 0.1},
}
PILOT_NAMES = ["benign-hosting", "attack-morse-lookalike", "benign-partial-payment"]
JEV_PRESET = "jev_fusion_conformal"
CASCADE_PRESET = "jev_fusion_conformal_cascade"


def _signal_runner(signals, outcome_for=lambda _ci: ("allow", ["stub_allow"])):
    """Stub runner whose DecisionRecord carries `signals` (merged over the all-null defaults)."""
    stub = _make_stub_runner(outcome_for)

    def runner(input_bytes, record_dir):
        verdict = stub(input_bytes, record_dir)
        path = record_dir / f"{verdict['request_id']}.json"
        record = json.loads(path.read_bytes())
        record["signals"].update(signals)
        raw = json.dumps(record, separators=(",", ":")).encode("utf-8")
        path.write_bytes(raw)
        return {**verdict, "record_sha256": hashlib.sha256(raw).hexdigest()}

    return runner


def _jev_source(tmp_path, names=PILOT_NAMES):
    """Record a Jev run with the stub: returns (source results file, record dir)."""
    rec = tmp_path / "rec"
    src = tmp_path / "src.json"
    run_all_configurations(
        Settings.load(),
        configurations=[(JEV_PRESET, eval_mod.preset_env(JEV_PRESET))],
        checker_fn=_signal_runner({"jev": JEV_SIGNAL}),
        output_path=src,
        scenario_names=names,
        record_dir=rec,
    )
    return src, rec


def _snapshot(directory):
    return {p.name: p.read_bytes() for p in sorted(directory.iterdir())}


def test_refuse_from_replaces_outcomes_and_recomputes_summary(tmp_path):
    src, rec = _jev_source(tmp_path)
    before = _snapshot(rec)
    assert len(before) == 3
    refused_calls = []

    def refuse_fn(record_bytes):
        rid = json.loads(record_bytes)["request_id"]
        refused_calls.append(rid)
        return {"outcome": "hold", "reasons": ["unusual_for_agent"]} if rid == "2" else {
            "outcome": "allow",
            "reasons": [],
        }

    out = tmp_path / "refused.json"
    combined = run_all_configurations(
        Settings.load(),
        configurations=[
            ("no_defense", eval_mod.preset_env("no_defense")),
            (JEV_PRESET, eval_mod.preset_env(JEV_PRESET)),
        ],
        checker_fn=_make_stub_runner(),
        output_path=out,
        record_dir=rec,
        refuse_from=src,
        refuse_fn=refuse_fn,
    )
    assert refused_calls == ["1", "2", "3"]
    assert combined["refused_from"] == "src.json"
    assert json.loads(out.read_text(encoding="utf-8"))["refused_from"] == "src.json"
    assert [c["name"] for c in combined["cases"]] == PILOT_NAMES
    assert [c["outcome"] for c in combined["cases"]] == ["allow", "hold", "allow"]
    assert combined["cases"][1]["reasons"] == ["unusual_for_agent"]
    assert all(c["refused"] is True for c in combined["cases"])
    assert all(c["jev_called"] is True for c in combined["cases"])
    assert combined["summary"]["held_attacks"] == 1
    assert combined["summary"]["missed_attacks"] == 0
    rows = {r["configuration"]: r for r in combined["configurations"]}
    assert rows[JEV_PRESET]["held_attacks"] == 1
    assert rows[JEV_PRESET]["jev_calls_per_payment"] == 1.0
    # The code-rules row ran normally over the source's scenarios (stub: all allow), not re-fused.
    assert rows["no_defense"]["missed_attacks"] == 1
    assert _snapshot(rec) == before


def test_refuse_from_skips_cascade_preset_with_caveat(tmp_path):
    src, rec = _jev_source(tmp_path)
    combined = run_all_configurations(
        Settings.load(),
        configurations=[
            (CASCADE_PRESET, eval_mod.preset_env(CASCADE_PRESET)),
            (JEV_PRESET, eval_mod.preset_env(JEV_PRESET)),
        ],
        output_path=tmp_path / "refused.json",
        record_dir=rec,
        refuse_from=src,
        refuse_fn=lambda _b: {"outcome": "allow", "reasons": []},
    )
    assert [r["configuration"] for r in combined["configurations"]] == [JEV_PRESET]
    caveat = "Cascade row not re-run: its Jev state differs (no classifier score), so it cannot be re-fused."
    assert combined["caveats"].count(caveat) == 1


def test_refuse_from_missing_record_file_exits(tmp_path):
    src, rec = _jev_source(tmp_path)
    (rec / "2.json").unlink()
    with pytest.raises(SystemExit, match=r"2\.json"):
        run_all_configurations(
            Settings.load(),
            configurations=[(JEV_PRESET, eval_mod.preset_env(JEV_PRESET))],
            output_path=tmp_path / "refused.json",
            record_dir=rec,
            refuse_from=src,
            refuse_fn=lambda _b: {"outcome": "allow", "reasons": []},
        )


def test_refuse_from_scenario_set_mismatch_exits(tmp_path):
    src, rec = _jev_source(tmp_path)
    with pytest.raises(SystemExit, match="scenario_set"):
        run_all_configurations(
            Settings.load(),
            configurations=[(JEV_PRESET, eval_mod.preset_env(JEV_PRESET))],
            output_path=tmp_path / "refused.json",
            scenario_set="redteam",
            record_dir=rec,
            refuse_from=src,
            refuse_fn=lambda _b: {"outcome": "allow", "reasons": []},
        )


def test_refuse_from_cli_argument_rules(tmp_path):
    src = tmp_path / "src.json"
    src.write_text("{}", encoding="utf-8")
    base = ["--refuse-from", str(src), "--output", str(tmp_path / "o.json")]
    with pytest.raises(SystemExit, match="record-dir"):
        main([*base, "--preset", JEV_PRESET])
    with pytest.raises(SystemExit, match="preset"):
        main([*base, "--record-dir", str(tmp_path / "rec")])
    with pytest.raises(SystemExit, match="scenario"):
        main([*base, "--record-dir", str(tmp_path / "rec"), "--preset", JEV_PRESET, "--scenario", "benign-hosting"])


def test_record_dir_rejects_non_empty_dir(tmp_path):
    rec = tmp_path / "rec"
    rec.mkdir()
    (rec / "1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="not empty"):
        run_all_configurations(
            Settings.load(),
            configurations=[("cfg", {"FUSION_MODE": "code_rules"})],
            checker_fn=_make_stub_runner(),
            output_path=tmp_path / "o.json",
            scenario_names=PILOT_NAMES,
            record_dir=rec,
        )
    assert _snapshot(rec) == {"1.json": b"{}"}


def test_record_dir_rejects_several_presets(tmp_path):
    with pytest.raises(SystemExit, match="one preset"):
        run_all_configurations(
            Settings.load(),
            configurations=[("a", {"FUSION_MODE": "code_rules"}), ("b", {"FUSION_MODE": "code_rules"})],
            checker_fn=_make_stub_runner(),
            output_path=tmp_path / "o.json",
            scenario_names=PILOT_NAMES,
            record_dir=tmp_path / "rec",
        )


def test_record_dir_cli_rejects_non_empty_dir(tmp_path):
    rec = tmp_path / "rec"
    rec.mkdir()
    (rec / "x").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="not empty"):
        main(["--record-dir", str(rec), "--output", str(tmp_path / "o.json"), "--scenario", "benign-hosting"])


def test_cases_carry_new_signal_keys_from_the_record():
    signals = {
        "jev": JEV_SIGNAL,
        "policy": {"ok": False, "violations": ["amount_mismatch_request"]},
        "counterparty": {"lookalike_of": "hostco.demo.testnet", "prior_payments": 0},
    }
    res = evaluate_scenarios(
        Settings.load(), scenario_names=["benign-hosting"], checker_fn=_signal_runner(signals)
    )
    case = res["cases"][0]
    assert case["jev_injection_driven"] == 0.7
    assert case["jev_receiver_risk"] == 0.25
    assert case["jev_label"] == "B"
    assert case["policy_violations"] == ["amount_mismatch_request"]
    assert case["lookalike_of"] == "hostco.demo.testnet"
    keys = list(case)
    assert keys[keys.index("jev_unusual") + 1 : keys.index("jev_unusual") + 6] == [
        "jev_injection_driven",
        "jev_receiver_risk",
        "jev_label",
        "policy_violations",
        "lookalike_of",
    ]


def test_cases_new_signal_keys_default_when_signals_absent():
    res = evaluate_scenarios(
        Settings.load(),
        scenario_names=["benign-hosting"],
        checker_fn=_signal_runner({"policy": None}),
    )
    case = res["cases"][0]
    assert case["jev_injection_driven"] is None
    assert case["jev_receiver_risk"] is None
    assert case["jev_label"] is None
    assert case["policy_violations"] == []
    assert case["lookalike_of"] is None


def test_preset_removes_exported_injection_hold_threshold(tmp_path, monkeypatch):
    import os

    name = "FUSION_JEV_INJECTION_HOLD_THRESHOLD"
    monkeypatch.setenv(name, "0.2")
    seen: list[dict[str, str | None]] = []
    _run_preset(tmp_path, _env_probe_runner([name], seen))
    assert seen and all(s[name] is None for s in seen)
    assert os.environ[name] == "0.2"
