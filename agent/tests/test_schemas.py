import json
import re

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
    assert len(benign) == 150
    assert len(attack) == 150
    assert {s.family for s in benign} == {"none"}
    families = [s.family for s in attack]
    assert set(families) == {
        "direct_injection", "encoded_injection", "indirect_injection",
        "memory_poisoning", "lookalike_receiver", "fake_invoice",
    }
    assert all(families.count(f) == 25 for f in set(families))


def _default_payees() -> set[str]:
    src = (REPO_ROOT / "checker" / "src" / "counterparty.rs").read_text(encoding="utf-8")
    body = src.split("pub fn with_default_payees", 1)[1].split("];", 1)[0]
    return set(re.findall(r'"([a-z0-9._-]+)"', body))


def test_generated_benign_receivers_are_default_payees():
    payees = _default_payees()
    assert len(payees) >= 20
    names = [n for n in list_scenarios() if n.startswith("benign-gen-")]
    assert len(names) == 120
    for n in names:
        s = load_scenario(n, "demo.testnet")
        receiver = s.scripted_tool_call["arguments"]["receiver_id"]
        assert receiver in payees, f"{n}: {receiver} not a default payee"
        amount = s.scripted_tool_call["arguments"]["amount"]
        assert amount.isdigit() and 1 <= int(amount) <= 150
        assert s.scripted_tool_call["arguments"]["memo"] in s.inbox[0].text
        assert amount in s.user_request


def test_redteam_set_is_attack_only():
    names = list_scenarios("redteam")
    assert len(names) >= 15
    ns = Settings.load().ns
    for n in names:
        assert load_scenario(n, ns, "redteam").label == "attack"


def test_unknown_scenario_set_rejected():
    with pytest.raises(ValueError, match=r"unknown scenario set 'nope'; expected main\|redteam\|external\|paysim"):
        list_scenarios("nope")
    with pytest.raises(ValueError, match="expected main\\|redteam\\|external\\|paysim"):
        load_scenario("x", "demo.testnet", "nope")


def test_external_set_valid(validator):
    names = list_scenarios("external")
    assert names
    s = Settings.load()
    scenarios = [load_scenario(n, s.ns, "external") for n in names]
    for scenario in scenarios:
        req = propose_payment(scenario, ScriptedLLM(scenario), "ref-1")
        assert req is not None
        req.validate()
        validator("payment-request").validate(req.to_args())
    benign = [x for x in scenarios if x.label == "benign"]
    attack = [x for x in scenarios if x.label == "attack"]
    assert len(benign) == len(attack)
    assert all(x.scripted_tool_call["arguments"]["receiver_id"].startswith("ext-") for x in attack)


def test_external_set_not_in_main():
    assert not [n for n in list_scenarios("main") if n.startswith("ext-")]


def test_external_amount_matches_invoice():
    """Every external scenario pays the invoice amount stated in inbox[0]; the label must not be readable from an amount mismatch."""
    import re

    s = Settings.load()
    names = list_scenarios("external")
    assert names
    for n in names:
        scenario = load_scenario(n, s.ns, "external")
        stated = re.search(r"amount due (\d+)\.00 USDC", scenario.inbox[0].text)
        assert stated, n
        assert scenario.scripted_tool_call["arguments"]["amount"] == stated.group(1), n
