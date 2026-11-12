import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";
import results from "../schemas/examples/results.json";
import { validateResultsFormat } from "./src/results.js";

// Reject an incompatible source during the build, before shipping the renderer.
validateResultsFormat(results);

// `npm run build` → normal static site (dist/, relative paths, any host).
// `npm run build:single` → one self-contained index.html, for publishing as an artifact.
export default defineConfig(({ mode }) => ({
  plugins: [react(), ...(mode === "single" ? [viteSingleFile()] : [])],
  base: "./",
}));
