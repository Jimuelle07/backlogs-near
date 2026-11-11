"""Tests for C5 — conformal calibration and unseen-family rotation."""

from __future__ import annotations

import math

import pytest

from firewall_agent.calibration import (
    ATTACK_FAMILIES,
    EPSILON_DEFAULT,
    calibrate,
    compute_q_hat,
    false_hold_rate,
    main,
    unseen_family_rotation,
)


# ---------------------------------------------------------------------------
# Unit tests: compute_q_hat
# ---------------------------------------------------------------------------


def test_q_hat_empty_returns_one():
    assert compute_q_hat([]) == 1.0


def test_q_hat_single():
    # rank = ceil(2 * 0.95) = 2, clamped to 1 → sorted_scores[0]
    assert compute_q_hat([0.3]) == pytest.approx(0.3)


def test_q_hat_known_example():
    # 20 benign scores, epsilon=0.05
    # rank = ceil(21 * 0.95) = ceil(19.95) = 20, clamped to 20
    # sorted 20 scores → q_hat = sorted[19]
    scores = [i * 0.05 for i in range(20)]  # 0.0, 0.05, ..., 0.95
    q = compute_q_hat(scores, epsilon=0.05)
    assert q == pytest.approx(sorted(scores)[19])


def test_q_hat_respects_epsilon():
    # With more scores the threshold should be tighter (lower q_hat for small epsilon).
    scores = [i / 100.0 for i in range(100)]  # 0.00 .. 0.99
    q_tight = compute_q_hat(scores, epsilon=0.05)
    q_loose = compute_q_hat(scores, epsilon=0.20)
    assert q_tight >= q_loose  # tighter epsilon → higher threshold (less likely to hold)


def test_false_hold_rate_basic():
    scores = [0.1, 0.4, 0.6, 0.8]
    assert false_hold_rate(scores, q_hat=0.5) == pytest.approx(2 / 4)
    assert false_hold_rate(scores, q_hat=0.0) == pytest.approx(1.0)
    assert false_hold_rate(scores, q_hat=1.1) == pytest.approx(0.0)


def test_false_hold_rate_empty():
    assert false_hold_rate([], q_hat=0.5) == 0.0


# ---------------------------------------------------------------------------
# Tests: calibrate() on synthetic case list
# ---------------------------------------------------------------------------


def _make_cases(unusual_scores: list[float], label: str = "benign") -> list[dict]:
    """Minimal case dicts for testing calibrate()."""
    return [
        {
            "name": f"case-{i}",
            "label": label,
            "family": "none",
            "outcome": "allow",
            "jev_unusual": s,
        }
        for i, s in enumerate(unusual_scores, start=1)
    ]


def test_calibrate_reads_jev_unusual_from_cases():
    # eval.py writes jev_unusual per case; no record_dir needed.
    cases = _make_cases([0.1, 0.2, 0.3, 0.4])
    result = calibrate(cases, record_dir=None, epsilon=0.05)
    assert result["n"] == 4
    # rank = ceil(5 * 0.95) = 5, clamped to 4 -> sorted[3] = 0.4
    assert result["q_hat"] == pytest.approx(0.4)
    assert result["empirical_false_hold_rate"] == pytest.approx(0.25)


def test_calibrate_skips_cases_without_jev_signal():
    cases = [
        {"name": "a", "label": "benign", "family": "none", "outcome": "allow"},
        {"name": "b", "label": "benign", "family": "none", "outcome": "allow", "jev_unusual": 0.2},
    ]
    assert calibrate(cases, record_dir=None)["n"] == 1


def test_calibrate_no_record_dir_missing_as_zero():
    # No jev_unusual anywhere: with missing_as_zero the case counts as 0.0.
    cases = [{"name": "a", "label": "benign", "family": "none", "outcome": "allow"}]
    result = calibrate(cases, record_dir=None, missing_as_zero=True, epsilon=0.05)
    assert result["n"] == 1
    assert result["q_hat"] == pytest.approx(0.0)
    assert result["sufficient_data"] is False


def test_calibrate_no_cases_returns_q_hat_one():
    result = calibrate([], record_dir=None, missing_as_zero=True)
    assert result["q_hat"] == 1.0
    assert result["n"] == 0


def test_calibrate_sufficient_data_flag():
    # min_n for epsilon=0.05 is ceil(1/0.05)-1 = 20-1 = 19.
    min_n = math.ceil(1.0 / EPSILON_DEFAULT) - 1
    scores_enough = [i / float(min_n + 1) for i in range(min_n + 1)]
    scores_few = [0.1] * (min_n - 1)
    cases_enough = _make_cases(scores_enough)
    cases_few = _make_cases(scores_few)
    r_enough = calibrate(cases_enough, missing_as_zero=True, epsilon=EPSILON_DEFAULT)
    r_few = calibrate(cases_few, missing_as_zero=True, epsilon=EPSILON_DEFAULT)
    assert r_enough["sufficient_data"] is True
    assert r_few["sufficient_data"] is False
    assert r_enough["min_n_for_guarantee"] == min_n


# ---------------------------------------------------------------------------
# Tests: unseen_family_rotation()
# ---------------------------------------------------------------------------


def _make_full_cases(n_benign: int = 30, n_per_family: int = 5) -> list[dict]:
    """Synthetic results.json cases matching the 30 benign / 30 attack split."""
    cases: list[dict] = []
    # Benign cases (all in family "none"); scores spread over [0, 0.6).
    for i in range(n_benign):
        cases.append(
            {
                "name": f"benign-{i}",
                "label": "benign",
                "family": "none",
                "outcome": "allow",
                "jev_unusual": round((i / max(1, n_benign)) * 0.6, 4),
            }
        )
    # Attack cases (5 per family × 6 families = 30).
    for fam in ATTACK_FAMILIES:
        for i in range(n_per_family):
            cases.append({"name": f"{fam}-{i}", "label": "attack", "family": fam, "outcome": "block"})
    return cases


def test_unseen_family_rotation_keys():
    cases = _make_full_cases()
    result = unseen_family_rotation(cases, record_dir=None)
    assert set(result["by_family"].keys()) == set(ATTACK_FAMILIES)
    assert "q_hat" in result
    assert "false_hold_rate" in result
    assert "within_target" in result
    assert result["attacks_total"] == 30
    assert result["attacks_detected"] == 30


def test_unseen_family_rotation_uses_held_out_benign_split():
    cases = _make_full_cases(n_benign=20)
    result = unseen_family_rotation(cases, record_dir=None, epsilon=0.05)
    # Every second benign case is held out of calibration.
    assert result["calibration_n"] + result["test_n"] == 20
    assert result["test_n"] == 10
    assert result["false_hold_rate"] <= 0.5


def test_unseen_family_rotation_reports_missed_attacks():
    cases = _make_full_cases()
    for c in cases:
        if c["family"] == "fake_invoice":
            c["outcome"] = "allow"
    result = unseen_family_rotation(cases, record_dir=None)
    assert result["by_family"]["fake_invoice"]["missed"] == 5
    assert result["by_family"]["fake_invoice"]["detection_rate"] == 0.0
    assert result["by_family"]["lookalike_receiver"]["detection_rate"] == 1.0


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_main_no_cases(tmp_path):
    results = {"format": "firewall.results.v1", "cases": []}
    f = tmp_path / "results.json"
    f.write_text('{"format": "firewall.results.v1", "cases": []}', encoding="utf-8")
    rc = main([str(f)])
    assert rc == 1


def test_main_with_cases(tmp_path, capsys):
    import json

    cases = _make_full_cases(n_benign=5)
    data = {"format": "firewall.results.v1", "cases": cases}
    f = tmp_path / "results.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    rc = main([str(f), "--missing-as-zero"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "q_hat" in out


def test_main_rotation_flag(tmp_path, capsys):
    import json

    cases = _make_full_cases()
    data = {"format": "firewall.results.v1", "cases": cases}
    f = tmp_path / "results.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    rc = main([str(f), "--rotation", "--missing-as-zero"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert set(parsed["by_family"].keys()) == set(ATTACK_FAMILIES)
