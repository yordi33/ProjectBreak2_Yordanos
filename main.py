from __future__ import annotations

import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from config import IMAGEN_DEMO


def _imprimir_turno(estado, desde: int) -> int:
    for linea in estado.log[desde:]:
        print(f"  {linea}")
    if estado.error:
        print(f"\n⚠️  {estado.error}")
    if estado.ultima_respuesta:
        print(f"\n🤖 {estado.ultima_respuesta}")
    if estado.ultimo_plan:
        print("\n📋 Plan propuesto:")
        for p in estado.ultimo_plan:
            print(f"   • {p}")
    return len(estado.log)


def _imprimir_tools(estado) -> None:
    trazas = [t for t in estado.trazas if t.get("turno") == estado.turnos]
    if trazas:
        print("\n🔧 Traza de tools:")
        for t in trazas:
            print(f"   [{t['especialista']}] {t['tool']} {t['status']} {t['ms']}ms · {t['preview'][:110]}")


def _decidir(estado, auto: bool | None, comentario_auto: str = ""):
    from src.agent import aprobar_plan

    if auto is not None:
        aprobar, comentario = auto, comentario_auto
        print(f"\n🧑 HITL (auto): {'APROBAR' if aprobar else 'RECHAZAR'}")
    else:
        r = input("\n🧑 HITL · ¿[a]probar o [r]echazar el plan? ").strip().lower()
        aprobar = r.startswith("a")
        comentario = input("   comentario (opcional): ").strip()
    n = len(estado.log)
    aprobar_plan(estado, aprobar, comentario)
    _imprimir_turno_hitl(estado, n)


def _imprimir_turno_hitl(estado, desde: int) -> None:
    for linea in estado.log[desde:]:
        print(f"  {linea}")
    print(f"  flags: {estado.flags()}")


def run_demo(auto_aprobar: bool) -> None:
    from src.agent import DEMO_PEDIDOS, procesar_turno
    from src.state import EstadoProducto

    estado = EstadoProducto()
    print(f"=== DEMO InfoSport Agente · thread_id={estado.thread_id} ===")
    for pedido, imagen, aprobar in DEMO_PEDIDOS:
        print(f"\n\n👤 {pedido}" + (f"  [imagen: {imagen}]" if imagen else ""))
        n = len(estado.log)
        procesar_turno(estado, pedido, imagen=imagen)
        _imprimir_turno(estado, n)
        _imprimir_tools(estado)
        if estado.hitl_pendiente:
            comentario = "" if aprobar else "Prefiero otro plan: pregunto otra cosa"
            _decidir(estado, aprobar if auto_aprobar else None, comentario)
    print(f"\n=== FIN DEMO · {estado.turnos} turnos en el mismo thread_id={estado.thread_id} ===")


def run_chat() -> None:
    from src.agent import historial, procesar_turno
    from src.state import EstadoProducto

    estado = EstadoProducto()
    imagen = None
    print(f"InfoSport Agente · thread_id={estado.thread_id}")
    print("Comandos: /imagen [ruta] adjunta imagen (por defecto la demo) · /nueva · /historial · /salir\n")
    while True:
        try:
            msg = input("👤 ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg in ("/salir", "/exit"):
            break
        if msg == "/nueva":
            estado, imagen = EstadoProducto(), None
            print(f"Nueva conversación · thread_id={estado.thread_id}")
            continue
        if msg == "/historial":
            print(json.dumps(historial(estado), ensure_ascii=False, indent=1))
            continue
        if msg.startswith("/imagen"):
            imagen = msg.split(maxsplit=1)[1] if " " in msg else str(IMAGEN_DEMO.relative_to(IMAGEN_DEMO.parents[1]))
            print(f"📎 imagen adjunta al próximo mensaje: {imagen}")
            continue
        n = len(estado.log)
        procesar_turno(estado, msg, imagen=imagen)
        imagen = None
        _imprimir_turno(estado, n)
        _imprimir_tools(estado)
        if estado.hitl_pendiente:
            _decidir(estado, None)


def main() -> None:
    ap = argparse.ArgumentParser(description="InfoSport Agente — LangGraph multiagente + RAG + HITL")
    ap.add_argument("--prepare", action="store_true", help="RAG: load → chunk → embed")
    ap.add_argument("--index", action="store_true", help="RAG: crear índice Chroma")
    ap.add_argument("--rag", type=str, help="Pregunta directa al RAG (sin agente)")
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--tool", type=str, help="Ejecutar una tool aislada")
    ap.add_argument("--args", type=str, default="{}", help="Args JSON para --tool")
    ap.add_argument("--demo", action="store_true", help="Demo guiada del agente")
    ap.add_argument("--auto", action="store_true", help="Con --demo: decisiones HITL automáticas")
    ap.add_argument("--chat", action="store_true", help="Modo interactivo con HITL manual")
    a = ap.parse_args()

    if not any([a.prepare, a.index, a.rag, a.tool, a.demo, a.chat]):
        ap.print_help()
        return
    if a.prepare or a.index:
        import rag

        if a.prepare:
            rag.preparar()
        if a.index:
            rag.indexar()
    if a.rag:
        from rag import responder

        r = responder(a.rag, a.top_k)
        print(json.dumps({k: v for k, v in r.items() if k != "chunks"}, ensure_ascii=False, indent=1))
        for c in r["chunks"]:
            print(f"  · {c['source']} (dist {c['distancia']}): {c['texto'][:120]!r}")
    if a.tool:
        from src.tools import ejecutar_tool

        print(json.dumps(ejecutar_tool(a.tool, json.loads(a.args)), ensure_ascii=False, indent=1))
    if a.demo:
        run_demo(auto_aprobar=a.auto)
    if a.chat:
        run_chat()


if __name__ == "__main__":
    main()
