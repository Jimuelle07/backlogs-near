import { useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Hourglass, LoaderCircle } from "lucide-react";
import { prefersReducedMotion } from "../motion.js";
import results from "../../../docs/results/results.json";
import { formatResultNumber, headline } from "../results.js";
import { PROJECT_NAME } from "../config.js";

// Runs `tick` every `ms` while the element is on screen; never under reduced motion.
function useTicker(ref, ms, tick) {
  useEffect(() => {
    if (prefersReducedMotion() || !ref.current) return undefined;
    let visible = false;
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    io.observe(ref.current);
    const id = setInterval(() => { if (visible && !document.hidden) tick(); }, ms);
    return () => { clearInterval(id); io.disconnect(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms]);
}

// 01 Hook: Morse-coded replies roll in and each one moves money out of the unprotected agent.
// Illustration of the demo's hook (docs/build/idea.md "Demo script"), not real traffic.
const MORSE = ["·−−· ·− −·−−", "··· · −· −··", "−· −−− ·−−", "·− ·−·· ·−··", "·−−· ·− −·−−  −· −−− ·−−"];
export function HookFeed() {
  const ref = useRef(null);
  const [n, setN] = useState(4);
  useTicker(ref, 1700, () => setN((x) => x + 1));
  const rows = [0, 1, 2, 3].map((i) => n - i);
  return (
    <div className="hookfeed" ref={ref} aria-hidden="true">
      {rows.map((k, i) => (
        <div className={`hf-row${i === 0 && k > 4 ? " fresh" : ""}`} key={k} style={{ "--i": i }}>
          <span className="hf-morse">{MORSE[k % MORSE.length]}</span>
          <span className="hf-to"><ArrowRight size={12} />hostc0</span>
          <span className="hf-amt">−180.00</span>
          <span className="hf-ok"><Check size={12} strokeWidth={2.4} /></span>
        </div>
      ))}
    </div>
  );
}

// 05 Hold path: the held payment's log types itself line by line, waits out the window, releases.
const HOLD_LINES = [
  ["req", "request_payment · 90 tUSDC → supplier.testnet"],
  ["hold", "verdict: hold · above usual range"],
  ["wait", "escrow · 1 h window"],
  ["done", "released · receipt written"],
];
export function HoldLog() {
  const ref = useRef(null);
  const reduce = typeof window !== "undefined" && prefersReducedMotion();
  // Steps: 1..4 show that many lines; 5–6 hold the full log on screen before it starts over.
  const [step, setStep] = useState(HOLD_LINES.length);
  useEffect(() => { if (!reduce) setStep(1); }, [reduce]);
  useTicker(ref, 900, () => setStep((s) => (s >= 6 ? 1 : s + 1)));
  const shown = Math.min(step, HOLD_LINES.length);
  return (
    <div className="holdlog" ref={ref} aria-hidden="true">
      <div className="hl-top"><Hourglass size={12} />supplier.testnet · hold</div>
      {HOLD_LINES.slice(0, shown).map(([kind, text], i) => (
        <div className={`hl-line ${kind}`} key={kind}>
          {kind === "wait" && shown === 3 ? <LoaderCircle size={12} className="hl-spin" /> : <span className="hl-mark">{i === 0 ? ">" : "↳"}</span>}
          {text}
        </div>
      ))}
      {shown < HOLD_LINES.length && <span className="hl-caret" />}
    </div>
  );
}

// Demo card 06: the committed evaluation numbers, no defense against Jev fusion + conformal threshold.
// Same source and rows as the Results section headline, so the two never disagree.
const NUMBERS = (() => {
  const top = headline(results);
  if (!top) return [];
  const row = (label, key) => [label, top.base[key], top.best[key]];
  return [row("Missed attacks", "missed_attacks_pct"), row("False blocks", "false_blocks_pct"), row("False holds", "false_holds_pct")];
})();

export function DemoNumbers() {
  if (!NUMBERS.length) return null;
  return (
    <div className="dnums">
      <div className="dn-row dn-head" aria-hidden="true"><span /><span>No defense</span><span>{PROJECT_NAME}</span></div>
      {NUMBERS.map(([label, base, best]) => (
        <div className="dn-row" key={label}>
          <span>{label}</span>
          <span className="dn-base">{formatResultNumber(base)}%</span>
          <b>{formatResultNumber(best)}%</b>
        </div>
      ))}
    </div>
  );
}
