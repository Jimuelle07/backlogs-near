import type React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { C, sans } from "../theme";
import { Lockup } from "./Lockup";
import { AskPanel, ChecksPanel, PausePanel, ProposalPanel, VerdictPanel } from "./Panels";
import { Stage } from "./Stage";
import { SEQ } from "./timeline";

// README GIF (docs/build/demo-storyboard.md "README GIF"): receipt #7 blocked, receipt #6 allowed.
// Flat colors and a static backdrop only, so the 256-color GIF palette and frame diffs stay small.
export const ReadmeDemo: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: C.ground, fontFamily: sans, color: C.text }}>
    <AbsoluteFill
      style={{
        backgroundImage: `radial-gradient(circle, ${C.line} 1.5px, transparent 2px)`,
        backgroundSize: "48px 48px",
      }}
    />
    <Stage />
    <Sequence name="Ask" from={SEQ.ask[0]} durationInFrames={SEQ.ask[1]} layout="none">
      <AskPanel />
    </Sequence>
    <Sequence name="Pause" from={SEQ.pause[0]} durationInFrames={SEQ.pause[1]} layout="none">
      <PausePanel />
    </Sequence>
    <Sequence name="Verdict block" from={SEQ.block[0]} durationInFrames={SEQ.block[1]} layout="none">
      <VerdictPanel kind="block" />
    </Sequence>
    <Sequence name="Verdict allow" from={SEQ.allow[0]} durationInFrames={SEQ.allow[1]} layout="none">
      <VerdictPanel kind="allow" />
    </Sequence>
    <Sequence name="Proposal" from={SEQ.proposal[0]} durationInFrames={SEQ.proposal[1]} layout="none">
      <ProposalPanel />
    </Sequence>
    <Sequence name="Checks block" from={SEQ.checksBlock[0]} durationInFrames={SEQ.checksBlock[1]} layout="none">
      <ChecksPanel kind="block" />
    </Sequence>
    <Sequence name="Checks allow" from={SEQ.checksAllow[0]} durationInFrames={SEQ.checksAllow[1]} layout="none">
      <ChecksPanel kind="allow" />
    </Sequence>
    <Lockup />
  </AbsoluteFill>
);
