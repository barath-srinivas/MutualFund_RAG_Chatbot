from __future__ import annotations

import logging
from typing import Protocol

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# BGE retrieval instruction prefix (documents are embedded without a prefix).
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...


class LocalBgeEmbedder:
    """Local BAAI/bge-small-en-v1.5 embedder via sentence-transformers (task 1.11)."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._device = device or settings.embedding_device
        self._batch_size = batch_size if batch_size is not None else get_settings().embedding_batch_size
        self._model = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return get_settings().embedding_dimensions

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install -r requirements-phase1.txt"
            ) from exc

        logger.info("Loading embedding model %s on %s", self._model_name, self._device)
        self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        vectors = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [_as_list(vector) for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        model = self._load_model()
        vector = model.encode(
            BGE_QUERY_PREFIX + text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return _as_list(vector)


def _as_list(vector) -> list[float]:
    if hasattr(vector, "tolist"):
        return vector.tolist()
    return list(vector)


def create_embedder() -> LocalBgeEmbedder:
    settings = get_settings()
    if settings.embedding_provider != "local":
        raise ValueError(
            f"Unsupported embedding provider: {settings.embedding_provider!r}. "
            "Only 'local' is implemented."
        )
    return LocalBgeEmbedder()
