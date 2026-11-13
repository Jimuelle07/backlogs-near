import { useEffect, useRef, useState } from "react";
import { Ban, Check, Hourglass, ShieldCheck } from "lucide-react";
import { DAILY_CAP } from "../config";
import { prefersReducedMotion } from "../motion.js";

// Static sample rows: a preview of the receipts view, not live data (the live panel is in #receipts).
const ROWS = [
  ["block", "hostc0.testnet", 180, "injection + lookalike payee"],
  ["allow", "hostco.testnet", 18, "known payee · usual amount"],
  ["hold", "supplier.testnet", 90, "above usual range · 1 h escrow"],
  ["allow", "dns-renew.testnet", 12.5, "allowlisted"],
];
const ICON = { allow: Check, hold: Hourglass, block: Ban };
const STEP_MS = 2000;
// Rows the demo cursor visits, one per step, so it travels up and down the list.
const VISIT = [1, 3, 0, 2];

// Same four sample rows and totals as before; the rows rotate so the newest arrives at the top.
export function Console() {
  const [turn, setTurn] = useState(0);
  const [cursor, setCursor] = useState(null); // { x, y, row, click }
  const box = useRef(null);
  const spent = ROWS.filter(([v]) => v === "allow").reduce((s, [, , a]) => s + a, 0);

  useEffect(() => {
    if (prefersReducedMotion()) return undefined;
    let visible = true;
    const el = document.querySelector(".hero .console");
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    if (el) io.observe(el);
    const id = setInterval(() => { if (visible && !document.hidden) setTurn((t) => t + 1); }, STEP_MS);
    return () => { clearInterval(id); io.disconnect(); };
  }, []);

  // Demo cursor: glide to this step's row (offset* ignores the console's tilt), then click it.
  useEffect(() => {
    if (prefersReducedMotion() || !box.current) return undefined;
    const row = VISIT[turn % VISIT.length];
    const chip = box.current.querySelectorAll(".vrow")[row]?.querySelector(".vchip");
    if (!chip) return undefined;
    setCursor({ x: chip.offsetLeft + chip.offsetWidth * 0.62, y: chip.offsetTop + chip.offsetHeight * 0.7, row, click: false });
    const t = setTimeout(() => setCursor((c) => c && { ...c, click: true }), 750);
    return () => clearTimeout(t);
  }, [turn]);

  // Cursor-driven movement: anywhere over the hero, the card tilts toward the pointer in 3D and
  // drifts after it, with the shadow moving opposite. A spring-like lerp eases every value, and the
  // loop stops once the card settles so the browser re-renders the text sharp at rest.
  useEffect(() => {
    const card = box.current;
    const hero = card?.closest(".hero");
    if (!card || !hero || prefersReducedMotion() || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return undefined;
    const target = { rx: 0, ry: 0, x: 0, y: 0 };
    const cur = { rx: 0, ry: 0, x: 0, y: 0 };
    let raf = 0;
    const tick = () => {
      let moving = false;
      for (const k in cur) {
        cur[k] += (target[k] - cur[k]) * 0.1;
        if (Math.abs(target[k] - cur[k]) > 0.02) moving = true;
      }
      const atRest = !moving && target.rx === 0 && target.ry === 0 && target.x === 0 && target.y === 0;
      card.style.transform = atRest
        ? ""
        : `perspective(900px) translate(${cur.x.toFixed(2)}px, ${cur.y.toFixed(2)}px) rotateX(${cur.rx.toFixed(2)}deg) rotateY(${cur.ry.toFixed(2)}deg)`;
      card.style.boxShadow = atRest ? "" : `${(-cur.ry * 2.2).toFixed(1)}px ${(50 + cur.rx * 2.2).toFixed(1)}px 100px -40px #1f1226bf, inset 0 1px #ffffff0f`;
      raf = moving ? requestAnimationFrame(tick) : 0;
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(tick); };
    const onMove = (e) => {
      const r = hero.getBoundingClientRect();
      const dx = (e.clientX - r.left) / r.width - 0.5;
      const dy = (e.clientY - r.top) / r.height - 0.5;
      target.ry = dx * 14; target.rx = dy * -10; target.x = dx * 24; target.y = dy * 16;
      kick();
    };
    const onLeave = () => { target.rx = target.ry = target.x = target.y = 0; kick(); };
    hero.addEventListener("pointermove", onMove);
    hero.addEventListener("pointerleave", onLeave);
    return () => {
      cancelAnimationFrame(raf);
      hero.removeEventListener("pointermove", onMove);
      hero.removeEventListener("pointerleave", onLeave);
      card.style.transform = ""; card.style.boxShadow = "";
    };
  }, []);

  const order = ROWS.map((_, i) => ROWS[(i - (turn % ROWS.length) + ROWS.length) % ROWS.length]);
  return (
    <div className="console" ref={box} role="figure" aria-label="Sample receipts view for a Guardian contract">
      <div className="console-top">
        <span className="live"><i className="dot" />guardian · your-agent.testnet</span>
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
        {order.map(([v, to, amt, why], i) => {
          const Icon = ICON[v];
          return (
            <li className={`vrow${i === 0 && turn > 0 ? " fresh" : ""}${cursor?.click && cursor.row === i ? " picked" : ""}`} key={to}>
              <span className={`vchip ${v}`}><Icon size={12} aria-hidden="true" />{v.toUpperCase()}</span>
              <span className="vmain"><span className="vto">{to}</span><span className="vwhy">{why}</span></span>
              <span className="amt">{amt.toFixed(2)}</span>
            </li>
          );
        })}
      </ol>
      {cursor && (
        <span
          className={`ccursor${cursor.click ? " click" : ""}`}
          style={{ transform: `translate(${cursor.x}px, ${cursor.y}px)` }}
          aria-hidden="true"
        >
          <svg width="18" height="20" viewBox="0 0 18 20">
            <path d="M1 1 L1 16 L5.2 12.3 L8 18.6 L10.9 17.3 L8.2 11.1 L13.8 11.1 Z" fill="#FFF3FB" stroke="#1F1226" strokeWidth="1.3" strokeLinejoin="round" />
          </svg>
        </span>
      )}
      <div className="console-foot">
        <span><ShieldCheck size={13} aria-hidden="true" /> verdict + reason codes</span>
        <span>receipts on-chain</span>
      </div>
    </div>
  );
}
