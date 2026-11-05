"""Registro de tools + allowlist + ejecución segura con traza.

El LLM solo *propone* {"tool": nombre, "args": {...}}; `ejecutar_tool` decide en Python
si se ejecuta: el nombre debe estar en la allowlist global y en la del especialista.
Cada llamada genera una entrada de traza (nombre, args, status, preview, ms).
"""
from __future__ import annotations

import time

from langchain_core.tools import BaseTool

from src.tools.api_dominio import buscar_polideportivos, tiempo_madrid
from src.tools.consultar_partidos import consultar_partidos
from src.tools.describir_imagen import describir_imagen
from src.tools.hora_actual import hora_actual
from src.tools.rag_ask import rag_ask

TOOLS: dict[str, BaseTool] = {
    t.name: t
    for t in (rag_ask, buscar_polideportivos, tiempo_madrid, consultar_partidos, hora_actual, describir_imagen)
}
ALLOWLIST: frozenset[str] = frozenset(TOOLS)

CATEGORIA = {
    "rag_ask": "RAG",
    "buscar_polideportivos": "API externa",
    "tiempo_madrid": "API externa",
    "consultar_partidos": "datos estructurados",
    "hora_actual": "auxiliar",
    "describir_imagen": "multimodal",
}


def describir_tools(nombres: list[str]) -> str:
    """Catálogo (nombre, descripción, args) para el prompt del especialista."""
    lineas = []
    for n in nombres:
        t = TOOLS[n]
        args = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in t.args.items()) or "sin argumentos"
        lineas.append(f"- {n}({args}): {' '.join(t.description.split())}")
    return "\n".join(lineas)


def ejecutar_tool(nombre: str, args: dict | None, permitidas: list[str] | None = None) -> dict:
    """Ejecuta una tool solo si está permitida. Nunca lanza excepción: devuelve la traza."""
    args = args if isinstance(args, dict) else {}
    traza = {"tool": nombre, "args": args, "status": "ok", "resultado": "", "preview": "", "ms": 0}
    if nombre not in ALLOWLIST:
        traza.update(status="bloqueada", resultado=f"Tool '{nombre}' no está en la allowlist")
    elif permitidas is not None and nombre not in permitidas:
        traza.update(status="bloqueada", resultado=f"Tool '{nombre}' no permitida para este especialista")
    else:
        t0 = time.perf_counter()
        try:
            traza["resultado"] = str(TOOLS[nombre].invoke(args))
        except Exception as e:  # noqa: BLE001 - el error queda en la traza, no rompe el grafo
            traza.update(status="error", resultado=f"{type(e).__name__}: {e}")
        traza["ms"] = round((time.perf_counter() - t0) * 1000)
    traza["preview"] = traza["resultado"][:160].replace("\n", " ")
    return traza
