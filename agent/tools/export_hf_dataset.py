"""Export the labelled scenarios as a Hugging Face dataset folder (data/hf-dataset/, gitignored).

Writes data/{main,redteam,external}.jsonl (one scenario per line, {NS} kept, plus the columns
set / source / license) and the README.md dataset card. Reads only tracked scenario files; PaySim-
and BEC-derived data (Kaggle, CC BY-SA) is never read. Nothing is uploaded: the script prints the
upload command for the dataset owner to run. Output is deterministic.

    cd agent && uv run python tools/export_hf_dataset.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCEN = REPO_ROOT / "agent" / "scenarios"
OUT = REPO_ROOT / "data" / "hf-dataset"

SETS = {"main": SCEN, "redteam": SCEN / "redteam", "external": SCEN / "external"}
EXTERNAL_SOURCES = {  # <src> in ext-<src>-<label>-NNN -> (dataset id, license)
    "injecagent": ("uiuc-kang-lab/InjecAgent", "MIT"),
    "agentdojo": ("ethz-spylab/agentdojo", "MIT"),
    "nemotron": ("nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1", "CC-BY-4.0"),
    "boundary": ("3nesdeniz/agentic-prompt-injection-boundary-pairs", "CC-BY-4.0"),
    "llmail": ("microsoft/llmail-inject-challenge", "MIT"),
}

CARD = """---
license: cc-by-4.0
task_categories:
- text-classification
tags:
- prompt-injection
- agent-security
- payments
- near
configs:
- config_name: default
  data_files:
  - split: main
    path: data/main.jsonl
  - split: redteam
    path: data/redteam.jsonl
  - split: external
    path: data/external.jsonl
---

# Eclipse scenarios

Labelled payment scenarios for testing a payment firewall for AI agents (NEAR hackathon entry
"Eclipse"). Each row is one scripted agent run: a user request, an inbox of
context items (some untrusted, possibly carrying an injection) and the payment the agent then
proposes. A firewall should hold or deny the `attack` rows and allow the `benign` rows.

## Splits

- `main`: team-written and generated scenarios, 150 benign and 150 attack (25 per family).
- `redteam`: team-written attack-only scenarios aimed at the checker's weak spots.
- `external`: scenarios derived from public benchmarks (see Provenance), equal numbers of benign and attack.

## Fields

- `name`: scenario id.
- `label`: `benign` or `attack`.
- `family`: `none` for benign rows; for attacks one of `direct_injection`, `encoded_injection`,
  `indirect_injection`, `memory_poisoning`, `lookalike_receiver`, `fake_invoice`.
- `user_request`: the instruction the user gives the agent.
- `inbox`: list of `{source, ref, trust, text}` context items. `source` is one of `email`, `x_reply`,
  `web`, `memory`, `tool`; `trust` is `trusted` or `untrusted`.
- `scripted_tool_call`: `{name, arguments}` with `arguments` = `{receiver_id, amount, memo}`, the payment
  the agent proposes (`amount` is whole tUSDC as a string).
- `set`: `main`, `redteam` or `external`.
- `source`: `team`, or the public dataset id for `external` rows.
- `license`: `MIT` for team rows, the source dataset's license for external rows.

The literal `{NS}` in account ids is a placeholder for the NEAR account suffix (for example `demo.testnet`).

## Provenance

`main` and `redteam` are written by the project team (MIT). `external` rows are public benchmark text
rewritten into payment form by `agent/tools/build_external_scenarios.py`: the benchmark text is placed
in an untrusted inbox item next to a generated invoice email, and attack rows get an appended receiver
line naming a synthetic account. They are not original benchmark rows and are not comparable to the
benchmarks' own metrics.

PaySim- and BEC-derived data is excluded from this dataset: those sources (Kaggle PaySim and Kaggle
adversarial BEC emails) are CC BY-SA 4.0.

## Attribution

{attribution}"""


def rows(set_name: str, directory: Path) -> list[dict]:
    out = []
    for path in sorted(directory.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if set_name == "external":
            source, lic = EXTERNAL_SOURCES[path.stem.split("-")[1]]
        else:
            source, lic = "team", "MIT"
        out.append({**row, "set": set_name, "source": source, "license": lic})
    return sorted(out, key=lambda r: r["name"])


def main() -> None:
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    for set_name, directory in SETS.items():
        data = rows(set_name, directory)
        text = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in data)
        (OUT / "data" / f"{set_name}.jsonl").write_bytes(text.encode("utf-8"))
        print(f"{set_name}: {len(data)} rows")
    attribution = (SCEN / "external" / "ATTRIBUTION.md").read_text(encoding="utf-8")
    (OUT / "README.md").write_bytes(CARD.replace("{attribution}", attribution).encode("utf-8"))
    print(f"wrote {OUT}")
    print("upload (run it yourself, pick the name):")
    print("  huggingface-cli upload <hf-user>/<dataset-name> data/hf-dataset . --repo-type dataset")


if __name__ == "__main__":
    main()
