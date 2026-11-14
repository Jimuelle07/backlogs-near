import type React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";

// Fades and lifts its children in, starting `delay` frames into the parent scene.
export const Reveal: React.FC<{
  readonly delay: number;
  readonly children: React.ReactNode;
  readonly style?: React.CSSProperties;
}> = ({ delay, children, style }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        opacity: interpolate(frame, [delay, delay + 14], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
        translate: interpolate(frame, [delay, delay + 18], ["0px 28px", "0px 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        ...style,
      }}
    >
      {children}
    </div>
  );
};
