// Pixel shield mark from the branding artifact.
const ROWS = ["0111110", "1111111", "1111101", "1011011", "1100111", "0111110", "0011100", "0001000"];

export function Logo({ size = 26, color = "#EDB1E8" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={(size * 8) / 7} viewBox="0 0 28 32" aria-hidden="true">
      {ROWS.flatMap((row, r) =>
        row.split("").map((v, c) =>
          v === "1" ? <rect key={`${r}-${c}`} x={c * 4} y={r * 4} width="3.4" height="3.4" fill={color} /> : null,
        ),
      )}
    </svg>
  );
}
