import type React from "react";
import { Easing, Interactive, interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// A straight arrow that draws itself between frames [start, start + 20].
const Arrow: React.FC<{
  readonly x1: number;
  readonly y1: number;
  readonly x2: number;
  readonly y2: number;
  readonly start: number;
}> = ({ x1, y1, x2, y2, start }) => {
  const frame = useCurrentFrame();
  const length = Math.hypot(x2 - x1, y2 - y1);
  const drawn = interpolate(frame, [start, start + 20], [0, 1], {
    ...clamp,
    easing: Easing.bezier(0.65, 0, 0.35, 1),
  });
  const dir = Math.sign(x2 - x1);
  return (
    <g stroke={C.accent} strokeWidth={4} fill="none" opacity={drawn > 0 ? 1 : 0}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} strokeDasharray={length} strokeDashoffset={length * (1 - drawn)} />
      <path
        d={`M ${x2 - dir * 18} ${y2 - 12} L ${x2} ${y2} L ${x2 - dir * 18} ${y2 + 12}`}
        opacity={drawn >= 1 ? 1 : 0}
      />
    </g>
  );
};

const Box: React.FC<{
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly delay: number;
  readonly children: React.ReactNode;
}> = ({ x, y, w, h, delay, children }) => (
  <Reveal delay={delay} style={{ position: "absolute", left: x, top: y, width: w, height: h }}>
    <div
      style={{
        height: "100%",
        boxSizing: "border-box",
        background: C.card,
        border: `2px solid ${C.line}`,
        borderRadius: 24,
        padding: "24px 30px",
      }}
    >
      {children}
    </div>
  </Reveal>
);

// One check inside the checker; its border lights up when it has run.
const Check: React.FC<{ readonly label: string; readonly tag?: string; readonly at: number }> = ({
  label,
  tag,
  at,
}) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 72,
        marginTop: 14,
        padding: "0 24px",
        borderRadius: 16,
        border: `2px solid ${interpolateColors(frame, [at, at + 10], [C.line, C.accent])}`,
        background: interpolateColors(frame, [at, at + 10], [C.ground, "#2a2132"]),
        fontSize: 32,
      }}
    >
      <span>{label}</span>
      <span style={{ fontFamily: mono, fontSize: 24, color: C.dim }}>
        {tag}
        <span style={{ color: C.accent, marginLeft: 16, opacity: interpolate(frame, [at + 6, at + 12], [0, 1], clamp) }}>
          ✓
        </span>
      </span>
    </div>
  );
};

const title: React.CSSProperties = { fontSize: 38, fontWeight: 700 };
const sub: React.CSSProperties = { fontFamily: mono, fontSize: 24, color: C.muted, marginTop: 10 };

const FlowInner = () => (
  <>
    <div style={{ position: "absolute", inset: 0, fontFamily: sans, color: C.text }}>
      <Reveal delay={0} style={{ position: "absolute", left: 160, top: 80 }}>
        <h1 style={{ fontSize: 76, margin: 0, fontWeight: 700 }}>Every payment pauses for a check.</h1>
      </Reveal>

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <Arrow x1={500} y1={335} x2={616} y2={335} start={30} />
        <Arrow x1={1000} y1={335} x2={1116} y2={335} start={70} />
        <Arrow x1={1120} y1={660} x2={1004} y2={660} start={170} />
        <Arrow x1={620} y1={660} x2={504} y2={660} start={215} />
      </svg>

      <Box x={160} y={260} w={340} h={150} delay={10}>
        <div style={title}>AI agent</div>
        <div style={sub}>request_payment(…)</div>
      </Box>
      <Box x={620} y={260} w={380} h={150} delay={45}>
        <div style={title}>Guardian</div>
        <div style={sub}>pauses (yield)</div>
      </Box>
      <Box x={1120} y={210} w={640} h={470} delay={85}>
        <div style={title}>Checker</div>
        <div style={{ ...sub, marginTop: 4 }}>OutLayer TEE on testnet</div>
        <Check label="Policy and provenance rules" at={105} />
        <Check label="Lookalike and counterparty" at={125} />
        <Check label="Injection classifier" tag="HTTPS" at={145} />
        <Check label="TypeSafe Jev decision" tag="HTTPS" at={165} />
      </Box>
      <Box x={620} y={555} w={380} h={210} delay={185}>
        <div style={title}>Verdict</div>
        <div style={{ ...sub, lineHeight: 1.5 }}>
          bound to receiver,
          <br />
          token, exact amount,
          <br />
          request_id
        </div>
      </Box>

      <div style={{ position: "absolute", left: 160, top: 555, width: 340 }}>
        <Reveal delay={230}>
          <Outcome color={C.allow} label="allow" detail="paid" />
        </Reveal>
        <Reveal delay={242}>
          <Outcome color={C.hold} label="hold" detail="escrow" />
        </Reveal>
        <Reveal delay={254}>
          <Outcome color={C.alarm} label="block" detail="refused" />
        </Reveal>
      </div>

      <Reveal delay={185} style={{ position: "absolute", left: 160, top: 900 }}>
        <div style={{ fontSize: 30, color: C.dim }}>
          The contract pays only on an exact match. The classifier and Jev answer from outside the TEE.
        </div>
      </Reveal>
    </div>
  </>
);

const Outcome: React.FC<{ readonly color: string; readonly label: string; readonly detail: string }> = ({
  color,
  label,
  detail,
}) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      height: 56,
      marginBottom: 14,
      padding: "0 22px",
      borderRadius: 14,
      border: `2px solid ${color}`,
      fontFamily: mono,
      fontSize: 28,
    }}
  >
    <span style={{ color, fontWeight: 600 }}>{label}</span>
    <span style={{ color: C.muted }}>{detail}</span>
  </div>
);

export const Flow = Interactive.create({
  Component: FlowInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
