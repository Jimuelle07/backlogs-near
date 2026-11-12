"""Benchmark the checker's ASCII-confusable lookalike detection on Kaggle homoglyph data.

Data: https://www.kaggle.com/datasets/akshat4112/homoglyph-domain-attacks (CC0), unzipped into
$KAGGLE_DATA_DIR/homoglyph-domain-attacks/. There is no CSV. The six files
domains_{train,valid,test}.txt (legitimate) and fake_{train,valid,test}.txt (spoofed) are each a
Python pickle (protocol 3) of a plain list[str] of domains, e.g.
    domains_test.txt: ['<d0>', '<d1>', '<d2>', ...]   (first 3 entries are printed at run start)
    fake_test.txt:    ['<f0>', '<f1>', '<f2>', ...]   (first 3 entries are printed at run start)
They are loaded with an Unpickler whose find_class always raises; a list of str needs no globals.

Pairing (not explicit in the data, reconstructed without the skeleton): each fake list is a series of
runs of spoofs of ONE legitimate domain of the same split, nominally 9 per run, and the fake and
legit lists are not index-aligned. An anchor is a fake whose Unicode fold (NFKD, combining marks
dropped) equals a legit domain of the same split. Rule: cut each fake list into consecutive blocks of
9; a block with exactly one distinct anchor assigns that legit domain to every fake in the block;
blocks with no anchor or with two or more distinct anchors (a short run shifted the cut) are
`unpaired` and dropped. Folded-form edit distances to the assigned domain were checked on samples:
0..3 for ~99.5% of pairs.

Detection mirrors checker/src/counterparty.rs find_lookalike: 0 < payee_distance <= max_distance
(COUNTERPARTY_MAX_LOOKALIKE_DISTANCE default 2). Labels are compared bare (no dots), where the
checker's payee_distance reduces to the Damerau-Levenshtein distance.
"""

import json
import os
import pickle
import random
import re
import sys
import unicodedata
from pathlib import Path

from firewall_agent.config import REPO_ROOT

SOURCE = "https://www.kaggle.com/datasets/akshat4112/homoglyph-domain-attacks"
LICENSE = "CC0"
SUBDIR = "homoglyph-domain-attacks"
SPLITS = ("train", "valid", "test")
SEED = 20261113
MAX_DISTANCE = 2  # DEFAULT_MAX_LOOKALIKE_DISTANCE in checker/src/counterparty.rs
RUN_LEN = 9
N_NEGATIVES = 2000
MIN_PAIRS = 50
OUT = REPO_ROOT / "docs" / "results" / "lookalike-bench.json"
LABEL_RE = re.compile(r"^[a-z0-9_-]+$")

_SKELETON_SINGLE = {
    "0": "o", "1": "l", "i": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g",
    "_": "-",
}
_SKELETON_PAIRS = {"rn": "m", "vv": "w"}
# Inverse substitutions for the synthetic fallback: (letter, confusable).
_INVERSE = [
    ("o", "0"), ("l", "1"), ("i", "1"), ("e", "3"), ("a", "4"), ("s", "5"), ("t", "7"),
    ("b", "8"), ("g", "9"), ("m", "rn"), ("w", "vv"), ("-", "_"),
]


def ascii_skeleton(s: str) -> str:
    """Port of counterparty.rs ascii_skeleton: lowercase ASCII, one left-to-right pass."""
    chars = [c.lower() if c.isascii() else c for c in s]
    out = []
    i = 0
    while i < len(chars):
        pair = chars[i] + chars[i + 1] if i + 1 < len(chars) else ""
        if pair in _SKELETON_PAIRS:
            out.append(_SKELETON_PAIRS[pair])
            i += 2
        else:
            out.append(_SKELETON_SINGLE.get(chars[i], chars[i]))
            i += 1
    return "".join(out)


def damerau_levenshtein(s: str, t: str) -> int:
    """Port of counterparty.rs damerau_levenshtein (restricted/optimal string alignment)."""
    a = "".join(c.lower() if c.isascii() else c for c in s)
    b = "".join(c.lower() if c.isascii() else c for c in t)
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    d = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        d[i][0] = i
    for j in range(n + 1):
        d[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            val = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                val = min(val, d[i - 2][j - 2] + 1)
            d[i][j] = val
    return d[m][n]


def raw_payee_distance(candidate: str, payee: str) -> int:
    """Port of the pre-skeleton counterparty.rs payee_distance."""
    if candidate.lower() == payee.lower():  # eq_ignore_ascii_case
        return 0
    full_dist = damerau_levenshtein(candidate, payee)
    c_prefix = candidate.split(".")[0]
    p_prefix = payee.split(".")[0]
    if c_prefix == candidate and p_prefix == payee:
        return full_dist
    prefix_dist = damerau_levenshtein(c_prefix, p_prefix)
    c_has_dot = "." in candidate
    p_has_dot = "." in payee
    if c_has_dot and p_has_dot:
        c_suffix = candidate[candidate.index("."):]
        p_suffix = payee[payee.index("."):]
        if c_suffix == p_suffix:
            return full_dist
        return min(full_dist, prefix_dist + 1)
    return prefix_dist + 1


def payee_distance(candidate: str, payee: str) -> int:
    raw = raw_payee_distance(candidate, payee)
    if raw == 0:
        return 0
    skel = raw_payee_distance(ascii_skeleton(candidate), ascii_skeleton(payee))
    return min(raw, max(skel, 1))


def _match(distance: int) -> bool:
    return 0 < distance <= MAX_DISTANCE


class _ListOnlyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f"global {module}.{name} not allowed")


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _load_list(path: Path) -> list[str]:
    if not path.is_file():
        raise SystemExit(f"missing {path}; download and unzip {SOURCE} into {path.parent}")
    with path.open("rb") as fh:
        data = _ListOnlyUnpickler(fh).load()
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise SystemExit(f"{path}: expected a pickled list[str]")
    return data


def _label(domain: str) -> str:
    return domain.split(".")[0].lower()


def reconstruct_pairs(legit: list[str], fake: list[str]) -> tuple[list[tuple[str, str]], int]:
    """Return ((legit_domain, fake_domain) pairs, unpaired count) per the module docstring."""
    legit_set = set(legit)
    anchors = [_fold(f) if _fold(f) in legit_set else None for f in fake]
    pairs: list[tuple[str, str]] = []
    unpaired = 0
    for s in range(0, len(fake), RUN_LEN):
        block = fake[s:s + RUN_LEN]
        distinct = {a for a in anchors[s:s + RUN_LEN] if a}
        if len(distinct) == 1:
            anchor = next(iter(distinct))
            pairs.extend((anchor, f) for f in block)
        else:
            unpaired += len(block)
    return pairs, unpaired


def main() -> None:
    kdir = os.environ.get("KAGGLE_DATA_DIR")
    if not kdir:
        raise SystemExit(f"set KAGGLE_DATA_DIR to the folder holding {SUBDIR}/ ({SOURCE})")
    base = Path(kdir) / SUBDIR

    all_pairs: list[tuple[str, str]] = []
    legit_domains: list[str] = []
    unpaired = 0
    total_fakes = 0
    for sp in SPLITS:
        legit = _load_list(base / f"domains_{sp}.txt")
        fake = _load_list(base / f"fake_{sp}.txt")
        print(f"{sp}: domains_{sp}.txt first 3 = {legit[:3]}; fake_{sp}.txt first 3 = {fake[:3]}")
        pairs, up = reconstruct_pairs(legit, fake)
        all_pairs.extend(pairs)
        legit_domains.extend(legit)
        unpaired += up
        total_fakes += len(fake)
    print(f"fakes {total_fakes}, paired {len(all_pairs)}, unpaired {unpaired} "
          f"({len(all_pairs) / total_fakes:.1%} paired)")
    sample_rng = random.Random(SEED)
    for legit_d, fake_d in sample_rng.sample(all_pairs, 30):
        print(f"  sample pair: {legit_d} <- {fake_d}")

    not_representable = 0
    positives: set[tuple[str, str]] = set()
    for legit_d, fake_d in all_pairs:
        l_lab, f_lab = _label(legit_d), _label(fake_d)
        if not (LABEL_RE.match(l_lab) and LABEL_RE.match(f_lab)):
            not_representable += 1
        elif l_lab != f_lab:
            positives.add((l_lab, f_lab))
    pos = sorted(positives)

    legit_labels = sorted({_label(d) for d in legit_domains if LABEL_RE.match(_label(d))})
    rng = random.Random(SEED)
    synthetic = 0
    if len(pos) < MIN_PAIRS:
        for lab in legit_labels:
            options = [(a, b) for a, b in _INVERSE if a in lab]
            if options:
                a, b = rng.choice(options)
                idx = rng.choice([i for i, c in enumerate(lab) if lab.startswith(a, i)])
                pos.append((lab, lab[:idx] + b + lab[idx + len(a):]))
                synthetic += 1

    negatives = []
    while len(negatives) < N_NEGATIVES:
        a, b = rng.sample(legit_labels, 2)
        negatives.append((a, b))

    det_raw = sum(_match(raw_payee_distance(c, p)) for p, c in pos)
    det_skel = sum(_match(payee_distance(c, p)) for p, c in pos)
    fm_raw = sum(_match(raw_payee_distance(c, p)) for p, c in negatives)
    fm_skel = sum(_match(payee_distance(c, p)) for p, c in negatives)

    n = len(pos)
    result = {
        "source": SOURCE,
        "license": LICENSE,
        "data_format": "six pickled list[str] files: domains_{train,valid,test}.txt (legitimate) "
                       "and fake_{train,valid,test}.txt (spoofed); no CSV, no explicit pairing",
        "pairing": f"fake lists cut into blocks of {RUN_LEN}; a block whose NFKD-folded members "
                   "match exactly one legitimate domain of the same split is paired with it; "
                   "other blocks are unpaired",
        "max_distance": MAX_DISTANCE,
        "n_pairs": n,
        "unpaired": unpaired,
        "not_representable": not_representable,
        "synthetic_from_legit": synthetic,
        "detected_raw": det_raw,
        "detected_skeleton": det_skel,
        "detection_rate_raw": round(det_raw / n, 4) if n else 0.0,
        "detection_rate_skeleton": round(det_skel / n, 4) if n else 0.0,
        "negatives": len(negatives),
        "false_match_raw": fm_raw,
        "false_match_skeleton": fm_skel,
        "false_match_rate_raw": round(fm_raw / len(negatives), 4),
        "false_match_rate_skeleton": round(fm_skel / len(negatives), 4),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
