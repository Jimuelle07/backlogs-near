import type React from "react";
import { interpolate, random, useCurrentFrame } from "remotion";
import { C, mono, sans } from "../theme";
import { ALLOW_REASONS, BLOCK_REASONS, DECODED, REQUEST, TOOL_CALL } from "./data";
import { Morse } from "./Morse";
import { clamp, E, fade, SEQ } from "./timeline";

// Horizontally centered on x 960, top edge at y.
const centered = (y: number): React.CSSProperties => ({
  position: "absolute",
  left: 0,
  width: 1920,
  top: y,
  textAlign: "center",
});

const kicker: React.CSSProperties = {
  fontFamily: mono,
  fontWeight: 600,
  fontSize: 28,
  letterSpacing: 4,
  color: C.dim,
};

const card: React.CSSProperties = {
  position: "absolute",
  top: 230,
  height: 204,
  boxSizing: "border-box",
  background: C.card,
  borderRadius: 20,
  padding: "28px 32px",
};

const decodeAt = (i: number) => 86 + 6 * i;

export const AskPanel: React.FC = () => {
  const frame = useCurrentFrame() + SEQ.ask[0];
  const words = `“${REQUEST}”`.split(" ");
  const cardsOut = fade(frame, { out: [128, 134] });
  return (
    <>
      <div style={{ ...centered(100), ...kicker, ...fade(frame, { inn: [22, 30], out: [130, 136] }) }}>
        THE AGENT IS ASKED
      </div>
      <div
        style={{
          ...centered(140),
          fontFamily: sans,
          fontWeight: 600,
          fontSize: 56,
          color: C.text,
          ...fade(frame, { out: [130, 136] }),
        }}
      >
        {words.map((w, i) => (
          <span key={i}>
            <span
              style={{
                display: "inline-block",
                ...fade(frame, { inn: [24 + 2 * i, 32 + 2 * i], from: [0, 16] }),
              }}
            >
              {w}
            </span>
            {i < words.length - 1 ? " " : null}
          </span>
        ))}
      </div>

      <div style={{ position: "absolute", inset: 0, ...cardsOut }}>
        <div
          style={{
            ...card,
            left: 120,
            width: 520,
            border: `2px solid ${C.line}`,
            ...fade(frame, { inn: [34, 46], from: [-40, 0] }),
            opacity:
              fade(frame, { inn: [34, 46] }).opacity * interpolate(frame, [112, 118], [1, 0.4], clamp),
          }}
        >
          <div style={{ ...kicker, letterSpacing: 0, fontWeight: 400 }}>EMAIL · INVOICE</div>
          <div style={{ fontFamily: mono, fontSize: 36, color: C.text, marginTop: 12, lineHeight: 1.3 }}>
            INV-2026-11
            <br />
            18.00 USDC → hostco
          </div>
        </div>

        <div
          style={{
            ...card,
            left: 680,
            width: 1120,
            border: `2px solid ${C.alarm}`,
            ...fade(frame, { inn: [60, 72], from: [140, 0] }),
          }}
        >
          <div style={{ position: "relative", width: "100%", height: "100%" }}>
            <div style={{ ...kicker, letterSpacing: 0, color: C.alarm }}>X REPLY · UNTRUSTED</div>
            <Morse frame={frame} decodeAt={decodeAt} />
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 98,
                display: "flex",
                gap: "0.6em",
                fontFamily: mono,
                fontWeight: 600,
                fontSize: 40,
                lineHeight: "48px",
              }}
            >
              {DECODED.map((word, i) => {
                const d = decodeAt(i);
                if (frame < d) return null;
                const text =
                  frame < d + 2
                    ? Array.from(word, (_, c) => (random(`${i}-${frame}-${c}`) < 0.5 ? "." : "-")).join("")
                    : word;
                return (
                  <span key={i} style={{ color: word === "180" || word === "hostc0" ? C.alarm : C.text }}>
                    {text}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export const PausePanel: React.FC = () => {
  const frame = useCurrentFrame() + SEQ.pause[0];
  return (
    <>
      <div
        style={{
          ...centered(110),
          fontFamily: sans,
          fontWeight: 700,
          fontSize: 64,
          color: C.text,
          ...fade(frame, { inn: [138, 150], from: [0, 24], out: [212, 219] }),
        }}
      >
        Every payment pauses for a check.
      </div>
      <div
        style={{
          ...centered(206),
          fontFamily: sans,
          fontWeight: 400,
          fontSize: 36,
          color: C.muted,
          ...fade(frame, { inn: [144, 156], out: [212, 219] }),
        }}
      >
        Funds stay in the contract. The agent holds only a function-call key.
      </div>
    </>
  );
};

const VERDICT = {
  block: {
    s: SEQ.block[0],
    headline: "Steps in front of the bad payment.",
    stamp: "BLOCK",
    color: C.alarm,
    outcome: "refused · 0 tUSDC moved",
    caption: "Policy and counterparty agree, and Jev scored above the hold threshold.",
    headIn: [12, 24],
    stampIn: [2, 10],
    outcomeIn: [8, 18],
    captionIn: [20, 30],
    out: [268, 276],
  },
  allow: {
    s: SEQ.allow[0],
    headline: "Stays in the background otherwise.",
    stamp: "ALLOW",
    color: C.allow,
    outcome: "paid · 18 tUSDC → hostco",
    caption: "One flag fired (jev_injection_driven). A Jev flag alone does not hold.",
    headIn: [2, 14],
    stampIn: [6, 14],
    outcomeIn: [11, 21],
    captionIn: [16, 26],
    out: [334, 342],
  },
} as const;

export const VerdictPanel: React.FC<{ readonly kind: "block" | "allow" }> = ({ kind }) => {
  const v = VERDICT[kind];
  const frame = useCurrentFrame() + v.s;
  const at = (r: readonly [number, number]) => [v.s + r[0], v.s + r[1]] as const;
  const stampIn = at(v.stampIn);
  const stampOut = fade(frame, { out: v.out });
  return (
    <>
      <div
        style={{
          ...centered(100),
          fontFamily: sans,
          fontWeight: 700,
          fontSize: 64,
          color: C.text,
          ...fade(frame, { inn: at(v.headIn), from: [0, 24], out: v.out }),
        }}
      >
        {v.headline}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          width: 1920,
          top: 240,
          height: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 40,
        }}
      >
        <div
          style={{
            fontFamily: mono,
            fontWeight: 600,
            fontSize: 76,
            lineHeight: 1.1,
            letterSpacing: 8,
            padding: "10px 28px 10px 36px",
            border: `6px solid ${v.color}`,
            borderRadius: 18,
            color: v.color,
            scale: interpolate(frame, stampIn, [1.7, 1], { ...clamp, easing: E.pop }),
            opacity: interpolate(frame, [stampIn[0], stampIn[0] + 3], [0, 1], clamp) * stampOut.opacity,
            translate: stampOut.translate,
          }}
        >
          {v.stamp}
        </div>
        <div
          style={{
            fontFamily: sans,
            fontWeight: 600,
            fontSize: 54,
            color: C.text,
            whiteSpace: "nowrap",
            ...fade(frame, { inn: at(v.outcomeIn), from: [24, 0], out: v.out }),
          }}
        >
          {v.outcome}
        </div>
      </div>
      <div
        style={{
          ...centered(326),
          fontFamily: sans,
          fontWeight: 400,
          fontSize: 34,
          color: C.muted,
          ...fade(frame, { inn: at(v.captionIn), out: v.out }),
        }}
      >
        {v.caption}
      </div>
    </>
  );
};

export const ProposalPanel: React.FC = () => {
  const frame = useCurrentFrame() + SEQ.proposal[0];
  const style = fade(frame, { inn: [116, 126], out: [146, 152] });
  return (
    <>
      <div style={{ ...centered(770), ...kicker, ...style }}>IT PROPOSES</div>
      <div
        style={{
          ...centered(820),
          fontFamily: mono,
          fontWeight: 600,
          fontSize: 44,
          color: C.text,
          whiteSpace: "pre",
          ...style,
        }}
      >
        {TOOL_CALL.split(/(hostc0|180)/).map((part, i) => (
          <span key={i} style={{ color: part === "hostc0" || part === "180" ? C.alarm : undefined }}>
            {part}
          </span>
        ))}
      </div>
    </>
  );
};

const CHIP_X = [156, 700, 1244];
const CHIP_Y = [796, 884];

const Chip: React.FC<{
  readonly code: string;
  readonly col: number;
  readonly row: number;
  readonly border: string;
  readonly dot: string;
  readonly text: string;
  readonly style: React.CSSProperties;
}> = ({ code, col, row, border, dot, text, style }) => (
  <div
    style={{
      position: "absolute",
      left: CHIP_X[col],
      top: CHIP_Y[row],
      width: 520,
      height: 68,
      boxSizing: "border-box",
      display: "flex",
      alignItems: "center",
      gap: 16,
      paddingLeft: 28,
      background: C.card,
      border: `2px solid ${border}`,
      borderRadius: 16,
      ...style,
    }}
  >
    <div style={{ width: 10, height: 10, borderRadius: 5, background: dot }} />
    <span style={{ fontFamily: mono, fontWeight: 600, fontSize: 34, color: text }}>{code}</span>
  </div>
);

export const ChecksPanel: React.FC<{ readonly kind: "block" | "allow" }> = ({ kind }) => {
  const block = kind === "block";
  const frame = useCurrentFrame() + (block ? SEQ.checksBlock[0] : SEQ.checksAllow[0]);
  const kickerStyle = block
    ? fade(frame, { inn: [150, 158], out: [268, 276] })
    : fade(frame, { inn: [290, 298], out: [334, 342] });
  return (
    <>
      <div style={{ position: "absolute", left: 156, top: 742, ...kicker, ...kickerStyle }}>THE CHECKER SEES</div>
      <div style={{ position: "absolute", right: 1920 - 1764, top: 742, ...kicker, ...kickerStyle }}>
        OUTLAYER TEE · TESTNET RECEIPT {block ? "#7" : "#6"}
      </div>
      {block
        ? BLOCK_REASONS.map((code, i) => {
            const t = 156 + 8 * i;
            const outP = interpolate(frame, [268 + i, 274 + i], [0, 1], { ...clamp, easing: E.in });
            return (
              <Chip
                key={code}
                code={code}
                col={i % 3}
                row={Math.floor(i / 3)}
                border={frame < t + 2 ? C.cream : C.alarm}
                dot={C.alarm}
                text={C.text}
                style={{
                  scale: interpolate(frame, [t, t + 7], [0.9, 1], { ...clamp, easing: E.pop }),
                  opacity: interpolate(frame, [t, t + 3], [0, 1], clamp) * (1 - outP),
                  translate: `0 ${20 * outP}px`,
                }}
              />
            );
          })
        : ALLOW_REASONS.map((code) => (
            <Chip
              key={code}
              code={code}
              col={0}
              row={0}
              border={C.dim}
              dot={C.dim}
              text={C.muted}
              style={fade(frame, { inn: [294, 301], out: [334, 342] })}
            />
          ))}
    </>
  );
};
