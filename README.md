# backlogs-near

> Working repository name. The final project name is decided by the human team lead. Working project title: "Attested Payment Firewall".

## What it is

A payment firewall for AI agents. The agent holds only a function-call key scoped to a Guardian contract that holds the funds. Each payment request pauses the contract and runs four checks (policy rules, injection classifier, masked re-run, counterparty signals) in a checker. Jev (TypeSafe) fuses the signals into allow / hold / block, with no human in the loop. NEAR holds the funds, enforces the key scope, binds each verdict to receiver, token and exact amount, enforces caps, settles, and records the receipt.

Plan and scope: [docs/build/idea.md](docs/build/idea.md). Status: Sunday scaffold. The checker returns a hard-coded allow; the checks land Tue–Wed.

## The problem

Prompt injection drains agent wallets. In May 2026 a Morse-code message made Grok's linked wallet pay out about $150,000 in DRB ([Giskard](https://giskard.ai/knowledge/how-grok-got-prompt-injected-an-x-user-drained-150-000-from-an-ai-wallet)). Chainalysis reports crypto theft rising from $2.2B to $3.4B. Both figures are to be verified against the primary source before submit. Host-side defenses run where a compromised agent can skip them ([PRD §2](docs/build/prd.md#2-problem)).

## How NEAR is used

- Contract custody: the Guardian contract holds the tUSDC; the agent cannot move it directly.
- Access keys: the agent account has only a function-call key limited to the Guardian's `request_payment`.
- Yield/resume: `request_payment` pauses; the checker's verdict resumes it, and the contract pays only on an exact receiver/token/amount/`request_id` match.
- NEP-141: payments are `ft_transfer` of a mock tUSDC token (6 decimals) deployed on testnet.
- On-chain receipts: outcome, reason codes, input and record hashes, checker version. The full decision record stays in the owner's off-chain log.

## Try it

Dry-run, no keys or funds. From the repo root:

1. `cargo build -p checker --release` → `target/release/checker` (`.exe` on Windows) exists.
2. `cd agent && uv sync` → the Python environment is ready.
3. `uv run firewall-demo --scenario benign-hosting` → five lines:
   ```
   scenario: benign-hosting (benign)
   proposed: pay 18000000 units (18 tUSDC) to hostco.demo.testnet memo="INV-2026-11"
   verdict: allow reasons=stub_allow record=<64 hex>
   action: would_pay
   record_file: data/decisions/dry-run/<request id>.json
   ```
4. `uv run firewall-demo --scenario attack-morse-lookalike` → `verdict: allow reasons=stub_allow`. The attack is allowed for now; the checks that block it land Tue–Wed.
5. Open the file named on the `record_file:` line (e.g. `data/decisions/dry-run/2.json`) → the full decision record; `sha256sum <that file>` equals the `record=` value. Each dry-run gets the next request id, so earlier records are kept; the checker refuses to overwrite a record with different content.

## Run locally

### Read-only receipts panel (React)

From `site/`, run `npm ci` then `npm run dev` → open the printed local URL at `#receipts` to see live receipts from `guardian-v2.jimuelle-firewall.testnet`, with status filters, exact token amounts and testnet explorer links. No wallet or keys are needed. See [site/README.md](site/README.md) for configuration, checks and production build instructions.

### Agent and contracts

Prerequisites: Rust 1.94+, `rustup target add wasm32-wasip2`, cargo-near 0.21.1 (`cargo install cargo-near --version 0.21.1 --locked --no-default-features`; on Windows use the [release binary](https://github.com/near/cargo-near/releases/tag/cargo-near-v0.21.1), since the source build needs a full Perl for OpenSSL), [uv](https://docs.astral.sh/uv/).

```
cp .env.example .env
cargo test --workspace
cargo build -p checker --release
cargo build -p checker --target wasm32-wasip2 --release
(cd contract/guardian && cargo near build non-reproducible-wasm --no-abi)
(cd contract/token && cargo near build non-reproducible-wasm --no-abi)
cd agent && uv sync && uv run pytest
```

Contract wasm files: `target/near/guardian/guardian.wasm` and `target/near/tusdc/tusdc.wasm`. `--no-abi` skips ABI generation, which fails to link on Windows MSVC. The dry-run needs no keys. Optional: `uv run firewall-jev-ping` checks the TypeSafe key (`TYPESAFE_API_KEY` in `.env`).

### Testnet

These commands sign testnet transactions. The human runs them; they are never run by the agent.

```
cd agent
uv sync --extra testnet
uv run firewall-setup-testnet
uv run firewall-relayer
uv run firewall-demo --scenario benign-hosting --mode testnet
```

Expected: the Guardian receipt reaches `paid` and the hostco tUSDC balance rises by 18. Keys are written to `.env.testnet` (gitignored).

## Architecture

- [System design](docs/build/system-design.md): data flow, trust boundaries, failure modes.
- [Software design](docs/build/sdd.md): modules, interfaces, configuration, testing.
- [Schemas](schemas/): frozen JSON formats with examples.

## Built with / third-party

- React, React DOM, Vite, `@vitejs/plugin-react` and vite-plugin-singlefile: shared landing page and read-only receipts frontend
- three, three-stdlib, `@react-three/fiber`, `@react-three/drei`, GSAP, Lenis and lucide-react: shared frontend stack ([site/README.md](site/README.md))
- Google Fonts (Geist, Geist Mono), NEARBlocks testnet explorer, FastNEAR public testnet RPC: frontend fonts and public data links

- [TypeSafe Jev](https://typesafe.ai): calibrated typed decisions, raw HTTPS
- [NEAR AI Cloud](https://cloud.near.ai): LLM for agent tool calls, masked re-run and decision fallback
- [OutLayer](https://app.outlayer.ai): TEE execution of the checker (wasm32-wasip2)
- [near-sdk-rs](https://github.com/near/near-sdk-rs) and near-contract-standards: contract SDK, NEP-141
- [cargo-near](https://github.com/near/cargo-near): contract build
- [py-near](https://github.com/pvolnov/py-near): NEAR Python client (testnet extra)
- [openai](https://github.com/openai/openai-python) (Python): NEAR AI Cloud client
- httpx, jsonschema, python-dotenv, pytest (Python)
- serde, serde_json, sha2, hex (Rust)
- [protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2): injection classifier, default; Apache-2.0 (verify on model card)
- [meta-llama/Llama-Prompt-Guard-2-86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M): injection classifier, when HF access is granted; Llama 4 Community License (verify on model card)

## Hackathon disclosures

- Built for NEAR HACKATHON (2026-11-01 → 2026-11-14). Pre-hackathon code: none — repository created 2026-11-08.
- Other projects by team members (Q-015): TBD(human).

## License

MIT, see [LICENSE](LICENSE).
