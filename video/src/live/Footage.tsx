import type React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { C, mono, sans } from "../theme";
import { sumAmounts } from "./captions";
import type { RunData, Side } from "./types";

// The summary line prints `--pause` (4 s) after the last verdict; keep it on screen a few seconds.
const TAIL_S = 7;
const MAX_TOTAL_S = 80;

export type TakeTiming = { readonly lead: number; readonly rate: number; readonly frames: number };

// Each take starts 1 s before its first scenario and ends shortly after its summary line. If both
// takes together run over 80 s, both play time-lapsed at the same rate.
export const takeTiming = (data: RunData, side: Side): TakeTiming => {
  const span = (s: Side) => {
    const t = data.takes[s];
    const lead = Math.max(0, t.first_start_s - 1);
    return { lead, length: Math.min(t.footage_seconds, t.last_verdict_s + TAIL_S) - lead };
  };
  const total = span("plain").length + span("eclipse").length;
  const rate = total > MAX_TOTAL_S ? total / MAX_TOTAL_S : 1;
  const { lead, length } = span(side);
  return { lead, rate, frames: Math.ceil((length / rate) * data.fps) };
};

const HEADER: Record<Side, { readonly title: string; readonly color: string; readonly note: string }> = {
  plain: { title: "WITHOUT ECLIPSE", color: C.alarm, note: "plain agent, full-access key: whatever it proposes is paid" },
  eclipse: { title: "WITH ECLIPSE", color: C.accent, note: "same proposals, checked by Eclipse before any payment" },
};

// One take full screen: a header with the running totals above the 4 tiled terminal windows.
export const Footage: React.FC<{ readonly data: RunData; readonly side: Side }> = ({ data, side }) => {
  const frame = useCurrentFrame();
  const take = data.takes[side];
  const { lead, rate } = takeTiming(data, side);
  const t = lead + (frame / data.fps) * rate;
  const scale = Math.min(1920 / take.width, (1080 - 60) / take.height);
  const w = take.width * scale;
  const h = take.height * scale;

  const done = data.events.filter((e) => e.side === side && e.t_verdict_s <= t);
  const lost = sumAmounts(done.filter((e) => e.to_attacker && e.result === (side === "plain" ? "paid" : "would_pay")).map((e) => e.amount));
  const held = sumAmounts(done.filter((e) => e.to_attacker && e.result === "held").map((e) => e.amount));
  const stopped = done.filter((e) => e.label === "attack" && (e.result === "refused" || e.result === "contract_refused")).length;
  const head = HEADER[side];

  return (
    <AbsoluteFill style={{ backgroundColor: C.ground, fontFamily: sans }}>
      <div style={{ height: 1080 - h, display: "flex", alignItems: "center", gap: 28, padding: "0 24px", borderBottom: `3px solid ${head.color}` }}>
        <div style={{ fontSize: 30, fontWeight: 700, color: head.color, letterSpacing: 1 }}>{head.title}</div>
        <div style={{ fontSize: 18, color: C.muted }}>{head.note}</div>
        <div style={{ flex: 1 }} />
        <div style={{ fontFamily: mono, fontSize: 21, color: C.text }}>
          paid to attackers: {lost} tUSDC
          {side === "eclipse" ? ` · in escrow: ${held} tUSDC · stopped: ${stopped}` : ""}
        </div>
        <div style={{ fontFamily: mono, fontSize: 16, color: C.dim }}>{rate > 1 ? `time-lapse ×${rate.toFixed(1)}` : "real time"}</div>
      </div>
      <OffthreadVideo
        src={staticFile(`live-demo/${take.file}`)}
        trimBefore={Math.round(lead * data.fps)}
        playbackRate={rate}
        muted
        style={{ position: "absolute", left: (1920 - w) / 2, top: 1080 - h, width: w, height: h }}
      />
    </AbsoluteFill>
  );
};
