import { useEffect, useRef, useState } from "react";
import { Frame } from "./Frame";
import { prefersReducedMotion } from "../motion.js";
import { DAILY_CAP, PER_PAYMENT_CAP } from "../config";
import { Ban, Check, Hourglass, ListChecks, ScanSearch, Sparkles, Undo2, UserSearch } from "lucide-react";

// D2: one payment, three verdicts. Same checks every time; only which ones fire changes.
// Block needs two attack signals from different detectors, at most one from Jev (idea.md, Decision model).
const CHECKS = [
  ["Policy", ListChecks],
  ["Injection", ScanSearch],
  ["Payee", UserSearch],
  ["Re-run", Undo2],
  ["Jev", Sparkles],
];
const PLANNED = 3; // masked re-run (MELON) is not scheduled yet

const VERDICTS = {
  allow: {
    label: "Allow",
    Icon: Check,
    title: "Pays now",
    text: "The payment fits this agent's history and no check raises a signal. The Guardian pays and writes the receipt.",
    fired: [],
    example: "18 tUSDC to hostco, the usual hosting invoice",
    facts: [["Wait", "none"], ["Moves", "the exact amount"], ["Receipt", "paid"]],
  },
  hold: {
    label: "Hold",
    Icon: Hourglass,
    title: "Escrow, re-check, release",
    text: "Jev scores it unusual for this agent, above the conformal threshold, but fewer than two attack signals agree. It waits in escrow and releases on its own if nothing turns up.",
    fired: [4],
    example: "90 tUSDC to a known supplier, above its usual range",
    facts: [["Wait", "10 min under 20 tUSDC, 1 h to 100, 6 h above"], ["Moves", "after the window, if clean"], ["Receipt", "held"]],
  },
  block: {
    label: "Block",
    Icon: Ban,
    title: "Nothing moves",
    text: "The injection classifier flags the reply the agent read, and the payee is a two-day-old lookalike of a known one. Two detectors agree, so the Guardian refuses.",
    fired: [1, 2],
    example: "180 tUSDC to hostc0 after a Morse-code reply",
    facts: [["Wait", "none"], ["Moves", "0 tUSDC"], ["Receipt", "refused, with reason codes"]],
  },
};

// The verdict title sits in a large highlighted box and cycles allow → hold → block on its own;
// the small list below is the control. The active item's bar fills over one cycle and advances
// the verdict when it ends. Picking a verdict stops the cycle.
const ORDER = ["allow", "hold", "block"];

export function VerdictExplorer() {
  const [v, setV] = useState("block");
  const [auto, setAuto] = useState(false);
  const [onScreen, setOnScreen] = useState(false);
  const root = useRef(null);
  const cur = VERDICTS[v];

  useEffect(() => {
    if (prefersReducedMotion()) return undefined;
    setAuto(true);
    const io = new IntersectionObserver(([e]) => setOnScreen(e.isIntersecting), { threshold: 0.3 });
    io.observe(root.current);
    return () => io.disconnect();
  }, []);

  const pick = (k) => { setAuto(false); setV(k); };
  const next = () => setV((k) => ORDER[(ORDER.indexOf(k) + 1) % ORDER.length]);

  return (
    <div className={`vx${auto ? " auto" : ""}${auto && !onScreen ? " paused" : ""}`} ref={root}>
      <div className="vx-left">
        <div aria-live="polite" className="vx-phrase">
          <h3 className={`vx-chip ${v}`} key={v}>{cur.title}</h3>
          <p key={`${v}-p`} className="vx-text">{cur.text}</p>
          <div className="vx-menu" role="group" aria-label="Choose a verdict">
            {ORDER.map((k) => {
              const { label, Icon } = VERDICTS[k];
              return (
                <button key={k} type="button" aria-pressed={v === k} onClick={() => pick(k)}>
                  <Icon size={15} aria-hidden="true" />
                  {label}
                  {v === k && auto && <span className="vx-timer" aria-hidden="true" onAnimationEnd={next} />}
                </button>
              );
            })}
          </div>
        </div>
        <Frame className="pipe">
          <div className="pipe-top">
            <span>Payment request</span>
            <b>Guardian contract</b>
          </div>
          <div className="pipe-boxes">
            {CHECKS.map(([name, Icon], i) => {
              const state = cur.fired.includes(i) ? "fail" : i === PLANNED ? "planned" : "lit";
              return (
                <div key={name} className={`pbox ${state}`}>
                  <Icon size={16} aria-hidden="true" />
                  {name}
                  <span className="sr">
                    {state === "fail" ? ": raised a signal" : state === "planned" ? ": planned" : ": clear"}
                  </span>
                </div>
              );
            })}
          </div>
          <ul className="pipe-legend" aria-hidden="true">
            <li><i className="lg fail" />raised a signal</li>
            <li><i className="lg lit" />clear</li>
            <li><i className="lg planned" />planned</li>
          </ul>
          <p className="pipe-foot">Same checks on every payment. Only the verdict changes.</p>
        </Frame>
      </div>
      <div className="vx-right">
        <Frame className={`vx-facts ${v}`}>
          <dl>
            <div>
              <dt>Example</dt>
              <dd>{cur.example}</dd>
            </div>
            {cur.facts.map(([k, val]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{val}</dd>
              </div>
            ))}
            <div>
              <dt>Whatever is fooled</dt>
              <dd>{PER_PAYMENT_CAP} tUSDC per payment, {DAILY_CAP} per day, in contract code</dd>
            </div>
          </dl>
        </Frame>
      </div>
    </div>
  );
}
