import type React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, mono, sans } from "../theme";
import { clamp, E, fade } from "./timeline";

const WORD = "Eclipse";

const centered = (y: number): React.CSSProperties => ({
  position: "absolute",
  left: 0,
  width: 1920,
  top: y,
  textAlign: "center",
});

// Name and tagline, visible 0–16 and 340–374. Every value is at rest for frames ≤ 8
// and ≥ 357, so frame 0 and frame 374 are identical and the GIF loops.
export const Lockup: React.FC = () => {
  const frame = useCurrentFrame();
  // Before frame 170 only the exit applies; after it only the entrance.
  const late = frame >= 170;
  return (
    <>
      <div
        style={{
          ...centered(372),
          fontFamily: sans,
          fontWeight: 700,
          fontSize: 160,
          letterSpacing: -2,
          lineHeight: 1,
          color: C.accent,
          ...(late ? {} : fade(frame, { out: [10, 16] })),
        }}
      >
        {Array.from(WORD, (ch, i) => (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity: late ? interpolate(frame, [340 + i, 345 + i], [0, 1], clamp) : 1,
              translate: late
                ? `0 ${interpolate(frame, [340 + i, 350 + i], [40, 0], { ...clamp, easing: E.out })}px`
                : "0 0px",
            }}
          >
            {ch}
          </span>
        ))}
      </div>
      <div
        style={{
          ...centered(580),
          fontFamily: sans,
          fontWeight: 600,
          fontSize: 52,
          color: C.text,
          ...(late ? fade(frame, { inn: [342, 352], from: [0, 20] }) : fade(frame, { out: [9, 15] })),
        }}
      >
        Steps in front of the bad payment.
      </div>
      <div
        style={{
          ...centered(648),
          fontFamily: sans,
          fontWeight: 600,
          fontSize: 52,
          color: C.muted,
          ...(late ? fade(frame, { inn: [344, 354], from: [0, 20] }) : fade(frame, { out: [9, 15] })),
        }}
      >
        Stays in the background otherwise.
      </div>
      <div
        style={{
          ...centered(790),
          fontFamily: mono,
          fontWeight: 400,
          fontSize: 30,
          color: C.dim,
          ...(late ? fade(frame, { inn: [348, 356] }) : fade(frame, { out: [8, 14] })),
        }}
      >
        A payment firewall for AI agents, on NEAR
      </div>
    </>
  );
};
