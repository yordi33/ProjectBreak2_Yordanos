"""Envoltorio mínimo sobre Gemini: texto, JSON y visión, con fallback de modelos.

Si un modelo devuelve 503/429/404 se reintenta y después se prueba el siguiente de
config.GEMINI_MODELS. Así el grafo no depende de la disponibilidad de un único modelo.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from google.genai import types

from config import GEMINI_MODELS, LLM_REINTENTOS, VISION_MODELS
from gemini_auth import get_client

_TRANSITORIOS = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "500", "INTERNAL", "deadline", "10053", "10054", "timed out", "Connection")


class LLMError(RuntimeError):
    pass


def _llamar(contents, *, temperature: float, json_mode: bool, modelos: list[str]) -> tuple[str, str]:
    client = get_client()
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json" if json_mode else None,
    )
    ultimo_error = None
    for modelo in modelos:
        for intento in range(LLM_REINTENTOS + 1):
            try:
                r = client.models.generate_content(model=modelo, contents=contents, config=cfg)
                return (r.text or "").strip(), modelo
            except Exception as e:  # noqa: BLE001 - se clasifica por el texto del error
                ultimo_error = e
                msg = str(e)
                if "404" in msg or "NOT_FOUND" in msg:
                    break  # modelo no disponible: siguiente modelo
                if any(t in msg for t in _TRANSITORIOS) and intento < LLM_REINTENTOS:
                    time.sleep(1.5 * (intento + 1))
                    continue
                break
    raise LLMError(f"Ningún modelo respondió ({', '.join(modelos)}): {ultimo_error}")


def generar_texto(prompt: str, *, temperature: float = 0.2) -> tuple[str, str]:
    return _llamar(prompt, temperature=temperature, json_mode=False, modelos=GEMINI_MODELS)


def parse_json(texto: str) -> dict:
    t = texto.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def generar_json(prompt: str, *, temperature: float = 0.0) -> tuple[dict, str]:
    texto, modelo = _llamar(prompt, temperature=temperature, json_mode=True, modelos=GEMINI_MODELS)
    try:
        return parse_json(texto), modelo
    except json.JSONDecodeError as e:
        raise LLMError(f"El modelo no devolvió JSON válido: {texto[:200]}") from e


def describir_imagen_llm(ruta: Path, instruccion: str) -> tuple[str, str]:
    mime = "image/png" if ruta.suffix.lower() == ".png" else "image/jpeg"
    parte = types.Part.from_bytes(data=ruta.read_bytes(), mime_type=mime)
    return _llamar([parte, instruccion], temperature=0.1, json_mode=False, modelos=VISION_MODELS)
