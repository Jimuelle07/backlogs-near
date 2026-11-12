"""Scenario loader: agent/scenarios/<name>.json with {NS} substitution."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import AGENT_DIR, REPO_ROOT
from .formats import ContextItem

SCENARIO_DIR = AGENT_DIR / "scenarios"
PAYSIM_DIR = REPO_ROOT / "data" / "external" / "derived" / "paysim"
SCENARIO_SETS = {
    "main": SCENARIO_DIR,
    "redteam": SCENARIO_DIR / "redteam",
    "external": SCENARIO_DIR / "external",
    "paysim": PAYSIM_DIR,
}
#: Checker env overrides a scenario set needs (merged into every preset by firewall-eval).
SCENARIO_SET_ENV: dict[str, dict[str, str]] = {
    "paysim": {"AGENT_PROFILE_PATH": str(PAYSIM_DIR / "profile.json")},
}
ATTACK_FAMILIES = (
    "direct_injection",
    "encoded_injection",
    "indirect_injection",
    "memory_poisoning",
    "lookalike_receiver",
    "fake_invoice",
)


@dataclass
class Scenario:
    name: str
    label: str
    family: str
    user_request: str
    inbox: list[ContextItem]
    scripted_tool_call: dict  # {"name": "pay_invoice", "arguments": {...}}


def _subst(value, ns: str):
    if isinstance(value, str):
        return value.replace("{NS}", ns)
    if isinstance(value, list):
        return [_subst(v, ns) for v in value]
    if isinstance(value, dict):
        return {k: _subst(v, ns) for k, v in value.items()}
    return value


def _set_dir(scenario_set: str):
    try:
        d = SCENARIO_SETS[scenario_set]
    except KeyError:
        raise ValueError(
            f"unknown scenario set {scenario_set!r}; expected {'|'.join(SCENARIO_SETS)}"
        ) from None
    if scenario_set == "paysim" and not d.is_dir():
        raise SystemExit("paysim set not built; run: uv run python tools/build_paysim_set.py")
    return d


def list_scenarios(scenario_set: str = "main") -> list[str]:
    return sorted(p.stem for p in _set_dir(scenario_set).glob("*.json") if p.stem != "profile")


def load_scenario(name: str, ns: str, scenario_set: str = "main") -> Scenario:
    path = _set_dir(scenario_set) / f"{name}.json"
    if not path.is_file():
        raise SystemExit(
            f"unknown scenario {name!r}; available: {', '.join(list_scenarios(scenario_set))}"
        )
    raw = _subst(json.loads(path.read_text(encoding="utf-8")), ns)
    if raw["label"] not in ("benign", "attack"):
        raise ValueError(f"{path.name}: label must be benign|attack")
    if raw["label"] == "benign" and raw["family"] != "none":
        raise ValueError(f"{path.name}: benign scenarios must have family none")
    if raw["label"] == "attack" and raw["family"] not in ATTACK_FAMILIES:
        raise ValueError(f"{path.name}: attack family must be one of {', '.join(ATTACK_FAMILIES)}")
    call = raw["scripted_tool_call"]
    if call.get("name") != "pay_invoice":
        raise ValueError(f"{path.name}: scripted_tool_call.name must be pay_invoice")
    for k in ("receiver_id", "amount", "memo"):
        if k not in call["arguments"]:
            raise ValueError(f"{path.name}: scripted_tool_call.arguments missing {k}")
    return Scenario(
        name=raw["name"],
        label=raw["label"],
        family=raw["family"],
        user_request=raw["user_request"],
        inbox=[ContextItem.from_dict(i) for i in raw["inbox"]],
        scripted_tool_call=call,
    )
