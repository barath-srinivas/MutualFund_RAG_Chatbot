from __future__ import annotations

import logging
from typing import Any, Protocol

from src.config.settings import get_settings
from src.ingest.models import DocumentChunk

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "mf_corpus"


class VectorStore(Protocol):
    def count(self) -> int: ...

    def get_source_content_hash(self, source_id: str) -> str | None: ...

    def delete_source(self, source_id: str) -> int: ...

    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int: ...

    def replace_source_chunks(
        self,
        source_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> int: ...


class ChromaVectorStore:
    """Persist chunk embeddings in ChromaDB (task 1.12)."""

    def __init__(
        self,
        *,
        path=None,
        collection_name: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._path = path or settings.vector_db_path
        self._collection_name = collection_name or settings.chroma_collection_name
        self._embedding_model = embedding_model or settings.embedding_model
        self._client = None
        self._collection = None

    @property
    def path(self):
        return self._path

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def embedding_model(self) -> str:
        return self._embedding_model

    def _connect(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "chromadb is required for the vector store. "
                "Install with: pip install -r requirements-phase1.txt"
            ) from exc

        self._path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._path))
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"embedding_model": self._embedding_model},
        )
        return self._collection

    def count(self) -> int:
        return self._connect().count()

    def count_for_source(self, source_id: str) -> int:
        collection = self._connect()
        result = collection.get(where={"source_id": source_id}, include=[])
        return len(result.get("ids") or [])

    def get_source_content_hash(self, source_id: str) -> str | None:
        collection = self._connect()
        result = collection.get(where={"source_id": source_id}, include=["metadatas"], limit=1)
        metadatas = result.get("metadatas") or []
        if not metadatas:
            return None
        return metadatas[0].get("content_hash") or None

    def list_source_ids(self) -> set[str]:
        collection = self._connect()
        if collection.count() == 0:
            return set()
        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas") or []
        ids: set[str] = set()
        for meta in metadatas:
            if meta and meta.get("source_id"):
                ids.add(str(meta["source_id"]))
        return ids

    def delete_source(self, source_id: str) -> int:
        collection = self._connect()
        existing = collection.get(where={"source_id": source_id}, include=[])
        ids = existing.get("ids") or []
        if ids:
            collection.delete(ids=ids)
        return len(ids)

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        if not chunks:
            return 0

        collection = self._connect()
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [_chunk_metadata(chunk, self._embedding_model) for chunk in chunks]
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(chunks)

    def replace_source_chunks(
        self,
        source_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> int:
        removed = self.delete_source(source_id)
        if removed:
            logger.debug("Removed %s existing chunks for source %s", removed, source_id)
        return self.upsert_chunks(chunks, embeddings)

    def query(
        self,
        query_embedding: list[float],
        *,
        n_results: int = 12,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search; returns dicts with id, text, metadata, distance, score."""
        collection = self._connect()
        if collection.count() == 0:
            return []

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        result = collection.query(**kwargs)
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[dict[str, Any]] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            score = _distance_to_score(distance)
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "text": text or "",
                    "metadata": metadata or {},
                    "distance": distance,
                    "score": score,
                }
            )
        return hits


def _distance_to_score(distance: float | None) -> float:
    """Map Chroma cosine distance to similarity score (1 = identical)."""
    if distance is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(distance)))


def _chunk_metadata(chunk: DocumentChunk, embedding_model: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "scheme_id": chunk.scheme_id or "",
        "doc_type": chunk.doc_type,
        "source_url": chunk.source_url,
        "source_id": chunk.source_id,
        "section": chunk.section,
        "topic": chunk.topic or "",
        "text_hash": chunk.text_hash,
        "content_hash": chunk.content_hash,
        "embedding_model": embedding_model,
    }
    if chunk.fetched_at is not None:
        metadata["fetched_at"] = chunk.fetched_at.isoformat()
    return metadata
