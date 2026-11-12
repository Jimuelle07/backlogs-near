import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// `npm run build` → normal static site (dist/, relative paths, any host).
// `npm run build:single` → one self-contained index.html, for publishing as an artifact.
export default defineConfig(({ mode }) => ({
  plugins: [react(), ...(mode === "single" ? [viteSingleFile()] : [])],
  base: "./",
  // The Results section imports ../docs/results/*.json from the repo root.
  server: { fs: { allow: [".."] } },
}));
