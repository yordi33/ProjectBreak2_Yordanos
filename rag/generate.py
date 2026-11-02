from __future__ import annotations

from config import RAG_BEHAVIOUR


def construir_contexto(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"--- Fragmento {i} (fuente: {c['source']}, distancia={c['distancia']}) ---\n{c['texto']}"
        for i, c in enumerate(chunks, 1)
    )


def construir_prompt(contexto: str, pregunta: str) -> str:
    return (
        f"{RAG_BEHAVIOUR}\n\n--- CONTEXTO RECUPERADO ---\n{contexto}\n\n"
        f"--- PREGUNTA ---\n{pregunta.strip()}\n\n--- JSON ---"
    )
