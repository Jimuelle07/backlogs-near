"""Build Jev reference examples from the Kaggle adversarial BEC dataset (plan step 7, D).

    export KAGGLE_DATA_DIR=<dir containing adversarial-bec-email-dataset/>
    cd agent && uv run python tools/build_bec_examples.py

Reads synthetic_bec.csv (or synthetic_emails.csv, the name inside the downloaded zip), columns
subject,body,label. The dataset is CC BY-SA 4.0: the output goes only to the gitignored
data/external/derived/bec-reference-examples.json and is never committed. This script prints counts
and lengths only. legitimate_examples come from the team's own main-set benign scenarios.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from firewall_agent.config import REPO_ROOT
from firewall_agent.scenarios import load_scenario

URL = "https://www.kaggle.com/datasets/yoadjei/adversarial-bec-email-dataset"
FILENAMES = ("synthetic_bec.csv", "synthetic_emails.csv")
KEYWORDS = re.compile(r"(?i)invoice|bank (details|account)|wire|remit|payment details")
BENIGN = [
    "benign-invoice-replaces",
    "benign-supplier-large",
    "benign-overage-fee",
    "benign-partial-payment",
    "benign-new-payee-named",
    "benign-urgent-tone",
]
N_FRAUD = 6
MAX_LEN = 500
OUT = REPO_ROOT / "data" / "external" / "derived" / "bec-reference-examples.json"


def find_csv() -> Path:
    root = Path(os.environ.get("KAGGLE_DATA_DIR", "")) / "adversarial-bec-email-dataset"
    for name in FILENAMES:
        if (root / name).is_file():
            return root / name
    raise SystemExit(
        "missing BEC csv; expected one of: "
        + " or ".join(str(root / n) for n in FILENAMES)
        + f"\ndownload from {URL} (set KAGGLE_DATA_DIR)"
    )


def main() -> None:
    path = find_csv()
    with path.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if KEYWORDS.search(r["body"])]
    rows.sort(key=lambda r: hashlib.sha256(r["body"].encode("utf-8")).hexdigest())
    fraud = [(r["subject"] + "\n" + r["body"])[:MAX_LEN] for r in rows[:N_FRAUD]]
    legit = [load_scenario(n, "demo.testnet").inbox[0].text for n in BENIGN]
    payload = {"fraud_examples": fraud, "legitimate_examples": legit}
    assert set(payload) == {"fraud_examples", "legitimate_examples"}
    for k, v in payload.items():
        assert 1 <= len(v) <= 10 and all(isinstance(s, str) and len(s) <= 600 for s in v), k
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    assert len(text) < 32000, len(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    print(
        f"bec: matching_rows={len(rows)} fraud={len(fraud)} legitimate={len(legit)} "
        f"max_len={max(len(s) for s in fraud + legit)} json_chars={len(text)}"
    )


if __name__ == "__main__":
    sys.exit(main())
