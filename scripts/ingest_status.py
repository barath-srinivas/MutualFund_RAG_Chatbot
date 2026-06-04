"""Print corpus URL list vs Chroma indexed state."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import chromadb

from src.ingest.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[1]
manifest = load_manifest(ROOT / "corpus" / "urls.yaml")
entries = manifest.all_sources()

print(f"URLs in corpus/urls.yaml: {len(entries)} sources\n")
for e in entries:
    sid = e.scheme_id or "shared"
    print(f"  {e.id:40} {sid:22} {e.doc_type}")

col = chromadb.PersistentClient(path=str(ROOT / "data" / "chroma")).get_collection("mf_corpus")
meta = col.get(include=["metadatas"])
by_source = Counter(m.get("source_id") for m in meta["metadatas"])
by_scheme = Counter((m.get("scheme_id") or "").strip() or "_none" for m in meta["metadatas"])

print(f"\nChroma total chunks: {col.count()}")
print("By scheme_id:", dict(sorted(by_scheme.items())))
print("\nChunks per source_id:")
for sid, n in by_source.most_common():
    print(f"  {sid}: {n}")

mans = sorted((ROOT / "corpus" / "manifests").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
print("\nRecent ingest runs:")
for p in mans[:8]:
    d = json.loads(p.read_text(encoding="utf-8"))
    print(
        f"  {p.name}: total={d.get('total_chunks')} failed={d.get('sources_failed')} "
        f"skipped={d.get('sources_skipped')} by_scheme={d.get('chunks_by_scheme')}"
    )
