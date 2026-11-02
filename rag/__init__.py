"""RAG completo de InfoSport (Project Break 1) adaptado como módulo del agente.

Pipeline offline: load → chunk → embed → index (Chroma).
Consulta: retrieve top-k → generación anclada al contexto → abstención si no hay evidencia.
"""
from rag.logic import rag_ask, responder

__all__ = ["rag_ask", "responder", "preparar", "indexar"]


def preparar() -> None:
    """load → chunk → embed (offline, reanudable)."""
    from rag.chunk import crear_chunks, guardar_chunks
    from rag.embed import ejecutar_embeddings
    from rag.load import cargar_documentos

    docs = cargar_documentos()
    chunks = crear_chunks(docs)
    guardar_chunks(chunks)
    print(f"{len(docs)} documentos → {len(chunks)} chunks")
    ejecutar_embeddings()


def indexar() -> int:
    from rag.index import indexar as _indexar

    return _indexar()
