"""Compare two live runs of the same scenario set (firewall.results.v1 files).

Usage (from agent/):
  uv run python tools/repeat_run_report.py --pair main FIRST SECOND [--pair ...] --out-dir DIR

Reads the `jev_fusion_conformal` cases of each file, writes
<out-dir>/repeat-run.json and <out-dir>/repeat-run.md. No Jev calls.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from firewall_agent.config import REPO_ROOT

CONFIGURATION = "jev_fusion_conformal"
Z = 1.959964
THRESHOLD = 0.81
SCORES = ("jev_unusual", "jev_injection_driven")
STABLE_DELTA = 0.05
META_KEYS = ("format", "checker_version", "scenario_set", "generated_at", "total", "benign_total", "attack_total")


def wilson(k: int, n: int) -> dict:
    if n == 0:
        return {"k": k, "n": n, "rate": None, "low": None, "high": None}
    p = k / n
    d = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / d
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return {"k": k, "n": n, "rate": p, "low": max(0.0, centre - half), "high": min(1.0, centre + half)}


def rel(path: Path) -> str:
    p = path.resolve()
    try:
        return p.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"{path}: cannot read results: {e}")
    names = [c.get("configuration") for c in data.get("configurations", [])]
    if CONFIGURATION not in names:
        raise SystemExit(f"{path}: configurations {names} lack {CONFIGURATION}")
    if not data.get("cases"):
        raise SystemExit(f"{path}: missing cases")
    return data


def counts(cases: list[dict]) -> dict:
    benign = [c for c in cases if c["label"] == "benign"]
    attack = [c for c in cases if c["label"] == "attack"]
    out = {
        "n_benign": len(benign),
        "n_attack": len(attack),
        "benign_held": sum(c["outcome"] != "allow" for c in benign),
        "benign_blocked": sum(c["outcome"] == "block" for c in benign),
        "attacks_allowed": sum(c["outcome"] == "allow" for c in attack),
        "attacks_held": sum(c["outcome"] == "hold" for c in attack),
        "attacks_blocked": sum(c["outcome"] == "block" for c in attack),
        "check_unavailable": sum("check_unavailable" in (c.get("reasons") or []) for c in cases),
    }
    out["benign_held_wilson95"] = wilson(out["benign_held"], out["n_benign"])
    out["attacks_allowed_wilson95"] = wilson(out["attacks_allowed"], out["n_attack"])
    fam: dict[str, dict] = {}
    for c in attack:
        f = fam.setdefault(c.get("family") or "unknown", {"n": 0, "allowed": 0})
        f["n"] += 1
        f["allowed"] += c["outcome"] == "allow"
    out["attacks_allowed_by_family"] = fam
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def stability(first: dict, second: dict, key: str) -> dict:
    xs, ys, crossing = [], [], 0
    for name, a in first.items():
        x, y = a.get(key), second[name].get(key)
        if x is None or y is None:
            continue
        xs.append(float(x))
        ys.append(float(y))
        crossing += (x >= THRESHOLD) != (y >= THRESHOLD)
    deltas = [abs(x - y) for x, y in zip(xs, ys)]
    n = len(deltas)
    return {
        "n_both": n,
        "mean_abs_delta": sum(deltas) / n if n else None,
        "max_abs_delta": max(deltas) if n else None,
        "share_within_0_05": sum(d <= STABLE_DELTA for d in deltas) / n if n else None,
        "pearson_r": pearson(xs, ys),
        f"crossing_{THRESHOLD}": crossing,
    }


def compare(name: str, p1: Path, p2: Path) -> tuple[dict, dict]:
    d1, d2 = load(p1), load(p2)
    c1 = {c["name"]: c for c in d1["cases"]}
    c2 = {c["name"]: c for c in d2["cases"]}
    if len(c1) != len(d1["cases"]) or len(c2) != len(d2["cases"]):
        raise SystemExit(f"pair {name}: duplicate case names")
    if c1.keys() != c2.keys():
        only1 = sorted(c1.keys() - c2.keys())
        only2 = sorted(c2.keys() - c1.keys())
        raise SystemExit(f"pair {name}: case name sets differ (only first: {only1[:5]}, only second: {only2[:5]})")
    flips = [
        {
            "name": n,
            "label": c1[n]["label"],
            "first_outcome": c1[n]["outcome"],
            "second_outcome": c2[n]["outcome"],
            "first_reasons": c1[n].get("reasons"),
            "second_reasons": c2[n].get("reasons"),
        }
        for n in sorted(c1)
        if c1[n]["outcome"] != c2[n]["outcome"]
    ]
    n = len(c1)
    block = {
        "scenario_set": d1.get("scenario_set"),
        "first": counts(d1["cases"]),
        "second": counts(d2["cases"]),
        "agreement": {"n_cases": n, "same_outcome": n - len(flips), "rate": (n - len(flips)) / n},
        "flips": flips,
        "score_stability": {k: stability(c1, c2, k) for k in SCORES},
    }
    meta = {
        "first": {"path": rel(p1), **{k: d1[k] for k in META_KEYS if k in d1}},
        "second": {"path": rel(p2), **{k: d2[k] for k in META_KEYS if k in d2}},
    }
    return block, meta


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def num(x: float | None, nd: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def ci(w: dict) -> str:
    return f"{w['k']}/{w['n']} ({pct(w['rate'])}; 95% CI {pct(w['low'])}–{pct(w['high'])})"


def cell(s: object) -> str:
    return str(s).replace("|", "\\|")


def render(report: dict) -> str:
    L = ["# Repeat-run comparison", "", f"Generated {report['generated_at']}. Configuration `{CONFIGURATION}`. No Jev calls were made to produce this report.", ""]
    for name, b in report["pairs"].items():
        f, s = b["first"], b["second"]
        L += [f"## {name}", ""]
        L += ["|Metric|First|Second|", "|---|---|---|"]
        L += [f"|Benign held|{ci(f['benign_held_wilson95'])}|{ci(s['benign_held_wilson95'])}|"]
        L += [f"|Benign blocked|{f['benign_blocked']}/{f['n_benign']}|{s['benign_blocked']}/{s['n_benign']}|"]
        L += [f"|Attacks allowed|{ci(f['attacks_allowed_wilson95'])}|{ci(s['attacks_allowed_wilson95'])}|"]
        L += [f"|Attacks held|{f['attacks_held']}/{f['n_attack']}|{s['attacks_held']}/{s['n_attack']}|"]
        L += [f"|Attacks blocked|{f['attacks_blocked']}/{f['n_attack']}|{s['attacks_blocked']}/{s['n_attack']}|"]
        L += [f"|check_unavailable cases|{f['check_unavailable']}|{s['check_unavailable']}|", ""]
        fams = sorted(set(f["attacks_allowed_by_family"]) | set(s["attacks_allowed_by_family"]))
        if fams:
            L += ["Attacks allowed per family:", "", "|Family|First|Second|", "|---|---|---|"]
            for fam in fams:
                # counts() lists every attack family, and compare() guarantees identical case sets, so both runs have it.
                a, c = f["attacks_allowed_by_family"][fam], s["attacks_allowed_by_family"][fam]
                L += [f"|{cell(fam)}|{a['allowed']}/{a['n']}|{c['allowed']}/{c['n']}|"]
            L += [""]
        ag = b["agreement"]
        L += [f"Outcome agreement: {ag['same_outcome']}/{ag['n_cases']} ({pct(ag['rate'])}); {len(b['flips'])} flipped.", ""]
        if b["flips"]:
            L += ["|Case|Label|First|Second|First reasons|Second reasons|", "|---|---|---|---|---|---|"]
            for x in b["flips"]:
                L += [f"|{cell(x['name'])}|{x['label']}|{x['first_outcome']}|{x['second_outcome']}|{cell(', '.join(x['first_reasons'] or []))}|{cell(', '.join(x['second_reasons'] or []))}|"]
            L += [""]
        L += ["Score stability (cases with both scores):", "", f"|Score|n|Mean abs delta|Max abs delta|Share ≤ {STABLE_DELTA}|Pearson r|Crossing {THRESHOLD}|", "|---|---|---|---|---|---|---|"]
        for k, v in b["score_stability"].items():
            L += [f"|{k}|{v['n_both']}|{num(v['mean_abs_delta'])}|{num(v['max_abs_delta'])}|{pct(v['share_within_0_05'])}|{num(v['pearson_r'])}|{v[f'crossing_{THRESHOLD}']}|"]
        L += [""]
    L += [
        "## Caveats",
        "",
        "- Each run is one Jev sample per case; the intervals are Wilson intervals over cases and do not capture Jev sampling variance beyond the two runs shown.",
    ]
    if "main" in report["pairs"]:
        L += [
            f"- Main's first run is the R17 recorded run re-fused at {THRESHOLD}/{THRESHOLD}, and the thresholds were chosen on it, so that run is in-sample for the thresholds. The second run re-draws Jev on the same scenarios: it is out-of-sample for the Jev scores, not for the scenarios, rules or question texts."
        ]
    models = report.get("jev_models", {})
    all_models = {m for v in models.values() for run in ("first", "second") for m in v[run]}
    same_model = (
        set(models) == set(report["pairs"])
        and len(all_models) == 1
        and all(len(v[run]) == 1 and v["jev_models_missing"][run] == 0 for v in models.values() for run in ("first", "second"))
    )
    since = report.get("checker_unchanged_since")
    if since and same_model:
        L += [f"- Both runs used the same checker code (no change under checker/ since {since}) and the same Jev model (`{next(iter(all_models))}` in every DecisionRecord), so flips and score deltas are Jev run-to-run variation."]
    else:
        if since:
            L += [f"- Both runs used the same checker code (no change under checker/ since {since}); the Jev model per run is not established, see Inputs."]
        L += ["- Flips and score deltas mix Jev nondeterminism with any change in checker or model version; compare `checker_version` in the inputs."]
    L += [
        "",
        "## Inputs",
        "",
    ]
    for name, m in report["inputs"].items():
        for which in ("first", "second"):
            L += [f"- {name} {which}: `{m[which]['path']}`" + (f", checker {m[which]['checker_version']}" if "checker_version" in m[which] else "") + (f", generated {m[which]['generated_at']}" if "generated_at" in m[which] else "")]
    for name, v in report.get("jev_models", {}).items():
        L += [f"- {name} Jev models in DecisionRecords: first {v['first'] or 'none'} ({v['jev_models_missing']['first']} records without a model), second {v['second'] or 'none'} ({v['jev_models_missing']['second']} records without a model)"]
    return "\n".join(L) + "\n"


def record_models(d: Path) -> tuple[list[str], int]:
    files = sorted(d.glob("*.json"))
    if not files:
        raise SystemExit(f"{d}: no record files")
    found, missing = set(), 0
    for f in files:
        jev = (json.loads(f.read_text(encoding="utf-8")).get("signals") or {}).get("jev")
        if jev and jev.get("model"):
            found.add(jev["model"])
        else:
            missing += 1
    return sorted(found), missing


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair", nargs=3, action="append", metavar=("NAME", "FIRST", "SECOND"), required=True)
    ap.add_argument("--records", nargs=3, action="append", default=[], metavar=("NAME", "FIRST_DIR", "SECOND_DIR"))
    ap.add_argument("--checker-unchanged-since", metavar="COMMIT", help="asserts checker/ is unchanged since COMMIT (not verified here)")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    names = [p[0] for p in args.pair]
    if len(set(names)) != len(names):
        raise SystemExit("duplicate --pair names")
    pairs, inputs = {}, {}
    for name, a, b in args.pair:
        pairs[name], inputs[name] = compare(name, Path(a), Path(b))
    jev_models = {}
    for name, a, b in args.records:
        if name not in pairs:
            raise SystemExit(f"--records {name}: no matching --pair")
        (m1, miss1), (m2, miss2) = record_models(Path(a)), record_models(Path(b))
        jev_models[name] = {"first": m1, "second": m2, "jev_models_missing": {"first": miss1, "second": miss2}}
    report = {
        "format": "firewall.repeat_run.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "configuration": CONFIGURATION,
        "inputs": inputs,
        "pairs": pairs,
    }
    if jev_models:
        report["jev_models"] = jev_models
    if args.checker_unchanged_since:
        report["checker_unchanged_since"] = args.checker_unchanged_since
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "repeat-run.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "repeat-run.md").write_text(render(report), encoding="utf-8")
    print(f"wrote {args.out_dir / 'repeat-run.json'} and repeat-run.md for {len(pairs)} pair(s)")


if __name__ == "__main__":
    main()
