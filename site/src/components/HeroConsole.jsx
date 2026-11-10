import { Ban, Check, Hourglass, ShieldCheck } from "lucide-react";
import { DAILY_CAP } from "../config";

// Static sample rows: a preview of the receipts view, not live data (the live panel is in #receipts).
const ROWS = [
  ["block", "hostc0.testnet", 180, "injection + lookalike payee"],
  ["allow", "hostco.testnet", 18, "known payee · usual amount"],
  ["hold", "supplier.testnet", 90, "above usual range · 1 h escrow"],
  ["allow", "dns-renew.testnet", 12.5, "allowlisted"],
];
const ICON = { allow: Check, hold: Hourglass, block: Ban };

export function HeroConsole() {
  const spent = ROWS.filter(([v]) => v === "allow").reduce((s, [, , a]) => s + a, 0);
  return (
    <div className="console" role="figure" aria-label="Sample receipts view for a Guardian contract">
      <div className="console-top">
        <span><i className="dot" />guardian · your-agent.testnet</span>
        <span className="ct-tag">SAMPLE DATA</span>
      </div>
      <div className="tally">
        <div><span>Allowed</span><b>2</b></div>
        <div><span>Held</span><b>1</b></div>
        <div><span>Blocked</span><b className="hot">1</b></div>
        <div><span>Stopped</span><b>180</b></div>
      </div>
      <div className="cap">
        <div className="cap-row">
          <span>Spent today</span>
          <span><b>{spent.toFixed(2)}</b> / {DAILY_CAP} tUSDC cap</span>
        </div>
        <div className="cap-bar" role="meter" aria-valuemin={0} aria-valuemax={DAILY_CAP} aria-valuenow={spent} aria-label="Spent against daily cap">
          <i style={{ width: `${(spent / DAILY_CAP) * 100}%` }} />
        </div>
      </div>
      <ol className="vlist">
        {ROWS.map(([v, to, amt, why]) => {
          const Icon = ICON[v];
          return (
            <li className="vrow" key={to}>
              <span className={`vchip ${v}`}><Icon size={12} aria-hidden="true" />{v.toUpperCase()}</span>
              <span className="vmain"><span className="vto">{to}</span><span className="vwhy">{why}</span></span>
              <span className="amt">{amt.toFixed(2)}</span>
            </li>
          );
        })}
      </ol>
      <div className="console-foot">
        <span><ShieldCheck size={13} aria-hidden="true" /> verdict + reason codes</span>
        <span>receipts on-chain</span>
      </div>
    </div>
  );
}
