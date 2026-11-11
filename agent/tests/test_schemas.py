import json

import pytest

from firewall_agent.agent import propose_payment
from firewall_agent.config import REPO_ROOT, Settings
from firewall_agent.guardian import LocalGuardian
from firewall_agent.llm import ScriptedLLM
from firewall_agent.scenarios import list_scenarios, load_scenario

EXAMPLES = sorted((REPO_ROOT / "schemas" / "examples").glob("*.json"))
FIXTURES = sorted((REPO_ROOT / "schemas" / "fixtures").glob("*.json"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_validate(path, validator):
    validator(path.stem).validate(json.loads(path.read_text(encoding="utf-8")))


def test_examples_exist():
    assert {p.stem for p in EXAMPLES} == {
        "payment-request", "checker-input", "verdict", "decision-record", "receipt", "results"
    }


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_decision_record_fixtures_validate(path, validator):
    validator("decision-record").validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("name", list_scenarios())
def test_scenario_requests_validate(name, validator):
    s = Settings.load()
    scenario = load_scenario(name, s.ns)
    req = propose_payment(scenario, ScriptedLLM(scenario), "ref-1")
    assert req is not None
    req.validate()
    validator("payment-request").validate(req.to_args())
    ci = LocalGuardian(s).build_checker_input(req, 1)
    validator("checker-input").validate(ci)


def test_scenario_set_balanced():
    ns = Settings.load().ns
    scenarios = [load_scenario(n, ns) for n in list_scenarios()]
    assert all(s.name == n for s, n in zip(scenarios, list_scenarios()))
    benign = [s for s in scenarios if s.label == "benign"]
    attack = [s for s in scenarios if s.label == "attack"]
    assert len(benign) == 30
    assert len(attack) == 30
    assert {s.family for s in benign} == {"none"}
    families = [s.family for s in attack]
    assert set(families) == {
        "direct_injection", "encoded_injection", "indirect_injection",
        "memory_poisoning", "lookalike_receiver", "fake_invoice",
    }
    assert all(families.count(f) == 5 for f in set(families))
