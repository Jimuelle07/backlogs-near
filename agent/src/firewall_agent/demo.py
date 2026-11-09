"""firewall-demo: the agent proposes a payment from an 'email'; the guardian decides."""

from __future__ import annotations

import argparse
import sys

from .agent import propose_payment
from .config import REPO_ROOT, TOKEN_DECIMALS, Settings
from .formats import units_to_display
from .guardian import LocalGuardian, TestnetGuardian
from .llm import NearAiLLM, ScriptedLLM
from .scenarios import list_scenarios, load_scenario


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="firewall-demo", description=__doc__)
    ap.add_argument("--scenario", required=True, help=f"one of: {', '.join(list_scenarios())}")
    ap.add_argument("--mode", choices=["dry-run", "testnet"], default="dry-run")
    ap.add_argument("--llm", choices=["scripted", "near-ai"], default="scripted")
    args = ap.parse_args(argv)

    s = Settings.load()
    scenario = load_scenario(args.scenario, s.ns)
    if args.llm == "scripted":
        llm = ScriptedLLM(scenario)
    else:
        llm = NearAiLLM(s.near_ai_base_url, s.near_ai_api_key, s.agent_model)

    print(f"scenario: {scenario.name} ({scenario.label})")
    req = propose_payment(scenario, llm, client_ref=f"{scenario.name}-1")
    if req is None:
        print("proposed: none")
        return 0
    print(
        f"proposed: pay {req.amount} units ({units_to_display(req.amount, TOKEN_DECIMALS)} tUSDC) "
        f'to {req.receiver_id} memo="{req.memo}"'
    )
    guardian = LocalGuardian(s) if args.mode == "dry-run" else TestnetGuardian(s)
    d = guardian.request_payment(req)
    print(f"verdict: {d.outcome} reasons={','.join(d.reasons)} record={d.record_sha256}")
    print(f"action: {d.status}")
    if args.mode == "dry-run" and d.record_path is not None:
        try:
            shown = d.record_path.relative_to(REPO_ROOT)
        except ValueError:
            shown = d.record_path
        print(f"record_file: {shown.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
