"""firewall-nightly-e2e: end-to-end testnet runner for nightly verification (B2).

Runs a list of scenarios (default: one benign and one attack) against the Guardian on testnet
(or dry-run), verifying that the end-to-end pipeline operates properly without breakage.
Human confirmation is enforced by default in testnet mode as per AGENTS.md §4.

`release_held` is a permissionless crank that pays a held request after its window with no
re-check, so on testnet every held attack is cancelled by the owner (`cancel_held`) and the run
fails if any attack of this run is still held at the end.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .agent import propose_payment
from .config import TOKEN_DECIMALS, Settings
from .demo import make_client_ref
from .formats import amount_to_units, units_to_display
from .guardian import ContractRefusal, Decision, LocalGuardian, PollTimeout, TestnetGuardian
from .llm import NearAiLLM, ScriptedLLM
from .scenarios import load_scenario

DEFAULT_BENIGN_SCENARIO = "benign-hosting"
DEFAULT_ATTACK_SCENARIO = "attack-morse-lookalike"

_REQUEST_ID = re.compile(r"request_id=(\d+)")
_PER_PAYMENT_CAP = re.compile(r"per[- _]payment cap", re.IGNORECASE)


@dataclass
class StepResult:
    step_name: str
    scenario: str
    label: str
    family: str
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
    request_id: str | None = None
    tx_hash: str | None = None
    cancel_tx: str | None = None
    balance_delta: int | None = None
    note: str | None = None
    message: str | None = None


@dataclass
class NightlyReport:
    started_at: str
    mode: str
    guardian_id: str
    agent_id: str
    finished_at: str = ""
    preflight: dict[str, Any] = field(default_factory=dict)
    steps: list[StepResult] = field(default_factory=list)
    leftover_held: list[dict[str, Any]] = field(default_factory=list)
    all_passed: bool = False
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    duration_total_s: float = 0.0

    @property
    def benign(self) -> StepResult | None:
        return next((s for s in self.steps if s.label == "benign"), None)

    @property
    def attack(self) -> StepResult | None:
        return next((s for s in self.steps if s.label == "attack"), None)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlannedStep:
    scenario: str
    label: str
    family: str
    receiver_id: str
    amount: int


class ScenarioPlanError(Exception):
    """A scenario name or file could not be loaded; nothing was sent."""


def plan_steps(names: list[str], settings: Settings) -> list[PlannedStep]:
    """Load each scenario (label, family, receiver, amount) from its file, in the given order."""
    planned = []
    for name in names:
        try:
            sc = load_scenario(name, settings.ns)
            args = sc.scripted_tool_call["arguments"]
            planned.append(
                PlannedStep(
                    scenario=sc.name,
                    label=sc.label,
                    family=sc.family,
                    receiver_id=str(args["receiver_id"]),
                    amount=amount_to_units(str(args["amount"]), TOKEN_DECIMALS),
                )
            )
        except (SystemExit, ValueError, KeyError, TypeError, OSError) as e:
            raise ScenarioPlanError(f"cannot plan scenario {name!r}: {e}") from e
    return planned


def preflight_check(settings: Settings, mode: str, has_attack: bool = False) -> list[str]:
    """Validate prerequisites before executing runs. Returns a list of error strings."""
    errors: list[str] = []
    if mode == "testnet":
        if not settings.guardian_id:
            errors.append("GUARDIAN_ID is not configured in .env or .env.testnet")
        if not settings.agent_account_id:
            errors.append("AGENT_ACCOUNT_ID is not configured in .env or .env.testnet")
        if not settings.agent_private_key:
            errors.append("AGENT_PRIVATE_KEY is not configured in .env or .env.testnet")
        if not settings.token_id:
            errors.append("TOKEN_ID is not configured in .env or .env.testnet")
        if has_attack and not (settings.owner_account_id and settings.owner_private_key):
            errors.append("attack steps need OWNER_ACCOUNT_ID and OWNER_PRIVATE_KEY to cancel holds")
    return errors


def cancel_command(settings: Settings, request_id: Any) -> str:
    """The near-cli command that cancels a held request by hand."""
    owner = settings.owner_account_id or "<owner>"
    return (
        f"near contract call-function as-transaction {settings.guardian_id} cancel_held "
        f"json-args '{{\"request_id\":\"{request_id}\"}}' prepaid-gas '30 Tgas' "
        f"attached-deposit '0 NEAR' sign-as {owner} network-config testnet "
        "sign-with-legacy-keychain send"
    )


def receipt_by_ref_command(settings: Settings, client_ref: str) -> str:
    """The near-cli command that looks up a request by its client_ref."""
    return (
        f"near contract call-function as-read-only {settings.guardian_id} get_receipt_by_ref "
        f"json-args '{{\"client_ref\":\"{client_ref}\"}}' network-config testnet now"
    )


def cancel_held_verified(
    guardian: Any, settings: Settings, request_id: Any
) -> tuple[str | None, str | None, str | None]:
    """Cancel a held request and re-read its receipt. Returns (cancel_tx, final_status, problem).

    The cancel command is only offered when the cancel itself failed; once a cancel tx exists,
    re-sending it would not help, so a failed re-read reports the tx and an unverified status.
    """
    try:
        cancel_tx = guardian.cancel_held(request_id)
    except (Exception, SystemExit) as e:
        return None, None, (
            f"held attack could NOT be cancelled ({e}); cancel it now with: "
            f"{cancel_command(settings, request_id)}"
        )
    try:
        final_status = (guardian.view("get_receipt", {"request_id": request_id}) or {}).get("status")
    except (Exception, SystemExit) as e:
        return cancel_tx, None, f"cancel sent (tx {cancel_tx}), status unverified ({e})"
    if final_status != "refused":
        return cancel_tx, final_status, (
            f"cancel sent (tx {cancel_tx}) but receipt status is {final_status!r}, expected 'refused'"
        )
    return cancel_tx, final_status, None


def _usage(raw: Any) -> dict[str, int | str] | None:
    if not raw:
        return None
    return {
        "day": str(raw.get("day")),
        "max_per_day": int(raw["max_per_day"]),
        "used": int(raw["used"]),
    }


def collect_preflight_snapshot(
    guardian: Any, settings: Settings, planned: list[PlannedStep]
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Read-only views: checker mode, OutLayer usage, Guardian balance, payee budgets.

    Returns (snapshot, errors, warnings).
    """
    snap: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []
    try:
        mode = guardian.view("get_checker_mode")
        if isinstance(mode, dict) and "outlayer" in mode:
            snap["checker_mode"] = "outlayer"
            snap["version_key"] = (mode["outlayer"] or {}).get("version_key")
        else:
            snap["checker_mode"] = str(mode)
            snap["version_key"] = None

        usage = _usage(guardian.view("get_outlayer_usage"))
        snap["outlayer_usage_before"] = usage
        if snap["checker_mode"] == "outlayer" and usage is not None:
            remaining = usage["max_per_day"] - usage["used"]
            if remaining < len(planned):
                errors.append(
                    f"OutLayer daily request budget too low: {remaining} left "
                    f"({usage['used']}/{usage['max_per_day']} used), run needs {len(planned)}"
                )

        benign_total = sum(p.amount for p in planned if p.label == "benign")
        balance = int(guardian.view("ft_balance_of", {"account_id": settings.guardian_id}, settings.token_id) or 0)
        snap["guardian_balance"] = balance
        snap["benign_total"] = benign_total
        if balance < benign_total:
            errors.append(
                f"Guardian tUSDC balance {units_to_display(balance, TOKEN_DECIMALS)} is below the "
                f"benign total {units_to_display(benign_total, TOKEN_DECIMALS)}"
            )

        budgets: dict[str, int] = {}
        for p in planned:
            if p.label != "benign" or p.receiver_id in budgets:
                continue
            budgets[p.receiver_id] = int(guardian.view("get_payee_budget", {"receiver_id": p.receiver_id}) or 0)
        snap["payee_budgets"] = budgets
        for p in planned:
            if p.label == "benign" and p.amount > budgets[p.receiver_id]:
                warnings.append(
                    f"{p.scenario}: {units_to_display(p.amount, TOKEN_DECIMALS)} tUSDC exceeds the payee budget of "
                    f"{p.receiver_id} ({units_to_display(budgets[p.receiver_id], TOKEN_DECIMALS)}); "
                    "escrow (status held, payee_budget_hold) expected"
                )
    except (Exception, SystemExit) as e:
        errors.append(f"preflight view failed: {e}")
    snap["warnings"] = warnings
    return snap, errors, warnings


def run_scenario_step(
    scenario_name: str,
    step_title: str,
    settings: Settings,
    mode: str = "testnet",
    llm_type: str = "scripted",
    guardian_factory: Callable[[Settings], Any] | None = None,
    client_ref: str | None = None,
) -> StepResult:
    """Execute a single scenario step through payment proposal and guardian submission.

    `client_ref` lets the caller fix the on-chain ref before anything is sent, so it can
    register the step as in flight and re-resolve it if this call never returns.
    """
    start_time = time.monotonic()
    scenario = load_scenario(scenario_name, settings.ns)

    if llm_type == "scripted":
        llm = ScriptedLLM(scenario)
    else:
        llm = NearAiLLM(settings.near_ai_base_url, settings.near_ai_api_key, settings.agent_model)

    client_ref = client_ref or make_client_ref(scenario.name, mode)
    req = propose_payment(scenario, llm, client_ref=client_ref)

    def result(**kw: Any) -> StepResult:
        base: dict[str, Any] = dict(
            step_name=step_title,
            scenario=scenario.name,
            label=scenario.label,
            family=scenario.family,
            client_ref=client_ref,
            receiver_id=req.receiver_id if req else "",
            amount=req.amount if req else 0,
            amount_display=f"{units_to_display(req.amount, TOKEN_DECIMALS)} tUSDC" if req else "0",
            memo=req.memo if req else "",
            outcome=None,
            reasons=[],
            status="error",
            record_sha256=None,
            detail="",
            passed=False,
            duration_s=round(time.monotonic() - start_time, 2),
        )
        base.update(kw)
        return StepResult(**base)

    if req is None:
        return result(status="none_proposed", message="Agent proposed no payment for scenario")

    # Select Guardian implementation
    if guardian_factory is not None:
        guardian = guardian_factory(settings)
    elif mode == "dry-run":
        guardian = LocalGuardian(settings)
    else:
        guardian = TestnetGuardian(settings)

    chain = mode == "testnet"
    is_benign = scenario.label == "benign"

    try:
        bal_before: int | None = None
        if chain and is_benign:
            bal_before = int(
                guardian.view("ft_balance_of", {"account_id": req.receiver_id}, settings.token_id) or 0
            )
        decision: Decision = guardian.request_payment(req)
    except PollTimeout:
        return result(
            status="timed_out",
            message=f"timed out waiting for a verdict (client_ref={client_ref})",
        )
    except ContractRefusal as e:
        msg = str(e)
        if is_benign:
            passed, status, error = False, "refused_by_contract", msg
        elif _PER_PAYMENT_CAP.search(msg):
            passed, status, error = True, "refused_by_contract", None
        else:
            # The checker never judged this request, so it proves nothing about the attack.
            passed, status = False, "inconclusive"
            error = f"contract refused before the checker judged it ({msg}); inconclusive"
        return result(
            outcome="refused",
            reasons=["contract_refusal"],
            status=status,
            detail=msg,
            passed=passed,
            message=error,
        )
    except (Exception, SystemExit) as e:
        return result(detail=str(e), message=f"Execution error: {e}")

    match = _REQUEST_ID.search(decision.detail or "")
    request_id = match.group(1) if match else None
    tx_hash = getattr(guardian, "last_tx_hash", None) or decision.tx_hash
    status = decision.status
    note: str | None = None
    problems: list[str] = []
    cancel_tx: str | None = None
    balance_delta: int | None = None

    if "check_unavailable" in decision.reasons:
        problems.append("checker did not get a Jev answer (check_unavailable)")

    if is_benign:
        passed = decision.outcome == "allow" and status in ("paid", "would_pay", "held")
        if decision.outcome == "allow" and status == "held":
            note = "payee_budget_hold"
        elif not passed:
            problems.append(f"benign payment expected allow + paid, got outcome={decision.outcome} status={status}")
        if chain and passed and status == "paid":
            try:
                after = int(
                    guardian.view("ft_balance_of", {"account_id": req.receiver_id}, settings.token_id) or 0
                )
                balance_delta = after - (bal_before or 0)
                if balance_delta != req.amount:
                    problems.append(
                        f"receiver balance changed by {balance_delta}, expected {req.amount}"
                    )
            except (Exception, SystemExit) as e:
                problems.append(f"could not read receiver balance after payment: {e}")
    else:
        passed = decision.outcome in ("block", "hold") and status in ("refused", "held")
        if not passed:
            problems.append(f"attack was not stopped: outcome={decision.outcome} status={status}")
        if chain and status == "held":
            if request_id is None:
                problems.append(
                    "held attack could NOT be cancelled (request id unknown); it is re-resolved by "
                    f"client_ref={client_ref} at the end of the run. If that fails, look it up with: "
                    f"{receipt_by_ref_command(settings, client_ref)} then cancel it with: "
                    f"{cancel_command(settings, '<request_id>')}"
                )
            else:
                cancel_tx, final_status, err = cancel_held_verified(guardian, settings, request_id)
                if err:
                    problems.append(err)
                else:
                    status = final_status or status
                    note = "hold_cancelled"

    if problems:
        passed = False
    return result(
        outcome=decision.outcome,
        reasons=list(decision.reasons),
        status=status,
        record_sha256=decision.record_sha256,
        detail=decision.detail,
        passed=passed,
        request_id=request_id,
        tx_hash=tx_hash,
        cancel_tx=cancel_tx,
        balance_delta=balance_delta,
        note=note,
        message="; ".join(problems) if problems else None,
    )


def resolve_unresolved_attacks(guardian: Any, settings: Settings, steps: list[StepResult]) -> None:
    """Settle attack steps whose request was sent but whose request_id never came back.

    Re-resolves each one by client_ref. A receipt that is now held is cancelled like any held
    attack; a request that still cannot be found fails the step with what to check by hand.
    """
    for s in steps:
        if s.label != "attack" or s.request_id is not None or s.status not in ("timed_out", "error", "held"):
            continue
        problem: str | None = None
        try:
            rec = guardian.view("get_receipt_by_ref", {"client_ref": s.client_ref})
        except (Exception, SystemExit) as e:
            rec, problem = None, f"get_receipt_by_ref failed: {e}"
        if not rec or rec.get("request_id") is None:
            problem = problem or "no receipt found for this client_ref"
            s.passed = False
            extra = (
                f"attack request could not be resolved after the run ({problem}); client_ref={s.client_ref}. "
                f"Look it up with: {receipt_by_ref_command(settings, s.client_ref)} . "
                "If it exists and is held, cancel it from get_held before its hold window ends"
            )
            s.message = f"{s.message}; {extra}" if s.message else extra
            continue
        s.request_id = str(rec["request_id"])
        rec_status = rec.get("status")
        if rec_status != "held":
            s.passed = False
            extra = (
                f"resolved by client_ref to request_id={s.request_id} with receipt status {rec_status!r}; "
                "verdict was never observed. It may still become held: check get_held for this request_id "
                f"and cancel it before its hold window ends with: {cancel_command(settings, s.request_id)}"
            )
            s.message = f"{s.message}; {extra}" if s.message else extra
            continue
        cancel_tx, final, err = cancel_held_verified(guardian, settings, s.request_id)
        s.cancel_tx = cancel_tx
        if final:
            s.status = final
        if err:
            s.passed = False
            s.message = f"{s.message}; {err}" if s.message else err
        else:
            s.passed = False  # a timed-out attack never had its verdict observed
            s.note = "hold_cancelled_after_timeout"
            extra = f"resolved by client_ref to held request_id={s.request_id}; cancelled (tx {cancel_tx})"
            s.message = f"{s.message}; {extra}" if s.message else extra


def check_leftover_held(
    guardian: Any, settings: Settings, steps: list[StepResult]
) -> tuple[list[dict[str, Any]], str | None]:
    """Held entries that belong to an attack step of this run. Fails closed when the views fail."""
    try:
        attack_ids: set[str] = set()
        for s in steps:
            if s.label == "attack" and s.request_id is not None:
                attack_ids.add(str(s.request_id))
        held: list[dict[str, Any]] = []
        index, page = 0, 50
        while True:
            chunk = guardian.view("get_held", {"from_index": index, "limit": page}) or []
            held.extend(chunk)
            if len(chunk) < page:
                break
            index += page
        return [h for h in held if str(h.get("request_id")) in attack_ids], None
    except (Exception, SystemExit) as e:
        return [], f"could not verify that no attack is still held: {e}"


def _counts(steps: list[StepResult]) -> dict[str, dict[str, int]]:
    out = {}
    for label in ("benign", "attack"):
        group = [s for s in steps if s.label == label]
        out[label] = {
            "passed": sum(1 for s in group if s.passed),
            "failed": sum(1 for s in group if not s.passed),
        }
    return out


def run_nightly_e2e(
    settings: Settings,
    mode: str = "testnet",
    benign_scenario: str = DEFAULT_BENIGN_SCENARIO,
    attack_scenario: str = DEFAULT_ATTACK_SCENARIO,
    llm_type: str = "scripted",
    guardian_factory: Callable[[Settings], Any] | None = None,
    interactive: bool = True,
    scenarios: list[str] | None = None,
    report_path: str | None = None,
) -> NightlyReport:
    """Run the nightly end-to-end check over `scenarios` (default: the benign and attack pair)."""
    overall_start = time.monotonic()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    guardian_id = settings.guardian_id if mode == "testnet" else f"guardian.{settings.ns}"
    agent_id = settings.agent_account_id if mode == "testnet" else f"agent.{settings.ns}"
    names = list(scenarios) if scenarios else [benign_scenario, attack_scenario]
    planned = plan_steps(names, settings)

    def finish(report: NightlyReport) -> NightlyReport:
        if report_path:
            write_report(report, report_path)
            print(f"\nReport written to {report_path}")
        return report

    def aborted() -> NightlyReport:
        return NightlyReport(
            started_at=now_utc,
            finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            mode=mode,
            guardian_id=guardian_id,
            agent_id=agent_id,
            all_passed=False,
            duration_total_s=0.0,
        )

    print("=" * 72)
    print("  ECLIPSE - NIGHTLY END-TO-END TEST (B2)")
    print(f"  Time (UTC): {now_utc}")
    print(f"  Mode:       {mode.upper()}")
    print(f"  Guardian:   {guardian_id}")
    print(f"  Agent:      {agent_id}")
    for i, p in enumerate(planned, 1):
        print(f"  Step {i}:     {p.scenario} ({p.label})")
    print("=" * 72)

    # Preflight validation
    errors = preflight_check(settings, mode, has_attack=any(p.label == "attack" for p in planned))
    if errors:
        print("\n[!] Preflight check FAILED:")
        for err in errors:
            print(f"    - {err}")
        print("\nAborting nightly run.")
        return finish(aborted())

    if guardian_factory is not None:
        guardian = guardian_factory(settings)
    elif mode == "dry-run":
        guardian = LocalGuardian(settings)
    else:
        guardian = TestnetGuardian(settings)

    snapshot: dict[str, Any] = {}
    if mode == "testnet":
        snapshot, snap_errors, snap_warnings = collect_preflight_snapshot(guardian, settings, planned)
        print("\n[PREFLIGHT SNAPSHOT]")
        mode_line = snapshot.get("checker_mode")
        if snapshot.get("version_key"):
            mode_line = f"{mode_line} (version_key {snapshot['version_key']})"
        print(f"  Checker mode:    {mode_line}")
        usage = snapshot.get("outlayer_usage_before")
        if usage:
            print(f"  OutLayer usage:  {usage['used']}/{usage['max_per_day']} (day {usage['day']})")
        if "guardian_balance" in snapshot:
            print(
                f"  Guardian tUSDC:  {units_to_display(snapshot['guardian_balance'], TOKEN_DECIMALS)}"
                f" (benign total {units_to_display(snapshot['benign_total'], TOKEN_DECIMALS)})"
            )
        for rcv, bud in snapshot.get("payee_budgets", {}).items():
            print(f"  Payee budget:    {rcv} = {units_to_display(bud, TOKEN_DECIMALS)} tUSDC")
        for w in snap_warnings:
            print(f"  WARNING: {w}")
        if snap_errors:
            print("\n[!] Preflight check FAILED:")
            for err in snap_errors:
                print(f"    - ERROR: {err}")
            print("\nAborting nightly run.")
            report = aborted()
            report.preflight = snapshot
            return finish(report)

    # Human confirmation guard for testnet transactions (AGENTS.md §4)
    if mode == "testnet" and interactive:
        benign_total = sum(p.amount for p in planned if p.label == "benign")
        print("\n[HUMAN CONFIRMATION REQUIRED (AGENTS.md §4)]")
        print(f"  This script will submit {len(planned)} payment transactions to NEAR testnet:")
        for i, p in enumerate(planned, 1):
            print(f"    {i}. {p.label.capitalize()} payment: {p.scenario}")
        print(f"  Total benign payments: {units_to_display(benign_total, TOKEN_DECIMALS)} tUSDC")
        print(
            "  Held attacks are cancelled automatically with the owner key "
            f"({settings.owner_account_id or 'not needed'}): one cancel_held transaction per held attack."
        )
        print(f"  Signer account:   {agent_id}")
        print(f"  Target contract:  {guardian_id}")
        confirm = input("\nProceed with testnet execution? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Aborted by human.")
            report = aborted()
            report.preflight = snapshot
            return finish(report)

    steps: list[StepResult] = []
    run_error: str | None = None
    interrupted: KeyboardInterrupt | None = None
    try:
        for i, p in enumerate(planned, 1):
            print(f"\n>>> [{i}/{len(planned)}] Executing {p.label.capitalize()} Payment: {p.scenario} ...")
            # Registered before anything is sent: if the call never returns (Ctrl-C, escaping
            # exception), this entry is what lets the end-of-run pass re-resolve and cancel it.
            client_ref = make_client_ref(p.scenario, mode)
            steps.append(
                StepResult(
                    step_name=f"{i}_{p.label}",
                    scenario=p.scenario,
                    label=p.label,
                    family=p.family,
                    client_ref=client_ref,
                    receiver_id=p.receiver_id,
                    amount=p.amount,
                    amount_display=f"{units_to_display(p.amount, TOKEN_DECIMALS)} tUSDC",
                    memo="",
                    outcome=None,
                    reasons=[],
                    status="error",
                    record_sha256=None,
                    detail="",
                    passed=False,
                    duration_s=0.0,
                    message=f"step was in flight when the run stopped; client_ref={client_ref}",
                )
            )
            res = run_scenario_step(
                p.scenario,
                step_title=f"{i}_{p.label}",
                settings=settings,
                mode=mode,
                llm_type=llm_type,
                guardian_factory=lambda _s: guardian,
                client_ref=client_ref,
            )
            steps[-1] = res
            _print_step_summary(res)
    except KeyboardInterrupt as e:
        interrupted = e
        run_error = "interrupted (KeyboardInterrupt) before all steps finished"
    except (Exception, SystemExit) as e:
        run_error = f"run aborted by {type(e).__name__}: {e}"
    if run_error:
        print(f"\n[!] {run_error}; checking for held attacks and writing the report.")

    # Always runs, even after an error or Ctrl-C: no held attack may be left behind unreported.
    leftover: list[dict[str, Any]] = []
    held_error: str | None = None
    if mode == "testnet":
        try:
            snapshot["outlayer_usage_after"] = _usage(guardian.view("get_outlayer_usage"))
        except (Exception, SystemExit) as e:
            snapshot["outlayer_usage_after"] = None
            snapshot["outlayer_usage_after_error"] = str(e)
        resolve_unresolved_attacks(guardian, settings, steps)
        leftover, held_error = check_leftover_held(guardian, settings, steps)
        for h in leftover:
            for s in steps:
                if s.label == "attack" and str(s.request_id) == str(h.get("request_id")):
                    s.passed = False
                    extra = f"attack is still held after the run; cancel it with: {cancel_command(settings, s.request_id)}"
                    s.message = f"{s.message}; {extra}" if s.message else extra

    all_passed = (
        bool(steps)
        and all(s.passed for s in steps)
        and not leftover
        and held_error is None
        and run_error is None
    )
    report = NightlyReport(
        started_at=now_utc,
        finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        mode=mode,
        guardian_id=guardian_id,
        agent_id=agent_id,
        preflight=snapshot,
        steps=steps,
        leftover_held=leftover,
        all_passed=all_passed,
        counts=_counts(steps),
        duration_total_s=round(time.monotonic() - overall_start, 2),
    )
    if held_error:
        report.preflight["held_check_error"] = held_error
    if run_error:
        report.preflight["run_error"] = run_error

    _print_final_summary(report)
    finish(report)
    if interrupted is not None:
        raise interrupted
    return report


def _print_step_summary(res: StepResult) -> None:
    mark = "[PASS]" if res.passed else "[FAIL]"
    print(
        f"    {mark} {res.scenario} ({res.label}) outcome={res.outcome} "
        f"status={res.status} reasons={','.join(res.reasons)}"
    )
    print(f"           Proposed: {res.amount_display} -> {res.receiver_id} (memo: \"{res.memo}\")")
    if res.request_id or res.tx_hash:
        print(f"           Request:  id={res.request_id} tx={res.tx_hash}")
    if res.record_sha256:
        print(f"           Record:   {res.record_sha256}")
    if res.cancel_tx:
        print(f"           Cancel:   held attack cancelled, tx={res.cancel_tx}, final status={res.status}")
    if res.note == "payee_budget_hold":
        print("           Escrow:   payee_budget_hold (allow, held by the payee budget; not cancelled)")
    if res.balance_delta is not None:
        print(f"           Balance:  receiver tUSDC {res.balance_delta:+d} base units")
    if res.message:
        print(f"           Error:    {res.message}")
    print(f"           Duration: {res.duration_s}s")


def _print_final_summary(report: NightlyReport) -> None:
    print("\n" + "=" * 72)
    print("  NIGHTLY RUN SUMMARY")
    print("=" * 72)
    for i, s in enumerate(report.steps, 1):
        print(f"  {i}. {s.label.capitalize()} ({s.scenario}): {'PASS' if s.passed else 'FAIL'} [{s.status}]")
    for label, c in report.counts.items():
        print(f"  {label}: {c['passed']} passed, {c['failed']} failed")
    for h in report.leftover_held:
        print(f"  STILL HELD: request {h.get('request_id')} -> {h.get('receiver_id')}")
    if report.preflight.get("held_check_error"):
        print(f"  ERROR: {report.preflight['held_check_error']}")
    print(f"  Total Duration: {report.duration_total_s}s")
    print(f"  Overall Status: {'SUCCESS' if report.all_passed else 'FAILURE'}")
    print("=" * 72)


def write_report(report: NightlyReport, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="firewall-nightly-e2e",
        description="Nightly end-to-end testnet runner over a list of scenarios (B2).",
    )
    parser.add_argument(
        "--mode",
        choices=["testnet", "dry-run"],
        default="testnet",
        help="Run against live testnet (default) or offline dry-run.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        metavar="NAME",
        help="Scenario to run; repeatable and comma-separated, executed in order. "
        "Overrides --benign-scenario/--attack-scenario.",
    )
    parser.add_argument(
        "--benign-scenario",
        default=DEFAULT_BENIGN_SCENARIO,
        help=f"Benign scenario name when no --scenario is given (default: {DEFAULT_BENIGN_SCENARIO})",
    )
    parser.add_argument(
        "--attack-scenario",
        default=DEFAULT_ATTACK_SCENARIO,
        help=f"Attack scenario name when no --scenario is given (default: {DEFAULT_ATTACK_SCENARIO})",
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
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write the full JSON report to PATH (parent directories are created).",
    )

    args = parser.parse_args(argv)
    settings = Settings.load()
    scenarios = [n.strip() for arg in args.scenario for n in arg.split(",") if n.strip()]

    try:
        report = run_nightly_e2e(
            settings=settings,
            mode=args.mode,
            benign_scenario=args.benign_scenario,
            attack_scenario=args.attack_scenario,
            llm_type=args.llm,
            interactive=not args.non_interactive,
            scenarios=scenarios or None,
            report_path=args.report,
        )
    except ScenarioPlanError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print("\n" + json.dumps(report.to_dict(), indent=2))

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
