import dataclasses
import hashlib
import json
import subprocess

import pytest

from firewall_agent import guardian as guardian_mod
from firewall_agent.agent import propose_payment
from firewall_agent.config import Settings
from firewall_agent.guardian import LocalGuardian
from firewall_agent.llm import ScriptedLLM
from firewall_agent.scenarios import load_scenario


@pytest.fixture
def settings(tmp_path):
    s = Settings.load()
    if not s.checker_bin.is_file():
        pytest.fail(f"checker binary not found at {s.checker_bin}; run: cargo build -p checker --release")
    return dataclasses.replace(s, checker_record_dir=tmp_path / "decisions")


def _benign_request(s):
    scenario = load_scenario("benign-hosting", s.ns)
    return propose_payment(scenario, ScriptedLLM(scenario), "ref-1")


def test_benign_allow(settings, validator):
    d = LocalGuardian(settings).request_payment(_benign_request(settings))
    assert d.outcome == "allow"
    assert d.status == "would_pay"
    assert d.reasons == ["stub_allow"]

    record_path = settings.checker_record_dir / "dry-run" / "1.json"
    raw = record_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == d.record_sha256
    validator("decision-record").validate(json.loads(raw))


def test_verdict_validates(settings, validator, monkeypatch):
    seen = {}
    real_run = subprocess.run

    def spy(*a, **kw):
        r = real_run(*a, **kw)
        seen["verdict"] = json.loads(r.stdout)
        return r

    monkeypatch.setattr(guardian_mod.subprocess, "run", spy)
    LocalGuardian(settings).request_payment(_benign_request(settings))
    validator("verdict").validate(seen["verdict"])


def test_mismatched_verdict_rejected(settings, monkeypatch):
    real_run = subprocess.run

    def tamper(*a, **kw):
        r = real_run(*a, **kw)
        v = json.loads(r.stdout)
        v["receiver_id"] = "evil.demo.testnet"
        return subprocess.CompletedProcess(r.args, r.returncode, json.dumps(v).encode(), r.stderr)

    monkeypatch.setattr(guardian_mod.subprocess, "run", tamper)
    with pytest.raises(ValueError, match="receiver_id"):
        LocalGuardian(settings).request_payment(_benign_request(settings))


def test_missing_binary(settings, tmp_path):
    s = dataclasses.replace(settings, checker_bin=tmp_path / "nope")
    with pytest.raises(SystemExit, match="cargo build -p checker --release"):
        LocalGuardian(s).request_payment(_benign_request(s))


def test_consecutive_runs_get_sequential_ids(settings):
    g = LocalGuardian(settings)
    d1 = g.request_payment(_benign_request(settings))
    d2 = LocalGuardian(settings).request_payment(_benign_request(settings))
    for n, d in ((1, d1), (2, d2)):
        assert d.record_path == settings.checker_record_dir / "dry-run" / f"{n}.json"
        assert hashlib.sha256(d.record_path.read_bytes()).hexdigest() == d.record_sha256
    assert d1.record_path.exists() and d2.record_path.exists()
