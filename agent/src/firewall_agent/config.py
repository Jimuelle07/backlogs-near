"""Settings loaded from the repo-root .env, then .env.testnet (no override)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# agent/src/firewall_agent/config.py -> parents[3] == repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = REPO_ROOT / "agent"

TOKEN_DECIMALS = 6


def _load_env() -> None:
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(REPO_ROOT / ".env.testnet", override=False)


def _path(value: str, default: Path) -> Path:
    if not value:
        return default
    p = Path(value)
    return p if p.is_absolute() else REPO_ROOT / p


@dataclass(frozen=True)
class Settings:
    ns: str
    checker_bin: Path
    checker_record_dir: Path
    near_ai_api_key: str
    near_ai_base_url: str
    agent_model: str
    typesafe_api_key: str
    near_network: str
    near_rpc_url: str
    owner_account_id: str
    owner_private_key: str
    guardian_id: str
    token_id: str
    agent_account_id: str
    agent_private_key: str
    checker_account_id: str
    checker_private_key: str

    @classmethod
    def load(cls) -> "Settings":
        _load_env()
        e = os.environ.get
        exe = "checker.exe" if sys.platform == "win32" else "checker"
        ns = e("OWNER_ACCOUNT_ID") or "demo.testnet"
        return cls(
            ns=ns,
            checker_bin=_path(e("CHECKER_BIN", ""), REPO_ROOT / "target" / "release" / exe),
            checker_record_dir=_path(e("CHECKER_RECORD_DIR", ""), REPO_ROOT / "data" / "decisions"),
            near_ai_api_key=e("NEAR_AI_API_KEY", ""),
            near_ai_base_url=e("NEAR_AI_BASE_URL", "https://cloud-api.near.ai/v1"),
            agent_model=e("AGENT_MODEL", ""),
            typesafe_api_key=e("TYPESAFE_API_KEY", ""),
            near_network=e("NEAR_NETWORK", "testnet"),
            near_rpc_url=e("NEAR_RPC_URL", ""),
            owner_account_id=e("OWNER_ACCOUNT_ID", ""),
            owner_private_key=e("OWNER_PRIVATE_KEY", ""),
            guardian_id=e("GUARDIAN_ID", ""),
            token_id=e("TOKEN_ID", ""),
            agent_account_id=e("AGENT_ACCOUNT_ID", ""),
            agent_private_key=e("AGENT_PRIVATE_KEY", ""),
            checker_account_id=e("CHECKER_ACCOUNT_ID", ""),
            checker_private_key=e("CHECKER_PRIVATE_KEY", ""),
        )
