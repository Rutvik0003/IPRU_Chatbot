import chromadb
from pathlib import Path

CHROMA_DIR = "data/chroma"
COLLECTION_NAME = "insurance_docs"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def is_indexed(source_file: str) -> bool:
    col = _get_collection()
    results = col.get(
        where={"source_file": {"$eq": source_file}},
        limit=1,
    )
    return len(results["ids"]) > 0


def add_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    base_metadata: dict,
):
    col = _get_collection()
    ids, docs, metas, embeds = [], [], [], []

    source_file = base_metadata.get("source_file", "")

    for chunk, emb in zip(chunks, embeddings):
        chunk_id = f"{source_file}::chunk::{chunk['index']}"
        ids.append(chunk_id)
        docs.append(chunk["text"])
        embeds.append(emb)
        metas.append({
            **base_metadata,
            "chunk_index": chunk["index"],
            "section": chunk.get("section", "general"),
            "word_count": chunk.get("word_count", 0),
        })

    if ids:
        col.add(ids=ids, embeddings=embeds, documents=docs, metadatas=metas)


def query(
    query_embedding: list[float],
    top_k: int = 8,
    where: dict = None,
) -> list[dict]:
    col = _get_collection()
    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    results = col.query(**kwargs)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": doc,
            "metadata": meta,
            "score": round(1 - dist, 4),  # cosine similarity
        })
    return hits


def delete_source(source_file: str):
    col = _get_collection()
    col.delete(where={"source_file": {"$eq": source_file}})


def count() -> int:
    return _get_collection().count()
