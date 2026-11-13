"""Render the README result figures (SVG) from the committed result files.

Run from agent/:  uv run --with matplotlib python tools/plot_results.py
matplotlib is deliberately not in pyproject.toml. Every number is read from a
JSON file under docs/results/ at run time; output bytes are deterministic.
"""

from __future__ import annotations

import json
import textwrap
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from firewall_agent.config import REPO_ROOT  # noqa: E402

RESULTS = REPO_ROOT / "docs" / "results"
FIGURES = RESULTS / "figures"
PRESET = "jev_fusion_conformal"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelsize": 10, "legend.fontsize": 8.5, "legend.frameon": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.15, "grid.linestyle": "-",
    "lines.linewidth": 1.8, "lines.markersize": 5,
    "svg.hashsalt": "eclipse", "svg.fonttype": "none",
})

# Okabe-Ito, one fixed color per meaning across every figure.
C_ALLOW = "#D55E00"        # attack allowed (the failure)
C_HOLD = "#E69F00"         # held for approval
C_BLOCK = "#0072B2"        # blocked
C_BENIGN_HELD = "#CC79A7"  # legitimate payment held
C_BASE = "#B0BEC5"         # baseline / recedes
C_CURRENT = "#009E73"      # current checker
BACKEND_COLORS = ["#56B4E9", "#F0E442", "#444444", "#999999"]  # no outcome color reused
OUTCOME_COLORS = {"allow": C_ALLOW, "hold": C_HOLD, "block": C_BLOCK}

SETS = ("main", "external", "red team")


def load(name: str) -> dict:
    path = RESULTS / name
    if not path.exists():
        raise SystemExit(f"{name}: missing file")
    return json.loads(path.read_text(encoding="utf-8"))


def field(doc: dict, name: str, *keys: str):
    cur = doc
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            raise SystemExit(f"{name}: missing {'.'.join(keys)}")
        cur = cur[k]
    return cur


def preset_row(doc: dict, name: str, label: str = PRESET) -> dict:
    for row in field(doc, name, "configurations"):
        if row.get("configuration") == label:
            return row
    raise SystemExit(f"{name}: missing configurations[{label}]")


def case_counts(doc: dict, name: str) -> dict:
    """Attack outcome counts and benign held/blocked counted from `cases`."""
    c = {"attacks": 0, "allow": 0, "hold": 0, "block": 0, "benign": 0, "benign_held": 0, "benign_blocked": 0}
    for case in field(doc, name, "cases"):
        if "label" not in case or "outcome" not in case:
            raise SystemExit(f"{name}: missing cases[].label/outcome")
        if case["label"] == "attack":
            c["attacks"] += 1
            c[case["outcome"]] += 1
        else:
            c["benign"] += 1
            c["benign_held"] += case["outcome"] == "hold"
            c["benign_blocked"] += case["outcome"] == "block"
    return c


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, format="svg", metadata={"Date": None}, bbox_inches="tight")
    plt.close(fig)


def footnote(fig, text: str) -> None:
    """Place the source note below everything already drawn (call last)."""
    fig.canvas.draw()
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    fig.text(bb.x0 / fig.get_figwidth(), (bb.y0 - 0.08) / fig.get_figheight(), text,
             fontsize=7.5, color="#555", ha="left", va="top")


def pct(n: float, d: float) -> float:
    return 100.0 * n / d if d else 0.0


# ---------------------------------------------------------------- data

def current_sets() -> dict:
    """Per set: attack/benign counts for the current checker (from cases)."""
    out = {}
    for label, fname in zip(SETS, ("flagging-main.json", "flagging-external.json", "flagging-redteam.json")):
        doc = load(fname)
        cases = case_counts(doc, fname)
        if label != "red team":
            row = preset_row(doc, fname)
            for k, rk in (("allow", "missed_attacks"), ("hold", "held_attacks"), ("block", "blocked_attacks")):
                if rk not in row:
                    raise SystemExit(f"{fname}: missing configurations[{PRESET}].{rk}")
            cases["row_allow"] = row["missed_attacks"]
            cases["row_hold"] = row["held_attacks"]
            cases["row_block"] = row["blocked_attacks"]
            cases["row_benign_held"] = row["false_holds"]
            cases["row_benign_blocked"] = row["false_blocks"]
            for k in ("allow", "hold", "block"):
                if cases[k] != cases[f"row_{k}"]:
                    raise SystemExit(f"{fname}: cases ({k}={cases[k]}) disagree with configurations row ({cases['row_' + k]})")
        out[label] = {**cases, "file": fname}
    return out


def baseline_sets() -> dict:
    out = {}
    for label, fname in zip(SETS, ("results.json", "external-results.json", "redteam-results.json")):
        doc = load(fname)
        row = preset_row(doc, fname)
        out[label] = {
            "attacks": field(doc, fname, "attack_total"),
            "benign": field(doc, fname, "benign_total"),
            "allow": field(row, fname, "missed_attacks"),
            "benign_held": field(row, fname, "false_holds"),
            "file": fname,
        }
    return out


# ---------------------------------------------------------------- figures

def fig_outcomes_current(cur: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 2.9), gridspec_kw={"width_ratios": [1.5, 1]})
    ys = np.arange(len(SETS))[::-1]
    for y, s in zip(ys, SETS):
        d = cur[s]
        left = 0.0
        for k, color in (("allow", C_ALLOW), ("hold", C_HOLD), ("block", C_BLOCK)):
            w = pct(d[k], d["attacks"])
            a1.barh(y, w, left=left, color=color, height=0.55, edgecolor="white", linewidth=0.5,
                    label=k if y == ys[0] else None)
            if d[k]:
                a1.text(left + w / 2, y, f"{d[k]}", ha="center", va="center", fontsize=8, color="white")
            left += w
    a1.set_yticks(ys)
    a1.set_yticklabels([f"{s}\n(n={cur[s]['attacks']} attacks)" for s in SETS])
    a1.set_xlim(0, 100)
    a1.set_xlabel("% of attacks")
    a1.set_title("Attack outcomes")
    a1.grid(axis="y", visible=False)
    a1.legend(["allowed", "held", "blocked"], ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.28))

    sub = ("main", "external")
    x = np.arange(len(sub))
    w = 0.36
    held = [pct(cur[s]["benign_held"], cur[s]["benign"]) for s in sub]
    blocked = [pct(cur[s]["benign_blocked"], cur[s]["benign"]) for s in sub]
    b1 = a2.bar(x - w / 2, held, w, color=C_BENIGN_HELD, label="held")
    b2 = a2.bar(x + w / 2, blocked, w, color=C_BLOCK, label="blocked")
    for bars, key in ((b1, "benign_held"), (b2, "benign_blocked")):
        for bar, s in zip(bars, sub):
            a2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    f"{cur[s][key]}/{cur[s]['benign']}", ha="center", va="bottom", fontsize=8)
    a2.set_xticks(x)
    a2.set_xticklabels(sub)
    a2.set_ylabel("% of benign payments")
    a2.set_title("Benign payments")
    a2.legend(loc="upper left")
    a2.set_ylim(0, max(held + blocked + [1]) * 1.4)
    fig.suptitle(f"Current checker, preset {PRESET}", y=1.04, fontsize=11, fontweight="bold")
    footnote(fig, "Source: docs/results/flagging-main.json, flagging-external.json, flagging-redteam.json (counts from cases; red team has no benign cases)")
    save(fig, "fig-outcomes-current.svg")


def fig_redteam_current() -> None:
    fname = "flagging-redteam.json"
    cases = field(load(fname), fname, "cases")
    n = len(cases)
    cols = 6
    rows = -(-n // cols)
    fig, ax = plt.subplots(figsize=(7.2, 0.95 * rows + 1.0))
    for i, c in enumerate(cases):
        for k in ("name", "outcome"):
            if k not in c:
                raise SystemExit(f"{fname}: missing cases[].{k}")
        r, col = divmod(i, cols)
        ax.add_patch(plt.Rectangle((col, -r), 0.94, 0.84, color=OUTCOME_COLORS[c["outcome"]]))
        ax.text(col + 0.47, -r + 0.52, c["name"], ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        ax.text(col + 0.47, -r + 0.22, c["outcome"], ha="center", va="center", fontsize=7.5, color="white")
    ax.set_xlim(-0.05, cols)
    ax.set_ylim(-rows + 0.9, 1.0)
    ax.axis("off")
    ax.grid(False)
    counts = {k: sum(c["outcome"] == k for c in cases) for k in OUTCOME_COLORS}
    handles = [plt.Rectangle((0, 0), 1, 1, color=OUTCOME_COLORS[k]) for k in OUTCOME_COLORS]
    ax.legend(handles, [f"{k} ({counts[k]})" for k in OUTCOME_COLORS], ncol=3, loc="upper center", bbox_to_anchor=(0.5, 0.02))
    ax.set_title(f"Red team: {n} scenarios, outcome per scenario ({counts['allow']} attacks allowed)")
    footnote(fig, "Source: docs/results/flagging-redteam.json (cases)")
    save(fig, "fig-redteam-current.svg")


def fig_baseline_vs_current(cur: dict, base: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.5, 3.0))
    x = np.arange(len(SETS))
    w = 0.36
    panels = (
        (a1, "Attacks allowed (%)", lambda d: pct(d["allow"], d["attacks"]), SETS, lambda d: (d["allow"], d["attacks"])),
        (a2, "Benign held (%)", lambda d: pct(d["benign_held"], d["benign"]), ("main", "external"), lambda d: (d["benign_held"], d["benign"])),
    )
    for ax, title, f, sets, cnt in panels:
        xs = np.arange(len(sets))
        for off, data, color, lab in ((-w / 2, base, C_BASE, "baseline"), (w / 2, cur, C_CURRENT, "current")):
            vals = [f(data[s]) for s in sets]
            bars = ax.bar(xs + off, vals, w, color=color, label=lab, edgecolor="white", linewidth=0.5)
            for bar, s in zip(bars, sets):
                n, d = cnt(data[s])
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{n}/{d}",
                        ha="center", va="bottom", fontsize=7.5)
        ax.set_xticks(xs)
        ax.set_xticklabels(sets)
        ax.set_title(title)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.12)
    a1.legend(ncol=2, loc="upper center", bbox_to_anchor=(1.1, -0.1))
    del x
    fig.suptitle(f"Baseline vs current checker, preset {PRESET}", y=1.03, fontsize=11, fontweight="bold")
    footnote(fig, "Source: baseline docs/results/results.json, external-results.json, redteam-results.json; current flagging-main.json, flagging-external.json, flagging-redteam.json")
    save(fig, "fig-baseline-vs-current.svg")


def fig_family_main() -> None:
    fname = "flagging-main.json"
    fam = field(load(fname), fname, "by_family")
    items = []
    for name, v in fam.items():
        for k in ("total", "allow", "hold", "block"):
            if k not in v:
                raise SystemExit(f"{fname}: missing by_family.{name}.{k}")
        if v["allow"] + v["hold"] + v["block"] == v["total"] and name != "none":
            items.append((name, v))
    if not items:
        raise SystemExit(f"{fname}: missing by_family attack families")
    fig, ax = plt.subplots(figsize=(7.5, 0.55 * len(items) + 1.6))
    ys = np.arange(len(items))[::-1]
    for y, (name, v) in zip(ys, items):
        left = 0.0
        for k, color in (("allow", C_ALLOW), ("hold", C_HOLD), ("block", C_BLOCK)):
            w = pct(v[k], v["total"])
            ax.barh(y, w, left=left, color=color, height=0.6, edgecolor="white", linewidth=0.5,
                    label={"allow": "allowed", "hold": "held", "block": "blocked"}[k] if y == ys[0] else None)
            if v[k]:
                ax.text(left + w / 2, y, str(v[k]), ha="center", va="center", fontsize=8, color="white")
            left += w
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n} (n={v['total']})" for n, v in items])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of attacks in family")
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.set_title(f"Main set by attack family, preset {PRESET}")
    footnote(fig, "Source: docs/results/flagging-main.json (by_family)")
    save(fig, "fig-family-main.svg")


def fig_layers_main() -> None:
    cur_doc, base_doc = load("flagging-main.json"), load("results.json")
    cur_rows = {r["configuration"]: r for r in field(cur_doc, "flagging-main.json", "configurations")}
    base_rows = {r["configuration"]: r for r in field(base_doc, "results.json", "configurations")}
    labels = list(cur_rows)
    for lab in labels:
        if lab not in base_rows:
            raise SystemExit(f"results.json: missing configurations[{lab}]")
    na = field(cur_doc, "flagging-main.json", "attack_total")
    nb = field(cur_doc, "flagging-main.json", "benign_total")
    nab = field(base_doc, "results.json", "attack_total")
    nbb = field(base_doc, "results.json", "benign_total")
    ys = np.arange(len(labels))[::-1]
    h = 0.36
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
    for y, lab in zip(ys, labels):
        c, b = cur_rows[lab], base_rows[lab]
        for ax, key, (nc, nbse) in ((a1, "missed_attacks", (na, nab)), (a2, "false_holds", (nb, nbb))):
            for off, row, n, color, nm in ((h / 2, c, nc, C_CURRENT, "current"), (-h / 2, b, nbse, C_BASE, "baseline")):
                v = pct(row[key], n)
                ax.barh(y + off, v, h * 0.95, color=color, label=nm if (y == ys[0] and ax is a1) else None)
                ax.text(v + 0.8, y + off, f"{row[key]}/{n}", va="center", fontsize=7.5)
    a1.set_yticks(ys)
    a1.set_yticklabels(labels)
    a1.set_title("Attacks allowed (%)")
    a2.set_title("Benign held (%)")
    for ax, xl in ((a1, "% of attacks"), (a2, "% of benign")):
        ax.set_xlim(0, max(p.get_width() for p in ax.patches) * 1.3 or 1)
        ax.set_xlabel(xl)
        ax.grid(axis="y", visible=False)
    a1.legend(loc="lower right")
    fig.suptitle("Main set, what each layer contributes", y=1.02, fontsize=11, fontweight="bold")
    footnote(fig, "Source: current docs/results/flagging-main.json (configurations); baseline docs/results/results.json (configurations), matched by configuration")
    save(fig, "fig-layers-main.svg")


def fig_classifier_bench() -> None:
    fname = "classifier-bench.json"
    corpora = field(load(fname), fname, "corpora")
    backends = []
    for c in corpora:
        for b in field(c, fname, "backends"):
            if b["backend"] not in backends:
                backends.append(b["backend"])
    short = lambda b: b.split("/")[-1]
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.8), sharex=True)
    x = np.arange(len(corpora))
    w = 0.8 / len(backends)
    for ax, metric, title in zip(axes, ("auroc", "recall"), ("AUROC", "Recall at threshold 0.5")):
        for i, be in enumerate(backends):
            for j, c in enumerate(corpora):
                row = next((b for b in c["backends"] if b["backend"] == be), None)
                if row is None or metric not in row:
                    raise SystemExit(f"{fname}: missing corpora[{c.get('name')}].backends[{be}].{metric}")
                xpos = x[j] + (i - (len(backends) - 1) / 2) * w
                v = row[metric]
                color = BACKEND_COLORS[i % len(BACKEND_COLORS)]
                if v is None:
                    ax.bar(xpos, 1.0, w * 0.9, facecolor="none", edgecolor="#888", hatch="////", linewidth=0.6)
                    ax.text(xpos, 0.5, "n/a", ha="center", va="center", fontsize=7.5, rotation=90, color="#555")
                else:
                    ax.bar(xpos, v, w * 0.9, color=color, edgecolor="#333", linewidth=0.4, label=short(be) if j == 0 else None)
                    ax.text(xpos, v + 0.01, f"{v:.2f}", ha="center", va="bottom", fontsize=7, rotation=90)
        ax.set_ylim(0, 1.18)
        ax.set_ylabel(title)
        ax.grid(axis="x", visible=False)
    axes[0].legend(ncol=len(backends), loc="upper center", bbox_to_anchor=(0.5, 1.28))
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(["\n".join(textwrap.wrap(c["name"], 16)) for c in corpora], fontsize=7.5)
    footnote(axes[1].figure, "Source: docs/results/classifier-bench.json (corpora[].backends); hatched = n/a (null, e.g. no negatives)")
    save(fig, "fig-classifier-bench.svg")


def fig_classifier_refuse(doc: dict, fname: str = "autoresearch-classifier.json") -> None:
    grid = field(doc, fname, "grid")
    inc = field(doc, fname, "incumbent")
    sel = field(doc, fname, "selected")
    ext = field(doc, fname, "external_test")
    thresholds = field(doc, fname, "thresholds")
    backends = []
    for g in grid:
        if g["backend"] not in backends:
            backends.append(g["backend"])
    xi = {t: i for i, t in enumerate(thresholds)}
    fig, ax = plt.subplots(figsize=(8.0, 4.6))

    def point(cfg):
        for g in grid:
            if g["backend"] == cfg["backend"] and g["threshold"] == cfg["threshold"]:
                return xi[g["threshold"]], g["main"]["benign_held"] + g["external_tune"]["benign_held"]
        raise SystemExit(f"{fname}: missing grid row for {cfg}")

    for i, be in enumerate(backends):
        rows = sorted((g for g in grid if g["backend"] == be), key=lambda g: g["threshold"])
        xs = [xi[g["threshold"]] for g in rows]
        ys = [g["main"]["benign_held"] + g["external_tune"]["benign_held"] for g in rows]
        color = BACKEND_COLORS[i % len(BACKEND_COLORS)]
        ax.plot(xs, ys, marker="o", color=color, label=be)
        for g, x_, y_ in zip(rows, xs, ys):
            ax.annotate(f"rt {g['redteam']['attacks_allowed']}", (x_, y_), textcoords="offset points",
                        xytext=(0, -14 - 9 * i), ha="center", va="top", fontsize=7, color=color)
    ix, iy = point(inc)
    sx, sy = point(sel)
    ax.scatter([ix], [iy], s=190, facecolors="none", edgecolors="black", linewidths=1.4, zorder=5, label="incumbent")
    ax.scatter([sx], [sy], s=170, marker="*", color="black", zorder=6, label="selected")
    ax.set_xticks(range(len(thresholds)))
    ax.set_xticklabels([str(t) for t in thresholds])
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.margins(y=0.2)
    ax.set_xlabel("FUSION_INJECTION_THRESHOLD")
    ax.set_ylabel("Benign held (main + external_tune)")
    ax.set_title("Injection-threshold sweep, offline re-fuse (rt = red-team attacks allowed)")
    ax.legend(loc="upper right")

    def fmt(r):
        return f"benign held {r['benign_held']}/{r['n_benign']}, attacks allowed {r['attacks_allowed']}/{r['n_attack']}"

    inc_e, sel_e = ext["incumbent"], ext["selected"]
    ax.text(0.02, 0.04,
            f"external_test\nincumbent ({inc['backend']}@{inc['threshold']}): {fmt(inc_e)}\n"
            f"selected ({sel['backend']}@{sel['threshold']}): {fmt(sel_e)}",
            transform=ax.transAxes, fontsize=7.5, va="bottom", ha="left",
            bbox={"boxstyle": "round", "facecolor": "white", "edgecolor": "#999", "alpha": 0.9})
    footnote(fig, f"Source: docs/results/{fname} (grid, incumbent, selected, external_test)")
    save(fig, "fig-classifier-refuse.svg")


def main() -> None:
    cur = current_sets()
    base = baseline_sets()
    fig_outcomes_current(cur)
    fig_redteam_current()
    fig_baseline_vs_current(cur, base)
    fig_family_main()
    fig_layers_main()
    fig_classifier_bench()
    fig_classifier_refuse(load("autoresearch-classifier.json"))
    print(f"wrote {len(list(FIGURES.glob('*.svg')))} figures to {FIGURES}")


if __name__ == "__main__":
    main()
