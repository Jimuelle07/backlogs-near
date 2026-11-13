import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

// The build prerenders the page into #root (scripts/prerender.mjs) so crawlers that do not run
// JavaScript still read the content; hydrate that markup, or render fresh in dev.
const root = document.getElementById("root");
const app = (
  <StrictMode>
    <App />
  </StrictMode>
);
if (root.hasChildNodes()) hydrateRoot(root, app);
else createRoot(root).render(app);
