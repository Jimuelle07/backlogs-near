import os

import pytest

from firewall_agent.config import _load_env


@pytest.fixture(autouse=True)
def _restore_guardian_id(monkeypatch):
    # Record the original state so monkeypatch restores it after _load_env mutates os.environ.
    monkeypatch.setenv("GUARDIAN_ID", "x")
    monkeypatch.delenv("GUARDIAN_ID", raising=False)


def _write(tmp_path, env: str, testnet: str):
    (tmp_path / ".env").write_text(env, encoding="utf-8")
    (tmp_path / ".env.testnet").write_text(testnet, encoding="utf-8")
    return tmp_path / ".env", tmp_path / ".env.testnet"


def test_empty_env_value_does_not_shadow_testnet(tmp_path):
    _load_env(*_write(tmp_path, "GUARDIAN_ID=\n", "GUARDIAN_ID=g.testnet\n"))
    assert os.environ["GUARDIAN_ID"] == "g.testnet"


def test_nonempty_env_wins_over_testnet(tmp_path):
    _load_env(*_write(tmp_path, "GUARDIAN_ID=g.env\n", "GUARDIAN_ID=g.testnet\n"))
    assert os.environ["GUARDIAN_ID"] == "g.env"


def test_key_only_in_testnet_loads(tmp_path):
    _load_env(*_write(tmp_path, "OTHER=1\n", "GUARDIAN_ID=g.testnet\n"))
    assert os.environ["GUARDIAN_ID"] == "g.testnet"


def test_key_empty_in_both_stays_empty(tmp_path):
    _load_env(*_write(tmp_path, "GUARDIAN_ID=\n", "GUARDIAN_ID=\n"))
    assert os.environ["GUARDIAN_ID"] == ""


def test_process_environment_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_ID", "g.proc")
    _load_env(*_write(tmp_path, "GUARDIAN_ID=g.env\n", "GUARDIAN_ID=g.testnet\n"))
    assert os.environ["GUARDIAN_ID"] == "g.proc"


def test_empty_process_environment_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("GUARDIAN_ID", "")
    _load_env(*_write(tmp_path, "GUARDIAN_ID=g.env\n", "GUARDIAN_ID=g.testnet\n"))
    assert os.environ["GUARDIAN_ID"] == ""
