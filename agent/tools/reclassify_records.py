"""Swap the injection signal of recorded DecisionRecords for another classifier's (offline).

Run from agent/:
    uv run --with transformers --with torch python tools/reclassify_records.py \
        --set main --results ../docs/results/flagging-main-calibration.json \
        --records ../data/eval/records/flagging-main \
        --model meta-llama/Llama-Prompt-Guard-2-86M --out ../data/eval/records/flagging-main-promptguard2

Record `<n>.json` belongs to `cases[n-1]` of `--results`. Each case's checker context is rebuilt
exactly as `firewall-eval` built it (scripted agent, eval namespace), scored with `--model`, and
written as `signals.injection` of a copy under `--out`; every other field is kept. The copies are
lab artifacts for `firewall-eval --refuse-from`: their `record_sha256` matches nothing on-chain.
No Jev or network call is made apart from the model download.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from firewall_agent.agent import propose_payment
from firewall_agent.classifier import ClassifierBackend
from firewall_agent.eval import EVAL_NAMESPACE, _check_record_dir
from firewall_agent.llm import ScriptedLLM
from firewall_agent.scenarios import SCENARIO_SETS, load_scenario


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=sorted(SCENARIO_SETS), dest="scenario_set")
    ap.add_argument("--results", required=True, type=Path, help="results.json the records came from")
    ap.add_argument("--records", required=True, type=Path, help="directory of <n>.json DecisionRecords")
    ap.add_argument("--model", required=True, help="Hugging Face model id of the substitute classifier")
    ap.add_argument("--out", required=True, type=Path, help="absent or empty output directory")
    args = ap.parse_args(argv)

    results = json.loads(args.results.read_text(encoding="utf-8"))
    if results.get("scenario_set") != args.scenario_set:
        raise SystemExit(
            f"{args.results}: scenario_set is {results.get('scenario_set')!r}, --set is {args.scenario_set!r}"
        )
    _check_record_dir(args.out, 1)
    args.out.mkdir(parents=True, exist_ok=True)

    backend = ClassifierBackend(args.model)
    n = 0
    for idx, case in enumerate(results["cases"], start=1):
        rec_file = args.records / f"{idx}.json"
        if not rec_file.is_file():
            raise SystemExit(f"missing record {rec_file}")
        record = json.loads(rec_file.read_text(encoding="utf-8"))
        recorded = (record.get("signals") or {}).get("injection")
        if recorded is None:
            raise SystemExit(f"record {idx} has no injection signal")

        scenario = load_scenario(case["name"], EVAL_NAMESPACE, args.scenario_set)
        req = propose_payment(scenario, ScriptedLLM(scenario), client_ref=f"{scenario.name}-1")
        if req is None:
            raise SystemExit(f"scenario {case['name']!r} did not propose a payment")
        items = req.context_dicts()
        if [i["ref"] for i in items] != [p["ref"] for p in recorded["per_item"]]:
            raise SystemExit(f"ref mismatch at {idx}")

        record["signals"]["injection"] = backend.score_batch(items)
        (args.out / f"{idx}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        n += 1
    print(f"reclassified {n} records with {args.model} -> {args.out}")


if __name__ == "__main__":
    main()
