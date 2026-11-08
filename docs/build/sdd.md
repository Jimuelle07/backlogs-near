# SDD — backlogs-near software design

## 1. Status

Draft, project undecided. Last updated 2026-11-08.

Everything below except §6 (contract surface), §7 (log storage) and §10 is project-independent and holds for any direction in [PRD §4](prd.md#4-candidate-directions).

## 2. Stack

Same decision as [AGENTS.md §5](../../AGENTS.md#5-stack-decided).

| Layer | Choice | Notes |
| --- | --- | --- |
| Smart contract | Rust, `near-sdk` (near-sdk-rs) | Built with `cargo near` _(unverified — confirm in https://docs.near.org/ before coding)_ |
| App runtime | TypeScript on Node.js LTS | One language for UI, orchestrator, scripts |
| Dashboard / UI | Next.js (`apps/web`) | API routes host the orchestrator entry points |
| Core logic | Node TS package (`packages/core`) | DecisionClient, policy gate, NEAR client, decision log |
| NEAR JS client | `near-api-js` | _(unverified — confirm the current recommended JS SDK at https://docs.near.org/ before coding)_ |
| Decision model | TypeSafe Jev via `@typesafe-ai/sdk` | `model: "jev-latest"` (→ jev-1.14.0 as of 14 Oct 2026, [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 1) |
| LLM (text output + decision fallback) | NEAR AI Cloud (https://cloud.near.ai) | Jev produces no text; anything written goes through the LLM (tracks ranked Part 1 limit 3) |
| Package manager | pnpm workspaces | Cargo workspace for `contract/` |
| Tests | `cargo test` (contract), Vitest (TS) | See §9 |

## 3. Repo layout

Planned; scaffolded when the project is chosen.

```
contract/          Rust near-sdk contract (cargo workspace member)
packages/core/     TS: DecisionClient, policy gates, NEAR client, decision log
apps/web/          Next.js dashboard + API routes
scripts/           eval / calibration / demo-seed scripts (TS)
docs/              see docs/index.md
```

Dependency rules:

- `apps/web` depends on `packages/core`; it never calls Jev, NEAR AI Cloud or NEAR RPC directly.
- `packages/core` talks to NEAR RPC and the contract only through its NEAR client module, and to the decision backends only through `DecisionClient`.
- `scripts/` depends on `packages/core` (same code path as the app, so eval numbers describe the shipped behavior).
- `contract/` has no TypeScript dependency; the TS side depends on its method names and JSON shapes only.

## 4. DecisionClient

Design contract: every judgment call in the system goes through this interface. Question and answer shapes follow Jev's primitives ([tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 1); Box is omitted until a project needs images.

```ts
type Question =
  | { type: "choice"; prompt: string; options: string[] }   // max 255 options
  | { type: "score"; prompt: string; rubric: string[] }
  | { type: "noul"; statement: string };
type Answer =
  | { type: "choice"; choice: string; probabilities: Record<string, number>; confidence: number }
  | { type: "score"; score: string; probabilities: Record<string, number>; confidence: number }
  | { type: "noul"; noul: number };
interface DecisionClient {
  decide(state: string, questions: Record<string, Question>): Promise<Record<string, Answer>>;
}
```

- **Primary: `JevDecisionClient`.** Calls `POST https://api.typesafe.ai/v1/systemone` with `Authorization: Bearer $TYPESAFE_API_KEY` and `model: "jev-latest"`, via `@typesafe-ai/sdk`. Exact request/response field names _(unverified — confirm in https://docs.typesafe.ai before coding)_. Keep questions atomic; combine them with weights in code, not in prompts (tracks ranked Part 1).
- **Fallback: `LlmDecisionClient`.** Calls NEAR AI Cloud and coerces the reply into the same `Answer` shape (reject and retry once on off-schema output; options outside the list are invalid). API compatibility _(unverified — confirm in https://docs.near.ai before coding)_. Reference design: TypeSafe's open-source System One LLM adapter (tracks ranked Part 1 limit 1).
- **Selection:** env `DECISION_BACKEND=jev|llm`, default `jev`. On network error or timeout from Jev, fall back to `llm` automatically and record `backend: "llm"` in the decision log entry.

## 5. Policy gate

```ts
type Stakes = "read" | "money";
type GateResult = "act" | "confirm" | "refuse";
function gate(answer: Answer, stakes: Stakes): GateResult;
```

- Thresholds live in code (a table keyed by stakes tier), never in prompts.
- Defaults (tracks ranked Part 1, "The confidence pattern"):

| Stakes | act | confirm | refuse |
| --- | --- | --- | --- |
| `read` | confidence ≥ 0.5 | — | < 0.5 |
| `money` | confidence ≥ 0.9 | 0.6 ≤ confidence < 0.9 | < 0.6 |

- For `noul` answers, use the probability itself (or `1 - noul` for a negative statement) as the confidence input.
- `confirm` routes to the human-approval UI; `refuse` logs and notifies. Both are part of the demo (PRD R1).
- **The gate is not a security boundary.** Hard limits (amount caps, allowed receivers/methods) live in the contract or in function-call access keys, never only in the gate: attackers can steer Jev-style models to a wrong-but-allowed answer ([arxiv papers](../tools/arxiv_papers_for_build.md) TL;DR #1 JevBreak 2611.03759, #2 2610.12292).
- Write each policy as examples plus counterexamples in the question text (arxiv TL;DR #3, 2611.02155).

## 6. NEAR integration

Project-independent:

- **Accounts:** testnet accounts for development and the demo; faucet funds only ([HACKATHON.md](../hackathon-context/HACKATHON.md) Q-008, Q-010).
- **Keys:** the agent signs with a function-call access key scoped to our contract (and to specific methods where possible), never a full-access key.
- **NEAR Intents:** no testnet exists; use mainnet `dry: true` quotes only, from a separate dev account. Any real mainnet transaction needs human confirmation (Q-007, AGENTS.md §4).
- **RPC:** a free public provider from https://docs.near.org/api/rpc/providers (Q-009), configured via `NEAR_RPC_URL`.

> **TBD(project):** contract methods (view/change, args, access control), storage layout, and emitted events — inputs: the chosen bet's NEAR role in [PRD §4](prd.md#4-candidate-directions), [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 4 for the track's NEAR hints.

## 7. Decision log

Every decision produces one entry:

```ts
interface DecisionLogEntry {
  id: string;                               // uuid
  timestamp: string;                        // ISO 8601 UTC
  stateHash: string;                        // sha256 of the state sent to the model (raw state is not logged)
  questionKey: string;
  answer: string | number;                  // choice / score label / noul probability
  probabilities: Record<string, number>;
  confidence: number;
  gateResult: "act" | "confirm" | "refuse";
  actionTaken: string;                      // what the system actually did
  txHash?: string;                          // when the action hit NEAR
}
```

Source: [tracks ranked](../hackathon-context/near_hackathon_tracks_ranked.md) Part 7 item 3.

> **TBD(project):** where entries are stored — on-chain contract events vs an off-chain public file (or both: hash on-chain, body off-chain) — inputs: contract design in §6, cost per entry on testnet.

## 8. Configuration

All configuration comes from environment variables; `.env.example` is the canonical list.

| Variable | Purpose |
| --- | --- |
| `TYPESAFE_API_KEY` | Jev API key, from console.typesafe.ai/keys |
| `DECISION_BACKEND` | `jev` (default) or `llm`; see §4 |
| `NEAR_AI_API_KEY` | NEAR AI Cloud key for the LLM fallback and text output; from https://cloud.near.ai (Q-000) |
| `NEAR_NETWORK` | `testnet` (default); mainnet only with human confirmation |
| `NEAR_ACCOUNT_ID` | dev account the app signs with |
| `NEAR_PRIVATE_KEY` | key for `NEAR_ACCOUNT_ID`; dev account only, never committed |
| `NEAR_RPC_URL` | RPC endpoint, picked from https://docs.near.org/api/rpc/providers |
| `NEAR_INTENTS_JWT` | optional 1Click JWT; without it a 0.2% fee applies (Q-006) |

## 9. Testing & evaluation

- **Contract:** Rust unit tests with `cargo test` covering every limit the contract enforces (caps, access control).
- **TS unit tests (Vitest):** the gate (threshold boundaries per stakes tier, `noul` handling) and both DecisionClient adapters (request mapping, `Answer` coercion, fallback on timeout) with recorded responses.
- **Eval script (`scripts/`):** runs the real DecisionClient over a labeled sample and outputs the [PRD §7](prd.md#7-success-metrics) metrics (p50/p95 latency, cost per 1,000 decisions, accuracy, false-block rate) plus the confidence-vs-accuracy calibration chart.
- **Attack fixtures:** candidates from [huggingface models](../tools/huggingface_models_for_build.md) (e.g. the `nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1` dataset, `deepset/prompt-injections`) and [arxiv papers](../tools/arxiv_papers_for_build.md) (CrAIBench from 2503.16248, Agentic Commerce Bench from 2609.35886). Verify each license before use.

## 10. Project-specific modules

> **TBD(project):** modules beyond the shared core (e.g. agent simulator for Bet A, intent matcher for Bet B, merchant loop for Bet C, labeling pipeline for the Thesis play), with their interfaces — inputs: [PRD §4 and §6](prd.md), the chosen bet's section in [huggingface models](../tools/huggingface_models_for_build.md).
