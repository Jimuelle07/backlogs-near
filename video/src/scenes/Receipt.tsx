import type React from "react";
import { Interactive } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

const Row: React.FC<{ readonly k: string; readonly v: string }> = ({ k, v }) => (
  <div style={{ display: "flex", justifyContent: "space-between", fontFamily: mono, fontSize: 30, marginTop: 18 }}>
    <span style={{ color: C.text }}>{k}</span>
    <span style={{ color: C.muted }}>{v}</span>
  </div>
);

const panel: React.CSSProperties = {
  background: C.card,
  border: `2px solid ${C.line}`,
  borderRadius: 28,
  padding: "40px 48px",
  height: 470,
  boxSizing: "border-box",
};

const heading: React.CSSProperties = { fontSize: 46, fontWeight: 700 };
const tag: React.CSSProperties = { fontFamily: mono, fontSize: 26, letterSpacing: 3, marginBottom: 12 };

const ReceiptInner = () => (
  <>
    <div style={{ padding: "0 160px", fontFamily: sans, color: C.text, width: "100%" }}>
      <Reveal delay={0}>
        <h1 style={{ fontSize: 84, margin: "0 0 60px", fontWeight: 700 }}>Every decision leaves a receipt.</h1>
      </Reveal>
      <div style={{ display: "flex", gap: 48 }}>
        <Reveal delay={20} style={{ flex: 1 }}>
          <div style={panel}>
            <div style={{ ...tag, color: C.accent }}>ON-CHAIN · PUBLIC</div>
            <div style={heading}>NEAR receipt</div>
            <Row k="outcome" v="paid · held · refused" />
            <Row k="reason codes" v="e.g. lookalike_receiver" />
            <Row k="input_sha256" v="hash of the check input" />
            <Row k="record_sha256" v="hash of the full record" />
            <Row k="checker version" v="which code decided" />
          </div>
        </Reveal>
        <Reveal delay={50} style={{ flex: 1 }}>
          <div style={panel}>
            <div style={{ ...tag, color: C.dim }}>OFF-CHAIN · OWNER ONLY</div>
            <div style={heading}>DecisionRecord</div>
            <div style={{ fontSize: 34, color: C.muted, marginTop: 26, lineHeight: 1.4 }}>
              The full record, Jev probabilities included, stays in the owner&apos;s log. Its hash is on-chain, so
              it can be checked later.
            </div>
          </div>
        </Reveal>
      </div>
      <Reveal delay={90}>
        <div style={{ fontSize: 40, color: C.accent, marginTop: 52, fontWeight: 600 }}>
          Probabilities are never sent to the agent or written on-chain.
        </div>
      </Reveal>
    </div>
  </>
);

export const Receipt = Interactive.create({
  Component: ReceiptInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
