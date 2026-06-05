from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from src.config.settings import get_settings
from src.ingest.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ops"])


def _last_ingest_path() -> Path:
    settings = get_settings()
    return settings.vector_db_path.parent / "last_ingest.json"


@router.get("/corpus-status")
def corpus_status(scheme_id: str | None = None) -> dict[str, Any]:
    """Last successful ingest metadata (written to the Chroma volume)."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "vector_db_path": str(settings.vector_db_path),
        "chunk_count": None,
        "last_ingest": None,
    }

    try:
        store = ChromaVectorStore()
        payload["chunk_count"] = store.count()
        if scheme_id:
            collection = store._connect()
            result = collection.get(
                where={"scheme_id": scheme_id},
                include=["metadatas"],
            )
            metas = result.get("metadatas") or []
            payload["scheme_sections"] = sorted(
                {
                    str(meta.get("section") or "").strip()
                    for meta in metas
                    if meta.get("section")
                }
            )
    except Exception as exc:
        logger.warning("Could not read Chroma count: %s", exc)
        payload["chunk_count_error"] = str(exc)

    path = _last_ingest_path()
    if path.is_file():
        try:
            payload["last_ingest"] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            payload["last_ingest_error"] = str(exc)

    return payload
