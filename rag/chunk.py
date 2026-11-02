"""Fragmentación con RecursiveCharacterTextSplitter y persistencia en output/chunks.json."""
from __future__ import annotations

import json

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_OVERLAP, CHUNK_SIZE, CHUNKS_JSON


def crear_chunks(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata["chunk_index"] = i
    return chunks


def guardar_chunks(chunks: list[Document]) -> None:
    CHUNKS_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "total_chunks": len(chunks),
        "chunks": [{"text": c.page_content, "metadata": dict(c.metadata)} for c in chunks],
    }
    CHUNKS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def cargar_chunks() -> list[dict]:
    if not CHUNKS_JSON.exists():
        raise FileNotFoundError(f"No existe {CHUNKS_JSON}. Ejecuta antes: python main.py --prepare")
    return json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))["chunks"]
