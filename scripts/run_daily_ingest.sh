#!/usr/bin/env bash
# Manual daily ingest wrapper (not scheduled — use GitHub Actions for 10:00 IST).
set -euo pipefail
cd "$(dirname "$0")/.."
python -m src.ingest --manifest corpus/urls.yaml --no-save-raw "$@"
