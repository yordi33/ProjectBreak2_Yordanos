"""Tools: allowlist, traza, fallback sin red y restricciones de seguridad."""
import json

import pytest

from src.tools import ALLOWLIST, CATEGORIA, TOOLS, ejecutar_tool
from src.tools.describir_imagen import _resolver


def test_allowlist_contiene_las_seis_tools_con_categoria():
    assert ALLOWLIST == set(TOOLS)
    assert set(CATEGORIA) == set(TOOLS)
    assert {"RAG", "API externa", "auxiliar", "multimodal"} <= set(CATEGORIA.values())


def test_tool_fuera_de_allowlist_queda_bloqueada():
    traza = ejecutar_tool("borrar_todo", {"ruta": "/"})
    assert traza["status"] == "bloqueada"
    assert "allowlist" in traza["resultado"]


def test_tool_valida_pero_no_permitida_al_especialista_queda_bloqueada():
    traza = ejecutar_tool("rag_ask", {"pregunta": "x"}, permitidas=["hora_actual"])
    assert traza["status"] == "bloqueada"
    assert "no permitida" in traza["resultado"]


def test_traza_tiene_los_campos_esperados():
    traza = ejecutar_tool("hora_actual", {})
    assert traza["status"] == "ok"
    assert set(traza) >= {"tool", "args", "status", "resultado", "preview", "ms"}
    assert len(traza["preview"]) <= 160


def test_error_de_una_tool_no_lanza_excepcion():
    traza = ejecutar_tool("describir_imagen", {"ruta": "../config.py"})
    assert traza["status"] == "error"
    assert "PermissionError" in traza["resultado"]


def test_args_no_dict_se_tratan_como_vacios():
    traza = ejecutar_tool("hora_actual", "no soy un dict")
    assert traza["status"] == "ok"


def test_hora_actual_devuelve_fecha_hora_y_dia():
    datos = json.loads(ejecutar_tool("hora_actual", {})["resultado"])
    assert datos["zona"] == "Europe/Madrid"
    assert len(datos["fecha"]) == 10 and len(datos["hora"]) == 5
    assert datos["dia_semana"] in {"lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"}


def test_consultar_partidos_encuentra_partido_concreto():
    traza = ejecutar_tool("consultar_partidos", {"equipo": "pechetings", "fecha": "2026-01-31"})
    datos = json.loads(traza["resultado"])
    assert datos["total_coincidencias"] == 1
    partido = datos["partidos"][0]
    assert partido["local"] == "PECHETINGS FC"
    assert partido["estado"] == "Finalizado"
    assert str(partido["coord_y"]).startswith("40.394")


def test_consultar_partidos_filtra_por_estado_y_limita_resultados():
    datos = json.loads(ejecutar_tool("consultar_partidos", {"estado": "suspendido", "max_resultados": 3})["resultado"])
    assert datos["total_coincidencias"] > 3
    assert len(datos["partidos"]) == 3
    assert all(p["estado"] == "Suspendido" for p in datos["partidos"])


def test_buscar_polideportivos_usa_fallback_sin_red(sin_red):
    datos = json.loads(ejecutar_tool("buscar_polideportivos", {"texto": "moratalaz"})["resultado"])
    assert datos["origen"] == "fallback"
    assert datos["resultados"][0]["nombre"] == "Centro Deportivo Municipal Moratalaz"
    assert "Pavones" in datos["resultados"][0]["transporte"]


def test_buscar_polideportivos_filtra_por_distrito(sin_red):
    datos = json.loads(ejecutar_tool("buscar_polideportivos", {"distrito": "Retiro", "max_resultados": 10})["resultado"])
    assert datos["total_encontrados"] >= 1
    assert all(r["distrito"] == "Retiro" for r in datos["resultados"])


def test_tiempo_madrid_marca_el_fallback_como_no_actual(sin_red):
    datos = json.loads(ejecutar_tool("tiempo_madrid", {})["resultado"])
    assert "NO actuales" in datos["origen"]
    assert {"temperatura_c", "cielo", "prob_lluvia_hoy_pct"} <= set(datos)


@pytest.mark.parametrize("ruta", ["../config.py", "C:/Windows/win.ini", "/etc/passwd", "../../.env"])
def test_describir_imagen_rechaza_rutas_fuera_de_assets(ruta):
    with pytest.raises((PermissionError, FileNotFoundError)):
        _resolver(ruta)


def test_describir_imagen_acepta_la_imagen_demo():
    assert _resolver("").name == "imagen_demo.png"
    assert _resolver("assets/imagen_demo.png").name == "imagen_demo.png"
