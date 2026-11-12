import {
  ArrowRight,

  Box,
  Check,
  Cpu,
  FileCheck,
  Fingerprint,
  Hourglass,
  Info,
  KeyRound,
  ListChecks,
  Lock,
  ScanSearch,
  ShieldCheck,
  Undo2,
  UserSearch,
} from "lucide-react";
import { ArchitectureDiagram } from "./components/ArchitectureDiagram";
import { HeroConsole } from "./components/HeroConsole";
import { Logo } from "./components/Logo";
import { ReceiptsPanel } from "./components/ReceiptsPanel";
import { ResultsSection } from "./components/ResultsSection";
import { VerdictExplorer } from "./components/VerdictExplorer";
import { DAILY_CAP, GUARDIAN_ID, NEAR_RPC_URL, PER_PAYMENT_CAP, PROJECT_NAME, REPO_URL, STATUS_NOTE } from "./config.js";
import { createReader } from "./near.js";

const receiptsReader = createReader({ guardian: GUARDIAN_ID, rpc: NEAR_RPC_URL });

const NAV = [
  ["#problem", "Problem"],
  ["#how", "How it works"],
  ["#near", "NEAR"],
  ["#jev", "Jev"],
  ["#safety", "Safety"],
  ["#demo", "Demo"],
  ["#results", "Results"],
];

const CHECKS = [
  { Icon: ListChecks, name: "Policy rules", text: "Allowlist, memo and amount sanity; the amount must match the user's request or invoice.", paper: ["Progent", "2504.11703"], planned: false },
  { Icon: ScanSearch, name: "Injection classifier", text: "Scores every email, reply and memory chunk the agent read before it proposed the payment.", paper: ["deberta-v3 prompt-injection", ""], planned: false },
  { Icon: UserSearch, name: "Counterparty signals", text: "Account age, contract or not, prior payments, and lookalike distance to known payees.", paper: ["Address Poisoning", "2501.16681"], planned: false },
  { Icon: Undo2, name: "Masked re-run", text: "Re-run the agent with the user's request hidden. If the payment still appears, it came from injected data.", paper: ["MELON", "2502.05174"], planned: true },
];

const NEAR_ROLES = [
  { Icon: Lock, title: "Contract custody", text: "The Guardian contract holds the tUSDC. The agent cannot move it directly." },
  { Icon: KeyRound, title: "Scoped access key", text: "The agent account has only a function-call key limited to request_payment. It cannot transfer, add keys or touch NEAR." },
  { Icon: Hourglass, title: "Yield and resume", text: "request_payment pauses the contract; the checker's verdict resumes it. Pay only on an exact receiver, token, amount and request_id match." },
  { Icon: Box, title: "NEP-141 settlement", text: "Payments are ft_transfer calls on a mock tUSDC token (6 decimals) on testnet." },
  { Icon: FileCheck, title: "On-chain receipts", text: "Outcome, reason codes, input and record hashes, and the checker version, written per payment." },
  { Icon: Cpu, title: "Checker in a TEE", text: "OutLayer runs the checker WASM inside Intel TDX and publishes the attestation for each run." },
];

const JEV_QUESTIONS = [
  ["verdict", "choice", "Neutral labels A / B / C, mapped to allow / hold / block in code"],
  ["unusual", "noul", "Is this payment unusual for this agent? Drives the hold threshold"],
  ["injection_driven", "noul", "Did untrusted content, not the user, propose it? A block signal"],
  ["receiver_risk", "score", "Known payee, new but plausible, or suspicious? A block signal"],
];

const DEMO = [
  ["Hook", "A Morse-code reply moved six figures from an agent that held the keys."],
  ["Normal payment", "The agent pays an 18 tUSDC hosting invoice. Allow; the receipt is on the explorer."],
  ["Attack, unprotected", "A plain agent with a full-access key pays a lookalike account. The balance drops."],
  ["Same attack, protected", "Through the Guardian: high injection score, lookalike payee, two days old. Block; the receipt shows why."],
  ["Hold path", "A bigger invoice from a known supplier waits in escrow and is released when its window ends. No human."],
  ["Numbers", "Missed attacks, false blocks and false holds from the evaluation, with latency and calls per payment."],
];

const PAPERS = [
  ["Progent", "2504.11703"],
  ["MELON", "2502.05174"],
  ["CaMeL", "2503.18813"],
  ["Blockchain Address Poisoning", "2501.16681"],
  ["AI Agents in Cryptoland", "2503.16248"],
  ["Conformal p-values", "2104.08279"],
];

export default function App() {
  return (
    <>
      <a className="skip" href="#top">Skip to content</a>
      <header className="wide">
        <nav className="topnav" aria-label="Main">
          <a className="brand" href="#top"><Logo />{PROJECT_NAME}</a>
          <div className="navlinks">
            {NAV.map(([href, label]) => <a key={href} href={href}>{label}</a>)}
          </div>
          <a className="pill pill-accent" href="#try">Try the dry-run</a>
        </nav>
      </header>
      <hr className="hr" />

      <main id="top">
        {/* Hero */}
        <div className="wide" style={{ paddingTop: 10 }}>
          <section className="lilac hero" aria-labelledby="hero-title">
            <div className="hero-in">
              <span className="eyebrow-ink"><ShieldCheck size={14} aria-hidden="true" />Payment firewall for AI agents</span>
              <h1 id="hero-title">Give your agent a wallet, not the keys.</h1>
              <p>
                Funds sit in a contract on NEAR that the agent can't control. Every payment is checked off the agent's
                host, and every verdict leaves a receipt anyone can read.
              </p>
              <div className="btnrow">
                <a className="pill pill-cream" href="#how">See how it works</a>
                <a className="pill pill-ghost-ink" href="#receipts">Testnet receipts <ArrowRight size={16} aria-hidden="true" /></a>
              </div>
              <p className="status"><Info size={14} aria-hidden="true" />{STATUS_NOTE}</p>
            </div>
            <HeroConsole />
          </section>
        </div>

        <div className="col">
          {/* Problem */}
          <section className="sec" id="problem" aria-labelledby="problem-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">Problem</span>
                <h2 id="problem-title">Agent wallets get drained by text</h2>
              </div>
              <p>
                Prompt injection turns an agent's own tools against its wallet. Guardrails that run on the agent's host
                can be skipped by the agent they are meant to stop.
              </p>
            </div>
            <div className="split">
              <div className="chaos">
                <span className="side-tag">Without</span>
                <h3>Guardrails on the agent's own host</h3>
                <div className="incidents">
                  <p className="incident"><b>May 2026</b>About $150,000 drained<span>A Morse-code reply on X made Grok's linked wallet pay out DRB</span></p>
                  <p className="incident"><b>Keys</b>Full-access key on the agent host<span>The agent can move every token it holds</span></p>
                  <p className="incident"><b>Checks</b>Skipped<span>The guardrail ran on the compromised host</span></p>
                  <p className="incident"><b>Payee</b>Lookalike account<span>hostc0 instead of hostco, two days old</span></p>
                </div>
              </div>
              <div className="calm">
                <span className="side-tag">With</span>
                <h3>Paying through the Guardian</h3>
                <span className="okchip"><Check size={18} aria-hidden="true" />Blocked 180.00 tUSDC to hostc0</span>
                <p>
                  The agent can only ask. The contract holds the funds, waits for the checker's verdict, and pays only
                  on allow, inside hard caps.
                </p>
              </div>
            </div>
            <p className="source">
              Source:{" "}
              <a href="https://giskard.ai/knowledge/how-grok-got-prompt-injected-an-x-user-drained-150-000-from-an-ai-wallet">
                Giskard, "How Grok got prompt-injected"
              </a>
              .
            </p>
          </section>

          {/* How it works */}
          <section className="sec" id="how" aria-labelledby="how-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">How it works</span>
                <h2 id="how-title">The agent asks, the checker decides, only the contract pays</h2>
              </div>
              <p>Four checks run on every payment. Jev fuses their signals into one verdict: allow, hold or block.</p>
            </div>
            <ArchitectureDiagram />
            <ol className="steps">
              <li>
                <KeyRound size={24} strokeWidth={1.5} aria-hidden="true" />
                <h3>The agent asks</h3>
                <p>A function-call key scoped to the Guardian. It can request a payment, never send one.</p>
              </li>
              <li>
                <Cpu size={24} strokeWidth={1.5} aria-hidden="true" />
                <h3>The checker decides</h3>
                <p>The checks run inside a TEE, so a compromised agent host cannot fake, skip or edit them.</p>
              </li>
              <li>
                <Lock size={24} strokeWidth={1.5} aria-hidden="true" />
                <h3>Only the contract pays</h3>
                <p>The Guardian acts on the verdict, pays only on an exact match, and writes the receipt.</p>
              </li>
            </ol>
            <VerdictExplorer />
            <div className="grid4">
              {CHECKS.map(({ Icon, name, text, paper, planned }) => (
                <div key={name}>
                  <Icon size={22} strokeWidth={1.5} aria-hidden="true" />
                  <h3>{name}</h3>
                  {planned && <span className="tag">Planned</span>}
                  <p>{text}</p>
                  {paper[1] ? (
                    <a className="paper" href={`https://arxiv.org/abs/${paper[1]}`}>{paper[0]} · arXiv {paper[1]}</a>
                  ) : (
                    <a className="paper" href="https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2">{paper[0]} · Hugging Face</a>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* NEAR's role */}
          <section className="sec" id="near" aria-labelledby="near-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">NEAR's role</span>
                <h2 id="near-title">NEAR holds the money and the rules</h2>
              </div>
              <p>Custody, key scope, caps, settlement and the audit log all live on-chain. The AI never touches funds.</p>
            </div>
            <div className="cards">
              {NEAR_ROLES.map(({ Icon, title, text }) => (
                <div className="card" key={title}>
                  <Icon size={24} strokeWidth={1.5} aria-hidden="true" />
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Jev's role */}
          <section className="sec" id="jev" aria-labelledby="jev-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">Jev's role</span>
                <h2 id="jev-title">Jev makes the judgment calls</h2>
              </div>
              <p>
                Jev (TypeSafe) turns the raw signals and the agent's payment history into calibrated judgments. Caps,
                sums and dates stay in code.
              </p>
            </div>
            <div className="cards">
              <div className="card lil">
                <Fingerprint size={24} strokeWidth={1.5} aria-hidden="true" />
                <h3>Four typed questions, one request</h3>
                <ul style={{ color: "inherit" }}>
                  {JEV_QUESTIONS.map(([q, t, d]) => (
                    <li key={q}><code>{q}</code> ({t}): {d}</li>
                  ))}
                </ul>
              </div>
              <div className="card">
                <h3>Hold when it's unusual</h3>
                <p>
                  A payment is held when Jev's <code className="ic">unusual</code> score passes a conformal threshold
                  set at ε = 5% on a pooled set of normal payments. An agent gets its own threshold after 99 normal payments.
                </p>
                <h3>Block only when two detectors agree</h3>
                <p>Above the threshold and two attack signals from different detectors, at most one of them from Jev.</p>
              </div>
              <div className="card">
                <h3>Hardened against the gate itself</h3>
                <ul>
                  <li>Neutral option labels, so names can't steer the answer</li>
                  <li>Untrusted text goes in as data only</li>
                  <li>Probabilities never reach the agent or the chain</li>
                  <li>If Jev fails or times out, a NEAR AI Cloud LLM decides and the record says so</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Safety layers */}
          <section className="sec" id="safety" aria-labelledby="safety-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">Safety layers</span>
                <h2 id="safety-title">No AI ever decides an amount</h2>
              </div>
              <p>A Jev gate alone is not a security boundary. The limits that bound the loss are in contract code.</p>
            </div>
            <div className="tiers">
              <div className="tier">
                <span className="name">Hard cap</span><span className="for">whatever is fooled</span>
                <span className="val">{DAILY_CAP} <small>tUSDC / day</small></span>
                <p>The absolute worst case, whatever the checks miss.</p>
              </div>
              <div className="tier">
                <span className="name">Per payment</span><span className="for">checked before the TEE runs</span>
                <span className="val">{PER_PAYMENT_CAP} <small>tUSDC</small></span>
                <p>Larger requests are refused outright.</p>
              </div>
            </div>
            <div className="tablewrap">
              <table>
                <thead><tr><th>Layer</th><th>Rule</th><th>Enforced by</th></tr></thead>
                <tbody>
                  <tr><td>Verdict bound to the request</td><td>Receiver, token, exact amount and a one-time request_id; any mismatch is refused</td><td>Contract code</td></tr>
                  <tr><td>Hard caps</td><td>{PER_PAYMENT_CAP} tUSDC per payment, {DAILY_CAP} tUSDC per day</td><td>Contract code</td></tr>
                  <tr><td>Hold windows</td><td>10 min under 20 tUSDC, 1 h up to 100, 6 h above</td><td>Contract escrow</td></tr>
                  <tr><td>Whole units only</td><td>Amounts in the token's smallest unit, compared with the request or invoice</td><td>Checker code</td></tr>
                  <tr><td>Per-payee budgets</td><td>A new payee starts at 20 tUSDC; an allow above the budget waits in escrow like a hold; each paid transfer raises the budget to twice that amount, up to the per-payment cap</td><td>Contract code</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Demo */}
          <section className="sec" id="demo" aria-labelledby="demo-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">Demo</span>
                <h2 id="demo-title">Same agent. Same attack. Different outcome.</h2>
              </div>
              <p>About two minutes, recorded on testnet with real transactions.</p>
            </div>
            <div className="demo">
              <div className="video" role="img" aria-label="Demo video placeholder">Demo video goes here once recorded</div>
              <ol className="dsteps">
                {DEMO.map(([title, text], i) => (
                  <li key={title}>
                    <span className="dn">{String(i + 1).padStart(2, "0")}</span>
                    <div><h3>{title}</h3><p>{text}</p></div>
                  </li>
                ))}
              </ol>
            </div>
          </section>

          {/* Results */}
          <ResultsSection />

          {/* Live receipts (E1) */}
          <section className="sec" id="receipts" aria-labelledby="receipts-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">Receipts</span>
                <h2 id="receipts-title">Don't trust us. Read the receipt.</h2>
              </div>
              <p>
                The receipt proves which checker version ran on which inputs. It does not prove Jev or the LLM answered
                correctly; those run outside.
              </p>
            </div>
            <ReceiptsPanel reader={receiptsReader} />
          </section>

          {/* Try it */}
          <section className="sec" id="try" aria-labelledby="try-title">
            <div className="head2">
              <div className="l">
                <span className="kicker">Try it</span>
                <h2 id="try-title">Run the dry-run, no keys needed</h2>
              </div>
              <p>From the repo root. Needs Rust and uv. Full steps, including testnet, are in the README.</p>
            </div>
            <div className="cards">
              <div className="card">
                <pre className="term">
                  <span className="c"># 1. build the checker</span>{"\n"}
                  cargo build -p checker --release{"\n"}
                  <span className="c"># 2. a benign payment</span>{"\n"}
                  cd agent && uv sync{"\n"}
                  uv run firewall-demo --scenario <span className="s">benign-hosting</span>{"\n"}
                  <span className="c"># 3. the Morse-code attack</span>{"\n"}
                  uv run firewall-demo --scenario <span className="s">attack-morse-lookalike</span>
                </pre>
              </div>
            </div>
          </section>
        </div>

        {/* Closing */}
        <div className="wide closing">
          <section className="lilac cta" aria-labelledby="cta-title">
            <span className="eyebrow-ink"><ShieldCheck size={14} aria-hidden="true" />Built on NEAR · testnet</span>
            <h2 id="cta-title">Every payment leaves a receipt.</h2>
            <p>Deploy a Guardian, scope the agent's key to one method, and every payment from then on is checked and recorded.</p>
            <div className="btnrow">
              <a className="pill pill-cream" href="#try">Try the dry-run</a>
              {REPO_URL && <a className="pill pill-ghost-ink" href={REPO_URL}>Source code</a>}
            </div>
          </section>
        </div>
      </main>

      {/* Links */}
      <footer style={{ marginTop: "clamp(40px, 5vw, 64px)" }}>
        <hr className="hr" />
        <div className="col">
          <span className="wordmark"><Logo size={22} />{PROJECT_NAME}</span>
          <div className="fcols">
            <div>
              <b>Project</b>
              <a href="#how">How it works</a>
              <a href="#safety">Safety layers</a>
              <a href="#receipts">Receipts</a>
              {REPO_URL ? <a href={REPO_URL}>Source code</a> : <span>Source: public at submission</span>}
            </div>
            <div>
              <b>Built with</b>
              <a href="https://docs.near.org/protocol/accounts-contracts/access-keys">NEAR access keys</a>
              <a href="https://app.outlayer.ai/docs/getting-started">OutLayer</a>
              <a href="https://typesafe.ai">TypeSafe Jev</a>
              <a href="https://cloud.near.ai">NEAR AI Cloud</a>
            </div>
            <div>
              <b>Research</b>
              {PAPERS.map(([name, id]) => <a key={id} href={`https://arxiv.org/abs/${id}`}>{name}</a>)}
            </div>
          </div>
          <div className="fine">
            <span>Built for NEAR HACKATHON 2026 · MIT licence</span>
            <span className="mono">rust · near-sdk · outlayer · jev · python</span>
          </div>
        </div>
      </footer>
    </>
  );
}
