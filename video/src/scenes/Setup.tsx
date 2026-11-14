import type React from "react";
import { Interactive } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";

const Card: React.FC<{
  readonly role: string;
  readonly title: string;
  readonly body: React.ReactNode;
}> = ({ role, title, body }) => (
  <div
    style={{
      flex: 1,
      background: C.card,
      border: `2px solid ${C.line}`,
      borderRadius: 28,
      padding: "44px 44px 52px",
      height: 440,
    }}
  >
    <div style={{ fontFamily: mono, fontSize: 28, color: C.accent, letterSpacing: 3 }}>{role}</div>
    <div style={{ fontSize: 48, fontWeight: 700, marginTop: 20, lineHeight: 1.1 }}>{title}</div>
    <div style={{ fontSize: 36, color: C.muted, marginTop: 24, lineHeight: 1.35 }}>{body}</div>
  </div>
);

const code: React.CSSProperties = { fontFamily: mono, color: C.text };

const SetupInner = () => (
  <>
    <div style={{ padding: "0 160px", fontFamily: sans, color: C.text, width: "100%" }}>
      <Reveal delay={0}>
        <div style={{ fontFamily: mono, fontSize: 32, color: C.dim, letterSpacing: 4 }}>
          HOW ECLIPSE IS DEPLOYED
        </div>
        <h1 style={{ fontSize: 88, margin: "16px 0 64px", fontWeight: 700 }}>
          The agent never holds the money.
        </h1>
      </Reveal>
      <div style={{ display: "flex", gap: 40 }}>
        <Reveal delay={25} style={{ flex: 1 }}>
          <Card
            role="OWNER"
            title="Funds a Guardian contract on NEAR"
            body={<>The contract holds the tUSDC (NEP-141), not the agent.</>}
          />
        </Reveal>
        <Reveal delay={55} style={{ flex: 1 }}>
          <Card
            role="AGENT"
            title="Gets a function-call key"
            body={
              <>
                It can call only <span style={code}>request_payment</span>. It cannot move funds itself.
              </>
            }
          />
        </Reveal>
        <Reveal delay={85} style={{ flex: 1 }}>
          <Card
            role="CONTRACT"
            title="Hard caps in code"
            body={
              <>
                200 tUSDC per payment
                <br />
                500 tUSDC per day
                <br />
                20 tUSDC for a new payee
              </>
            }
          />
        </Reveal>
      </div>
      <Reveal delay={120}>
        <div style={{ fontSize: 44, color: C.accent, marginTop: 56, fontWeight: 600 }}>
          No AI judges an amount.
        </div>
      </Reveal>
    </div>
  </>
);

export const Setup = Interactive.create({
  Component: SetupInner,
  layout: "absolute-fill",
  schema: { ...Interactive.backgroundSchema },
});
