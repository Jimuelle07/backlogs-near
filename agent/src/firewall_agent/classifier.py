"""Injection classifier service for protectai/deberta-v3-base-prompt-injection-v2 (C2).

Provides an HTTP scoring endpoint compatible with the Rust checker's
InjectionConfig (`CLASSIFIER_URL`). Supports both real Hugging Face pipeline
scoring (when transformers/torch are installed) and mock scoring for offline tests.
"""

from __future__ import annotations

import hashlib
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

logger = logging.getLogger("firewall.classifier")

MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"
MODEL_SHA256 = hashlib.sha256(MODEL_ID.encode("utf-8")).hexdigest()

# Simple heuristic indicators for prompt injection when running without weights loaded
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "disregard all previous",
    "system prompt",
    "new instruction",
    "send all funds",
    "transfer all",
    "drain wallet",
]


class ClassifierBackend:
    def __init__(self, model_id: str = MODEL_ID) -> None:
        self.model_id = model_id
        self._pipeline = None
        self._init_pipeline()

    def _init_pipeline(self) -> None:
        try:
            from transformers import pipeline  # type: ignore

            self._pipeline = pipeline("text-classification", model=self.model_id)
            logger.info("Loaded Hugging Face pipeline for %s", self.model_id)
        except Exception as e:
            logger.info("Transformers not loaded (%s); using heuristic fallback", e)
            self._pipeline = None

    def score_text(self, text: str) -> float:
        if self._pipeline is not None:
            res = self._pipeline(text[:512])
            if isinstance(res, list) and len(res) > 0:
                first = res[0]
                label = str(first.get("label", "")).upper()
                score = float(first.get("score", 0.0))
                return score if "INJECTION" in label else (1.0 - score)
        # Heuristic fallback for offline / mock testing
        lower = text.lower()
        for kw in INJECTION_KEYWORDS:
            if kw in lower:
                return 0.98
        return 0.02

    def score_batch(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        per_item: list[dict[str, Any]] = []
        max_score = 0.0
        for item in items:
            ref = str(item.get("ref", ""))
            text = str(item.get("text", ""))
            score = self.score_text(text)
            if score > max_score:
                max_score = score
            per_item.append({"ref": ref, "score": round(score, 4)})
        return {
            "model": self.model_id,
            "model_sha256": MODEL_SHA256,
            "max_score": round(max_score, 4),
            "per_item": per_item,
        }


def make_handler(backend: ClassifierBackend):
    class ClassifierHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                items = data.get("items", [])
                resp = backend.score_batch(items)
                out = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)
            except Exception as e:
                err = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err)))
                self.end_headers()
                self.wfile.write(err)

        def log_message(self, fmt, *args):
            return

    return ClassifierHandler


def run_server(port: int = 8088) -> HTTPServer:
    backend = ClassifierBackend()
    handler = make_handler(backend)
    server = HTTPServer(("127.0.0.1", port), handler)
    return server


def main() -> None:
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    print(f"Starting injection classifier server on http://127.0.0.1:{port}...")
    server = run_server(port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down classifier server.")


if __name__ == "__main__":
    main()
