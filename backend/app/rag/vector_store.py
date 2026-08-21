"""
Vector store for the RAG pipeline (ChromaDB, embedded & persistent).

Firestore remains the store for users / auth / application data; this
module is solely the semantic-retrieval layer over the JSON knowledge
base.

* Documents are embedded with Chroma's default ONNX MiniLM model and
  stored in a persistent collection under ``backend/data/chroma``.
* The index is built once at startup (idempotent upsert) and reused.
* Every call degrades gracefully — if Chroma or the embedding model is
  unavailable the retriever falls back to lexical scoring.
"""

from __future__ import annotations

import threading
from typing import Any

from app.config import get_settings
from app.core import get_logger
from app.rag.loader import DATA_DIR, DataDocument, get_knowledge_base

log = get_logger("rag.vector_store")

# Persistent collection location + name.
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "kb_documents"

# Cosine-distance cutoff — hits further than this from the query are
# discarded so unrelated questions fall back to pure-LLM mode.
MAX_DISTANCE = 0.85

_lock = threading.Lock()
_collection: Any | None = None
_broken = False  # Set when initialisation fails; stops retry storms.


def vector_enabled() -> bool:
    """True when semantic retrieval is switched on and usable."""
    if not get_settings().rag_vector_enabled:
        return False
    return _get_collection() is not None


def _get_collection() -> Any | None:
    """Lazily create/return the shared Chroma collection (None if unavailable)."""
    global _collection, _broken
    if _broken:
        return None
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is not None or _broken:
            return _collection
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            # Default embedding function: ONNX all-MiniLM-L6-v2 (no torch).
            _collection = client.get_or_create_collection(COLLECTION_NAME)
            log.info(
                "Vector store ready: {path} ({n} vectors)",
                path=CHROMA_DIR,
                n=_collection.count(),
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            _broken = True
            log.warning("Vector store unavailable, lexical fallback active: {exc}", exc=exc)
            return None
    return _collection


def _metadata_for(doc: DataDocument) -> dict[str, Any]:
    """Chroma metadata must be flat str/int/float/bool values."""
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "source": doc.source,
        "difficulty": doc.difficulty or "",
        "number": doc.number if doc.number is not None else -1,
        "tags": ",".join(doc.tags),
    }


def build_index() -> int:
    """
    Index every knowledge-base document (idempotent).

    Skips work when the collection already holds at least as many vectors
    as there are documents. Delete ``backend/data/chroma`` to force a full
    rebuild after changing KB content. Returns the collection size.
    """
    col = _get_collection()
    if col is None:
        return 0
    docs = get_knowledge_base().documents
    if not docs:
        return 0
    try:
        if col.count() >= len(docs):
            return col.count()
        col.upsert(
            ids=[d.doc_id for d in docs],
            documents=[d.index_text for d in docs],
            metadatas=[_metadata_for(d) for d in docs],
        )
        log.info("Vector index built: {n} documents", n=col.count())
        return col.count()
    except Exception as exc:  # pragma: no cover - environment dependent
        log.warning("Vector index build failed, lexical fallback active: {exc}", exc=exc)
        return 0


def semantic_search(query: str, top_k: int = 5) -> list[tuple[str, float]]:
    """
    Return ``[(doc_id, cosine_distance), ...]`` best-first.

    Results beyond :data:`MAX_DISTANCE` are filtered out. Returns an empty
    list whenever the store is disabled, empty or erroring — callers are
    expected to fall back to lexical retrieval.
    """
    col = _get_collection()
    if col is None or not query.strip():
        return []
    try:
        total = col.count()
        if total == 0:
            return []
        res = col.query(query_texts=[query], n_results=min(top_k, total))
    except Exception as exc:  # pragma: no cover - environment dependent
        log.warning("Semantic query failed, lexical fallback active: {exc}", exc=exc)
        return []

    ids = (res.get("ids") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    return [
        (doc_id, distance)
        for doc_id, distance in zip(ids, distances)
        if distance <= MAX_DISTANCE
    ]
