import { Interactive } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

const HookInner = () => (
  <>
    <div style={{ padding: "0 180px", fontFamily: sans, color: C.text }}>
      <Reveal delay={0}>
        <div style={{ fontFamily: mono, fontSize: 36, color: C.alarm, letterSpacing: 4 }}>
          MAY 2026
        </div>
      </Reveal>
      <Reveal delay={10}>
        <h1 style={{ fontSize: 104, lineHeight: 1.05, margin: "28px 0 0", fontWeight: 700 }}>
          A Morse-code reply drained
          <br />
          an AI agent&apos;s wallet.
        </h1>
      </Reveal>
      <Reveal delay={40}>
        <div style={{ fontSize: 48, color: C.muted, marginTop: 40 }}>
          About $150,000 in DRB left Grok&apos;s linked wallet.
        </div>
      </Reveal>
      <Reveal delay={75}>
        <div style={{ fontSize: 56, color: C.accent, marginTop: 64, fontWeight: 600 }}>
          The agent held the keys.
        </div>
      </Reveal>
      <Reveal delay={75}>
        <div style={{ fontFamily: mono, fontSize: 26, color: C.dim, marginTop: 72 }}>
          Source: Giskard, &quot;How Grok got prompt-injected&quot;
        </div>
      </Reveal>
    </div>
  </>
);

export const Hook = Interactive.create({
  Component: HookInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
