"""Lightweight local vector store (numpy + joblib), namespaced per business.

Each business gets its own index file: rag_index_{business_id}.pkl.
Public interface mirrors a minimal vector store: upsert / query / reset / count.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np

MODEL_DIR = os.environ.get("ML_MODELS_DIR", "/app/ml_models")

# Process-local cache keyed by business_id. Each entry holds {store, mtime}.
_cache: dict[int, dict] = {}


def _index_path(business_id: int) -> str:
    return os.path.join(MODEL_DIR, f"rag_index_{business_id}.pkl")


def _empty() -> dict:
    return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}


def _load(business_id: int) -> dict:
    import joblib

    path = _index_path(business_id)
    entry = _cache.get(business_id, {"store": None, "mtime": None})

    if not os.path.exists(path):
        if entry["store"] is None:
            entry = {"store": _empty(), "mtime": None}
            _cache[business_id] = entry
        return entry["store"]

    mtime = os.path.getmtime(path)
    if entry["store"] is None or entry["mtime"] != mtime:
        entry = {"store": joblib.load(path), "mtime": mtime}
        _cache[business_id] = entry
    return entry["store"]


def _save(business_id: int, store: dict) -> None:
    import joblib

    path = _index_path(business_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(store, path)
    _cache[business_id] = {"store": store, "mtime": os.path.getmtime(path)}


def reset_collection(business_id: int) -> None:
    """Drop everything for this business so a re-index starts clean."""
    _save(business_id, _empty())


def upsert(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
    business_id: int = 1,
) -> None:
    if not ids:
        return
    store = _load(business_id)
    pos = {doc_id: i for i, doc_id in enumerate(store["ids"])}
    for doc_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
        emb = list(map(float, emb))
        if doc_id in pos:
            i = pos[doc_id]
            store["embeddings"][i] = emb
            store["documents"][i] = doc
            store["metadatas"][i] = meta
        else:
            pos[doc_id] = len(store["ids"])
            store["ids"].append(doc_id)
            store["embeddings"].append(emb)
            store["documents"].append(doc)
            store["metadatas"].append(meta)
    _save(business_id, store)


def query(embedding: list[float], n_results: int = 5, business_id: int = 1) -> list[dict]:
    """Return the nearest stored chunks by cosine similarity for this business."""
    store = _load(business_id)
    if not store["embeddings"]:
        return []

    matrix = np.asarray(store["embeddings"], dtype=np.float32)
    q = np.asarray(embedding, dtype=np.float32)

    matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12)
    q_norm = q / (np.linalg.norm(q) + 1e-12)
    sims = matrix_norm @ q_norm

    top = np.argsort(-sims)[:n_results]
    hits: list[dict] = []
    for i in top:
        i = int(i)
        hits.append({
            "id": store["ids"][i],
            "document": store["documents"][i],
            "metadata": store["metadatas"][i],
            "distance": float(1.0 - sims[i]),
        })
    return hits


def count(business_id: int = 1) -> int:
    return len(_load(business_id)["ids"])
