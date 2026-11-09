"""Scenario loader: agent/scenarios/<name>.json with {NS} substitution."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import AGENT_DIR
from .formats import ContextItem

SCENARIO_DIR = AGENT_DIR / "scenarios"


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


def list_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.json"))


def load_scenario(name: str, ns: str) -> Scenario:
    path = SCENARIO_DIR / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"unknown scenario {name!r}; available: {', '.join(list_scenarios())}")
    raw = _subst(json.loads(path.read_text(encoding="utf-8")), ns)
    if raw["label"] not in ("benign", "attack"):
        raise ValueError(f"{path.name}: label must be benign|attack")
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
