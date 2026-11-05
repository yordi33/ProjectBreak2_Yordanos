"""Grafo: enrutado, límites en Python, fallbacks, HITL y persistencia por thread_id."""
import pytest

import src.graph
from config import MAX_ITER, MAX_STEPS
from src.agent import aprobar_plan, historial, procesar_turno
from src.graph import ruta_fallback, supervisor, tool_por_defecto
from src.state import EstadoProducto


@pytest.mark.parametrize("pedido, esperado", [
    ("¿Qué multa hay por una infracción?", "especialista_normativa"),
    ("¿A qué hora abre el polideportivo de Retiro?", "especialista_instalaciones"),
    ("Lee este cartel", "especialista_imagen"),
    ("hola", "especialista_normativa"),
])
def test_ruta_fallback_por_palabras_clave(pedido, esperado):
    assert ruta_fallback({"pedido": pedido, "visitados": []}) == esperado


def test_ruta_fallback_prioriza_la_imagen_adjunta():
    assert ruta_fallback({"pedido": "¿qué pone?", "imagen": "assets/imagen_demo.png", "visitados": []}) == "especialista_imagen"


def test_ruta_fallback_sintetiza_si_ya_se_visito_todo():
    estado = {"pedido": "multa en el polideportivo", "visitados": ["especialista_normativa", "especialista_instalaciones"]}
    assert ruta_fallback(estado) == "sintetizar"


def test_supervisor_corrige_una_eleccion_invalida_del_llm(monkeypatch):
    monkeypatch.setattr(src.graph, "generar_json", lambda p, temperature=0: ({"siguiente": "borrar_base_de_datos"}, "falso"))
    salida = supervisor({"pedido": "¿qué multa hay?", "visitados": [], "notas": {}})
    assert salida["siguiente"] == "especialista_normativa"
    assert "fallback determinista" in salida["log"][0]


def test_supervisor_no_sintetiza_sin_notas(monkeypatch):
    monkeypatch.setattr(src.graph, "generar_json", lambda p, temperature=0: ({"siguiente": "sintetizar"}, "falso"))
    salida = supervisor({"pedido": "¿horario del polideportivo?", "visitados": [], "notas": {}})
    assert salida["siguiente"] == "especialista_instalaciones"


def test_supervisor_respeta_max_iter():
    salida = supervisor({"pedido": "x", "iteracion": MAX_ITER, "notas": {"a": "b"}})
    assert salida["siguiente"] == "sintetizar"
    assert "MAX_ITER" in salida["log"][0]


def test_supervisor_cierra_cuando_ya_hay_plan():
    assert supervisor({"plan": ["paso"], "iteracion": 2})["siguiente"] == "FINISH"


def test_tool_por_defecto_de_cada_especialista():
    assert tool_por_defecto("especialista_normativa", {"pedido": "multa"})[0] == "rag_ask"
    assert tool_por_defecto("especialista_imagen", {"pedido": "x", "imagen": "a.png"})[0] == "describir_imagen"
    assert tool_por_defecto("especialista_instalaciones", {"pedido": "¿lloverá hoy?"})[0] == "tiempo_madrid"
    assert tool_por_defecto("especialista_instalaciones", {"pedido": "partidos suspendidos"})[0] == "consultar_partidos"


def test_turno_completo_pausa_en_hitl(llm_falso):
    estado = procesar_turno(EstadoProducto(), "¿Qué hora es? quiero ir al polideportivo")
    assert estado.error == ""
    assert estado.hitl_pendiente and not estado.done
    assert estado.ultimo_plan == ["Paso 1", "Paso 2"]
    assert [t["tool"] for t in estado.trazas] == ["hora_actual"]
    assert estado.trazas[0]["especialista"] == "especialista_instalaciones"
    assert any("interrupt_before" in linea for linea in estado.log)


def test_aprobar_cierra_con_done(llm_falso):
    estado = procesar_turno(EstadoProducto(), "¿horario del polideportivo?")
    aprobar_plan(estado, True, "ok")
    assert estado.done and not estado.hitl_pendiente
    assert historial(estado)[-1]["decision"] == "aprobar"


def test_rechazar_permite_seguir_en_el_mismo_hilo(llm_falso):
    estado = procesar_turno(EstadoProducto(), "¿horario del polideportivo?")
    thread = estado.thread_id
    aprobar_plan(estado, False, "no me convence")
    assert not estado.done and not estado.hitl_pendiente and estado.ultimo_plan == []
    procesar_turno(estado, "¿y mañana a qué hora abre el polideportivo?")
    aprobar_plan(estado, True)
    assert estado.thread_id == thread and estado.turnos == 2
    assert [h["decision"] for h in historial(estado)] == ["rechazar", "aprobar"]


def test_no_acepta_otro_pedido_con_plan_pendiente(llm_falso):
    estado = procesar_turno(EstadoProducto(), "¿horario del polideportivo?")
    procesar_turno(estado, "otra pregunta")
    assert "pendiente" in estado.error and estado.turnos == 1


def test_validaciones_del_contrato():
    assert "vacío" in procesar_turno(EstadoProducto(), "   ").error
    assert "supera" in procesar_turno(EstadoProducto(), "x" * 501).error
    assert "No hay ningún plan" in aprobar_plan(EstadoProducto(), True).error


def test_hilos_distintos_no_comparten_estado(llm_falso):
    a = procesar_turno(EstadoProducto(), "¿horario del polideportivo?")
    b = EstadoProducto()
    assert a.thread_id != b.thread_id
    assert historial(b) == []
    assert procesar_turno(b, "¿y en Retiro?").error == ""


def test_max_steps_corta_las_llamadas_a_tools(monkeypatch):
    from tests.conftest import LLMFalso

    monkeypatch.setattr(src.graph, "generar_json", LLMFalso(siempre_tool=True))
    estado = procesar_turno(EstadoProducto(), "¿horario del polideportivo?")
    assert len(estado.trazas) == MAX_STEPS
    assert any(f"MAX_STEPS={MAX_STEPS}" in linea for linea in estado.log)


def test_tool_no_permitida_propuesta_por_el_llm_queda_bloqueada(monkeypatch):
    from tests.conftest import LLMFalso

    monkeypatch.setattr(src.graph, "generar_json", LLMFalso(tool_instalaciones="rag_ask", args={"pregunta": "x"}))
    estado = procesar_turno(EstadoProducto(), "¿horario del polideportivo?")
    assert estado.trazas[0]["tool"] == "rag_ask"
    assert estado.trazas[0]["status"] == "bloqueada"


def test_sin_llm_el_grafo_sigue_con_fallbacks_y_datos_reales(llm_caido, sin_red):
    estado = procesar_turno(EstadoProducto(), "¿Va a llover hoy? quiero ir al polideportivo")
    assert estado.hitl_pendiente
    assert estado.trazas[0]["tool"] == "tiempo_madrid"
    assert estado.trazas[0]["status"] == "ok"
    assert any("fallback determinista" in linea for linea in estado.log)
    assert estado.ultimo_plan
