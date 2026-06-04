#!/usr/bin/env bash
# Railway cron service (10:00 IST) — triggers ingest on the API service via private networking.
set -euo pipefail

: "${INGEST_TRIGGER_URL:?Set INGEST_TRIGGER_URL, e.g. http://<api-service>.railway.internal:8080/internal/ingest}"
: "${INGEST_TRIGGER_SECRET:?Set INGEST_TRIGGER_SECRET (same as API service)}"

echo "Triggering corpus ingest at ${INGEST_TRIGGER_URL}"
python3 "$(dirname "$0")/railway_cron_trigger.py"
