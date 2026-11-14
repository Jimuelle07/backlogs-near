import { Component, lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Box,
  Check,
  Cpu,
  FileCheck,
  Fingerprint,
  Hourglass,
  KeyRound,
  ListChecks,
  Lock,
  Plus,
  ScanSearch,
  ShieldCheck,
  Undo2,
  UserSearch,
  BarChart3,
  Radio,
  TriangleAlert,
  Menu,
  X,
} from "lucide-react";
import { ArchitectureDiagram } from "./components/ArchitectureDiagram";
import { Console } from "./components/Console";
import { DotField } from "./components/DotField";
import { DemoNumbers, HookFeed, HoldLog } from "./components/DemoAnims";
import { Frame } from "./components/Frame";
import { Logo } from "./components/Logo";
import { MorseField } from "./components/MorseField";
import { ReceiptsPanel } from "./components/ReceiptsPanel";
import { ResultsSection } from "./components/ResultsSection";
import { VerdictExplorer } from "./components/VerdictExplorer";
import { DAILY_CAP, GUARDIAN_ID, NEAR_RPC_URL, PER_PAYMENT_CAP, PROJECT_NAME, REPO_URL } from "./config.js";
import { createReader } from "./near.js";
import { FAQ } from "./faq.js";
import { startMotion } from "./motion.js";

// three.js loads after first paint, in its own chunk; the prerender shows the placeholder.
const Eclipse = lazy(() => import("./components/Eclipse.jsx"));

// A missing WebGL context (graphics acceleration off, blocklisted GPU) or a failed chunk load
// must cost only the globe, not unmount the whole page.
class SceneBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error) { console.warn("3D scene disabled:", error); }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

const receiptsReader = createReader({ guardian: GUARDIAN_ID, rpc: NEAR_RPC_URL });

const NAV = [
  ["#problem", "Problem"],
  ["#how", "How it works"],
  ["#near", "NEAR"],
  ["#jev", "Jev"],
  ["#safety", "Safety"],
  ["#demo", "Demo"],
  ["#results", "Results"],
  ["#faq", "FAQ"],
];

const INCIDENTS = [
  ["May 2026", "About $150,000 drained", "A Morse-code reply on X made Grok's linked wallet pay out DRB"],
  ["Keys", "Full-access key on the agent host", "The agent can move every token it holds"],
  ["Checks", "Skipped", "The guardrail ran on the compromised host"],
  ["Payee", "Lookalike account", "hostc0 instead of hostco, two days old"],
];

const STEPS = [
  { Icon: KeyRound, title: "The agent asks", text: "A function-call key scoped to the Guardian. It can request a payment, never send one." },
  { Icon: Cpu, title: "The checker decides", text: "The checks run inside a TEE, so a compromised agent host cannot fake, skip or edit them." },
  { Icon: Lock, title: "Only the contract pays", text: "The Guardian acts on the verdict, pays only on an exact match, and writes the receipt." },
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

// Icons for the demo steps, in order.
const DEMO_ICONS = [Radio, Check, TriangleAlert, ShieldCheck, Hourglass, BarChart3];

const PAPERS = [
  ["Progent", "2504.11703"],
  ["MELON", "2502.05174"],
  ["CaMeL", "2503.18813"],
  ["Blockchain Address Poisoning", "2501.16681"],
  ["AI Agents in Cryptoland", "2503.16248"],
  ["Conformal p-values", "2104.08279"],
];

// Decorative tiles in the closing card (icons only).
// Closing-card tiles: two three-tile clusters beside the copy. Each tile starts scattered
// (dx, dy px, tilt deg) and glides into its cell while the main button is hovered: [icon, side, row, col, dx, dy, tilt, dark?].
const CTA_TILES = [
  [ShieldCheck, "left", 1, 2, -120, -150, -16, false],
  [FileCheck, "left", 2, 1, 40, 150, 14, true],
  [Fingerprint, "left", 2, 2, 90, 120, -10, false],
  [Lock, "right", 1, 1, 150, -160, 18, false],
  [Cpu, "right", 1, 2, -80, 110, -12, false],
  [KeyRound, "right", 2, 2, -40, 150, 10, true],
];
// Facts for the bottom strip, all stated elsewhere on this page.
const CTA_FACTS = [
  [Lock, `Hard caps: ${PER_PAYMENT_CAP} tUSDC per payment, ${DAILY_CAP} tUSDC per day, in contract code`],
  [KeyRound, "Scoped access key"],
  [Cpu, "Checker in a TEE"],
  [FileCheck, "On-chain receipts"],
  [Check, "Verdict bound to the request"],
  [ShieldCheck, "No AI ever decides an amount"],
];

// Safety layers as visuals: the two caps as a gauge, then each rule as a card with a small diagram.
// Every rule's wording is the same as the old table; the diagrams only restate those numbers.
function SafetyVisual() {
  const perPct = (PER_PAYMENT_CAP / DAILY_CAP) * 100;
  return (
    <div className="safety">
      <div className="caps">
        <div className="caps-top">
          <div className="cap-fig">
            <span className="cap-name">Hard cap</span><span className="cap-for">whatever is fooled</span>
            <b>{DAILY_CAP}<small> tUSDC / day</small></b>
            <p>The absolute worst case, whatever the checks miss.</p>
          </div>
          <div className="cap-fig">
            <span className="cap-name">Per payment</span><span className="cap-for">checked before the TEE runs</span>
            <b>{PER_PAYMENT_CAP}<small> tUSDC</small></b>
            <p>Larger requests are refused outright.</p>
          </div>
        </div>
        <div className="gauge" aria-hidden="true">
          <div className="gauge-track">
            <span className="gauge-pay" style={{ width: `${perPct}%` }}><i>{PER_PAYMENT_CAP} per payment</i></span>
          </div>
          <div className="gauge-scale"><span>0</span><span>{DAILY_CAP} tUSDC / day</span></div>
        </div>
      </div>

      <ul className="rules">
        <li className="rule">
          <div className="rule-head"><span className="itile"><Fingerprint size={20} strokeWidth={1.6} aria-hidden="true" /></span><span className="enf">Contract code</span></div>
          <h3>Verdict bound to the request</h3>
          <div className="rule-viz bind" aria-hidden="true">
            {["Receiver", "Token", "Exact amount", "request_id"].map((k) => <span key={k}><Check size={12} />{k}</span>)}
          </div>
          <p>Receiver, token, exact amount and a one-time request_id; any mismatch is refused</p>
        </li>
        <li className="rule">
          <div className="rule-head"><span className="itile"><Lock size={20} strokeWidth={1.6} aria-hidden="true" /></span><span className="enf">Contract code</span></div>
          <h3>Hard caps</h3>
          <div className="rule-viz bars" aria-hidden="true">
            <span style={{ width: `${perPct}%` }}>{PER_PAYMENT_CAP}</span>
            <span style={{ width: "100%" }}>{DAILY_CAP}</span>
          </div>
          <p>{PER_PAYMENT_CAP} tUSDC per payment, {DAILY_CAP} tUSDC per day</p>
        </li>
        <li className="rule">
          <div className="rule-head"><span className="itile"><Hourglass size={20} strokeWidth={1.6} aria-hidden="true" /></span><span className="enf">Contract escrow</span></div>
          <h3>Hold windows</h3>
          <div className="rule-viz steps3" aria-hidden="true">
            <span><b>10 min</b>{"< 20"}</span><span><b>1 h</b>{"≤ 100"}</span><span><b>6 h</b>{"> 100"}</span>
          </div>
          <p>10 min under 20 tUSDC, 1 h up to 100, 6 h above</p>
        </li>
        <li className="rule">
          <div className="rule-head"><span className="itile"><ListChecks size={20} strokeWidth={1.6} aria-hidden="true" /></span><span className="enf">Checker code</span></div>
          <h3>Whole units only</h3>
          <div className="rule-viz units" aria-hidden="true">
            <span>request</span><b>=</b><span>invoice</span><b>=</b><span>payment</span>
          </div>
          <p>Amounts in the token's smallest unit, compared with the request or invoice</p>
        </li>
        <li className="rule rule-wide">
          <div className="rule-head"><span className="itile"><UserSearch size={20} strokeWidth={1.6} aria-hidden="true" /></span><span className="enf">Contract code</span></div>
          <h3>Per-payee budgets</h3>
          <div className="rule-viz ladder" aria-hidden="true">
            {[20, 40, 80, 160, PER_PAYMENT_CAP].map((v, k) => (
              <span key={v} style={{ height: `${(v / PER_PAYMENT_CAP) * 100}%` }}><i>{v}</i>{k < 4 && <em>×2</em>}</span>
            ))}
          </div>
          <p>A new payee starts at 20 tUSDC; an allow above the budget waits in escrow like a hold; each paid transfer raises the budget to twice that amount, up to the per-payment cap</p>
        </li>
      </ul>
    </div>
  );
}

function Head({ id, kicker, title, children }) {
  return (
    <div className="head2">
      <div className="l">
        <h2 id={id}>{title}</h2>
      </div>
      <p>{children}</p>
    </div>
  );
}

const IconTile = ({ Icon }) => (
  <span className="itile"><Icon size={20} strokeWidth={1.6} aria-hidden="true" /></span>
);

export default function App() {
  const refs = {
    heroGlow: useRef({ v: 1 }),
    ctaGlow: useRef({ v: 0.4 }),
    morseProgress: useRef(0),
  };
  // The protocol scene reports its phase; the matching step card lights up (CSS on data-step).
  const stepsRef = useRef(null);
  const onStep = useCallback((i) => { if (stepsRef.current) stepsRef.current.dataset.step = i; }, []);
  const [client, setClient] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);
  const [ctaOn, setCtaOn] = useState(false); // closing card: tiles assemble while the main button is hovered or focused

  useEffect(() => {
    setClient(true);
    let stop = () => {};
    let cancelled = false;
    startMotion(refs).then((fn) => { if (cancelled) fn(); else stop = fn; });
    return () => { cancelled = true; stop(); };
    // refs are stable objects
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <a className="skip" href="#top">Skip to content</a>
      <header className="site-header">
        <nav className="topnav wide" aria-label="Main">
          <a className="brand" href="#top"><Logo />{PROJECT_NAME}</a>
          <div className="navlinks">
            {NAV.map(([href, label]) => <a key={href} href={href}>{label}</a>)}
          </div>
          <a className="pill pill-accent nav-cta" href="#try">Try the dry-run</a>
          <button type="button" className="menu-btn" aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen} aria-controls="mobile-menu" onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
          </button>
        </nav>
      </header>
      <div className="mini">
        <a className="mini-chip" href="#top" tabIndex={-1} aria-hidden="true"><Logo size={18} />{PROJECT_NAME}</a>
        <a className="pill pill-accent nav-cta" href="#try" tabIndex={-1} aria-hidden="true">Try the dry-run</a>
        <button type="button" className="menu-btn mini-menu" aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen} aria-controls="mobile-menu" onClick={() => setMenuOpen((o) => !o)}>
          {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
        </button>
      </div>
      {/* Phones: the three-line menu opens this panel. */}
      <div className={`mmenu-scrim${menuOpen ? " open" : ""}`} onClick={() => setMenuOpen(false)} aria-hidden="true" />
      <nav id="mobile-menu" className={`mmenu${menuOpen ? " open" : ""}`} aria-label="Menu" hidden={!menuOpen}>
        {NAV.map(([href, label]) => <a key={href} href={href} onClick={() => setMenuOpen(false)}>{label}</a>)}
        <a className="pill pill-accent" href="#try" onClick={() => setMenuOpen(false)}>Try the dry-run</a>
      </nav>

      <main id="top">
        {/* Hero */}
        <div className="wide hero-wrap">
          <section className="lilac hero" aria-labelledby="hero-title">
            <DotField glow={refs.heroGlow} />
            <div className="hero-in">
              <span className="eyebrow-ink"><ShieldCheck size={14} aria-hidden="true" />{PROJECT_NAME} · payment firewall for AI agents on NEAR</span>
              <h1 id="hero-title">Give your agent a wallet, not the keys.</h1>
              <p>
                Funds sit in a contract on NEAR that the agent can't control. Every payment is checked off the agent's
                host, and every verdict leaves a receipt anyone can read.
              </p>
              <div className="btnrow">
                <a className="pill pill-cream" href="#how">See how it works</a>
                <a className="pill pill-ghost-ink" href="#receipts">Testnet receipts <ArrowRight size={16} aria-hidden="true" /></a>
              </div>
            </div>
            <div className="console-wrap"><Console /></div>
          </section>
        </div>

        <div className="col">
          {/* Problem */}
          <section className="sec" id="problem" aria-labelledby="problem-title">
            <Head id="problem-title" kicker="Problem" title="Agent wallets get drained by text">
              Prompt injection turns an agent's own tools against its wallet. Guardrails that run on the agent's host
              can be skipped by the agent they are meant to stop.
            </Head>
            <div className="split">
              <div className="chaos">
                <MorseField progress={refs.morseProgress} />
                <span className="side-tag">Without</span>
                <h3>Guardrails on the agent's own host</h3>
                <div className="asciigrid">
                  {INCIDENTS.map(([tag, title, detail]) => (
                    <div className="ascii" key={tag}>
                      <p className="incident">
                        <b>{tag}</b>{title}<span>{detail}</span>
                      </p>
                    </div>
                  ))}
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
            <Head id="how-title" kicker="How it works" title="The agent asks, the checker decides, only the contract pays">
              Four checks run on every payment. Jev fuses their signals into one verdict: allow, hold or block.
            </Head>
            <ArchitectureDiagram />
            <div className="protocol">
              <Frame className="stage3" id="protocol">
                {client ? (
                  <SceneBoundary fallback={<div className="globe globe-wait" aria-hidden="true" />}>
                    <Suspense fallback={<div className="globe globe-wait" aria-hidden="true" />}>
                      <Eclipse onStep={onStep} />
                    </Suspense>
                  </SceneBoundary>
                ) : <div className="globe globe-wait" aria-hidden="true" />}
                <ol className="psteps psteps-overlay" ref={stepsRef}>
                  {STEPS.map(({ Icon, title, text }, i) => (
                    <li key={title}>
                      <span className="pstep-n">{String(i + 1).padStart(2, "0")}</span>
                      <IconTile Icon={Icon} />
                      <div><h3>{title}</h3><p>{text}</p></div>
                    </li>
                  ))}
                </ol>
              </Frame>
            </div>
            <VerdictExplorer />
            <div className="grid4">
              {CHECKS.map(({ Icon, name, text, paper, planned }) => (
                <div key={name}>
                  <IconTile Icon={Icon} />
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
            <Head id="near-title" kicker="NEAR's role" title="NEAR holds the money and the rules">
              Custody, key scope, caps, settlement and the audit log all live on-chain. The AI never touches funds.
            </Head>
            <div className="cards">
              {NEAR_ROLES.map(({ Icon, title, text }) => (
                <div className="card" key={title}>
                  <IconTile Icon={Icon} />
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Jev's role */}
          <section className="sec" id="jev" aria-labelledby="jev-title">
            <Head id="jev-title" kicker="Jev's role" title="Jev makes the judgment calls">
              Jev (TypeSafe) turns the raw signals and the agent's payment history into calibrated judgments. Caps,
              sums and dates stay in code.
            </Head>
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
            <Head id="safety-title" kicker="Safety layers" title="No AI ever decides an amount">
              A Jev gate alone is not a security boundary. The limits that bound the loss are in contract code.
            </Head>
            <SafetyVisual />
          </section>

          {/* Demo */}
          <section className="sec" id="demo" aria-labelledby="demo-title">
            <Head id="demo-title" kicker="Demo" title="Same agent. Same attack. Different outcome.">
              About three and a half minutes: the story first, then a live run on NEAR testnet with real transactions.
            </Head>
            {/* Bento: the video, then the six steps of the demo script as cards. */}
            <ol className="dbento">
              <li className="dcard dvideo">
                <video
                  className="video"
                  src={`${import.meta.env.BASE_URL}video/eclipse-demo.mp4`}
                  poster={`${import.meta.env.BASE_URL}video/eclipse-demo-poster.jpg`}
                  controls
                  playsInline
                  preload="metadata"
                  aria-label="Eclipse demo video"
                />
              </li>
              {DEMO.map(([title, text], i) => {
                const Icon = DEMO_ICONS[i];
                return (
                  <li key={title} className={`dcard d${i + 1}${i === 0 ? " accent" : ""}`}>
                    <div className="dhead">
                      <span className="itile"><Icon size={20} strokeWidth={1.6} aria-hidden="true" /></span>
                      <span className="dn">{String(i + 1).padStart(2, "0")}</span>
                    </div>
                    {i === 0 && <HookFeed />}
                    {i === 4 && <HoldLog />}
                    {i === 5 && <DemoNumbers />}
                    <div className="dbody"><h3>{title}</h3><p>{text}</p></div>
                  </li>
                );
              })}
            </ol>
          </section>

          {/* Results */}
          <ResultsSection />

          {/* Live receipts (E1) */}
          <section className="sec" id="receipts" aria-labelledby="receipts-title">
            <Head id="receipts-title" kicker="Receipts" title="Don't trust us. Read the receipt.">
              The receipt proves which checker version ran on which inputs. It does not prove Jev or the LLM answered
              correctly; those run outside.
            </Head>
            <ReceiptsPanel reader={receiptsReader} />
          </section>

          {/* Try it */}
          <section className="sec" id="try" aria-labelledby="try-title">
            <div className="side-split try-split">
            <Head id="try-title" kicker="Try it" title="Run the dry-run, no keys needed">
              From the repo root. Needs Rust and uv. Full steps, including testnet, are in the README.
            </Head>
            <div className="term-win"><div className="term-bar" aria-hidden="true"><span className="win-dots"><i /><i /><i /></span>dry-run</div>
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

          {/* FAQ: plain answers; the same list feeds the FAQPage structured data. */}
          <section className="sec" id="faq" aria-labelledby="faq-title">
            <div className="faq-split">
            <Head id="faq-title" kicker="FAQ" title="Questions, answered plainly">
              Short answers about what {PROJECT_NAME} is, how it decides, and what it does not cover.
            </Head>
            <div className="faq-wrap">
              {/* Native disclosure: answers stay in the HTML for crawlers and the FAQPage data. */}
              <div className="faq">
                {FAQ.map(({ q, a }, i) => (
                  <details key={q} className="faq-item" open={i === 0}>
                    <summary>
                      <span className="faq-n">{String(i + 1).padStart(2, "0")}</span>
                      <h3>{q}</h3>
                      <Plus className="faq-icon" size={18} aria-hidden="true" />
                    </summary>
                    <p>{a}</p>
                  </details>
                ))}
              </div>
            </div>
            </div>
          </section>
        </div>

        {/* Closing */}
        <div className="wide closing">
          <section className={`lilac cta${ctaOn ? " assembled" : ""}`} aria-labelledby="cta-title">
            <DotField glow={refs.ctaGlow} />
            <div className="cta-in">
              <span className="eyebrow-ink"><ShieldCheck size={14} aria-hidden="true" />Built on NEAR · testnet</span>
              <h2 id="cta-title">Every payment leaves a receipt.</h2>
              <p>Deploy a Guardian, scope the agent's key to one method, and every payment from then on is checked and recorded.</p>
              <div className="btnrow">
                <a
                  className="pill pill-cream"
                  href="#try"
                  onMouseEnter={() => setCtaOn(true)}
                  onMouseLeave={() => setCtaOn(false)}
                  onFocus={() => setCtaOn(true)}
                  onBlur={() => setCtaOn(false)}
                >
                  Try the dry-run
                </a>
                {REPO_URL && <a className="pill pill-ghost-ink" href={REPO_URL}>Source code</a>}
              </div>
            </div>
            <div className="cta-art" aria-hidden="true">
              {["left", "right"].map((side) => (
                <div className={`cta-cluster ${side}`} key={side}>
                  <Frame className="cta-frame">
                    <div className="cta-grid">
                      {CTA_TILES.filter((t) => t[1] === side).map(([Icon, , row, col, dx, dy, tilt, dark]) => (
                        <div className="cta-slot" key={`${row}-${col}`} style={{ gridRow: row, gridColumn: col, "--dx": `${dx}px`, "--dy": `${dy}px`, "--tilt": `${tilt}deg` }}>
                          <div className={`cta-tile${dark ? " dark" : ""}`}><Icon size={26} strokeWidth={1.5} /></div>
                        </div>
                      ))}
                    </div>
                  </Frame>
                </div>
              ))}
            </div>
            <div className="cta-strip" aria-label="Key facts">
              <div className="cta-strip-track">
                {[0, 1].map((copy) => (
                  <ul key={copy} aria-hidden={copy === 1 ? "true" : undefined}>
                    {CTA_FACTS.map(([Icon, text]) => (
                      <li key={text}><Icon size={16} strokeWidth={1.6} aria-hidden="true" />{text}</li>
                    ))}
                  </ul>
                ))}
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* Links */}
      <footer>
        <div className="col">
          <span className="wordmark"><Logo size={22} />{PROJECT_NAME}</span>
          <div className="fcols">
            <div>
              <b>Project</b>
              <a href="#how">How it works</a>
              <a href="#safety">Safety layers</a>
              <a href="#receipts">Receipts</a>
              <a href="#results">Results</a>
              <a href="#faq">FAQ</a>
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
            <span>Built for NEAR HACKATHON 2026</span>
          </div>
        </div>
      </footer>
    </>
  );
}
