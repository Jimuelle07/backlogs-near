"""Injection classifier service (default protectai/deberta-v3-base-prompt-injection-v2; --model selects another binary injection classifier).

Provides an HTTP scoring endpoint compatible with the Rust checker's
InjectionConfig (`CLASSIFIER_URL`). By default it loads the Hugging Face model
(transformers + torch) and fails if it cannot; `--heuristic` / `load_model=False`
selects a keyword heuristic for offline tests, reported as model `keyword-heuristic`.
"""

from __future__ import annotations

import hashlib
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

logger = logging.getLogger("firewall.classifier")

MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"
PROMPT_GUARD_MODEL_ID = "meta-llama/Llama-Prompt-Guard-2-86M"
HEURISTIC_MODEL_ID = "keyword-heuristic"

# Pipeline label names per binary classifier: protectai reports SAFE/INJECTION,
# Prompt Guard 2 reports BENIGN/MALICIOUS (class 0 / class 1), possibly as LABEL_0/LABEL_1.
POSITIVE_LABELS = frozenset({"INJECTION", "MALICIOUS", "LABEL_1"})
NEGATIVE_LABELS = frozenset({"SAFE", "BENIGN", "LABEL_0"})

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
    def __init__(self, model_id: str = MODEL_ID, load_model: bool = True) -> None:
        self.model_id = model_id
        self._pipeline = None
        if load_model:
            self._init_pipeline()

    def _init_pipeline(self) -> None:
        try:
            from transformers import pipeline  # type: ignore

            self._pipeline = pipeline("text-classification", model=self.model_id)
        except Exception as e:
            raise RuntimeError(f"classifier model {self.model_id} failed to load: {e}") from e
        logger.info("Loaded Hugging Face pipeline for %s", self.model_id)

    @property
    def reported_model(self) -> str:
        return self.model_id if self._pipeline is not None else HEURISTIC_MODEL_ID

    def score_text(self, text: str) -> float:
        if self._pipeline is None:
            # Keyword heuristic backend (load_model=False); never used when a model is loaded.
            lower = text.lower()
            for kw in INJECTION_KEYWORDS:
                if kw in lower:
                    return 0.98
            return 0.02
        res = self._pipeline(text, truncation=True, max_length=512)
        if (
            not isinstance(res, list)
            or len(res) == 0
            or not isinstance(res[0], dict)
            or "label" not in res[0]
            or "score" not in res[0]
        ):
            raise RuntimeError(
                f"classifier model {self.model_id} returned an unexpected result: {repr(res)[:200]}"
            )
        first = res[0]
        label = str(first["label"]).upper()
        score = float(first["score"])
        if label in POSITIVE_LABELS:
            return score
        if label in NEGATIVE_LABELS:
            return 1.0 - score
        raise RuntimeError(f"classifier model {self.model_id} returned an unknown label {label!r}")

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
        model = self.reported_model
        return {
            "model": model,
            "model_sha256": hashlib.sha256(model.encode("utf-8")).hexdigest(),
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


def run_server(port: int = 8088, load_model: bool = True, model_id: str = MODEL_ID) -> HTTPServer:
    backend = ClassifierBackend(model_id=model_id, load_model=load_model)
    handler = make_handler(backend)
    server = HTTPServer(("127.0.0.1", port), handler)
    return server


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="firewall-classifier", description=__doc__)
    ap.add_argument("port", nargs="?", type=int, default=8088)
    ap.add_argument(
        "--heuristic",
        action="store_true",
        help="use the keyword heuristic instead of loading the model (offline tests)",
    )
    ap.add_argument(
        "--model",
        default=MODEL_ID,
        help="Hugging Face model id to serve (default: %(default)s)",
    )
    args = ap.parse_args(argv)
    server = run_server(args.port, load_model=not args.heuristic, model_id=args.model)
    print(f"Starting injection classifier server on http://127.0.0.1:{args.port}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down classifier server.")


if __name__ == "__main__":
    main()
