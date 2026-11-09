import json

import pytest

from firewall_agent.agent import propose_payment
from firewall_agent.config import REPO_ROOT, Settings
from firewall_agent.guardian import LocalGuardian
from firewall_agent.llm import ScriptedLLM
from firewall_agent.scenarios import list_scenarios, load_scenario

EXAMPLES = sorted((REPO_ROOT / "schemas" / "examples").glob("*.json"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_validate(path, validator):
    validator(path.stem).validate(json.loads(path.read_text(encoding="utf-8")))


def test_examples_exist():
    assert {p.stem for p in EXAMPLES} == {
        "payment-request", "checker-input", "verdict", "decision-record", "receipt"
    }


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
