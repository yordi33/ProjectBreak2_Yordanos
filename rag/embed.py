"""Embeddings con gemini-embedding-001 por lotes, con reintento ante límites de cuota (429)."""
from __future__ import annotations

import re
import time

import joblib

from config import EMBED_BATCH_SIZE, EMBEDDING_MODEL, EMBEDDINGS_FILE
from gemini_auth import get_client
from rag.chunk import cargar_chunks


def _embed_lote(textos: list[str], task_type: str) -> list[list[float]]:
    client = get_client()
    for intento in range(8):
        try:
            r = client.models.embed_content(
                model=EMBEDDING_MODEL, contents=textos, config={"task_type": task_type}
            )
            return [list(e.values) for e in r.embeddings]
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            transitorio = any(t in msg for t in ("429", "503", "RESOURCE_EXHAUSTED", "10053", "10054", "timed out"))
            if not transitorio and not isinstance(e, (ConnectionError, OSError)) and "Connect" not in type(e).__name__:
                raise
            m = re.search(r"retry in (\d+(?:\.\d+)?)s", msg) or re.search(r"'retryDelay': '(\d+)s'", msg)
            espera = float(m.group(1)) + 1 if m else 15 * (intento + 1)
            print(f"  cuota/servicio ocupado, espero {espera:.0f}s…", flush=True)
            time.sleep(espera)
    raise RuntimeError("No se pudieron generar embeddings tras varios reintentos")


def embed_textos(textos: list[str]) -> list[list[float]]:
    vectores: list[list[float]] = []
    for i in range(0, len(textos), EMBED_BATCH_SIZE):
        vectores.extend(_embed_lote(textos[i : i + EMBED_BATCH_SIZE], "RETRIEVAL_DOCUMENT"))
    return vectores


def embed_pregunta(pregunta: str) -> list[float]:
    return _embed_lote([pregunta.strip()], "RETRIEVAL_QUERY")[0]


def ejecutar_embeddings() -> list[dict]:
    """Embebe todos los chunks y los guarda en output/embeddings.joblib (reanudable)."""
    chunks = cargar_chunks()
    previos: dict[str, list[float]] = {}
    if EMBEDDINGS_FILE.exists():  # reaprovecha vectores ya calculados (mismo texto)
        previos = {it["text"]: it["vector"] for it in joblib.load(EMBEDDINGS_FILE)["items"]}
    pendientes = [c["text"] for c in chunks if c["text"] not in previos]
    print(f"Chunks: {len(chunks)} · ya embebidos: {len(chunks) - len(pendientes)} · pendientes: {len(pendientes)}")
    for i in range(0, len(pendientes), EMBED_BATCH_SIZE):
        bloque = pendientes[i : i + EMBED_BATCH_SIZE]
        previos.update(zip(bloque, embed_textos(bloque)))
        print(f"  progreso {len(chunks) - len(pendientes) + i + len(bloque)}/{len(chunks)}", flush=True)
        _guardar(chunks, previos)  # checkpoint parcial por si se corta
    items = _guardar(chunks, previos)
    print(f"Embeddings guardados en {EMBEDDINGS_FILE} ({len(items)} vectores)")
    return items


def _guardar(chunks: list[dict], vectores: dict[str, list[float]]) -> list[dict]:
    items = [
        {"text": c["text"], "metadata": c["metadata"], "vector": vectores[c["text"]]}
        for c in chunks
        if c["text"] in vectores
    ]
    EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"embedding_model": EMBEDDING_MODEL, "items": items}, EMBEDDINGS_FILE, compress=3)
    return items
