#!/usr/bin/env bash
# Nightly end-to-end testnet runner (Sprint 1 task B2)
# Usage: ./scripts/nightly-e2e.sh [--mode testnet|dry-run] [-y]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}/agent"
exec uv run firewall-nightly-e2e "$@"
