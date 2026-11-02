from __future__ import annotations

import json
import time
from datetime import datetime

from config import MAX_PREGUNTA, RAG_LOG_JSON, TEMPERATURE_RAG, TOP_K
from rag.generate import construir_contexto, construir_prompt
from rag.retrieve import buscar
from src.llm import LLMError, generar_json


def _resultado(**kw) -> dict:
    base = {"respuesta": "", "hay_evidencia": False, "fuentes": [], "chunks": [], "error": None, "modelo": None}
    base.update(kw)
    return base


def responder(pregunta: str, top_k: int | None = None) -> dict:
    t0 = time.perf_counter()
    pregunta = (pregunta or "").strip()
    top_k = top_k or TOP_K
    if not pregunta:
        return _resultado(error="La pregunta no puede estar vacía")
    if len(pregunta) > MAX_PREGUNTA:
        return _resultado(error=f"La pregunta supera {MAX_PREGUNTA} caracteres")
    try:
        chunks = buscar(pregunta, top_k)
    except Exception as e:
        return _resultado(error=f"Fallo en la recuperación: {e}")
    if not chunks:
        return _resultado(respuesta="No hay fragmentos en el índice.", error="índice vacío")
    try:
        datos, modelo = generar_json(construir_prompt(construir_contexto(chunks), pregunta), temperature=TEMPERATURE_RAG)
    except LLMError as e:
        return _resultado(chunks=chunks, error=str(e))
    out = _resultado(
        respuesta=str(datos.get("respuesta", "")),
        hay_evidencia=bool(datos.get("hay_evidencia", False)),
        fuentes=list(datos.get("fuentes_citadas", []) or []),
        chunks=chunks,
        modelo=modelo,
        latencia_s=round(time.perf_counter() - t0, 2),
        top_k=top_k,
    )
    _log(pregunta, out)
    return out


def rag_ask(pregunta: str, top_k: int | None = None) -> str:
    r = responder(pregunta, top_k)
    if r["error"]:
        return f"[RAG ERROR] {r['error']}"
    if not r["hay_evidencia"]:
        return f"[SIN EVIDENCIA EN EL CORPUS] {r['respuesta']}"
    return f"{r['respuesta']}\nFuentes: {', '.join(r['fuentes']) or '—'}"


def _log(pregunta: str, r: dict) -> None:
    try:
        RAG_LOG_JSON.parent.mkdir(parents=True, exist_ok=True)
        datos = json.loads(RAG_LOG_JSON.read_text(encoding="utf-8")) if RAG_LOG_JSON.exists() else []
        datos.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pregunta": pregunta,
            "top_k": r.get("top_k"),
            "modelo": r.get("modelo"),
            "latencia_s": r.get("latencia_s"),
            "abstencion": not r["hay_evidencia"],
            "fuentes": r["fuentes"],
            "distancias": [c["distancia"] for c in r["chunks"]],
        })
        RAG_LOG_JSON.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass
