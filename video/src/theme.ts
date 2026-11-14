import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadGeistMono } from "@remotion/google-fonts/GeistMono";

// Brand tokens copied from site/src/styles.css so the video matches the landing page.
export const C = {
  ground: "#15131d",
  surface: "#1b1925",
  card: "#17151e",
  line: "#2e2a3b",
  text: "#eeeaf5",
  muted: "#a39db5",
  dim: "#8f89a3",
  accent: "#edb1e8",
  accentDeep: "#c77dc6",
  alarm: "#ff8fb0",
  allow: "#9fe3b8",
  hold: "#f5d58a",
  cream: "#fff3fb",
} as const;

export const sans = loadGeist("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
}).fontFamily;

export const mono = loadGeistMono("normal", {
  weights: ["400", "600"],
  subsets: ["latin"],
}).fontFamily;
