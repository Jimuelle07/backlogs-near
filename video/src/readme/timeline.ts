import { Easing, interpolate } from "remotion";

// ReadmeDemo timing: 375 frames at 25 fps. Every frame number in src/readme/ is a
// composition frame; panels inside a <Sequence> add their `from` back (SEQ).

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

type Ease = (t: number) => number;
const linear: Ease = (t) => t;

export const E = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // entrances, settles
  inOut: Easing.bezier(0.65, 0, 0.35, 1), // travel
  in: Easing.bezier(0.7, 0, 0.84, 0), // exits
  pop: Easing.bezier(0.34, 1.56, 0.64, 1), // stamps, chips
  snap: Easing.bezier(0.7, 0, 0.2, 1), // launch, eclipse step
  arc: Easing.bezier(0.33, 0, 0.2, 1), // y of diagonal moves, so the path curves
} as const;

export const G = {
  laneY: 560,
  agentX: 220,
  receiverX: 1700,
  box: 120,
  boxR: 28,
  labelY: 640,
  sunHome: 380,
  sunPause: 810,
  sunDest: 1540,
  guardX: 960,
  sunR: 46,
  moonR: 52,
  markSun: { x: 972, y: 300, r: 58 },
  markMoon: { x: 952, y: 300, r: 56 },
} as const;

export const DURATION = 375;

// [from, durationInFrames] of each panel <Sequence>.
export const SEQ = {
  ask: [22, 115],
  pause: [138, 82],
  block: [220, 57],
  allow: [294, 49],
  proposal: [116, 37],
  checksBlock: [150, 130],
  checksAllow: [290, 53],
} as const;

// Keyframe track: [frame, value, easing into this key]. Equal frames make a jump.
export type Key = readonly [number, number, Ease?];
export const track = (frame: number, keys: readonly Key[]): number => {
  if (frame <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [f0, v0] = keys[i - 1];
    const [f1, v1, ease] = keys[i];
    if (frame < f1) {
      return interpolate(frame, [f0, f1], [v0, v1], { ...clamp, easing: ease ?? linear });
    }
  }
  return keys[keys.length - 1][1];
};

// 1 -> peak -> 1 over [a, b], peak at `at`.
export const bump = (frame: number, a: number, at: number, b: number, peak: number): number =>
  track(frame, [
    [a, 1],
    [at, peak, E.out],
    [b, 1, E.inOut],
  ]);

// Fade rule: "in a-b" = opacity 0->1 over a..a+5 plus a move from `from` over a-b (E.out);
// "out c-d" = opacity 1->0 and translate 0 -> -20px over c-d (E.in).
export const fade = (
  frame: number,
  opts: {
    readonly inn?: readonly [number, number];
    readonly from?: readonly [number, number];
    readonly out?: readonly [number, number];
  },
): { opacity: number; translate: string } => {
  const [fx, fy] = opts.from ?? [0, 0];
  let opacity = 1;
  let x = 0;
  let y = 0;
  if (opts.inn) {
    const [a, b] = opts.inn;
    opacity *= interpolate(frame, [a, a + 5], [0, 1], clamp);
    const p = interpolate(frame, [a, b], [0, 1], { ...clamp, easing: E.out });
    x += fx * (1 - p);
    y += fy * (1 - p);
  }
  if (opts.out) {
    const [c, d] = opts.out;
    const q = interpolate(frame, [c, d], [0, 1], { ...clamp, easing: E.in });
    opacity *= 1 - q;
    y -= 20 * q;
  }
  return { opacity, translate: `${x}px ${y}px` };
};
