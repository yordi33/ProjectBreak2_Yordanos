"""Orquestación: contrato único para CLI y Streamlit.

    procesar_turno(estado, mensaje, imagen=None) → ejecuta el grafo hasta la pausa HITL
    aprobar_plan(estado, aprobar, comentario)    → update_state + invoke(None) → aplicar
    run_demo(auto_aprobar)                       → recorrido guiado para la presentación

El grafo se compila una sola vez por proceso: el MemorySaver vive con él y el mismo
thread_id recupera la conversación entre turnos.
"""
from __future__ import annotations

import json
from datetime import datetime

from config import AGENT_LOG_JSONL, MAX_MENSAJE, MAX_TURNS
from src.graph import build_graph
from src.state import EstadoProducto

_GRAFO = None


def get_graph():
    global _GRAFO
    if _GRAFO is None:
        _GRAFO = build_graph()
    return _GRAFO


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}


def _marcar_hitl(estado: EstadoProducto) -> EstadoProducto:
    """Sincroniza el estado de producto con el snapshot del checkpointer."""
    snap = get_graph().get_state(_config(estado.thread_id))
    valores = snap.values or {}
    estado.hitl_pendiente = tuple(snap.next) == ("aplicar",)
    estado.done = bool(valores.get("done", False))
    # con SqliteSaver el hilo puede venir de otro proceso: se recupera el contador de turnos
    estado.turnos = max(estado.turnos, int(valores.get("turno", 0) or 0))
    estado.ultima_respuesta = valores.get("respuesta", "")
    estado.ultimo_plan = list(valores.get("plan", []))
    estado.log = list(valores.get("log", []))
    estado.trazas = list(valores.get("trazas", []))
    return estado


def _guardar_traza(estado: EstadoProducto, evento: str, extra: dict | None = None) -> None:
    try:
        AGENT_LOG_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with AGENT_LOG_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "evento": evento,
                                **estado.flags(), **(extra or {})}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def procesar_turno(estado: EstadoProducto, mensaje: str, imagen: str | None = None) -> EstadoProducto:
    estado.error = ""
    mensaje = (mensaje or "").strip()
    if not mensaje:
        estado.error = "El mensaje está vacío."
        return estado
    if len(mensaje) > MAX_MENSAJE:
        estado.error = f"El mensaje supera {MAX_MENSAJE} caracteres."
        return estado
    _marcar_hitl(estado)
    if estado.hitl_pendiente:
        estado.error = "Hay un plan pendiente de revisión: apruébalo o recházalo antes de otro pedido."
        return estado
    if estado.turnos >= MAX_TURNS:
        estado.error = f"Límite de {MAX_TURNS} turnos alcanzado: inicia una nueva conversación."
        return estado

    estado.turnos += 1
    entrada = {
        "pedido": mensaje,
        "imagen": imagen or "",
        "turno": estado.turnos,
        "notas": {},
        "visitados": [],
        "siguiente": "",
        "iteracion": 0,
        "respuesta": "",
        "plan": [],
        "decision": "",
        "comentario_humano": "",
        "done": False,
        "log": [f"── turno {estado.turnos} · thread {estado.thread_id} · pedido: {mensaje[:80]}"],
    }
    try:
        get_graph().invoke(entrada, _config(estado.thread_id))
    except Exception as e:  # noqa: BLE001 - la UI muestra el error sin romperse
        estado.error = f"Error ejecutando el grafo: {type(e).__name__}: {e}"
    _marcar_hitl(estado)
    if estado.hitl_pendiente:
        estado.log.append("[HITL] grafo en pausa antes de 'aplicar' (interrupt_before) → esperando decisión humana")
    _guardar_traza(estado, "turno", {"pedido": mensaje, "plan": estado.ultimo_plan,
                                     "tools": [t["tool"] for t in estado.trazas if t.get("turno") == estado.turnos]})
    return estado


def aprobar_plan(estado: EstadoProducto, aprobar: bool, comentario: str = "") -> EstadoProducto:
    estado.error = ""
    _marcar_hitl(estado)
    if not estado.hitl_pendiente:
        estado.error = "No hay ningún plan pendiente de aprobación."
        return estado
    cfg = _config(estado.thread_id)
    grafo = get_graph()
    grafo.update_state(cfg, {"decision": "aprobar" if aprobar else "rechazar", "comentario_humano": comentario})
    try:
        grafo.invoke(None, cfg)  # reanuda desde el interrupt → ejecuta 'aplicar'
    except Exception as e:  # noqa: BLE001
        estado.error = f"Error al aplicar la decisión: {type(e).__name__}: {e}"
    _marcar_hitl(estado)
    _guardar_traza(estado, "hitl", {"decision": "aprobar" if aprobar else "rechazar", "comentario": comentario})
    return estado


def historial(estado: EstadoProducto) -> list[dict]:
    snap = get_graph().get_state(_config(estado.thread_id))
    return list((snap.values or {}).get("historial", []))


DEMO_PEDIDOS = [
    ("Quiero ir a nadar al Centro Deportivo Municipal Moratalaz esta tarde: ¿a qué hora cierra la "
     "taquilla, cómo llego en metro y qué normas del reglamento debo cumplir como usuario?", None, True),
    ("¿Qué equipo quedó primero en la clasificación del grupo JDM VIV MBC BEN MIX y hace buen tiempo hoy "
     "para jugar al aire libre?", None, False),
    ("Lee este cartel y dime qué horario tiene la taquilla y qué días cierra el centro.", "assets/imagen_demo.png", True),
]
