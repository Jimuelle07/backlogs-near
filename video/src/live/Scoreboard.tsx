import type React from "react";
import { AbsoluteFill } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";
import { badge, caption } from "./captions";
import type { RunData } from "./types";

const cell: React.CSSProperties = { padding: "9px 12px", borderBottom: `1px solid ${C.line}`, verticalAlign: "top" };
const head: React.CSSProperties = { ...cell, fontFamily: mono, fontSize: 15, letterSpacing: 2, color: C.dim, textAlign: "left" };

export const Scoreboard: React.FC<{ readonly data: RunData }> = ({ data }) => {
  const order = (side: "plain" | "eclipse") =>
    data.events.filter((e) => e.side === side).sort((a, b) => a.row - b.row || a.index - b.index);
  const plain = order("plain");
  const ecl = order("eclipse");
  const { plain: tp, eclipse: te } = data.totals;
  return (
    <AbsoluteFill style={{ backgroundColor: C.ground, fontFamily: sans, padding: "56px 80px", color: C.text }}>
      <Reveal delay={0}>
        <div style={{ fontFamily: mono, fontSize: 22, letterSpacing: 4, color: C.accent }}>SCOREBOARD · RUN {data.run.toUpperCase()}</div>
      </Reveal>
      <Reveal delay={10} style={{ marginTop: 20 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 19 }}>
          <thead>
            <tr>
              <th style={head}>SCENARIO</th>
              <th style={head}>TYPE</th>
              <th style={head}>WITHOUT ECLIPSE</th>
              <th style={head}>WITH ECLIPSE</th>
              <th style={{ ...head, textAlign: "right" }}>CHECK S</th>
            </tr>
          </thead>
          <tbody>
            {plain.map((p, i) => {
              const e = ecl[i];
              const pb = badge(p);
              const eb = badge(e);
              return (
                <tr key={`${p.row}-${p.index}`}>
                  <td style={cell}>
                    <div style={{ fontFamily: mono, fontSize: 17 }}>{p.scenario}</div>
                    <div style={{ fontSize: 15, color: C.muted, marginTop: 2 }}>{caption(p)}</div>
                  </td>
                  <td style={{ ...cell, fontSize: 16, color: p.label === "attack" ? C.alarm : C.allow }}>
                    {p.label} · {p.family.split("_").join(" ")}
                  </td>
                  <td style={{ ...cell, fontFamily: mono, fontSize: 17, fontWeight: 600, color: pb.color }}>{pb.text}</td>
                  <td style={cell}>
                    <div style={{ fontFamily: mono, fontSize: 17, fontWeight: 600, color: eb.color }}>{eb.text}</div>
                    <div style={{ fontFamily: mono, fontSize: 13, color: C.dim, marginTop: 3 }}>{e.reasons.slice(0, 3).join(" · ")}</div>
                  </td>
                  <td style={{ ...cell, fontFamily: mono, fontSize: 17, textAlign: "right", color: C.muted }}>
                    {e.check_s === null ? "—" : e.check_s.toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Reveal>
      <Reveal delay={40} style={{ marginTop: 26, display: "flex", gap: 40, fontSize: 22 }}>
        <div style={{ flex: 1, border: `1px solid ${C.line}`, borderRadius: 10, padding: "16px 22px" }}>
          <div style={{ fontWeight: 700, color: C.alarm }}>WITHOUT ECLIPSE</div>
          <div style={{ fontFamily: mono, marginTop: 10 }}>paid to attackers: {tp.paid_to_attacker} tUSDC</div>
          <div style={{ fontFamily: mono, marginTop: 6, color: C.muted }}>
            attacks that reached the attacker: {tp.reached_attacker} of {tp.attacks} · benign paid: {tp.benign_paid}
          </div>
        </div>
        <div style={{ flex: 1, border: `1px solid ${C.line}`, borderRadius: 10, padding: "16px 22px" }}>
          <div style={{ fontWeight: 700, color: C.accent }}>WITH ECLIPSE</div>
          <div style={{ fontFamily: mono, marginTop: 10 }}>
            paid to attackers: {te.paid_to_attacker} tUSDC · held for attackers: {te.held_for_attacker} tUSDC
          </div>
          <div style={{ fontFamily: mono, marginTop: 6, color: C.muted }}>
            attacks stopped: {te.stopped} of {te.attacks} · benign paid {te.benign_paid} / held {te.benign_held} / blocked {te.benign_blocked}
          </div>
        </div>
      </Reveal>
    </AbsoluteFill>
  );
};
