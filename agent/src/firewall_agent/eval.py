"""firewall-eval: run the checker binary over every scenario, score label vs. verdict, write results.json.

C4 — Full eval run: runs the checker under several configurations (env-var presets, one row per
     configuration in results.json, cost and latency per row) and writes the combined file.

Configuration presets are plain checker env vars (`checker/src/*::from_env`); nothing is hidden in
Python. Every preset sets all five switches (FUSION_MODE, CASCADE_ENABLED, POLICY_ENABLED,
INJECTION_ENABLED, COUNTERPARTY_ENABLED); presets that do not set FUSION_HOLD_THRESHOLD or
JEV_REFERENCE_EXAMPLES_JSON run with them removed from the environment (ALWAYS_CLEARED_ENV), so the
checker's frozen default (the C5 q̂) applies and no exported reference examples reach the Jev state.
A scenario set that supplies AGENT_PROFILE_PATH (`paysim`) also runs with AGENT_PROFILE_JSON removed,
since the checker prefers it over the path. FUSION_AGENT_HOLD_THRESHOLD, and AGENT_PROFILE_JSON /
AGENT_PROFILE_PATH for sets without their own, pass through from the caller's shell. All are restored
afterwards:
    no_defense                    — code rules, every check off: the undefended baseline
    policy_only                   — code rules, policy check only
    classifier_only               — code rules, injection classifier only
    code_rules_all_signals        — code rules, policy + classifier + counterparty (no Jev)
    jev_fusion_all_signals        — Jev fusion, all checks on, FUSION_HOLD_THRESHOLD=0.5
    jev_fusion_conformal          — Jev fusion, all checks on, the frozen default q̂
    jev_fusion_conformal_cascade  — as above, classifier runs only when Jev `unusual` > threshold
MELON ("masked re-run") was cut (idea.md cut list) and has no preset.

Per case the eval records whether Jev and the classifier were called (read back from the
DecisionRecord signals; a null Jev signal with `check_unavailable` in jev mode counts as an attempted
Jev call) and, when CASCADE_ENABLED is true and the classifier is enabled (INJECTION_ENABLED, or
CLASSIFIER_URL set when unset), the cascade path taken. Per row it
reports mean Jev/classifier calls per payment and a cost per payment priced from
EVAL_JEV_USD_PER_CALL / EVAL_CLASSIFIER_USD_PER_CALL (default 0.0 = unpriced).

`--configuration NAME` only labels the summary row; pass the checker env vars yourself.
`--all-configurations` runs every preset above, sequentially, against the real checker binary.
`--preset NAME` runs one preset: any label above, or the opt-in `jev_fusion_conformal_bec`
(`jev_fusion_conformal` plus JEV_REFERENCE_EXAMPLES_JSON read from the gitignored
data/external/derived/bec-reference-examples.json; not part of `--all-configurations`).
`--scenario-set redteam|external|paysim` evaluates that set instead of the main set (`external`:
agent/scenarios/external, from public benchmarks; `paysim`: built locally under data/, with its
own AGENT_PROFILE_PATH).
`--record-dir DIR` keeps the DecisionRecords as DIR/<n>.json (n = the 1-based case index). DIR must
be absent or empty and only one preset may write to it, because the checker never overwrites a
record with different bytes.
`--refuse-from RESULTS.json` (needs `--record-dir DIR`, which it only reads, and `--preset` or
`--all-configurations`; not with `--scenario`) makes no Jev call. For each Jev preset it re-fuses
every case of RESULTS.json from DIR/<n>.json with `checker --refuse` under that preset's env,
replaces `outcome` and `reasons`, marks the case `refused`, and keeps the recorded scores,
`jev_called` and latency. The cascade preset is skipped with a caveat, because its Jev state
differs. Code-rules presets run normally, with a temporary record dir. The output carries
`refused_from`.
`--calibration FILE` adds q_hat and unseen_family_rotation computed from FILE's cases.

Scenarios are always evaluated in the `demo.testnet` namespace (EVAL_NAMESPACE), the one the
checker's default agent profile knows, so results do not depend on OWNER_ACCOUNT_ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from .agent import propose_payment
from .calibration import calibrate, unseen_family_rotation
from .config import REPO_ROOT, Settings
from .formats import compact_json
from .guardian import LocalGuardian, binds, run_checker
from .llm import ScriptedLLM
from .scenarios import SCENARIO_SET_ENV, SCENARIO_SETS, list_scenarios, load_scenario

RESULTS_FORMAT = "firewall.results.v1"
DEFAULT_RESULTS_PATH = REPO_ROOT / "data" / "eval" / "results.json"

# Namespace of AgentProfile::with_default_payees() in checker/src/counterparty.rs; eval is offline
# and must not depend on OWNER_ACCOUNT_ID.
EVAL_NAMESPACE = "demo.testnet"

UNPRICED_CAVEAT = (
    "Cost per payment is unpriced (EVAL_JEV_USD_PER_CALL and EVAL_CLASSIFIER_USD_PER_CALL unset); "
    "call counts per payment are reported instead."
)
MELON_CAVEAT = "MELON masked re-run was not built (cut list, idea.md); its row is omitted."
JEV_FAILED_CAVEAT = "Jev calls that failed (check_unavailable) count as attempted calls."
CASCADE_NOT_REFUSED_CAVEAT = (
    "Cascade row not re-run: its Jev state differs (no classifier score), so it cannot be re-fused."
)

CAVEATS = [
    "The conformal false-hold bound (epsilon = 5%) assumes exchangeability between calibration and live traffic.",
    "Attack detection rates cover the evaluated attack families; worst-case loss under adaptive or unseen attacks is bounded by the Guardian contract's hard per-payment and daily caps.",
]

CheckerRunner = Callable[[bytes, Path], dict]

_TRUE = {"1", "true", "on", "yes"}


def _injection_enabled() -> bool:
    """Same rule as checker InjectionConfig::from_vars (unset: enabled iff CLASSIFIER_URL is set)."""
    raw = os.environ.get("INJECTION_ENABLED", "").strip().lower()
    if raw:
        if raw in _TRUE:
            return True
        if raw in ("0", "false", "off", "no"):
            return False
        raise ValueError(f"INJECTION_ENABLED: expected 1/0/true/false/on/off/yes/no, got {raw!r}")
    return bool(os.environ.get("CLASSIFIER_URL", "").strip())


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


def _env_float(name: str) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return 0.0
    try:
        val = float(raw)
    except ValueError:
        raise ValueError(f"{name}: expected a non-negative number, got {raw!r}") from None
    if val < 0 or math.isnan(val):
        raise ValueError(f"{name}: expected a non-negative number, got {raw!r}")
    return val


def evaluate_scenarios(
    settings: Settings,
    scenario_names: list[str] | None = None,
    configuration: str = "stub_allow",
    checker_fn: CheckerRunner | None = None,
    record_dir: Path | None = None,
    scenario_set: str = "main",
) -> dict:
    """Run the checker over `scenario_names` (default: the whole set) and return the results.json dict."""
    names = list_scenarios(scenario_set) if scenario_names is None else list(scenario_names)
    runner = checker_fn or (
        lambda input_bytes, rec_dir: run_checker(settings.checker_bin, input_bytes, rec_dir)
    )
    local_guardian = LocalGuardian(settings)
    # Mirrors checker InjectionConfig::from_vars: explicit INJECTION_ENABLED wins, else enabled iff
    # CLASSIFIER_URL is set. With the classifier off there is no cascade path to report.
    classifier_on = _injection_enabled()
    cascade_on = classifier_on and os.environ.get("CASCADE_ENABLED", "").strip().lower() in _TRUE
    jev_mode = os.environ.get("FUSION_MODE", "").strip().lower() in ("", "jev")

    with tempfile.TemporaryDirectory() as tmp:
        active_record_dir = record_dir if record_dir is not None else Path(tmp) / "records"
        active_record_dir.mkdir(parents=True, exist_ok=True)

        cases: list[dict] = []
        jev_failed = 0
        checker_version = "0.1.0"

        for idx, name in enumerate(names, start=1):
            scenario = load_scenario(name, EVAL_NAMESPACE, scenario_set)
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
            jev_unusual: float | None = None
            jev_injection_driven: float | None = None
            jev_receiver_risk: float | None = None
            jev_label: str | None = None
            policy_violations: list = []
            lookalike_of: str | None = None
            jev_called = False
            classifier_called = False
            reasons_rec: list = []
            if rec_file.is_file():
                raw_rec = rec_file.read_bytes()
                if hashlib.sha256(raw_rec).hexdigest() != verdict["record_sha256"]:
                    raise ValueError(f"scenario {name!r}: record_sha256 mismatch")
                rec_json = json.loads(raw_rec)
                signals = rec_json.get("signals") or {}
                reasons_rec = rec_json.get("reasons") or []
                policy_sig = signals.get("policy")
                if isinstance(policy_sig, dict) and "ok" in policy_sig:
                    policy_ok = bool(policy_sig["ok"])
                # C5 calibration reads this back from results.json.
                jev_sig = signals.get("jev")
                jev_called = jev_sig is not None
                if jev_sig is None and jev_mode and "check_unavailable" in reasons_rec:
                    # Jev was queried but failed: an attempted call costs the same.
                    jev_called = True
                    jev_failed += 1
                if isinstance(jev_sig, dict):
                    if isinstance(jev_sig.get("unusual"), (int, float)):
                        jev_unusual = float(jev_sig["unusual"])
                    if isinstance(jev_sig.get("injection_driven"), (int, float)):
                        jev_injection_driven = float(jev_sig["injection_driven"])
                    if isinstance(jev_sig.get("receiver_risk"), (int, float)):
                        jev_receiver_risk = float(jev_sig["receiver_risk"])
                    if isinstance(jev_sig.get("label"), str):
                        jev_label = jev_sig["label"]
                if isinstance(policy_sig, dict):
                    policy_violations = list(policy_sig.get("violations") or [])
                counterparty_sig = signals.get("counterparty")
                if isinstance(counterparty_sig, dict) and isinstance(counterparty_sig.get("lookalike_of"), str):
                    lookalike_of = counterparty_sig["lookalike_of"]
                classifier_called = signals.get("injection") is not None

            cascade_path: str | None = None
            if cascade_on:
                cascade_path = "classifier_run" if classifier_called else "classifier_skipped"

            checker_version = str(verdict.get("checker_version", checker_version))
            outcome = verdict["outcome"]

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
                    "jev_unusual": jev_unusual,
                    "jev_injection_driven": jev_injection_driven,
                    "jev_receiver_risk": jev_receiver_risk,
                    "jev_label": jev_label,
                    "policy_violations": policy_violations,
                    "lookalike_of": lookalike_of,
                    "jev_called": jev_called,
                    "classifier_called": classifier_called,
                    "cascade_path": cascade_path,
                    "latency_ms": elapsed_ms,
                }
            )

    return _build_results(cases, configuration, scenario_set, checker_version, cascade_on, jev_failed)


def _build_results(
    cases: list[dict],
    configuration: str,
    scenario_set: str,
    checker_version: str,
    cascade_on: bool,
    jev_failed: int,
) -> dict:
    """The results.json dict (summary, latency, row, by_family, caveats) for finished `cases`."""
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

    sorted_lat = sorted(c["latency_ms"] for c in cases)
    p50_ms = _percentile(sorted_lat, 0.50)
    p95_ms = _percentile(sorted_lat, 0.95)
    mean_ms = round(sum(sorted_lat) / len(sorted_lat), 3) if sorted_lat else 0.0
    min_ms = round(sorted_lat[0], 3) if sorted_lat else 0.0
    max_ms = round(sorted_lat[-1], 3) if sorted_lat else 0.0

    n_cases = len(cases)
    jev_calls_per_payment = round(sum(1 for c in cases if c["jev_called"]) / n_cases, 4) if n_cases else 0.0
    classifier_calls_per_payment = (
        round(sum(1 for c in cases if c["classifier_called"]) / n_cases, 4) if n_cases else 0.0
    )
    jev_price = _env_float("EVAL_JEV_USD_PER_CALL")
    classifier_price = _env_float("EVAL_CLASSIFIER_USD_PER_CALL")
    cost_per_payment_usd = round(
        jev_calls_per_payment * jev_price + classifier_calls_per_payment * classifier_price, 6
    )

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
        "jev_calls_per_payment": jev_calls_per_payment,
        "classifier_calls_per_payment": classifier_calls_per_payment,
        "cost_per_payment_usd": cost_per_payment_usd,
    }
    if cascade_on:
        latency_by_path: dict[str, dict] = {}
        for path in ("classifier_run", "classifier_skipped"):
            vals = [c["latency_ms"] for c in cases if c["cascade_path"] == path]
            if vals:
                latency_by_path[path] = {
                    "count": len(vals),
                    "median_ms": round(statistics.median(vals), 3),
                }
        summary_row["latency_by_path"] = latency_by_path

    caveats = list(CAVEATS)
    if jev_failed:
        caveats.append(JEV_FAILED_CAVEAT)
    if jev_price == 0.0 and classifier_price == 0.0:
        caveats.append(UNPRICED_CAVEAT)
    caveats.append(MELON_CAVEAT)

    return {
        "format": RESULTS_FORMAT,
        "checker_version": checker_version,
        "scenario_set": scenario_set,
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
        "cost_per_payment_usd": cost_per_payment_usd,
        "configurations": [summary_row],
        "by_family": by_family,
        "caveats": caveats,
        "cases": cases,
    }


def write_results(results: dict, output_path: Path = DEFAULT_RESULTS_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return output_path


def apply_calibration(results: dict, calibration_file: Path) -> None:
    """Add `q_hat` and `unseen_family_rotation` (from `calibration_file`'s cases) to `results`.

    `q_hat` is null when the calibration file has no benign Jev scores. `unseen_family_rotation`
    is a list: one row per attack family (`family`, `total`, `detected`, `missed`,
    `detection_rate`) followed by a pooled row with `family` `"all"` carrying the held-out
    false-hold rate.
    """
    data = json.loads(Path(calibration_file).read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    cal = calibrate(cases)
    results["q_hat"] = cal["q_hat"] if cal["n"] > 0 else None
    rot = unseen_family_rotation(cases)
    rows = [{"family": fam, **stats} for fam, stats in rot["by_family"].items()]
    rows.append(
        {
            "family": "all",
            "total": rot["attacks_total"],
            "detected": rot["attacks_detected"],
            "missed": rot["attacks_total"] - rot["attacks_detected"],
            "detection_rate": rot["attack_detection_rate"],
            "epsilon": rot["epsilon"],
            "calibration_n": rot["calibration_n"],
            "test_n": rot["test_n"],
            "q_hat": rot["q_hat"],
            "false_hold_rate": rot["false_hold_rate"],
            "within_target": rot["within_target"],
            "sufficient_data": rot["sufficient_data"],
        }
    )
    results["unseen_family_rotation"] = rows


# ---------------------------------------------------------------------------
# C4 — Multi-configuration presets
# ---------------------------------------------------------------------------


def _preset(
    mode: str, cascade: str, policy: str, injection: str, counterparty: str, **extra: str
) -> dict[str, str]:
    env = {
        "FUSION_MODE": mode,
        "CASCADE_ENABLED": cascade,
        "POLICY_ENABLED": policy,
        "INJECTION_ENABLED": injection,
        "COUNTERPARTY_ENABLED": counterparty,
    }
    env.update(extra)
    return env


#: Ordered presets for the full run. Each entry is (label, checker env overrides). The checker reads
#: these from the environment, so they are set before each pass and restored afterwards. Presets
#: remove ALWAYS_CLEARED_ENV unless they set it, so the checker's defaults apply.
ALWAYS_CLEARED_ENV = ("FUSION_HOLD_THRESHOLD", "FUSION_JEV_INJECTION_HOLD_THRESHOLD", "JEV_REFERENCE_EXAMPLES_JSON")
EVAL_CONFIGURATIONS: list[tuple[str, dict[str, str]]] = [
    ("no_defense", _preset("code_rules", "false", "false", "false", "false")),
    ("policy_only", _preset("code_rules", "false", "true", "false", "false")),
    ("classifier_only", _preset("code_rules", "false", "false", "true", "false")),
    ("code_rules_all_signals", _preset("code_rules", "false", "true", "true", "true")),
    (
        "jev_fusion_all_signals",
        _preset("jev", "false", "true", "true", "true", FUSION_HOLD_THRESHOLD="0.5"),
    ),
    ("jev_fusion_conformal", _preset("jev", "false", "true", "true", "true")),
    ("jev_fusion_conformal_cascade", _preset("jev", "true", "true", "true", "true")),
]

BEC_REFERENCE_EXAMPLES_PATH = REPO_ROOT / "data" / "external" / "derived" / "bec-reference-examples.json"


def _bec_preset() -> dict[str, str]:
    if not BEC_REFERENCE_EXAMPLES_PATH.is_file():
        raise SystemExit(
            "missing data/external/derived/bec-reference-examples.json; "
            "run: uv run python tools/build_bec_examples.py"
        )
    return _preset(
        "jev",
        "false",
        "true",
        "true",
        "true",
        JEV_REFERENCE_EXAMPLES_JSON=BEC_REFERENCE_EXAMPLES_PATH.read_text(encoding="utf-8"),
    )


#: Opt-in presets for `--preset` only (never part of `--all-configurations`). Lazy: they read
#: gitignored files built from manual downloads.
EXTRA_PRESETS: dict[str, Callable[[], dict[str, str]]] = {
    "jev_fusion_conformal_bec": _bec_preset,
}


def preset_env(name: str) -> dict[str, str]:
    """Checker env overrides for preset `name` (EVAL_CONFIGURATIONS or EXTRA_PRESETS)."""
    if name in EXTRA_PRESETS:
        return EXTRA_PRESETS[name]()
    return dict(EVAL_CONFIGURATIONS)[name]


def _check_record_dir(record_dir: Path, n_presets: int) -> None:
    """The checker refuses to overwrite a record with different bytes: one preset, an empty directory."""
    if n_presets > 1:
        raise SystemExit("--record-dir: more than one preset would write to it; use one preset")
    if record_dir.exists() and (not record_dir.is_dir() or any(record_dir.iterdir())):
        raise SystemExit(f"--record-dir: {record_dir} exists and is not empty")


def _real_refuse(checker_bin: Path | str) -> Callable[[bytes], dict]:
    """`checker --refuse` as a subprocess under the current environment."""

    def refuse(record_bytes: bytes) -> dict:
        proc = subprocess.run([str(checker_bin), "--refuse"], input=record_bytes, capture_output=True)
        if proc.returncode != 0:
            raise SystemExit(f"checker --refuse failed ({proc.returncode}): {proc.stderr.decode('utf-8', 'replace').strip()}")
        return json.loads(proc.stdout)

    return refuse


def _refuse_results(
    source: dict, label: str, scenario_set: str, record_dir: Path, refuse_fn: Callable[[bytes], dict]
) -> dict:
    """Re-fuse every case of `source` from `record_dir/<n>.json` under the current env; never writes."""
    cases: list[dict] = []
    for idx, src_case in enumerate(source["cases"], start=1):
        rec_file = record_dir / f"{idx}.json"
        if not rec_file.is_file():
            raise SystemExit(f"--refuse-from: missing record file {rec_file}")
        verdict = refuse_fn(rec_file.read_bytes())
        cases.append({**src_case, "outcome": verdict["outcome"], "reasons": list(verdict["reasons"]), "refused": True})
    jev_failed = sum(1 for c in source["cases"] if c["jev_called"] and "check_unavailable" in c["reasons"])
    return _build_results(
        cases, label, scenario_set, str(source.get("checker_version", "0.1.0")), False, jev_failed
    )


def run_all_configurations(
    settings: Settings,
    configurations: list[tuple[str, dict[str, str]]] | None = None,
    checker_fn: CheckerRunner | None = None,
    output_path: Path = DEFAULT_RESULTS_PATH,
    scenario_set: str = "main",
    calibration_file: Path | None = None,
    scenario_names: list[str] | None = None,
    record_dir: Path | None = None,
    refuse_from: Path | None = None,
    refuse_fn: Callable[[bytes], dict] | None = None,
) -> dict:
    """Run the checker over all scenarios for each configuration preset.

    Returns a combined results.json dict with one entry per configuration in
    ``configurations``.  The ``configurations`` key in the output holds all rows;
    the top-level ``summary`` and ``by_family`` reflect the last (or only) run.

    Args:
        settings: loaded Settings.
        configurations: list of (label, env_overrides) pairs; defaults to EVAL_CONFIGURATIONS.
        checker_fn: optional in-process checker runner (overrides the binary).
        output_path: where to write the final results.json.
        scenario_set: a key of SCENARIO_SETS; its SCENARIO_SET_ENV is merged into every preset.
        calibration_file: optional results.json whose cases feed `q_hat` / `unseen_family_rotation`.
        scenario_names: run only these scenarios; defaults to the whole set (with `refuse_from`: the
            source file's cases, in order).
        record_dir: persist DecisionRecords as `<record_dir>/<n>.json` (one preset, empty or absent
            directory); with `refuse_from` it is only read.
        refuse_from: results.json of a recorded Jev run: its Jev rows are re-fused from `record_dir`
            (via `checker --refuse`, or `refuse_fn(record_bytes) -> {"outcome", "reasons"}`) instead of run.

    Returns:
        The combined results dict.
    """
    cfgs = configurations or EVAL_CONFIGURATIONS
    refusing = refuse_from is not None
    names = scenario_names
    source: dict = {}
    if refusing:
        source = json.loads(refuse_from.read_text(encoding="utf-8"))
        if source.get("scenario_set") != scenario_set:
            raise SystemExit(
                f"--refuse-from: scenario_set of {refuse_from.name} is {source.get('scenario_set')!r}, "
                f"--scenario-set is {scenario_set!r}"
            )
        names = [c["name"] for c in source["cases"]]
    elif record_dir is not None:
        _check_record_dir(record_dir, len(cfgs))
    all_config_rows: list[dict] = []
    last_result: dict = {}
    skipped_cascade = False

    for label, preset_overrides in cfgs:
        env_overrides = {**preset_overrides, **SCENARIO_SET_ENV.get(scenario_set, {})}
        if refusing and env_overrides.get("FUSION_MODE") == "jev" and env_overrides.get("CASCADE_ENABLED") == "true":
            skipped_cascade = True
            continue
        # ALWAYS_CLEARED_ENV is removed unless the preset sets it, so an exported value cannot leak
        # into a preset that means "default". A set that supplies AGENT_PROFILE_PATH also removes
        # AGENT_PROFILE_JSON, which the checker prefers over the path.
        cleared = set(ALWAYS_CLEARED_ENV)
        if "AGENT_PROFILE_PATH" in SCENARIO_SET_ENV.get(scenario_set, {}):
            cleared.add("AGENT_PROFILE_JSON")
        old_env: dict[str, str | None] = {}
        for k in {*env_overrides, *cleared}:
            old_env[k] = os.environ.get(k)
            if k in env_overrides:
                os.environ[k] = env_overrides[k]
            else:
                os.environ.pop(k, None)

        try:
            if refusing and env_overrides.get("FUSION_MODE") == "jev":
                result = _refuse_results(
                    source, label, scenario_set, record_dir, refuse_fn or _real_refuse(settings.checker_bin)
                )
            else:
                result = evaluate_scenarios(
                    settings,
                    scenario_names=names,
                    configuration=label,
                    checker_fn=checker_fn,
                    scenario_set=scenario_set,
                    record_dir=None if refusing else record_dir,
                )
            # Collect the configuration summary row.
            if result["configurations"]:
                all_config_rows.append(result["configurations"][0])
            last_result = result
        finally:
            # Restore env.
            for k, old in old_env.items():
                if old is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = old

    if not last_result:
        return {}

    # Combine: last run's top-level metadata + all configuration rows.
    combined = dict(last_result)
    combined["configurations"] = all_config_rows
    if skipped_cascade:
        combined["caveats"] = [*combined["caveats"], CASCADE_NOT_REFUSED_CAVEAT]
    if refuse_from is not None:
        combined["refused_from"] = refuse_from.name
    if calibration_file is not None:
        apply_calibration(combined, calibration_file)
    write_results(combined, output_path)
    return combined


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
    ap.add_argument(
        "--scenario-set",
        choices=list(SCENARIO_SETS),
        default="main",
        help="scenario set to evaluate (default: main)",
    )
    ap.add_argument(
        "--calibration",
        type=Path,
        default=None,
        help="results.json whose cases feed q_hat and unseen_family_rotation in the output",
    )
    which = ap.add_mutually_exclusive_group()
    which.add_argument(
        "--all-configurations",
        action="store_true",
        help=(
            "C4: run all standard configuration presets sequentially and write a "
            "combined results.json (requires the checker binary to be built)"
        ),
    )
    which.add_argument(
        "--preset",
        choices=[label for label, _ in EVAL_CONFIGURATIONS] + list(EXTRA_PRESETS),
        default=None,
        help="run one configuration preset (sets its checker env vars)",
    )
    ap.add_argument(
        "--record-dir",
        type=Path,
        default=None,
        help="persist the DecisionRecords as DIR/<n>.json (must be empty or absent; one preset only)",
    )
    ap.add_argument(
        "--refuse-from",
        type=Path,
        default=None,
        metavar="RESULTS.json",
        help="re-fuse the Jev rows of RESULTS.json from the records in --record-dir (read-only), no Jev calls",
    )
    args = ap.parse_args(argv)

    s = Settings.load()

    if args.refuse_from is not None:
        if args.record_dir is None:
            raise SystemExit("--refuse-from requires --record-dir")
        if not (args.all_configurations or args.preset):
            raise SystemExit("--refuse-from requires --preset or --all-configurations")
        if args.scenarios:
            raise SystemExit("--refuse-from cannot be combined with --scenario: the source file defines the scenarios")

    if args.all_configurations or args.preset:
        combined = run_all_configurations(
            s,
            configurations=[(args.preset, preset_env(args.preset))] if args.preset else None,
            output_path=args.output,
            scenario_set=args.scenario_set,
            calibration_file=args.calibration,
            scenario_names=args.scenarios,
            record_dir=args.record_dir,
            refuse_from=args.refuse_from,
        )
        if not combined:
            print("ERROR: no results produced", file=sys.stderr)
            return 1
        lat = combined["latency_ms"]
        print(
            f"scenarios: {combined['total']} "
            f"(benign={combined['benign_total']}, attack={combined['attack_total']})"
        )
        print(f"configurations: {len(combined['configurations'])}")
        for row in combined["configurations"]:
            print(
                f"  {row['configuration']}: "
                f"false_holds={row['false_holds']} ({row['false_holds_pct']}%) "
                f"missed_attacks={row['missed_attacks']} ({row['missed_attacks_pct']}%)"
            )
        print(f"latency_ms (last run): p50={lat['p50_ms']} p95={lat['p95_ms']}")
        try:
            shown = args.output.relative_to(REPO_ROOT)
        except ValueError:
            shown = args.output
        print(f"results_file: {shown.as_posix()}")
        return 0

    if args.record_dir is not None:
        _check_record_dir(args.record_dir, 1)
    results = evaluate_scenarios(
        s,
        scenario_names=args.scenarios,
        configuration=args.configuration,
        scenario_set=args.scenario_set,
        record_dir=args.record_dir,
    )
    if args.calibration is not None:
        apply_calibration(results, args.calibration)
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
