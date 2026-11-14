import type React from "react";
import { interpolate, interpolateColors, useCurrentFrame } from "remotion";
import { C, mono } from "../theme";
import { bump, clamp, E, G, track } from "./timeline";

const LANE_XS = Array.from({ length: 56 }, (_, i) => 300 + i * 24); // 300 … 1620
const SHAKE: Record<number, number> = { 220: 6, 221: -4, 222: 2 };
const ARC_R = 68;
const ARC_SPAN = 48;

// Sun x before (A) and after (B) its reset at frame 270.
const sunXA = (f: number) =>
  track(f, [
    [12, G.markSun.x],
    [26, G.sunHome, E.inOut],
    [130, G.sunHome],
    [133, 366, E.out],
    [143, 814, E.snap],
    [147, G.sunPause, E.out],
  ]);
const sunXB = (f: number) =>
  track(f, [
    [280, G.sunHome],
    [283, 368, E.out],
    [292, G.sunPause, E.snap],
    [297, G.sunPause],
    [309, G.sunDest, E.inOut],
    [334, G.sunDest],
    [350, G.markSun.x, E.inOut],
  ]);

const arcPath = (cx: number, cy: number, r: number, centerDeg: number) => {
  const a0 = ((centerDeg - ARC_SPAN / 2) * Math.PI) / 180;
  const a1 = ((centerDeg + ARC_SPAN / 2) * Math.PI) / 180;
  return `M ${cx + r * Math.cos(a0)} ${cy + r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(a1)} ${cy + r * Math.sin(a1)}`;
};

const label = (x: number, w: number): React.CSSProperties => ({
  position: "absolute",
  left: x - w / 2,
  top: G.labelY,
  width: w,
  textAlign: "center",
  fontFamily: mono,
  fontWeight: 600,
});

export const Stage: React.FC = () => {
  const frame = useCurrentFrame();

  // Stage chrome: in 16–34, out 334–342.
  const chromeOut = interpolate(frame, [334, 342], [1, 0], clamp);
  const agentOp = interpolate(frame, [18, 26], [0, 1], clamp) * chromeOut;
  const guardOp = interpolate(frame, [24, 32], [0, 1], clamp) * chromeOut;
  const recvOp = interpolate(frame, [26, 34], [0, 1], clamp) * chromeOut;

  // Sun.
  const sunX = frame < 270 ? sunXA(frame) : sunXB(frame);
  const sunY = track(frame, [
    [12, G.markSun.y],
    [26, G.laneY, E.arc],
    [334, G.laneY],
    [350, G.markSun.y, E.arc],
  ]);
  const sunR = track(frame, [
    [12, G.markSun.r],
    [26, G.sunR, E.inOut],
    [334, G.sunR],
    [350, G.markSun.r, E.inOut],
  ]);
  let sx = 1;
  let sy = 1;
  if (frame >= 94 && frame < 102) {
    sx = sy = bump(frame, 94, 98, 102, 1.25);
  } else if (frame >= 133 && frame < 143) {
    sx = bump(frame, 133, 138, 143, 1.5);
    sy = bump(frame, 133, 138, 143, 0.85);
  } else if (frame >= 270 && frame < 278) {
    sx = sy = interpolate(frame, [270, 278], [0, 1], { ...clamp, easing: E.pop });
  } else if (frame >= 283 && frame < 292) {
    sx = bump(frame, 283, 288, 292, 1.5);
    sy = bump(frame, 283, 288, 292, 0.85);
  } else if (frame >= 297 && frame < 309) {
    sx = bump(frame, 297, 303, 309, 1.3);
  } else if (frame >= 309 && frame < 314) {
    sx = interpolate(frame, [309, 314], [1.15, 1], { ...clamp, easing: E.out });
    sy = interpolate(frame, [309, 314], [0.88, 1], { ...clamp, easing: E.out });
  }
  const sunFill = frame < 270 ? interpolateColors(frame, [94, 100], [C.accent, C.alarm]) : C.accent;
  const sunOp = frame < 270 ? interpolate(frame, [218, 221], [1, 0], clamp) : 1;

  // Moon.
  const moonX =
    track(frame, [
      [12, G.markMoon.x],
      [26, G.guardX, E.inOut],
      [208, G.guardX],
      [212, 970, E.out],
      [220, G.sunPause, E.snap],
      [236, G.sunPause],
      [248, G.guardX, E.inOut],
      [336, G.guardX],
      [350, G.markMoon.x, E.inOut],
    ]) + (SHAKE[frame] ?? 0);
  const moonY = track(frame, [
    [12, G.markMoon.y],
    [26, G.laneY, E.inOut],
    [336, G.laneY],
    [350, G.markMoon.y, E.inOut],
  ]);
  const moonR = track(frame, [
    [12, G.markMoon.r],
    [26, G.moonR, E.inOut],
    [336, G.moonR],
    [350, G.markMoon.r, E.inOut],
  ]);
  const moonScale = track(frame, [
    [288, 1],
    [296, 0.86, E.out],
    [309, 0.86],
    [318, 1, E.out],
  ]);
  const moonSx = frame >= 212 && frame < 220 ? bump(frame, 212, 216, 220, 1.12) : 1;
  const rimOp = track(frame, [
    [16, 0],
    [26, 1],
    [336, 1],
    [346, 0],
  ]);
  const rimW = track(frame, [
    [143, 3],
    [147, 8, E.out],
    [151, 3, E.inOut],
  ]);
  const rimColor = interpolateColors(frame, [288, 296, 309, 318], [C.accentDeep, C.line, C.line, C.accentDeep]);

  // Lane trail.
  const blockTrail = frame >= 133 && frame < 244 ? sunXA(frame) : -1;
  const blockTrailColor = interpolateColors(frame, [232, 244], [C.alarm, C.line]);
  const allowTrail = frame >= 283 ? (frame >= 309 ? G.sunDest : sunXB(frame)) : -1;
  const dotColor = (x: number) => {
    if (x < allowTrail) return C.accent;
    if (x < blockTrail) return blockTrailColor;
    return C.line;
  };

  const recvStroke = interpolateColors(
    frame,
    [112, 118, 270, 276, 309, 313],
    [C.line, C.alarm, C.alarm, C.line, C.line, C.allow],
  );

  const sun = (
    <ellipse cx={sunX} cy={sunY} rx={sunR * sx} ry={sunR * sy} fill={sunFill} opacity={sunOp} />
  );
  const moon = (
    <ellipse
      cx={moonX}
      cy={moonY}
      rx={moonR * moonScale * moonSx}
      ry={moonR * moonScale}
      fill={C.ground}
      stroke={rimColor}
      strokeWidth={rimW}
      strokeOpacity={rimOp}
    />
  );
  const sunOnTop = frame >= 270 && frame < 334;

  // Arcs around the moon.
  const arcR = ARC_R * moonScale;
  const arcLen = (arcR * ARC_SPAN * Math.PI) / 180;
  const blockArcOp = interpolate(frame, [268, 274], [1, 0], clamp);
  const blockArcColor = frame < 220 ? interpolateColors(frame, [208, 212], [C.alarm, C.cream]) : C.alarm;
  const allowArcOp = interpolate(frame, [318, 326], [1, 0], clamp);
  const arcs = Array.from({ length: 6 }, (_, i) => {
    const center = -90 + 60 * i;
    const d = arcPath(moonX, moonY, arcR, center);
    const blockDrawn = interpolate(frame, [156 + 8 * i, 161 + 8 * i], [0, 1], clamp);
    const allowDrawn = interpolate(frame, [291 + i, 293 + i], [0, 1], clamp);
    return (
      <g key={i} fill="none" strokeWidth={6} strokeLinecap="round">
        {blockDrawn > 0 && blockArcOp > 0 ? (
          <path
            d={d}
            stroke={blockArcColor}
            opacity={blockArcOp}
            strokeDasharray={arcLen}
            strokeDashoffset={arcLen * (1 - blockDrawn)}
          />
        ) : null}
        {allowDrawn > 0 && allowArcOp > 0 ? (
          <path
            d={d}
            stroke={C.allow}
            opacity={allowArcOp}
            strokeDasharray={arcLen}
            strokeDashoffset={arcLen * (1 - allowDrawn)}
          />
        ) : null}
      </g>
    );
  });

  // Corona at the pause point, 218–236.
  const corona =
    frame >= 218 && frame <= 236 ? (
      <g>
        {frame <= 220 ? (
          <circle
            cx={766}
            cy={G.laneY}
            r={interpolate(frame, [218, 220], [8, 12], clamp)}
            fill={C.cream}
          />
        ) : null}
        {frame >= 220
          ? Array.from({ length: 24 }, (_, k) => {
              const deg = 15 * k;
              const a = (deg * Math.PI) / 180;
              const dist = interpolate(frame, [220, 234], [60, 132], { ...clamp, easing: E.out });
              const op =
                interpolate(frame, [220, 222], [0, 1], clamp) * interpolate(frame, [228, 236], [1, 0], clamp);
              const fill = frame <= 223 ? C.cream : C.alarm;
              const x = G.sunPause + dist * Math.cos(a);
              const y = G.laneY + dist * Math.sin(a);
              return k % 2 === 0 ? (
                <circle key={k} cx={x} cy={y} r={6} fill={fill} opacity={op} />
              ) : (
                <rect
                  key={k}
                  x={-10}
                  y={-4}
                  width={20}
                  height={8}
                  rx={4}
                  fill={fill}
                  opacity={op}
                  transform={`translate(${x} ${y}) rotate(${deg})`}
                />
              );
            })
          : null}
        {frame >= 220 ? (
          <circle
            cx={G.sunPause}
            cy={G.laneY}
            r={interpolate(frame, [220, 234], [56, 170], { ...clamp, easing: E.out })}
            fill="none"
            stroke={C.alarm}
            strokeWidth={interpolate(frame, [220, 234], [4, 1], clamp)}
            opacity={interpolate(frame, [224, 234], [1, 0], clamp)}
          />
        ) : null}
      </g>
    ) : null;

  // Amount tag over the sun.
  const tagBlock = frame < 270;
  const tagOp = tagBlock
    ? interpolate(frame, [36, 41], [0, 1], clamp) * interpolate(frame, [218, 221], [1, 0], clamp)
    : interpolate(frame, [276, 281], [0, 1], clamp) * chromeOut;
  const tagRise = tagBlock
    ? interpolate(frame, [36, 44], [16, 0], { ...clamp, easing: E.out })
    : interpolate(frame, [276, 282], [16, 0], { ...clamp, easing: E.out });
  const tagColor = tagBlock
    ? interpolateColors(frame, [94, 100], [C.accent, C.alarm])
    : interpolateColors(frame, [309, 313], [C.accent, C.allow]);
  const zero = tagBlock ? interpolate(frame, [94, 100], [0, 1], { ...clamp, easing: E.out }) : 0;

  // Receiver name: last character rolls o -> 0 (112–118) and back (270–276).
  const rollIn = interpolate(frame, [112, 118], [0, 1], { ...clamp, easing: E.out });
  const rollBack = interpolate(frame, [270, 276], [0, 1], { ...clamp, easing: E.out });
  const oPos = frame < 200 ? -rollIn : 1 - rollBack; // o: 0 → -1 (up), then 1 → 0
  const zeroPos = frame < 200 ? 1 - rollIn : -rollBack; // 0: 1 → 0, then 0 → -1
  const nameColor = interpolateColors(frame, [226, 232, 270, 276], [C.text, C.dim, C.dim, C.text]);
  const strikeDrawn = interpolate(frame, [226, 232], [0, 1], clamp);
  const strikeOp = interpolate(frame, [270, 276], [1, 0], clamp);

  const paused = interpolate(frame, [143, 147, 232, 236], [0, 1, 1, 0], clamp);

  return (
    <>
      <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
        {LANE_XS.map((x) => {
          const start = 16 + ((x - 300) / 1320) * 10;
          return (
            <circle
              key={x}
              cx={x}
              cy={G.laneY}
              r={3}
              fill={dotColor(x)}
              opacity={interpolate(frame, [start, start + 4], [0, 1], clamp) * chromeOut}
            />
          );
        })}
        <g opacity={agentOp}>
          <rect
            x={G.agentX - G.box / 2}
            y={G.laneY - G.box / 2}
            width={G.box}
            height={G.box}
            rx={G.boxR}
            fill={C.card}
            stroke={C.line}
            strokeWidth={3}
          />
          <text
            x={G.agentX}
            y={G.laneY}
            textAnchor="middle"
            dominantBaseline="central"
            fontFamily={mono}
            fontWeight={600}
            fontSize={44}
            fill={C.accent}
          >
            {">_"}
          </text>
        </g>
        <g opacity={recvOp}>
          <rect
            x={G.receiverX - G.box / 2}
            y={G.laneY - G.box / 2}
            width={G.box}
            height={G.box}
            rx={G.boxR}
            fill={C.card}
            stroke={recvStroke}
            strokeWidth={3}
          />
          <text
            x={G.receiverX}
            y={G.laneY}
            textAnchor="middle"
            dominantBaseline="central"
            fontFamily={mono}
            fontWeight={600}
            fontSize={44}
            fill={C.muted}
          >
            @
          </text>
        </g>
        {strikeDrawn > 0 && strikeOp > 0 ? (
          <line
            x1={1638}
            y1={660}
            x2={1638 + 124 * strikeDrawn}
            y2={660}
            stroke={C.alarm}
            strokeWidth={3}
            opacity={strikeOp * recvOp}
          />
        ) : null}
        {sunOnTop ? moon : sun}
        {sunOnTop ? sun : moon}
        {arcs}
        {corona}
      </svg>

      <div style={{ ...label(G.agentX, 300), fontSize: 30, color: C.muted, opacity: agentOp }}>AGENT</div>

      <div style={{ ...label(G.guardX, 400), fontSize: 30, height: 40, opacity: guardOp }}>
        <span style={{ position: "absolute", left: 0, right: 0, color: C.muted, opacity: 1 - paused }}>
          GUARDIAN
        </span>
        <span style={{ position: "absolute", left: 0, right: 0, color: C.accent, opacity: paused }}>PAUSED</span>
      </div>

      <div
        style={{
          ...label(G.receiverX, 300),
          fontSize: 36,
          display: "flex",
          justifyContent: "center",
          lineHeight: "44px",
          color: nameColor,
          opacity: recvOp,
        }}
      >
        <span>hostc</span>
        <span
          style={{
            position: "relative",
            display: "inline-block",
            width: "1ch",
            height: 44,
            overflow: "hidden",
          }}
        >
          <span style={{ position: "absolute", left: 0, top: 0, translate: `0 ${oPos * 44}px`, opacity: 1 - Math.abs(oPos) }}>
            o
          </span>
          <span
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              color: C.alarm,
              translate: `0 ${zeroPos * 44}px`,
              opacity: 1 - Math.abs(zeroPos),
            }}
          >
            0
          </span>
        </span>
      </div>

      {tagOp > 0 ? (
        <div
          style={{
            position: "absolute",
            left: sunX - 200,
            top: 458,
            width: 400,
            display: "flex",
            justifyContent: "center",
            fontFamily: mono,
            fontWeight: 600,
            fontSize: 38,
            lineHeight: "46px",
            whiteSpace: "pre",
            color: tagColor,
            opacity: tagOp,
            translate: `0 ${tagRise}px`,
          }}
        >
          <span>18</span>
          <span style={{ display: "inline-block", width: `${zero}ch`, overflow: "hidden", height: 46 }}>
            <span style={{ display: "inline-block", translate: `0 ${(1 - zero) * 16}px` }}>0</span>
          </span>
          <span> tUSDC</span>
        </div>
      ) : null}
    </>
  );
};
