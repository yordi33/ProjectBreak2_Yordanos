"""Índice vectorial persistente en ChromaDB (distancia coseno)."""
from __future__ import annotations

import chromadb
import joblib

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDINGS_FILE, MAX_GRUPO_CHROMA


def _client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection() -> chromadb.Collection:
    try:
        return _client().get_collection(COLLECTION_NAME)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"No existe el índice '{COLLECTION_NAME}'. Ejecuta: python main.py --prepare --index"
        ) from e


def _sanitizar(metadata: dict) -> dict:
    return {k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in metadata.items() if v is not None}


def indexar() -> int:
    if not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"No existe {EMBEDDINGS_FILE}. Ejecuta antes: python main.py --prepare")
    data = joblib.load(EMBEDDINGS_FILE)
    items, modelo = data["items"], data["embedding_model"]
    client = _client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001
        pass
    col = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    for i in range(0, len(items), MAX_GRUPO_CHROMA):
        lote = items[i : i + MAX_GRUPO_CHROMA]
        col.add(
            ids=[f"chunk_{it['metadata'].get('chunk_index', i + j)}" for j, it in enumerate(lote)],
            embeddings=[it["vector"] for it in lote],
            documents=[it["text"] for it in lote],
            metadatas=[{**_sanitizar(it["metadata"]), "embedding_model": modelo} for it in lote],
        )
    print(f"{col.count()} chunks indexados en la colección '{COLLECTION_NAME}' ({CHROMA_DIR})")
    return col.count()
