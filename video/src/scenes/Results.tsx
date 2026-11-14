import type React from "react";
import { Interactive, interpolate, useCurrentFrame } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

// Counts down from `from` to `to` attacks allowed: baseline checker to current checker.
const Count: React.FC<{ readonly from: number; readonly to: number; readonly at: number }> = ({ from, to, at }) => {
  const frame = useCurrentFrame();
  return <>{Math.round(interpolate(frame, [at, at + 30], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))}</>;
};

const Stat: React.FC<{
  readonly baseline: number;
  readonly current: number;
  readonly total: number;
  readonly set: string;
  readonly at: number;
}> = ({ baseline, current, total, set, at }) => (
  <div style={{ flex: 1, borderTop: `3px solid ${C.accent}`, paddingTop: 28 }}>
    <div style={{ fontSize: 140, fontWeight: 700, lineHeight: 1 }}>
      <Count from={baseline} to={current} at={at} />
      <span style={{ fontSize: 56, color: C.muted, fontWeight: 400 }}> of {total}</span>
    </div>
    <div style={{ fontSize: 38, marginTop: 18 }}>{set}</div>
    <div style={{ fontFamily: mono, fontSize: 26, color: C.dim, marginTop: 10 }}>
      baseline checker: {baseline} of {total}
    </div>
  </div>
);

const ResultsInner = () => (
  <>
    <div style={{ padding: "0 160px", fontFamily: sans, color: C.text, width: "100%" }}>
      <Reveal delay={0}>
        <div style={{ fontFamily: mono, fontSize: 30, color: C.dim, letterSpacing: 4 }}>
          ATTACKS ALLOWED · CURRENT CHECKER, REAL JEV
        </div>
      </Reveal>
      <div style={{ display: "flex", gap: 72, marginTop: 48 }}>
        <Reveal delay={10} style={{ flex: 1 }}>
          <Stat baseline={29} current={0} total={150} set="Main set (in-sample)" at={25} />
        </Reveal>
        <Reveal delay={25} style={{ flex: 1 }}>
          <Stat baseline={17} current={0} total={100} set="External set" at={40} />
        </Reveal>
        <Reveal delay={40} style={{ flex: 1 }}>
          <Stat baseline={7} current={2} total={17} set="Red team" at={55} />
        </Reveal>
      </div>
      <Reveal delay={95}>
        <div style={{ fontSize: 48, color: C.accent, marginTop: 72, fontWeight: 600 }}>
          0 benign payments blocked on any set.
        </div>
      </Reveal>
      <Reveal delay={115}>
        <div style={{ fontSize: 30, color: C.dim, marginTop: 28, lineHeight: 1.4 }}>
          Main is in-sample; external and red team were in view when the rules were written.
          <br />
          These are not rates on unseen attacks. The contract caps are the guaranteed bound.
        </div>
      </Reveal>
    </div>
  </>
);

export const Results = Interactive.create({
  Component: ResultsInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
