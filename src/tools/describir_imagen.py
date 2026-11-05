"""Tool multimodal: imagen → texto con Gemini (visión).

Por seguridad solo se aceptan imágenes dentro de assets/ o output/uploads/.
"""
from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from config import ASSETS_DIR, IMAGEN_DEMO, OUTPUT_DIR
from src.llm import describir_imagen_llm

UPLOADS_DIR = OUTPUT_DIR / "uploads"
_PERMITIDAS = (ASSETS_DIR.resolve(), UPLOADS_DIR.resolve())


def _resolver(ruta: str) -> Path:
    p = Path(ruta) if ruta else IMAGEN_DEMO
    if not p.is_absolute():
        p = (ASSETS_DIR.parent / p) if p.parts and p.parts[0] in ("assets", "output") else ASSETS_DIR / p
    p = p.resolve()
    if not any(p.is_relative_to(d) for d in _PERMITIDAS):
        raise PermissionError(f"Ruta no permitida: {ruta} (solo assets/ u output/uploads/)")
    if p.suffix.lower() not in {".png", ".jpg", ".jpeg"} or not p.exists():
        raise FileNotFoundError(f"No existe la imagen {p.name} o el formato no es png/jpg")
    return p


@tool
def describir_imagen(ruta: str = "", pregunta: str = "") -> str:
    """Lee una imagen (cartel, panel informativo, folleto, horario…) y devuelve su texto y una
    descripción. `ruta`: imagen en assets/ u output/uploads/ (vacío = assets/imagen_demo.png).
    `pregunta`: qué interesa extraer de la imagen (opcional)."""
    p = _resolver(ruta)
    instruccion = (
        "Eres un lector de imágenes para un asistente de deporte municipal de Madrid. "
        "1) Transcribe el texto legible relevante (horarios, precios, direcciones, normas). "
        "2) Describe brevemente qué es la imagen. No inventes nada que no se vea. "
        + (f"3) Responde a esto usando solo la imagen: {pregunta}" if pregunta else "")
    )
    texto, modelo = describir_imagen_llm(p, instruccion)
    return f"[imagen: {p.name} · modelo: {modelo}]\n{texto}"
