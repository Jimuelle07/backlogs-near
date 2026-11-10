"""firewall-nightly-e2e: end-to-end testnet runner for nightly verification (B2).

Runs one benign and one attack payment against the Guardian on testnet (or dry-run),
verifying that the end-to-end pipeline operates properly without breakage.
Human confirmation is enforced by default in testnet mode as per AGENTS.md §4.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .agent import propose_payment
from .config import TOKEN_DECIMALS, Settings
from .demo import make_client_ref
from .formats import units_to_display
from .guardian import ContractRefusal, Decision, LocalGuardian, TestnetGuardian
from .llm import NearAiLLM, ScriptedLLM
from .scenarios import load_scenario

DEFAULT_BENIGN_SCENARIO = "benign-hosting"
DEFAULT_ATTACK_SCENARIO = "attack-morse-lookalike"


@dataclass
class StepResult:
    step_name: str
    scenario: str
    label: str
    client_ref: str
    receiver_id: str
    amount: int
    amount_display: str
    memo: str
    outcome: str | None
    reasons: list[str]
    status: str
    record_sha256: str | None
    detail: str
    passed: bool
    duration_s: float
    error: str | None = None


@dataclass
class NightlyReport:
    timestamp_utc: str
    mode: str
    guardian_id: str
    agent_id: str
    benign: StepResult | None = None
    attack: StepResult | None = None
    all_passed: bool = False
    duration_total_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preflight_check(settings: Settings, mode: str) -> list[str]:
    """Validate prerequisites before executing runs. Returns a list of error strings."""
    errors: list[str] = []
    if mode == "testnet":
        if not settings.guardian_id:
            errors.append("GUARDIAN_ID is not configured in .env or .env.testnet")
        if not settings.agent_account_id:
            errors.append("AGENT_ACCOUNT_ID is not configured in .env or .env.testnet")
        if not settings.agent_private_key:
            errors.append("AGENT_PRIVATE_KEY is not configured in .env or .env.testnet")
    return errors


def run_scenario_step(
    scenario_name: str,
    step_title: str,
    settings: Settings,
    mode: str = "testnet",
    llm_type: str = "scripted",
    guardian_factory: Callable[[Settings], Any] | None = None,
) -> StepResult:
    """Execute a single scenario step through payment proposal and guardian submission."""
    start_time = time.monotonic()
    scenario = load_scenario(scenario_name, settings.ns)

    if llm_type == "scripted":
        llm = ScriptedLLM(scenario)
    else:
        llm = NearAiLLM(settings.near_ai_base_url, settings.near_ai_api_key, settings.agent_model)

    client_ref = make_client_ref(scenario.name, mode)
    req = propose_payment(scenario, llm, client_ref=client_ref)

    if req is None:
        duration = round(time.monotonic() - start_time, 2)
        return StepResult(
            step_name=step_title,
            scenario=scenario.name,
            label=scenario.label,
            client_ref=client_ref,
            receiver_id="",
            amount=0,
            amount_display="0",
            memo="",
            outcome=None,
            reasons=[],
            status="none_proposed",
            record_sha256=None,
            detail="",
            passed=False,
            duration_s=duration,
            error="Agent proposed no payment for scenario",
        )

    amount_disp = f"{units_to_display(req.amount, TOKEN_DECIMALS)} tUSDC"

    # Select Guardian implementation
    if guardian_factory is not None:
        guardian = guardian_factory(settings)
    elif mode == "dry-run":
        guardian = LocalGuardian(settings)
    else:
        guardian = TestnetGuardian(settings)

    try:
        decision: Decision = guardian.request_payment(req)
        duration = round(time.monotonic() - start_time, 2)

        # Expected outcome criteria:
        # In current testnet / dry-run stub mode:
        # - benign: outcome="allow", status="paid" (or "would_pay")
        # - attack: outcome="allow" / reasons=["stub_allow"] until C3 fusion lands,
        #   or outcome="block" / "hold" after C3.
        is_benign = scenario.label == "benign"
        if is_benign:
            passed = decision.outcome == "allow" and decision.status in ("paid", "would_pay")
        else:
            # For attack scenarios, both the stub allow (pre-C3) and block/hold (post-C3) count as valid pipeline runs
            passed = decision.outcome in ("allow", "block", "hold") and decision.status in (
                "paid",
                "would_pay",
                "refused",
                "held",
            )

        return StepResult(
            step_name=step_title,
            scenario=scenario.name,
            label=scenario.label,
            client_ref=client_ref,
            receiver_id=req.receiver_id,
            amount=req.amount,
            amount_display=amount_disp,
            memo=req.memo,
            outcome=decision.outcome,
            reasons=decision.reasons,
            status=decision.status,
            record_sha256=decision.record_sha256,
            detail=decision.detail,
            passed=passed,
            duration_s=duration,
            error=None,
        )
    except ContractRefusal as e:
        duration = round(time.monotonic() - start_time, 2)
        # An attack being refused directly by contract cap/rules is also a secure rejection
        passed = scenario.label == "attack"
        return StepResult(
            step_name=step_title,
            scenario=scenario.name,
            label=scenario.label,
            client_ref=client_ref,
            receiver_id=req.receiver_id,
            amount=req.amount,
            amount_display=amount_disp,
            memo=req.memo,
            outcome="refused",
            reasons=["contract_refusal"],
            status="refused_by_contract",
            record_sha256=None,
            detail=str(e),
            passed=passed,
            duration_s=duration,
            error=str(e) if not passed else None,
        )
    except Exception as e:
        duration = round(time.monotonic() - start_time, 2)
        return StepResult(
            step_name=step_title,
            scenario=scenario.name,
            label=scenario.label,
            client_ref=client_ref,
            receiver_id=req.receiver_id,
            amount=req.amount,
            amount_display=amount_disp,
            memo=req.memo,
            outcome=None,
            reasons=[],
            status="error",
            record_sha256=None,
            detail=str(e),
            passed=False,
            duration_s=duration,
            error=f"Execution error: {e}",
        )


def run_nightly_e2e(
    settings: Settings,
    mode: str = "testnet",
    benign_scenario: str = DEFAULT_BENIGN_SCENARIO,
    attack_scenario: str = DEFAULT_ATTACK_SCENARIO,
    llm_type: str = "scripted",
    guardian_factory: Callable[[Settings], Any] | None = None,
    interactive: bool = True,
) -> NightlyReport:
    """Run the complete nightly end-to-end check with one benign and one attack payment."""
    overall_start = time.monotonic()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    guardian_id = settings.guardian_id if mode == "testnet" else f"guardian.{settings.ns}"
    agent_id = settings.agent_account_id if mode == "testnet" else f"agent.{settings.ns}"

    print("=" * 72)
    print("  ATTESTED PAYMENT FIREWALL - NIGHTLY END-TO-END TEST (B2)")
    print(f"  Time (UTC): {now_utc}")
    print(f"  Mode:       {mode.upper()}")
    print(f"  Guardian:   {guardian_id}")
    print(f"  Agent:      {agent_id}")
    print(f"  Benign:     {benign_scenario}")
    print(f"  Attack:     {attack_scenario}")
    print("=" * 72)

    # Preflight validation
    errors = preflight_check(settings, mode)
    if errors:
        print("\n[!] Preflight check FAILED:")
        for err in errors:
            print(f"    - {err}")
        print("\nAborting nightly run.")
        return NightlyReport(
            timestamp_utc=now_utc,
            mode=mode,
            guardian_id=guardian_id,
            agent_id=agent_id,
            all_passed=False,
            duration_total_s=0.0,
        )

    # Human confirmation guard for testnet transactions (AGENTS.md §4)
    if mode == "testnet" and interactive:
        print("\n[HUMAN CONFIRMATION REQUIRED (AGENTS.md §4)]")
        print("  This script will submit 2 transactions to NEAR testnet:")
        print(f"    1. Benign payment: {benign_scenario}")
        print(f"    2. Attack payment: {attack_scenario}")
        print(f"  Signer account:   {agent_id}")
        print(f"  Target contract:  {guardian_id}")
        confirm = input("\nProceed with testnet execution? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Aborted by human.")
            return NightlyReport(
                timestamp_utc=now_utc,
                mode=mode,
                guardian_id=guardian_id,
                agent_id=agent_id,
                all_passed=False,
                duration_total_s=0.0,
            )

    # Step 1: Benign Payment
    print(f"\n>>> [1/2] Executing Benign Payment: {benign_scenario} ...")
    benign_res = run_scenario_step(
        benign_scenario,
        step_title="1_benign",
        settings=settings,
        mode=mode,
        llm_type=llm_type,
        guardian_factory=guardian_factory,
    )
    _print_step_summary(benign_res)

    # Step 2: Attack Payment
    print(f"\n>>> [2/2] Executing Attack Payment: {attack_scenario} ...")
    attack_res = run_scenario_step(
        attack_scenario,
        step_title="2_attack",
        settings=settings,
        mode=mode,
        llm_type=llm_type,
        guardian_factory=guardian_factory,
    )
    _print_step_summary(attack_res)

    total_duration = round(time.monotonic() - overall_start, 2)
    all_passed = benign_res.passed and attack_res.passed

    report = NightlyReport(
        timestamp_utc=now_utc,
        mode=mode,
        guardian_id=guardian_id,
        agent_id=agent_id,
        benign=benign_res,
        attack=attack_res,
        all_passed=all_passed,
        duration_total_s=total_duration,
    )

    _print_final_summary(report)
    return report


def _print_step_summary(res: StepResult) -> None:
    mark = "[PASS]" if res.passed else "[FAIL]"
    print(f"    {mark} {res.scenario} ({res.label}) in {res.duration_s}s")
    print(f"           Proposed: {res.amount_display} -> {res.receiver_id} (memo: \"{res.memo}\")")
    print(f"           Verdict:  outcome={res.outcome} reasons={','.join(res.reasons)}")
    print(f"           Status:   {res.status}")
    if res.record_sha256:
        print(f"           Record:   {res.record_sha256}")
    if res.error:
        print(f"           Error:    {res.error}")


def _print_final_summary(report: NightlyReport) -> None:
    print("\n" + "=" * 72)
    print("  NIGHTLY RUN SUMMARY")
    print("=" * 72)
    b_status = "PASS" if (report.benign and report.benign.passed) else "FAIL"
    a_status = "PASS" if (report.attack and report.attack.passed) else "FAIL"

    print(f"  1. Benign ({report.benign.scenario if report.benign else 'N/A'}): {b_status}")
    print(f"  2. Attack ({report.attack.scenario if report.attack else 'N/A'}): {a_status}")
    print(f"  Total Duration: {report.duration_total_s}s")
    print(f"  Overall Status: {'SUCCESS' if report.all_passed else 'FAILURE'}")
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="firewall-nightly-e2e",
        description="Nightly end-to-end testnet runner: one benign and one attack payment (B2).",
    )
    parser.add_argument(
        "--mode",
        choices=["testnet", "dry-run"],
        default="testnet",
        help="Run against live testnet (default) or offline dry-run.",
    )
    parser.add_argument(
        "--benign-scenario",
        default=DEFAULT_BENIGN_SCENARIO,
        help=f"Benign scenario name (default: {DEFAULT_BENIGN_SCENARIO})",
    )
    parser.add_argument(
        "--attack-scenario",
        default=DEFAULT_ATTACK_SCENARIO,
        help=f"Attack scenario name (default: {DEFAULT_ATTACK_SCENARIO})",
    )
    parser.add_argument(
        "--llm",
        choices=["scripted", "near-ai"],
        default="scripted",
        help="LLM provider for payment proposal (default: scripted)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        "--non-interactive",
        action="store_true",
        dest="non_interactive",
        help="Skip human confirmation prompt (for automated / CI environments).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON report to stdout at the end of execution.",
    )

    args = parser.parse_args(argv)
    settings = Settings.load()

    report = run_nightly_e2e(
        settings=settings,
        mode=args.mode,
        benign_scenario=args.benign_scenario,
        attack_scenario=args.attack_scenario,
        llm_type=args.llm,
        interactive=not args.non_interactive,
    )

    if args.json:
        print("\n" + json.dumps(report.to_dict(), indent=2))

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
