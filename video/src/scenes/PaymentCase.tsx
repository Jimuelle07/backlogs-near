import type React from "react";
import { Easing, Interactive, interpolate, useCurrentFrame } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

type InboxItem = { readonly source: string; readonly text: string };

type Props = {
  readonly kicker: string;
  readonly color: string;
  readonly request: string;
  readonly inbox: readonly InboxItem[];
  readonly proposed: string;
  readonly signals: readonly string[];
  readonly verdict: string;
  readonly outcome: string;
  readonly note: string;
};

const Stamp: React.FC<{ readonly at: number; readonly color: string; readonly children: React.ReactNode }> = ({
  at,
  color,
  children,
}) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        display: "inline-block",
        marginTop: 36,
        padding: "14px 40px",
        border: `5px solid ${color}`,
        borderRadius: 18,
        color,
        fontFamily: mono,
        fontWeight: 600,
        fontSize: 84,
        letterSpacing: 8,
        opacity: interpolate(frame, [at, at + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        scale: interpolate(frame, [at, at + 14], [1.5, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
      }}
    >
      {children}
    </div>
  );
};

const label: React.CSSProperties = { fontFamily: mono, fontSize: 26, color: C.dim, letterSpacing: 3 };

const PaymentCaseInner = ({ kicker, color, request, inbox, proposed, signals, verdict, outcome, note }: Props) => {
  const signalsStart = 95;
  const stampAt = signalsStart + signals.length * 16 + 10;
  return (
    <>
      <div style={{ position: "absolute", inset: 0, fontFamily: sans, color: C.text, padding: "0 160px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Reveal delay={0}>
          <div style={{ fontFamily: mono, fontSize: 34, color, letterSpacing: 6, fontWeight: 600 }}>{kicker}</div>
        </Reveal>
        <div style={{ display: "flex", gap: 100, marginTop: 40 }}>
          <div style={{ flex: 1 }}>
            <Reveal delay={10}>
              <div style={label}>THE AGENT IS ASKED</div>
              <div style={{ fontSize: 46, fontWeight: 600, marginTop: 12 }}>“{request}”</div>
            </Reveal>
            {inbox.map((item, i) => (
              <Reveal key={item.source} delay={30 + i * 16}>
                <div
                  style={{
                    marginTop: 24,
                    padding: "18px 24px",
                    background: C.card,
                    border: `2px solid ${C.line}`,
                    borderRadius: 16,
                  }}
                >
                  <div style={{ ...label, fontSize: 22 }}>{item.source}</div>
                  <div style={{ fontFamily: mono, fontSize: 28, color: C.muted, marginTop: 8 }}>{item.text}</div>
                </div>
              </Reveal>
            ))}
            <Reveal delay={72}>
              <div style={{ ...label, marginTop: 40 }}>IT PROPOSES</div>
              <div style={{ fontFamily: mono, fontSize: 44, fontWeight: 600, marginTop: 10 }}>{proposed}</div>
            </Reveal>
          </div>
          <div style={{ flex: 1 }}>
            <Reveal delay={signalsStart - 10}>
              <div style={label}>THE CHECKER SEES</div>
            </Reveal>
            {signals.map((s, i) => (
              <Reveal key={s} delay={signalsStart + i * 16}>
                <div style={{ fontFamily: mono, fontSize: 32, marginTop: 18, color: C.text }}>
                  <span style={{ color }}>▸ </span>
                  {s}
                </div>
              </Reveal>
            ))}
            <Stamp at={stampAt} color={color}>
              {verdict}
            </Stamp>
            <Reveal delay={stampAt + 20}>
              <div style={{ fontSize: 44, fontWeight: 600, marginTop: 36 }}>{outcome}</div>
            </Reveal>
            <Reveal delay={stampAt + 40}>
              <div style={{ fontSize: 34, color: C.muted, marginTop: 16, lineHeight: 1.35 }}>{note}</div>
            </Reveal>
          </div>
        </div>
      </div>
    </>
  );
};

export const PaymentCase = Interactive.create({
  Component: PaymentCaseInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
