"""
Milestone 4 (part 1) — Embed chunks and load them into ChromaDB.

Runs the ingestion pipeline, embeds every chunk locally with all-MiniLM-L6-v2, and stores the
vectors in a persistent ChromaDB collection together with {source, chunk_index} metadata so
retrieval can attribute each answer to its source document.

Run:  python build_index.py        (rebuilds the index from scratch)
"""

from __future__ import annotations

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import build_chunks

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_DIR = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "unofficial_guide"

# module-level singletons so query.py reuses the loaded model / client
_model: SentenceTransformer | None = None
_client: chromadb.ClientAPI | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def build_index() -> int:
    """(Re)build the vector store from the documents folder. Returns the chunk count."""
    chunks = build_chunks()
    model = get_model()
    client = get_client()

    # start clean so re-running doesn't duplicate or leave stale chunks
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine distance suits sentence embeddings
    )

    texts = [c.text for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    collection.add(
        ids=[c.id for c in chunks],
        documents=texts,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=[{"source": c.source, "chunk_index": c.chunk_index} for c in chunks],
    )

    print(f"\nIndexed {len(chunks)} chunks into ChromaDB collection '{COLLECTION_NAME}'")
    print(f"Persisted at: {CHROMA_DIR}")
    return len(chunks)


def get_collection() -> chromadb.Collection:
    """Open the existing collection (used by query.py). Build it first if missing."""
    client = get_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            "Vector store not found. Run `python build_index.py` first."
        ) from exc


if __name__ == "__main__":
    build_index()
