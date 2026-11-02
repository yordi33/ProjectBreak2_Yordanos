"""Genera assets/imagen_demo.png: panel informativo de un centro deportivo municipal.

Los textos del panel salen del open data de polideportivos (data/fallback/polideportivos.json,
copia de datos.madrid.es), así la tool multimodal lee datos reales y verificables.
Uso: python scripts/crear_imagen_demo.py
"""
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from config import FALLBACK_DIR, IMAGEN_DEMO  # noqa: E402

CENTRO = "Centro Deportivo Municipal Moratalaz"


def _fuente(tam: int, negrita: bool = False):
    for nombre in (("arialbd.ttf" if negrita else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    datos = json.loads((FALLBACK_DIR / "polideportivos.json").read_text(encoding="utf-8"))["@graph"]
    p = next(x for x in datos if x["title"] == CENTRO)
    adr, org = p["address"], p["organization"]
    horario = " ".join(org["schedule"].split())
    taquilla = horario.split("Horario de taquilla")[1].split("Cierre completo")[0].strip()
    cierre = horario.split("Cierre completo del centro")[1].strip()
    metro = " ".join(org["organization-desc"].split()).split("Bicicleta")[0].strip()

    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "#F0FDFA")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 130], fill="#0F766E")
    d.text((50, 30), "INFOSPORT · FICHA DE INSTALACIÓN DEPORTIVA (demo)", font=_fuente(26), fill="white")
    d.text((50, 68), CENTRO.upper(), font=_fuente(40, True), fill="white")

    y = 170
    bloques = [
        ("DIRECCIÓN", f"{adr['street-address']}, {adr['postal-code']} Madrid · Distrito Moratalaz"),
        ("HORARIO DE TAQUILLA", taquilla),
        ("CIERRE COMPLETO DEL CENTRO", cierre),
        ("CÓMO LLEGAR", metro),
        ("ACCESIBILIDAD", "Centro accesible para personas con movilidad reducida" if org.get("accesibility") == "1" else "Consultar en el centro"),
    ]
    for titulo, texto in bloques:
        d.text((50, y), titulo, font=_fuente(26, True), fill="#0F766E")
        y += 38
        for linea in textwrap.wrap(texto, 70):
            d.text((50, y), linea, font=_fuente(28), fill="#134E4A")
            y += 36
        y += 18
    d.text((50, H - 45), "Fuente: datos.madrid.es · Centros deportivos municipales (open data)", font=_fuente(20), fill="#5f7f7b")
    IMAGEN_DEMO.parent.mkdir(parents=True, exist_ok=True)
    img.save(IMAGEN_DEMO)
    print(f"Imagen generada: {IMAGEN_DEMO}")


if __name__ == "__main__":
    main()
