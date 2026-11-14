import { Interactive } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

const CloseInner = () => (
  <>
    <div style={{ fontFamily: sans, color: C.text, textAlign: "center" }}>
      <Reveal delay={0}>
        <div style={{ fontSize: 150, fontWeight: 700, color: C.accent, letterSpacing: -2 }}>Eclipse</div>
      </Reveal>
      <Reveal delay={15}>
        <div style={{ fontSize: 50, marginTop: 12 }}>Steps in front of the bad payment.</div>
        <div style={{ fontSize: 50, color: C.muted, marginTop: 8 }}>Stays in the background otherwise.</div>
      </Reveal>
      <Reveal delay={40}>
        <div style={{ fontFamily: mono, fontSize: 28, color: C.dim, marginTop: 64 }}>
          Running on NEAR testnet · guardian-v2.jimuelle-firewall.testnet
        </div>
      </Reveal>
    </div>
  </>
);

export const Close = Interactive.create({
  Component: CloseInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
