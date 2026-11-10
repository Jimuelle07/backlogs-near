import { useState } from "react";
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

export function VerdictExplorer() {
  const [v, setV] = useState("block");
  const cur = VERDICTS[v];
  return (
    <div className="vx">
      <div className="vx-left">
        <div className="seg" role="group" aria-label="Choose a verdict">
          {Object.entries(VERDICTS).map(([k, { label, Icon }]) => (
            <button key={k} type="button" aria-pressed={v === k} onClick={() => setV(k)}>
              <Icon size={16} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
        <div aria-live="polite">
          <h3>{cur.title}</h3>
          <p>{cur.text}</p>
        </div>
        <div className="pipe">
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
          <p className="pipe-foot">Same checks on every payment. Only the verdict changes.</p>
        </div>
      </div>
      <dl className="vx-right">
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
    </div>
  );
}
