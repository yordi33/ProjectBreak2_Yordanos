"""RAG: ingesta, chunking, validaciones y abstención (sin índice ni LLM reales)."""
import importlib
import json

import rag.logic
from config import CLASIFICACION_CSV, MAX_PREGUNTA
from rag.chunk import crear_chunks
from rag.load import cargar_clasificacion, normalizar
from src.tools import ejecutar_tool

tool_rag = importlib.import_module("src.tools.rag_ask")

CHUNKS_FALSOS = [{"id": "chunk_1", "texto": "Artículo 60...", "source": "reglamento.pdf", "distancia": 0.31}]


def test_clasificacion_un_documento_por_grupo_con_cabecera():
    docs = cargar_clasificacion(CLASIFICACION_CSV)
    assert len(docs) == 1557
    doc = next(d for d in docs if d.metadata["grupo"] == "JDM VIV MBC BEN MIX")
    assert doc.page_content.startswith("CLASIFICACIÓN del grupo JDM VIV MBC BEN MIX")
    assert "Posición 1: VALLEKAS BASKET ANGEL NIETO" in doc.page_content


def test_la_tabla_de_clasificacion_no_se_parte_en_chunks():
    docs = [d for d in cargar_clasificacion(CLASIFICACION_CSV) if d.metadata["grupo"] == "JDM VIV MBC BEN MIX"]
    chunks = crear_chunks(docs)
    assert len(chunks) == 1
    assert "cabecera" not in chunks[0].metadata
    assert "Posición 1:" in chunks[0].page_content and "Posición 8:" in chunks[0].page_content


def test_normalizar_colapsa_espacios_y_saltos():
    assert normalizar("a\r\n\n\n\nb   c\t d ") == "a\n\nb c d"


def test_pregunta_vacia_devuelve_error_sin_consultar():
    r = rag.logic.responder("   ")
    assert r["error"] and not r["hay_evidencia"]


def test_pregunta_demasiado_larga_devuelve_error():
    r = rag.logic.responder("x" * (MAX_PREGUNTA + 1))
    assert "supera" in r["error"]


def test_respuesta_con_evidencia(monkeypatch):
    monkeypatch.setattr(rag.logic, "buscar", lambda p, k=None: CHUNKS_FALSOS)
    monkeypatch.setattr(rag.logic, "generar_json", lambda prompt, temperature=0: (
        {"respuesta": "Hasta 3.000 euros.", "hay_evidencia": True, "fuentes_citadas": ["reglamento.pdf"]}, "falso"))
    r = rag.logic.responder("¿multa muy grave?")
    assert r["hay_evidencia"] and r["fuentes"] == ["reglamento.pdf"] and r["error"] is None
    assert "Fuentes: reglamento.pdf" in rag.logic.rag_ask("¿multa muy grave?")


def test_abstencion_sin_evidencia(monkeypatch):
    monkeypatch.setattr(rag.logic, "buscar", lambda p, k=None: CHUNKS_FALSOS)
    monkeypatch.setattr(rag.logic, "generar_json", lambda prompt, temperature=0: (
        {"respuesta": "El contexto no habla de calorías.", "hay_evidencia": False, "fuentes_citadas": []}, "falso"))
    assert rag.logic.rag_ask("¿calorías en las barcas?").startswith("[SIN EVIDENCIA EN EL CORPUS]")


def test_el_prompt_incluye_contexto_y_reglas_de_abstencion(monkeypatch):
    vistos = []
    monkeypatch.setattr(rag.logic, "buscar", lambda p, k=None: CHUNKS_FALSOS)

    def generar(prompt, temperature=0):
        vistos.append(prompt)
        return {"respuesta": "x", "hay_evidencia": False, "fuentes_citadas": []}, "falso"

    monkeypatch.setattr(rag.logic, "generar_json", generar)
    rag.logic.responder("pregunta")
    assert "Usa ÚNICAMENTE el contexto" in vistos[0]
    assert "fuente: reglamento.pdf" in vistos[0]


def test_fallo_de_recuperacion_se_devuelve_como_error(monkeypatch):
    def rompe(p, k=None):
        raise RuntimeError("No existe el índice")

    monkeypatch.setattr(rag.logic, "buscar", rompe)
    r = rag.logic.responder("¿algo?")
    assert "recuperación" in r["error"]


def test_tool_rag_ask_envuelve_responder(monkeypatch):
    monkeypatch.setattr(tool_rag, "responder", lambda p: {
        "respuesta": "ok", "hay_evidencia": True, "fuentes": ["f.pdf"], "chunks": CHUNKS_FALSOS, "error": None})
    datos = json.loads(ejecutar_tool("rag_ask", {"pregunta": "x"})["resultado"])
    assert datos["hay_evidencia"] and datos["chunks"][0]["source"] == "reglamento.pdf"


def test_tool_rag_ask_marca_error_en_la_traza(monkeypatch):
    monkeypatch.setattr(tool_rag, "responder", lambda p: {"error": "índice vacío"})
    assert ejecutar_tool("rag_ask", {"pregunta": "x"})["status"] == "error"
