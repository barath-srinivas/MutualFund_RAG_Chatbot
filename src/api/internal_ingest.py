from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.ingest.pipeline import run_ingest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["internal"])

_lock = threading.Lock()
_running = False


class IngestTriggerRequest(BaseModel):
    """Optional body for POST /internal/ingest."""

    force: bool = Field(
        default=False,
        description="Re-fetch and re-index all sources even when raw content hash is unchanged.",
    )


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


def _ingest_worker(*, force: bool) -> None:
    global _running
    settings = get_settings()
    try:
        logger.info(
            "Starting scheduled corpus ingest (manifest=%s, force=%s)",
            settings.corpus_urls_path,
            force,
        )
        report = run_ingest(
            manifest_path=settings.corpus_urls_path,
            dry_run=False,
            save_raw=False,
            force=force,
        )
        logger.info(
            "Corpus ingest finished: %s chunks, %s failed (run_id=%s)",
            report.total_chunks,
            report.sources_failed,
            report.run_id,
        )
    except Exception:
        logger.exception("Corpus ingest failed")
    finally:
        with _lock:
            _running = False


@router.post("/internal/ingest")
def trigger_ingest(
    body: IngestTriggerRequest | None = None,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """
    Start corpus ingest on this service (where Chroma volume is mounted).

    Returns 202 immediately; ingest runs in a background thread so Railway/proxy
    timeouts do not kill a 30–60+ minute job. Poll GET /corpus-status for completion.
    """
    global _running
    _authorize(authorization)

    with _lock:
        if _running:
            raise HTTPException(status_code=409, detail="Ingest already in progress")
        _running = True

    force = body.force if body is not None else False
    started_at = datetime.now(timezone.utc).isoformat()
    thread = threading.Thread(
        target=_ingest_worker,
        kwargs={"force": force},
        name="corpus-ingest",
        daemon=True,
    )
    thread.start()

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Ingest started in background; poll /corpus-status for completion.",
            "started_at": started_at,
            "force": force,
        },
    )
