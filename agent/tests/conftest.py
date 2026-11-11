import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from firewall_agent.config import REPO_ROOT

SCHEMA_DIR = REPO_ROOT / "schemas"


@pytest.fixture(autouse=True)
def _offline_decision_client(monkeypatch):
    # The checker subprocess inherits os.environ, and config._load_env never overrides a key that
    # is already set: empty keys keep it off the network (no decision client -> Jev unavailable).
    for key in ("TYPESAFE_API_KEY", "NEAR_AI_API_KEY", "CHECKER_LLM_MODEL"):
        monkeypatch.setenv(key, "")


@pytest.fixture(scope="session")
def schemas() -> dict:
    return {
        p.name.removesuffix(".schema.json"): json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(SCHEMA_DIR.glob("*.schema.json"))
    }


@pytest.fixture(scope="session")
def validator(schemas):
    registry = Registry().with_resources(
        [(s["$id"], Resource.from_contents(s)) for s in schemas.values()]
    )

    def make(name: str) -> Draft202012Validator:
        return Draft202012Validator(schemas[name], registry=registry)

    return make
