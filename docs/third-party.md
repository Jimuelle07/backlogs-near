# Third-party libraries, tools and datasets

Moved from the README on 2026-11-13. The README keeps a names-only table: [README Built with](../README.md#built-with).

## Decision and platform

- [TypeSafe Jev](https://typesafe.ai): calibrated typed decisions, raw HTTPS; the decision brain
- [NEAR AI Cloud](https://cloud.near.ai): LLM for agent tool calls and decision fallback; optional Jev route (`JEV_PROVIDER=nearai`)
- [OutLayer](https://app.outlayer.ai): TEE execution of the checker (wasm32-wasip2)
- [protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2): injection classifier, default; Apache-2.0 (verify on model card)
- [meta-llama/Llama-Prompt-Guard-2-86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M): injection classifier, when HF access is granted; Llama 4 Community License (verify on model card)
- [transformers](https://github.com/huggingface/transformers) and [PyTorch](https://pytorch.org) (optional, only for `firewall-classifier`; not in `pyproject.toml`, installed with `uv run --with`)

## Datasets (used by the benchmarks and the external set; full attribution in [agent/scenarios/external/ATTRIBUTION.md](../agent/scenarios/external/ATTRIBUTION.md))

- [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections): Apache-2.0; read by `bench_classifier.py` only, not committed
- [3nesdeniz/agentic-prompt-injection-boundary-pairs](https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-boundary-pairs): CC-BY-4.0; rewritten rows in `agent/scenarios/external/`; also read by the classifier benchmark
- [nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1): CC-BY-4.0; rewritten rows in `agent/scenarios/external/`; also read by the classifier benchmark
- [microsoft/llmail-inject-challenge](https://huggingface.co/datasets/microsoft/llmail-inject-challenge): MIT; benign emails in `agent/scenarios/external/`; also read by the classifier benchmark
- [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent): MIT; rewritten rows in `agent/scenarios/external/`
- [AgentDojo](https://github.com/ethz-spylab/agentdojo): MIT; rewritten rows in `agent/scenarios/external/`
- [Kaggle homoglyph domain attacks](https://www.kaggle.com/datasets/akshat4112/homoglyph-domain-attacks): CC0; benchmark input only (`bench_lookalike.py`), not committed
- [Kaggle adversarial BEC email dataset](https://www.kaggle.com/datasets/yoadjei/adversarial-bec-email-dataset): CC BY-SA 4.0; read by `build_bec_examples.py`, not committed
- [Kaggle PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1): CC BY-SA 4.0; read by `build_paysim_set.py`, not committed
- [Jim10/attested-payment-firewall-scenarios-eclipse](https://huggingface.co/datasets/Jim10/attested-payment-firewall-scenarios-eclipse): this project's own scenarios (main, redteam, external splits) as exported by `agent/tools/export_hf_dataset.py`; published copy

## Rust (contracts and checker)

- [near-sdk-rs](https://github.com/near/near-sdk-rs) and near-contract-standards (`=5.29.1`): contract SDK, NEP-141
- [cargo-near](https://github.com/near/cargo-near): contract build
- serde, serde_json, sha2, hex: serialization and hashing (checker; hex also in the Guardian)
- ureq (native checker) and wasi-http-client (wasm32-wasip2 checker): HTTP client

## Python (agent, relayer, eval)

- [uv](https://docs.astral.sh/uv/) and hatchling: environment and build
- [py-near](https://github.com/pvolnov/py-near): NEAR Python client (testnet extra)
- [openai](https://github.com/openai/openai-python): NEAR AI Cloud client
- httpx, jsonschema, python-dotenv, pytest
- [matplotlib](https://matplotlib.org): README figures (`agent/tools/plot_results.py`; not in `pyproject.toml`, installed with `uv run --with`)

## Frontend (`site/`)

- React, React DOM, Vite, `@vitejs/plugin-react` and vite-plugin-singlefile: shared landing page and read-only receipts frontend
- three, three-stdlib, `@react-three/fiber`, `@react-three/drei`, GSAP, Lenis and lucide-react: shared frontend stack ([site/README.md](../site/README.md))
- Google Fonts (Geist, Geist Mono), NEARBlocks testnet explorer, FastNEAR public testnet RPC: frontend fonts and public data links

## Video (`video/`)

- [Remotion](https://www.remotion.dev) (`remotion`, `@remotion/cli`, `@remotion/transitions`, `@remotion/google-fonts`): the explainer video of how Eclipse runs; Remotion License, free for individuals and companies of up to 3 people, company license otherwise (see [remotion.dev/license](https://www.remotion.dev/docs/license))
- React and TypeScript: video components
