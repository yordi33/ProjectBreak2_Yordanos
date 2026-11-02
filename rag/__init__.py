from rag.logic import rag_ask, responder

__all__ = ["rag_ask", "responder", "preparar", "indexar"]


def preparar() -> None:
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
