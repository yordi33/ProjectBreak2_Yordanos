"""Fixtures comunes: sin red, sin cuota de Gemini y sin escribir en output/."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import rag.logic  # noqa: E402
import src.agent  # noqa: E402
import src.graph  # noqa: E402
from src.llm import LLMError  # noqa: E402
from src.tools import api_dominio  # noqa: E402


@pytest.fixture(autouse=True)
def aislar_salidas(tmp_path, monkeypatch):
    """Los logs de cada test van a una carpeta temporal y el grafo se compila de nuevo."""
    monkeypatch.setattr(src.agent, "AGENT_LOG_JSONL", tmp_path / "agent_trazas.jsonl")
    monkeypatch.setattr(rag.logic, "RAG_LOG_JSON", tmp_path / "rag_metrics_log.json")
    monkeypatch.setattr(src.agent, "_GRAFO", None)
    api_dominio._polideportivos.cache_clear()
    yield
    api_dominio._polideportivos.cache_clear()


@pytest.fixture
def sin_red(monkeypatch):
    """Cualquier llamada HTTP de las tools de API falla, para forzar el fallback local."""
    def falla(*args, **kwargs):
        raise ConnectionError("sin red (test)")

    monkeypatch.setattr(api_dominio.requests, "get", falla)


class LLMFalso:
    """Sustituye a Gemini: responde según el tipo de prompt y guarda lo que recibe."""

    def __init__(self, tool_instalaciones="hora_actual", args=None, siempre_tool=False):
        self.tool = tool_instalaciones
        self.args = args or {}
        self.siempre_tool = siempre_tool
        self.prompts: list[str] = []

    def __call__(self, prompt, temperature=0.0):
        self.prompts.append(prompt)
        if "Eres el SUPERVISOR" in prompt:
            if "(ninguna todavía)" in prompt:
                return {"siguiente": "especialista_instalaciones", "motivo": "test"}, "falso"
            return {"siguiente": "sintetizar", "motivo": "test"}, "falso"
        if prompt.startswith("Eres especialista_"):
            if self.siempre_tool or "(todavía ninguna)" in prompt:
                return {"accion": "tool", "tool": self.tool, "args": dict(self.args)}, "falso"
            return {"accion": "terminar", "notas": "Dato obtenido con la tool (hora_actual)."}, "falso"
        if "Eres el SINTETIZADOR" in prompt:
            return {"respuesta": "Respuesta de prueba (hora_actual).", "plan": ["Paso 1", "Paso 2"]}, "falso"
        raise AssertionError(f"Prompt inesperado: {prompt[:80]}")


@pytest.fixture
def llm_falso(monkeypatch):
    falso = LLMFalso()
    monkeypatch.setattr(src.graph, "generar_json", falso)
    return falso


@pytest.fixture
def llm_caido(monkeypatch):
    def caido(prompt, temperature=0.0):
        raise LLMError("LLM no disponible (test)")

    monkeypatch.setattr(src.graph, "generar_json", caido)
