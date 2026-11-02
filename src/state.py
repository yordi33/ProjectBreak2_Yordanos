"""Estado de producto (lo que ven CLI y Streamlit), separado del estado interno del grafo."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def nuevo_thread_id() -> str:
    return f"infosport-{uuid.uuid4().hex[:8]}"


@dataclass
class EstadoProducto:
    thread_id: str = field(default_factory=nuevo_thread_id)
    turnos: int = 0
    hitl_pendiente: bool = False
    done: bool = False
    ultima_respuesta: str = ""
    ultimo_plan: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)       # log completo del hilo
    trazas: list[dict] = field(default_factory=list)   # trazas de tools del hilo
    error: str = ""

    def flags(self) -> dict:
        return {"thread_id": self.thread_id, "turnos": self.turnos,
                "hitl_pendiente": self.hitl_pendiente, "done": self.done}
