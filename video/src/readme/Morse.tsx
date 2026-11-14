import type React from "react";
import { interpolate } from "remotion";
import { C } from "../theme";
import { MORSE } from "./data";

const U = 7; // one Morse unit in px
const ROW_GAP = 24; // row 2 sits 24 px below row 1
const ROWS = [
  [0, 1, 2],
  [3, 4],
] as const;
// Linear left-to-right reveal of each row.
const REVEAL = [
  [66, 78],
  [76, 84],
] as const;

type Mark = { readonly x: number; readonly w: number };

// Lay out one word: dot 1u, dash 3u, 1u inside a letter, 3u between letters.
const layoutWord = (word: string, x0: number): { marks: Mark[]; end: number } => {
  const marks: Mark[] = [];
  let x = x0;
  word.split(" ").forEach((letter, li) => {
    if (li > 0) x += 2 * U; // 1u already added after the last symbol
    for (const sym of letter) {
      const w = sym === "-" ? 3 * U : U;
      marks.push({ x, w });
      x += w + U;
    }
  });
  return { marks, end: x - U };
};

const WORDS = MORSE.split(" / ");
const LAYOUT = ROWS.map((row) => {
  let x = 0;
  return row.map((wi) => {
    const { marks, end } = layoutWord(WORDS[wi], x);
    x = end + 7 * U;
    return { wi, marks, end };
  });
});

// The Morse X reply as rows of dots and dashes; word i lights up at decodeAt(i).
export const Morse: React.FC<{
  readonly frame: number;
  readonly decodeAt: (i: number) => number;
}> = ({ frame, decodeAt }) => (
  <svg width={1056} height={ROW_GAP + U} style={{ position: "absolute", left: 0, top: 50, overflow: "visible" }}>
    {LAYOUT.map((row, ri) => {
      const rowEnd = row[row.length - 1].end;
      const clipW = interpolate(frame, REVEAL[ri], [0, rowEnd], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      return (
        <g key={ri}>
          <clipPath id={`morse-row-${ri}`}>
            <rect x={0} y={ri * ROW_GAP - 2} width={clipW} height={U + 4} />
          </clipPath>
          <g clipPath={`url(#morse-row-${ri})`}>
            {row.map(({ wi, marks }) => {
              const d = decodeAt(wi);
              const fill = frame < d ? C.muted : frame < d + 2 ? C.cream : C.alarm;
              return marks.map((m) => (
                <rect key={`${wi}-${m.x}`} x={m.x} y={ri * ROW_GAP} width={m.w} height={U} rx={U / 2} fill={fill} />
              ));
            })}
          </g>
        </g>
      );
    })}
  </svg>
);
