from __future__ import annotations

import json

from langchain_core.tools import tool

from rag import responder


@tool
def rag_ask(pregunta: str) -> str:
    """Consulta el RAG del corpus de deporte municipal de Madrid (reglamento de instalaciones
    deportivas municipales, Juegos Deportivos Municipales y clasificaciones por grupo).
    Devuelve la respuesta anclada al corpus, si hay evidencia y las fuentes citadas."""
    r = responder(pregunta)
    if r["error"]:
        raise RuntimeError(r["error"])
    return json.dumps(
        {
            "respuesta": r["respuesta"],
            "hay_evidencia": r["hay_evidencia"],
            "fuentes": r["fuentes"],
            "chunks": [{"source": c["source"], "distancia": c["distancia"]} for c in r["chunks"]],
        },
        ensure_ascii=False,
    )
