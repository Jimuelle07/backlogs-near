import type React from "react";
import { AbsoluteFill } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";
import type { RunData } from "./types";

const line: React.CSSProperties = { fontSize: 34, lineHeight: 1.35, color: C.text, marginTop: 26 };

export const Intro: React.FC<{ readonly data: RunData }> = ({ data }) => {
  const runs = data.events.length;
  const scenarios = runs / 2;
  return (
    <AbsoluteFill style={{ backgroundColor: C.ground, fontFamily: sans, padding: "90px 140px", justifyContent: "center" }}>
      <Reveal delay={0}>
        <div style={{ fontFamily: mono, fontSize: 24, letterSpacing: 4, color: C.accent }}>
          LIVE TEST · REAL KEYS · ONE TAKE PER SIDE
        </div>
      </Reveal>
      <Reveal delay={12}>
        <div style={{ fontSize: 52, fontWeight: 700, lineHeight: 1.2, color: C.text, marginTop: 30 }}>
          May 2026: a Morse-code reply drained an AI agent's wallet. The agent had the keys.
        </div>
        <div style={{ fontSize: 20, color: C.dim, marginTop: 10 }}>Source: Giskard</div>
      </Reveal>
      <Reveal delay={75} style={line}>
        {scenarios} scenarios, run twice = {runs} runs, {data.rows} terminals per side. First: the agent{" "}
        <b style={{ color: C.alarm }}>without Eclipse</b>. Then: the same agent <b style={{ color: C.accent }}>behind Eclipse</b>.
      </Reveal>
      <Reveal delay={135} style={line}>
        Agent: already fooled — it proposes the attacker's payment from each scenario file. The test is what happens next.
      </Reveal>
      <Reveal delay={195} style={{ ...line, color: C.muted, fontSize: 28 }}>
        Real: TypeSafe Jev · injection classifier (protectai DeBERTa, local) · native checker
      </Reveal>
      <Reveal delay={240} style={{ ...line, color: C.muted, fontSize: 28, marginTop: 12 }}>
        Chain: dry-run mirror of the Guardian contract caps — nothing signed, no tokens moved.
      </Reveal>
    </AbsoluteFill>
  );
};
