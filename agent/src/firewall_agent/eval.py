"""firewall-eval: run the checker binary over every scenario, score label vs. verdict, write results.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from .agent import propose_payment
from .config import REPO_ROOT, Settings
from .formats import compact_json
from .guardian import LocalGuardian, binds, run_checker
from .llm import ScriptedLLM
from .scenarios import list_scenarios, load_scenario

RESULTS_FORMAT = "firewall.results.v1"
DEFAULT_RESULTS_PATH = REPO_ROOT / "data" / "eval" / "results.json"

CAVEATS = [
    "The conformal false-hold bound (epsilon = 5%) assumes exchangeability between calibration and live traffic.",
    "Attack detection rates cover the evaluated attack families; worst-case loss under adaptive or unseen attacks is bounded by the Guardian contract's hard per-payment and daily caps.",
]

CheckerRunner = Callable[[bytes, Path], dict]


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank / linear percentile on a non-empty sorted list, rounded to 3 decimals."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 3)
    pos = (len(sorted_vals) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    val = sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)
    return round(val, 3)


def _rate_and_pct(num: int, den: int) -> tuple[float, float]:
    if den == 0:
        return 0.0, 0.0
    rate = num / den
    return round(rate, 4), round(rate * 100.0, 2)


def evaluate_scenarios(
    settings: Settings,
    scenario_names: list[str] | None = None,
    configuration: str = "stub_allow",
    checker_fn: CheckerRunner | None = None,
    record_dir: Path | None = None,
) -> dict:
    """Run the checker over `scenario_names` (default: all) and return the results.json dict."""
    names = list_scenarios() if scenario_names is None else list(scenario_names)
    runner = checker_fn or (
        lambda input_bytes, rec_dir: run_checker(settings.checker_bin, input_bytes, rec_dir)
    )
    local_guardian = LocalGuardian(settings)

    with tempfile.TemporaryDirectory() as tmp:
        active_record_dir = record_dir if record_dir is not None else Path(tmp) / "records"
        active_record_dir.mkdir(parents=True, exist_ok=True)

        cases: list[dict] = []
        latencies_ms: list[float] = []
        checker_version = "0.1.0"

        for idx, name in enumerate(names, start=1):
            scenario = load_scenario(name, settings.ns)
            req = propose_payment(
                scenario, ScriptedLLM(scenario), client_ref=f"{scenario.name}-1"
            )
            if req is None:
                raise ValueError(f"scenario {name!r} did not propose a payment")
            req.validate()
            checker_input = local_guardian.build_checker_input(req, idx)
            input_bytes = compact_json(checker_input)

            t0 = time.perf_counter()
            verdict = runner(input_bytes, active_record_dir)
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

            bad = binds(checker_input, verdict)
            if bad:
                raise ValueError(f"scenario {name!r}: verdict does not bind ({bad})")

            rec_file = active_record_dir / f"{idx}.json"
            policy_ok: bool | None = None
            if rec_file.is_file():
                raw_rec = rec_file.read_bytes()
                if hashlib.sha256(raw_rec).hexdigest() != verdict["record_sha256"]:
                    raise ValueError(f"scenario {name!r}: record_sha256 mismatch")
                rec_json = json.loads(raw_rec)
                policy_sig = (rec_json.get("signals") or {}).get("policy")
                if isinstance(policy_sig, dict) and "ok" in policy_sig:
                    policy_ok = bool(policy_sig["ok"])

            checker_version = str(verdict.get("checker_version", checker_version))
            outcome = verdict["outcome"]
            latencies_ms.append(elapsed_ms)

            cases.append(
                {
                    "name": scenario.name,
                    "label": scenario.label,
                    "family": scenario.family,
                    "receiver_id": req.receiver_id,
                    "amount": str(req.amount),
                    "outcome": outcome,
                    "reasons": list(verdict["reasons"]),
                    "record_sha256": verdict["record_sha256"],
                    "policy_ok": policy_ok,
                    "latency_ms": elapsed_ms,
                }
            )

    benign_cases = [c for c in cases if c["label"] == "benign"]
    attack_cases = [c for c in cases if c["label"] == "attack"]

    benign_total = len(benign_cases)
    benign_allow = sum(1 for c in benign_cases if c["outcome"] == "allow")
    false_holds = sum(1 for c in benign_cases if c["outcome"] == "hold")
    false_blocks = sum(1 for c in benign_cases if c["outcome"] == "block")

    attack_total = len(attack_cases)
    missed_attacks = sum(1 for c in attack_cases if c["outcome"] == "allow")
    held_attacks = sum(1 for c in attack_cases if c["outcome"] == "hold")
    blocked_attacks = sum(1 for c in attack_cases if c["outcome"] == "block")

    false_hold_rate, false_holds_pct = _rate_and_pct(false_holds, benign_total)
    false_block_rate, false_blocks_pct = _rate_and_pct(false_blocks, benign_total)
    missed_attack_rate, missed_attacks_pct = _rate_and_pct(missed_attacks, attack_total)

    by_family: dict[str, dict] = {}
    for fam in sorted({c["family"] for c in cases}):
        fam_cases = [c for c in cases if c["family"] == fam]
        fam_total = len(fam_cases)
        fam_allow = sum(1 for c in fam_cases if c["outcome"] == "allow")
        fam_hold = sum(1 for c in fam_cases if c["outcome"] == "hold")
        fam_block = sum(1 for c in fam_cases if c["outcome"] == "block")
        is_attack = any(c["label"] == "attack" for c in fam_cases)
        fam_missed = fam_allow if is_attack else 0
        fam_missed_rate, fam_missed_pct = _rate_and_pct(
            fam_missed, fam_total if is_attack else 0
        )
        by_family[fam] = {
            "total": fam_total,
            "allow": fam_allow,
            "hold": fam_hold,
            "block": fam_block,
            "missed_attacks": fam_missed,
            "missed_attack_rate": fam_missed_rate,
            "missed_attacks_pct": fam_missed_pct,
            "false_holds": 0 if is_attack else fam_hold,
            "false_blocks": 0 if is_attack else fam_block,
        }

    sorted_lat = sorted(latencies_ms)
    p50_ms = _percentile(sorted_lat, 0.50)
    p95_ms = _percentile(sorted_lat, 0.95)
    mean_ms = round(sum(sorted_lat) / len(sorted_lat), 3) if sorted_lat else 0.0
    min_ms = round(sorted_lat[0], 3) if sorted_lat else 0.0
    max_ms = round(sorted_lat[-1], 3) if sorted_lat else 0.0

    summary_row = {
        "configuration": configuration,
        "false_holds": false_holds,
        "false_hold_rate": false_hold_rate,
        "false_holds_pct": false_holds_pct,
        "false_blocks": false_blocks,
        "false_block_rate": false_block_rate,
        "false_blocks_pct": false_blocks_pct,
        "missed_attacks": missed_attacks,
        "missed_attack_rate": missed_attack_rate,
        "missed_attacks_pct": missed_attacks_pct,
        "held_attacks": held_attacks,
        "blocked_attacks": blocked_attacks,
        "median_latency_ms": p50_ms,
        "p95_latency_ms": p95_ms,
        "cost_per_payment_usd": 0.0,
    }

    return {
        "format": RESULTS_FORMAT,
        "checker_version": checker_version,
        "total": len(cases),
        "benign_total": benign_total,
        "attack_total": attack_total,
        "summary": {
            "benign_allow": benign_allow,
            "false_holds": false_holds,
            "false_hold_rate": false_hold_rate,
            "false_holds_pct": false_holds_pct,
            "false_blocks": false_blocks,
            "false_block_rate": false_block_rate,
            "false_blocks_pct": false_blocks_pct,
            "missed_attacks": missed_attacks,
            "missed_attack_rate": missed_attack_rate,
            "missed_attacks_pct": missed_attacks_pct,
            "held_attacks": held_attacks,
            "blocked_attacks": blocked_attacks,
        },
        "latency_ms": {
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
            "mean_ms": mean_ms,
            "min_ms": min_ms,
            "max_ms": max_ms,
        },
        "cost_per_payment_usd": 0.0,
        "configurations": [summary_row],
        "by_family": by_family,
        "caveats": list(CAVEATS),
        "cases": cases,
    }


def write_results(results: dict, output_path: Path = DEFAULT_RESULTS_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="firewall-eval", description=__doc__)
    ap.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="path to write results.json (default: data/eval/results.json)",
    )
    ap.add_argument(
        "--configuration",
        default="stub_allow",
        help="configuration label for the summary table row",
    )
    ap.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="run only the named scenario(s); defaults to all scenarios",
    )
    args = ap.parse_args(argv)

    s = Settings.load()
    results = evaluate_scenarios(
        s,
        scenario_names=args.scenarios,
        configuration=args.configuration,
    )
    out = write_results(results, args.output)
    try:
        shown = out.relative_to(REPO_ROOT)
    except ValueError:
        shown = out

    summ = results["summary"]
    lat = results["latency_ms"]
    print(
        f"scenarios: {results['total']} "
        f"(benign={results['benign_total']}, attack={results['attack_total']})"
    )
    print(
        f"benign: allow={summ['benign_allow']} "
        f"false_holds={summ['false_holds']} ({summ['false_holds_pct']}%) "
        f"false_blocks={summ['false_blocks']} ({summ['false_blocks_pct']}%)"
    )
    print(
        f"attack: missed={summ['missed_attacks']} ({summ['missed_attacks_pct']}%) "
        f"held={summ['held_attacks']} blocked={summ['blocked_attacks']}"
    )
    print(f"latency_ms: p50={lat['p50_ms']} p95={lat['p95_ms']} mean={lat['mean_ms']}")
    print(f"results_file: {shown.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
