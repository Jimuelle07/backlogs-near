"""firewall-demo: the agent proposes a payment from an 'email'; the guardian decides."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from .agent import propose_payment
from .config import REPO_ROOT, TOKEN_DECIMALS, Settings
from .formats import units_to_display
from .guardian import ContractRefusal, LocalGuardian, TestnetGuardian
from .llm import NearAiLLM, ScriptedLLM
from .scenarios import list_scenarios, load_scenario


def make_client_ref(scenario_name: str, mode: str, now_ns: int | None = None) -> str:
    """Dry-run keeps a fixed ref; testnet must be unique per run (the contract rejects duplicates).

    Result matches the contract's `^[A-Za-z0-9_-]{1,64}$`.
    """
    if mode == "dry-run":
        return f"{scenario_name}-1"
    suffix = str(time.time_ns() if now_ns is None else now_ns)
    return f"{scenario_name[: 64 - 1 - len(suffix)]}-{suffix}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="firewall-demo", description=__doc__)
    ap.add_argument("--scenario", required=True, help=f"one of: {', '.join(list_scenarios())}")
    ap.add_argument("--mode", choices=["dry-run", "testnet"], default="dry-run")
    ap.add_argument("--llm", choices=["scripted", "near-ai"], default="scripted")
    ap.add_argument(
        "--reset-spend", action="store_true", help="dry-run only: clear today's daily spend first"
    )
    args = ap.parse_args(argv)

    s = Settings.load()
    scenario = load_scenario(args.scenario, s.ns)
    if args.llm == "scripted":
        llm = ScriptedLLM(scenario)
    else:
        llm = NearAiLLM(s.near_ai_base_url, s.near_ai_api_key, s.agent_model)

    print(f"scenario: {scenario.name} ({scenario.label})")
    req = propose_payment(scenario, llm, client_ref=make_client_ref(scenario.name, args.mode))
    if req is None:
        print("proposed: none")
        return 0
    print(
        f"proposed: pay {req.amount} units ({units_to_display(req.amount, TOKEN_DECIMALS)} tUSDC) "
        f'to {req.receiver_id} memo="{req.memo}"'
    )
    guardian = LocalGuardian(s) if args.mode == "dry-run" else TestnetGuardian(s)
    if args.reset_spend:
        if args.mode == "dry-run":
            guardian.reset_spend()
        else:
            print("note: --reset-spend only applies to dry-run; ignored")
    try:
        d = guardian.request_payment(req)
    except ContractRefusal as e:
        print(f"refused by contract: {e}")
        if args.mode == "dry-run" and str(e) == "Daily cap reached":
            print(
                "dry-run: daily spend is kept across runs like the contract; "
                "rerun with --reset-spend to start a fresh day"
            )
        return 1
    print(f"verdict: {d.outcome} reasons={','.join(d.reasons)} record={d.record_sha256}")
    print(f"action: {d.status}")
    if d.release_at_ns is not None:
        release = datetime.fromtimestamp(d.release_at_ns // 10**9, tz=timezone.utc)
        print(f"held until {release.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if args.mode == "dry-run" and d.record_path is not None:
        try:
            shown = d.record_path.relative_to(REPO_ROOT)
        except ValueError:
            shown = d.record_path
        print(f"record_file: {shown.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
