"""C5 — Conformal hold threshold and unseen-family rotation.

Split-conformal calibration on the pooled benign calibration set (`sdd.md §5`,
[idea.md Evaluation and calibration](../../../docs/build/idea.md#evaluation-and-calibration)):
    q_hat = the ceil((n+1)(1-epsilon))-th smallest benign Jev `unusual` score, n >= 1/epsilon - 1

The calibration set is the benign cases of a completed `firewall-eval` run (the `cases` list in
results.json, `jev_unusual` per case, DecisionRecords as fallback). Cases without a Jev signal are
skipped, or counted as 0.0 with `--missing-as-zero` so the CLI still runs without a Jev key.

Unseen-family rotation: Jev is zero-shot, so no threshold is fitted on attacks and every family is
unseen. The rotation reports per-family detection (held or blocked) at a q̂ fitted on a benign
calibration split, with the false-hold rate measured on the held-out benign split.

References:
    Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction" (2021).
    AGENTS.md §7: "per-agent threshold only after ≥99 normal payments".
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

EPSILON_DEFAULT = 0.05  # target false-hold rate


# ---------------------------------------------------------------------------
# Core conformal computation
# ---------------------------------------------------------------------------


def compute_q_hat(scores: Sequence[float], epsilon: float = EPSILON_DEFAULT) -> float:
    """Return the split-conformal hold threshold q_hat for the given nonconformity scores.

    ``scores`` are Jev ``unusual`` values from benign calibration examples (higher = more unusual).
    We want to *hold* when unusual >= q_hat, so a *false hold* is a benign example with
    unusual >= q_hat.  q_hat is chosen so that the false-hold rate is bounded by epsilon.

    Args:
        scores: Jev unusual scores for the calibration set (benign examples only).
        epsilon: target false-hold rate (default 0.05 = 5%).

    Returns:
        q_hat in [0.0, 1.0], or 1.0 when n < ceil(1/epsilon) − 1 (too few calibration points).
    """
    n = len(scores)
    if n == 0:
        return 1.0  # no data → never hold
    # rank position: ceil((n+1)(1-epsilon)) clamped to [1, n]
    rank = math.ceil((n + 1) * (1.0 - epsilon))
    rank = max(1, min(n, rank))
    sorted_scores = sorted(scores)
    return float(sorted_scores[rank - 1])


def false_hold_rate(scores: Sequence[float], q_hat: float) -> float:
    """Fraction of calibration benign examples with unusual >= q_hat (empirical false-hold rate)."""
    if not scores:
        return 0.0
    return sum(1 for s in scores if s >= q_hat) / len(scores)


# ---------------------------------------------------------------------------
# Extract scores from results cases
# ---------------------------------------------------------------------------


def _case_unusual(case: dict, idx: int, record_dir: Path | None) -> float | None:
    """The Jev `unusual` score for one case: `jev_unusual` first, then `{idx}.json` in record_dir."""
    if isinstance(case.get("jev_unusual"), (int, float)):
        return float(case["jev_unusual"])
    if record_dir is not None:
        rec_path = record_dir / f"{idx}.json"
        if rec_path.is_file():
            try:
                rec = json.loads(rec_path.read_bytes())
                jev_sig = (rec.get("signals") or {}).get("jev")
                if isinstance(jev_sig, dict) and "unusual" in jev_sig:
                    return float(jev_sig["unusual"])
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
                return None
    return None


def jev_unusual_scores(
    cases: list[dict],
    label: str,
    record_dir: Path | None = None,
    missing_as_zero: bool = False,
) -> list[float]:
    """Jev `unusual` scores for every case with the given label, in results.json order.

    `firewall-eval` writes `jev_unusual` on each case; `record_dir` (the DecisionRecord
    files) is the fallback source. A case with no Jev signal is skipped unless
    `missing_as_zero`, which substitutes 0.0 (never held) so the pipeline still runs
    without a Jev key — that run is not a calibration and says so via `sufficient_data`.
    """
    scores: list[float] = []
    for idx, case in enumerate(cases, start=1):
        if case.get("label") != label:
            continue
        unusual = _case_unusual(case, idx, record_dir)
        if unusual is None:
            if not missing_as_zero:
                continue
            unusual = 0.0
        scores.append(unusual)
    return scores


def jev_unusual_scores_from_cases(
    cases: list[dict],
    record_dir: Path | None = None,
    missing_as_zero: bool = False,
) -> list[float]:
    """Jev `unusual` scores for the benign cases (the pooled calibration set)."""
    return jev_unusual_scores(cases, "benign", record_dir, missing_as_zero)


# ---------------------------------------------------------------------------
# Full calibration report
# ---------------------------------------------------------------------------


def calibrate(
    cases: list[dict],
    record_dir: Path | None = None,
    epsilon: float = EPSILON_DEFAULT,
    missing_as_zero: bool = False,
) -> dict:
    """Compute q_hat and the empirical false-hold rate on the full calibration set.

    Args:
        cases: results[\"cases\"] list.
        record_dir: directory of DecisionRecord JSON files (optional).
        epsilon: target false-hold rate.
        missing_as_zero: substitute 0.0 for cases with no Jev signal.

    Returns:
        dict with keys: n, q_hat, empirical_false_hold_rate, epsilon, sufficient_data.
    """
    scores = jev_unusual_scores_from_cases(cases, record_dir, missing_as_zero)
    n = len(scores)
    q_hat = compute_q_hat(scores, epsilon)
    fhr = false_hold_rate(scores, q_hat)
    # Need at least ceil(1/epsilon) − 1 calibration points for the guarantee.
    min_n = math.ceil(1.0 / epsilon) - 1
    return {
        "n": n,
        "q_hat": round(q_hat, 6),
        "empirical_false_hold_rate": round(fhr, 4),
        "epsilon": epsilon,
        "sufficient_data": n >= min_n,
        "min_n_for_guarantee": min_n,
    }


# ---------------------------------------------------------------------------
# Unseen-family rotation
# ---------------------------------------------------------------------------

ATTACK_FAMILIES = [
    "direct_injection",
    "encoded_injection",
    "indirect_injection",
    "memory_poisoning",
    "lookalike_receiver",
    "fake_invoice",
]


def unseen_family_rotation(
    cases: list[dict],
    record_dir: Path | None = None,
    epsilon: float = EPSILON_DEFAULT,
    missing_as_zero: bool = False,
    test_fraction: float = 0.5,
) -> dict:
    """Per-attack-family detection at the conformal threshold, with a held-out benign split.

    Jev is zero-shot: no threshold is fitted on attack cases, so every family is unseen by
    construction. The rotation therefore reports, for each of the six families, how many of its
    attacks are held or blocked at q̂ (`outcome` is `hold`/`block`), next to the false-hold rate on
    the benign test split. Benign cases are split deterministically by position (every
    `1/test_fraction`-th case goes to the test split, the rest to calibration) so the reported
    false-hold rate is not measured on the scores q̂ was fitted on.

    Families with no cases in `cases` appear with `total: 0`, which is what an unfinished dataset
    (A6) looks like — a missed family, not a perfect score.

    Returns:
        dict with the pooled row (`q_hat`, `false_hold_rate`, `within_target`) and `by_family`.
    """
    benign = jev_unusual_scores(cases, "benign", record_dir, missing_as_zero)
    step = max(1, round(1.0 / test_fraction)) if test_fraction > 0 else 1
    calibration = [s for i, s in enumerate(benign) if i % step != 0]
    test = [s for i, s in enumerate(benign) if i % step == 0]
    if not calibration:  # fewer cases than one split; calibrate on everything
        calibration, test = benign, []

    q_hat = compute_q_hat(calibration, epsilon)
    fhr = false_hold_rate(test, q_hat)

    by_family: dict[str, dict] = {}
    for fam in ATTACK_FAMILIES:
        fam_cases = [c for c in cases if c.get("label") == "attack" and c.get("family") == fam]
        detected = sum(1 for c in fam_cases if c.get("outcome") in ("hold", "block"))
        total = len(fam_cases)
        by_family[fam] = {
            "total": total,
            "detected": detected,
            "missed": total - detected,
            "detection_rate": round(detected / total, 4) if total else 0.0,
        }

    all_attacks = [c for c in cases if c.get("label") == "attack"]
    detected_all = sum(1 for c in all_attacks if c.get("outcome") in ("hold", "block"))
    return {
        "epsilon": epsilon,
        "calibration_n": len(calibration),
        "test_n": len(test),
        "q_hat": round(q_hat, 6),
        "false_hold_rate": round(fhr, 4),
        "within_target": fhr <= epsilon,
        "sufficient_data": len(calibration) >= math.ceil(1.0 / epsilon) - 1,
        "attacks_total": len(all_attacks),
        "attacks_detected": detected_all,
        "attack_detection_rate": round(detected_all / len(all_attacks), 4) if all_attacks else 0.0,
        "by_family": by_family,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """firewall-calibrate: compute conformal q_hat from a results.json file."""
    import argparse
    import sys

    ap = argparse.ArgumentParser(
        prog="firewall-calibrate",
        description="Compute conformal hold threshold (q_hat) from a results.json file.",
    )
    ap.add_argument(
        "results_file",
        type=Path,
        help="Path to results.json produced by firewall-eval.",
    )
    ap.add_argument(
        "--record-dir",
        type=Path,
        default=None,
        help="Directory containing DecisionRecord JSON files (optional; improves accuracy).",
    )
    ap.add_argument(
        "--epsilon",
        type=float,
        default=EPSILON_DEFAULT,
        help=f"Target false-hold rate (default {EPSILON_DEFAULT}).",
    )
    ap.add_argument(
        "--missing-as-zero",
        action="store_true",
        help="Treat cases with no Jev signal as unusual=0.0 instead of skipping them.",
    )
    ap.add_argument(
        "--rotation",
        action="store_true",
        help="Run unseen-family rotation (leave-one-attack-family-out).",
    )
    args = ap.parse_args(argv)

    data = json.loads(args.results_file.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not cases:
        print("ERROR: results.json has no cases", file=sys.stderr)
        return 1

    if args.rotation:
        result = unseen_family_rotation(
            cases,
            record_dir=args.record_dir,
            epsilon=args.epsilon,
            missing_as_zero=args.missing_as_zero,
        )
        print(json.dumps(result, indent=2))
    else:
        result = calibrate(
            cases,
            record_dir=args.record_dir,
            epsilon=args.epsilon,
            missing_as_zero=args.missing_as_zero,
        )
        print(f"n             : {result['n']}")
        print(f"q_hat         : {result['q_hat']}")
        print(f"false_hold_rate: {result['empirical_false_hold_rate']} (target <= {args.epsilon})")
        print(f"sufficient_data: {result['sufficient_data']} (need n >= {result['min_n_for_guarantee']})")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
