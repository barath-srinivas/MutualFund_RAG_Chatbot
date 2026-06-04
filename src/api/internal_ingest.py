from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from src.config.settings import get_settings
from src.ingest.pipeline import run_ingest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal"])

_lock = threading.Lock()
_running = False


def _authorize(authorization: str | None) -> None:
    settings = get_settings()
    if not settings.enable_internal_ingest:
        raise HTTPException(status_code=404, detail="Not found")
    secret = settings.ingest_trigger_secret.strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Ingest trigger not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    if token != secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/internal/ingest")
def trigger_ingest(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """
    Run corpus ingest on this service (where Chroma volume is mounted).

    Called by GitHub Actions (or Railway cron) at 10:00 IST; ingest runs on this host where Chroma is mounted.
    """
    global _running
    _authorize(authorization)

    with _lock:
        if _running:
            raise HTTPException(status_code=409, detail="Ingest already in progress")
        _running = True

    settings = get_settings()
    try:
        logger.info("Starting scheduled corpus ingest (manifest=%s)", settings.corpus_urls_path)
        report = run_ingest(
            manifest_path=settings.corpus_urls_path,
            dry_run=False,
            save_raw=False,
        )
        return {
            "status": "ok",
            "run_id": report.run_id,
            "finished_at": report.finished_at,
            "sources_processed": report.sources_processed,
            "sources_failed": report.sources_failed,
            "sources_skipped": report.sources_skipped,
            "total_chunks": report.total_chunks,
            "errors": report.errors[:5],
        }
    except Exception as exc:
        logger.exception("Corpus ingest failed: %s", exc)
        raise HTTPException(status_code=500, detail="Ingest failed; see API logs") from exc
    finally:
        with _lock:
            _running = False
