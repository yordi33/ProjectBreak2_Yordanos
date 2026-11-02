"""Recuperación top-k sobre Chroma."""
from __future__ import annotations

from config import TOP_K
from rag.embed import embed_pregunta
from rag.index import get_collection


def buscar(pregunta: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or TOP_K
    col = get_collection()
    res = col.query(
        query_embeddings=[embed_pregunta(pregunta)],
        n_results=min(top_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "id": res["ids"][0][i],
            "texto": res["documents"][0][i],
            "source": res["metadatas"][0][i].get("source", "?"),
            "distancia": round(res["distances"][0][i], 4),
        }
        for i in range(len(res["ids"][0]))
    ]
