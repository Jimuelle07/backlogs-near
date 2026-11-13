"""Render the README result figures (SVG) from the committed result files.

Run from agent/:  uv run --with matplotlib python tools/plot_results.py
matplotlib is deliberately not in pyproject.toml. Every number is read from a
JSON file under docs/results/ at run time; output bytes are deterministic.
"""

from __future__ import annotations

import argparse
import json
import textwrap
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from firewall_agent.config import REPO_ROOT  # noqa: E402

RESULTS = REPO_ROOT / "docs" / "results"
FIGURES = RESULTS / "figures"
PRESET = "jev_fusion_conformal"

FONT_STACK = ["Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]
INK, MUTED = "#222222", "#666666"
W1, W2 = 7.0, 9.0  # figure widths (in): single-panel / two-panel

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": FONT_STACK,
    "font.size": 11, "text.color": INK,
    "axes.titlesize": 12.5, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.labelsize": 10.5, "axes.labelcolor": "#444444",
    "xtick.labelsize": 10, "ytick.labelsize": 10,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK, "ytick.labelcolor": INK,
    "xtick.major.size": 3, "ytick.major.size": 3, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "legend.fontsize": 10, "legend.frameon": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "figure.facecolor": "white", "savefig.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#8A8A8A", "axes.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "grid.alpha": 0.15, "grid.linestyle": "-", "grid.color": "#000000",
    "lines.linewidth": 1.8, "lines.markersize": 5,
    "svg.hashsalt": "eclipse", "svg.fonttype": "none",
})

# Okabe-Ito, one fixed color per meaning across every figure.
C_ALLOW = "#D55E00"        # attack allowed (the failure)
C_HOLD = "#E69F00"         # held for approval
C_BLOCK = "#0072B2"        # blocked
C_BENIGN_HELD = "#CC79A7"  # legitimate payment held
C_BASE = "#B0BEC5"         # baseline / first run (recedes)
C_CURRENT = "#009E73"      # current checker
BACKEND_COLORS = ["#56B4E9", "#9AA5AD", "#444444", "#F0E442"]  # never an outcome color
OUTCOME_COLORS = {"allow": C_ALLOW, "hold": C_HOLD, "block": C_BLOCK}
OUTCOME_LABELS = {"allow": "allowed", "hold": "held", "block": "blocked"}
TEXT_ON = {C_ALLOW: "white", C_HOLD: INK, C_BLOCK: "white"}  # label contrast per fill
TITLE_PAD = 26  # leaves room for a frameless legend between title and plot

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


WRITTEN: list[Path] = []


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, format="svg", metadata={"Date": None}, bbox_inches="tight")
    WRITTEN.append(FIGURES / name)
    plt.close(fig)


def footnote(fig, text: str) -> None:
    """Place a small grey, wrapped source note below everything already drawn (call last)."""
    text = "\n".join(textwrap.wrap(text, width=int(fig.get_figwidth() * 15)))
    fig.canvas.draw()
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    fig.text(bb.x0 / fig.get_figwidth(), (bb.y0 - 0.12) / fig.get_figheight(), text,
             fontsize=7.5, color="#777777", ha="left", va="top", linespacing=1.4)


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

def swatches(pairs):
    """Legend handles/labels from (color, label) pairs."""
    return [Patch(facecolor=c, edgecolor="none") for c, _ in pairs], [lab for _, lab in pairs]


def head(ax, title: str, pairs=None) -> None:
    """Left-aligned title with an optional frameless legend row between title and plot."""
    ax.set_title(title, pad=TITLE_PAD)
    if pairs:
        handles, labels = swatches(pairs)
        ax.legend(handles, labels, ncol=len(pairs), loc="lower left", bbox_to_anchor=(0, 1.0),
                  borderaxespad=0.2, handlelength=1.1, handleheight=1.0, columnspacing=1.6, handletextpad=0.5)


def pct_axis(axis) -> None:
    axis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%g%%"))


def stacked_rows(ax, ys, rows, height=0.55) -> None:
    """Horizontal 100% stacked bars; rows = [{allow, hold, block, total}]; segment labels are counts."""
    for y, v in zip(ys, rows):
        left = 0.0
        for k in ("allow", "hold", "block"):
            w = pct(v[k], v["total"])
            color = OUTCOME_COLORS[k]
            ax.barh(y, w, left=left, color=color, height=height, edgecolor="white", linewidth=0.8)
            if v[k]:
                ax.text(left + w / 2, y, str(v[k]), ha="center", va="center", fontsize=9.5,
                        fontweight="semibold", color=TEXT_ON[color])
            left += w
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 25))
    pct_axis(ax.xaxis)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)


def bar_label(ax, bar, text: str, dy: float, size=9) -> None:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + dy, text, ha="center", va="bottom",
            fontsize=size, color=INK)


def fig_outcomes_current(cur: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 3.0), gridspec_kw={"width_ratios": [1.7, 1], "wspace": 0.45})
    ys = np.arange(len(SETS))[::-1]
    stacked_rows(a1, ys, [{**cur[s], "total": cur[s]["attacks"]} for s in SETS])
    a1.set_yticks(ys)
    a1.set_yticklabels([f"{s}  (n={cur[s]['attacks']})" for s in SETS])
    head(a1, "Attack outcomes", [(OUTCOME_COLORS[k], OUTCOME_LABELS[k]) for k in OUTCOME_COLORS])

    sub = ("main", "external")
    x = np.arange(len(sub))
    w = 0.34
    held = [pct(cur[s]["benign_held"], cur[s]["benign"]) for s in sub]
    blocked = [pct(cur[s]["benign_blocked"], cur[s]["benign"]) for s in sub]
    b1 = a2.bar(x - w / 2 - 0.01, held, w, color=C_BENIGN_HELD, edgecolor="white", linewidth=0.6)
    b2 = a2.bar(x + w / 2 + 0.01, blocked, w, color=C_BLOCK, edgecolor="white", linewidth=0.6)
    top = max(held + blocked + [1])
    for bars, key in ((b1, "benign_held"), (b2, "benign_blocked")):
        for bar, s in zip(bars, sub):
            bar_label(a2, bar, f"{cur[s][key]}/{cur[s]['benign']}", top * 0.02)
    a2.set_xticks(x)
    a2.set_xticklabels(sub)
    a2.set_xlim(-0.6, len(sub) - 0.4)
    a2.set_ylabel("% of benign payments")
    pct_axis(a2.yaxis)
    a2.set_ylim(0, top * 1.25)
    head(a2, "Benign payments", [(C_BENIGN_HELD, "held"), (C_BLOCK, "blocked")])
    footnote(fig, f"Preset {PRESET}. Source: docs/results/flagging-main.json, flagging-external.json, flagging-redteam.json (counts from cases; red team has no benign cases)")
    save(fig, "fig-outcomes-current.svg")


def fig_redteam_current() -> None:
    fname = "flagging-redteam.json"
    cases = field(load(fname), fname, "cases")
    n = len(cases)
    cols = 6
    rows = -(-n // cols)
    fig, ax = plt.subplots(figsize=(W1, 0.9 * rows + 0.9))
    for i, c in enumerate(cases):
        for k in ("name", "outcome"):
            if k not in c:
                raise SystemExit(f"{fname}: missing cases[].{k}")
        r, col = divmod(i, cols)
        color = OUTCOME_COLORS[c["outcome"]]
        ax.add_patch(plt.Rectangle((col + 0.03, -r + 0.03), 0.94, 0.84, facecolor=color, edgecolor="none"))
        ax.text(col + 0.5, -r + 0.57, c["name"], ha="center", va="center", fontsize=9, color=TEXT_ON[color], fontweight="semibold")
        ax.text(col + 0.5, -r + 0.30, OUTCOME_LABELS[c["outcome"]], ha="center", va="center", fontsize=8.5, color=TEXT_ON[color])
    ax.set_xlim(0, cols)
    ax.set_ylim(-rows + 1, 1.0)
    ax.axis("off")
    counts = {k: sum(c["outcome"] == k for c in cases) for k in OUTCOME_COLORS}
    head(ax, f"Red team: outcome per scenario ({n} attacks)",
         [(OUTCOME_COLORS[k], f"{OUTCOME_LABELS[k]} ({counts[k]})") for k in OUTCOME_COLORS])
    footnote(fig, f"Preset {PRESET}. Source: docs/results/flagging-redteam.json (cases)")
    save(fig, "fig-redteam-current.svg")


def fig_baseline_vs_current(cur: dict, base: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 3.2), gridspec_kw={"width_ratios": [3, 2], "wspace": 0.3})
    w = 0.34
    panels = (
        (a1, "Attacks allowed", "% of attacks", lambda d: pct(d["allow"], d["attacks"]), SETS, lambda d: (d["allow"], d["attacks"])),
        (a2, "Benign payments held", "% of benign payments", lambda d: pct(d["benign_held"], d["benign"]), ("main", "external"), lambda d: (d["benign_held"], d["benign"])),
    )
    for ax, title, ylab, f, sets, cnt in panels:
        xs = np.arange(len(sets))
        top = max(f(d[s]) for d in (base, cur) for s in sets) or 1.0
        for off, data, color in ((-w / 2 - 0.01, base, C_BASE), (w / 2 + 0.01, cur, C_CURRENT)):
            bars = ax.bar(xs + off, [f(data[s]) for s in sets], w, color=color, edgecolor="white", linewidth=0.6)
            for bar, s in zip(bars, sets):
                n, d = cnt(data[s])
                bar_label(ax, bar, f"{n}/{d}", top * 0.02)
        ax.set_xticks(xs)
        ax.set_xticklabels(sets)
        ax.set_xlim(-0.6, len(sets) - 0.4)
        ax.set_ylim(0, top * 1.25)
        ax.set_ylabel(ylab)
        pct_axis(ax.yaxis)
        head(ax, title, [(C_BASE, "baseline"), (C_CURRENT, "current")] if ax is a1 else None)
    footnote(fig, f"Preset {PRESET}. Source: baseline docs/results/results.json, external-results.json, redteam-results.json; current flagging-main.json, flagging-external.json, flagging-redteam.json")
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
    fig, ax = plt.subplots(figsize=(W1, 0.5 * len(items) + 1.2))
    ys = np.arange(len(items))[::-1]
    stacked_rows(ax, ys, [v for _, v in items], height=0.6)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n}  (n={v['total']})" for n, v in items])
    ax.set_xlabel("% of attacks in family")
    head(ax, "Main set by attack family", [(OUTCOME_COLORS[k], OUTCOME_LABELS[k]) for k in OUTCOME_COLORS])
    footnote(fig, f"Preset {PRESET}. Source: docs/results/flagging-main.json (by_family)")
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
    h = 0.34
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 3.9), sharey=True, gridspec_kw={"wspace": 0.12})
    metrics = ((a1, "missed_attacks", na, nab, "Attacks allowed", "% of attacks", [(C_BASE, "baseline"), (C_CURRENT, "current")]),
               (a2, "false_holds", nb, nbb, "Benign payments held", "% of benign payments", None))
    for ax, key, n_cur, n_base, title, xl, pairs in metrics:
        series = (("current", cur_rows, n_cur, C_CURRENT, h / 2 + 0.01), ("baseline", base_rows, n_base, C_BASE, -h / 2 - 0.01))
        peak = max(pct(rows[lab][key], n) for _, rows, n, _, _ in series for lab in labels) or 1.0
        xmax = peak * 1.3
        for y, lab in zip(ys, labels):
            for _, rows, n, color, off in series:
                v = pct(rows[lab][key], n)
                ax.barh(y + off, v, h, color=color, edgecolor="white", linewidth=0.6)
                ax.text(v + xmax * 0.015, y + off, f"{rows[lab][key]}/{n}", va="center", fontsize=9, color=INK)
        ax.set_xlim(0, xmax)
        if xmax > 100:
            ax.set_xticks(range(0, 101, 20))
        ax.set_xlabel(xl)
        pct_axis(ax.xaxis)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        head(ax, title, pairs)
    a1.set_yticks(ys)
    a1.set_yticklabels(labels)
    footnote(fig, "Main set. Source: current docs/results/flagging-main.json (configurations); baseline docs/results/results.json (configurations), matched by configuration")
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
    fig, axes = plt.subplots(2, 1, figsize=(W2, 6.2), sharex=True, gridspec_kw={"hspace": 0.45})
    x = np.arange(len(corpora))
    w = 0.8 / len(backends)
    for ax, metric, title in zip(axes, ("auroc", "recall"), ("AUROC", "Recall at threshold 0.5")):
        for i, be in enumerate(backends):
            color = BACKEND_COLORS[i % len(BACKEND_COLORS)]
            for j, c in enumerate(corpora):
                row = next((b for b in c["backends"] if b["backend"] == be), None)
                if row is None or metric not in row:
                    raise SystemExit(f"{fname}: missing corpora[{c.get('name')}].backends[{be}].{metric}")
                xpos = x[j] + (i - (len(backends) - 1) / 2) * w
                v = row[metric]
                if v is None:
                    ax.bar(xpos, 1.0, w * 0.88, facecolor="none", edgecolor="#9A9A9A", hatch="////", linewidth=0.6)
                    ax.text(xpos, 0.5, "n/a", ha="center", va="center", fontsize=8.5, color=MUTED,
                            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
                else:
                    ax.bar(xpos, v, w * 0.88, color=color, edgecolor="white", linewidth=0.6)
                    ax.text(xpos, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5, color=INK)
        ax.set_ylim(0, 1.12)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0", "0.25", "0.5", "0.75", "1"])
        head(ax, title, [(BACKEND_COLORS[i % len(BACKEND_COLORS)], short(be)) for i, be in enumerate(backends)] if ax is axes[0] else None)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(["\n".join(textwrap.wrap(c["name"], 18)) for c in corpora], fontsize=9)
    footnote(fig, "Source: docs/results/classifier-bench.json (corpora[].backends); hatched = n/a (null, e.g. no negatives)")
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
    fig, ax = plt.subplots(figsize=(W1, 3.9))

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
        ax.plot(xs, ys, marker="o", color=color, label=be, zorder=3)
        for g, x_, y_ in zip(rows, xs, ys):
            ax.annotate(f"rt {g['redteam']['attacks_allowed']}", (x_, y_), textcoords="offset points",
                        xytext=(0, -12 - 11 * i), ha="center", va="top", fontsize=9, color="#444444")
    ix, iy = point(inc)
    sx, sy = point(sel)
    ax.scatter([ix], [iy], s=190, facecolors="none", edgecolors="black", linewidths=1.3, zorder=5, label="incumbent")
    ax.scatter([sx], [sy], s=150, marker="*", color="black", zorder=6, label="selected")
    ax.set_xticks(range(len(thresholds)))
    ax.set_xticklabels([str(t) for t in thresholds])
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.margins(y=0.25)
    ax.grid(axis="y")
    ax.set_xlabel("FUSION_INJECTION_THRESHOLD")
    ax.set_ylabel("Benign held (main + external_tune)")
    ax.set_title("Injection-threshold sweep", pad=TITLE_PAD)
    ax.legend(ncol=len(backends) + 2, loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2,
              columnspacing=1.4, handletextpad=0.4)

    def fmt(r):
        return f"benign held {r['benign_held']}/{r['n_benign']}, attacks allowed {r['attacks_allowed']}/{r['n_attack']}"

    inc_e, sel_e = ext["incumbent"], ext["selected"]
    ax.text(0, -0.24,
            f"external_test\nincumbent ({inc['backend']}@{inc['threshold']}): {fmt(inc_e)}\n"
            f"selected ({sel['backend']}@{sel['threshold']}): {fmt(sel_e)}",
            transform=ax.transAxes, fontsize=9, va="top", ha="left", color=INK, linespacing=1.5)
    footnote(fig, f"Offline re-fuse. rt = red-team attacks allowed. Source: docs/results/{fname} (grid, incumbent, selected, external_test)")
    save(fig, "fig-classifier-refuse.svg")


C_REPEAT = "#56B4E9"  # repeat-run series (not an outcome colour)
REPEAT_RUN = Path("rerun-2026-11-13") / "repeat-run.json"
REPEAT_KEYS = {"main": ("main",), "external": ("external",), "red team": ("redteam", "red team", "red_team")}


def fig_repeat_run(doc: dict, fname: str = REPEAT_RUN.as_posix()) -> None:
    pairs = field(doc, fname, "pairs")
    panels = (
        ("Benign payments held", "% of benign payments", "benign_held", "n_benign", "benign_held_wilson95"),
        ("Attacks allowed", "% of attacks", "attacks_allowed", "n_attack", "attacks_allowed_wilson95"),
    )
    blocks = {}
    for s in SETS:
        key = next((k for k in REPEAT_KEYS[s] if k in pairs), None)
        if key is None:
            raise SystemExit(f"{fname}: missing pairs.{REPEAT_KEYS[s][0]}")
        blocks[s] = field(doc, fname, "pairs", key)
        for part in ("first", "second"):
            for _, _, _, nk, wk in panels:
                field(blocks[s], fname, part, nk)
                for k in ("k", "n", "rate", "low", "high"):
                    field(blocks[s], fname, part, wk, k)
        for k in ("same_outcome", "n_cases"):
            field(blocks[s], fname, "agreement", k)
    fig, axes = plt.subplots(1, 2, figsize=(W2, 3.6), gridspec_kw={"width_ratios": [2, 3], "wspace": 0.3})
    w = 0.32
    for ax, (title, ylab, ck, nk, wk) in zip(axes, panels):
        sets = [s for s in SETS if blocks[s]["first"][nk] > 0]
        xs = np.arange(len(sets))
        top = max(100 * blocks[s][p][wk]["high"] for s in sets for p in ("first", "second")) or 1.0
        for off, part, c in ((-w / 2 - 0.06, "first", C_BASE), (w / 2 + 0.06, "second", C_REPEAT)):
            ws = [blocks[s][part][wk] for s in sets]
            vals = [100 * x["rate"] for x in ws]
            err = [[max(0.0, 100 * (x["rate"] - x["low"])) for x in ws], [max(0.0, 100 * (x["high"] - x["rate"])) for x in ws]]
            ax.bar(xs + off, vals, w, color=c, edgecolor="white", linewidth=0.6,
                   yerr=err, error_kw={"elinewidth": 0.9, "capsize": 2.5, "ecolor": "#555555"})
            for x, s in zip(xs, sets):
                ax.text(x + off, 100 * blocks[s][part][wk]["high"] + top * 0.02, f"{blocks[s][part][ck]}/{blocks[s][part][nk]}",
                        ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{s}\nagreement\n{blocks[s]['agreement']['same_outcome']}/{blocks[s]['agreement']['n_cases']}" for s in sets], fontsize=9.5)
        ax.set_xlim(-0.6, len(sets) - 0.4)
        ax.set_ylim(0, top * 1.2)
        ax.set_ylabel(ylab)
        pct_axis(ax.yaxis)
        head(ax, title, [(C_BASE, "first run"), (C_REPEAT, "repeat run")] if ax is axes[0] else None)
    footnote(fig, f"Preset {PRESET}; whiskers are Wilson 95% intervals. Source: docs/results/{fname} (pairs.*.first/second, agreement); red team has no benign cases")
    save(fig, "fig-repeat-run.svg")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Render README figures from committed results.")
    ap.add_argument("--repeat-run", action="store_true", help=f"also render fig-repeat-run.svg from docs/results/{REPEAT_RUN.as_posix()}")
    args = ap.parse_args(argv)
    cur = current_sets()
    base = baseline_sets()
    fig_outcomes_current(cur)
    fig_redteam_current()
    fig_baseline_vs_current(cur, base)
    fig_family_main()
    fig_layers_main()
    fig_classifier_bench()
    fig_classifier_refuse(load("autoresearch-classifier.json"))
    if args.repeat_run:
        fig_repeat_run(load(REPEAT_RUN.as_posix()))
    print(f"wrote {len(WRITTEN)} figures to {FIGURES}")


if __name__ == "__main__":
    main()
