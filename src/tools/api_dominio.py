from __future__ import annotations

import json
import unicodedata
from functools import lru_cache

import requests
from langchain_core.tools import tool

from config import FALLBACK_DIR, HTTP_TIMEOUT, MADRID_LAT, MADRID_LON, METEO_URL, POLIDEPORTIVOS_URL, TIMEZONE

_WMO = {
    0: "despejado", 1: "casi despejado", 2: "parcialmente nuboso", 3: "cubierto",
    45: "niebla", 48: "niebla con escarcha", 51: "llovizna débil", 53: "llovizna", 55: "llovizna intensa",
    61: "lluvia débil", 63: "lluvia", 65: "lluvia intensa", 71: "nieve débil", 73: "nieve", 75: "nieve intensa",
    80: "chubascos débiles", 81: "chubascos", 82: "chubascos fuertes", 95: "tormenta", 96: "tormenta con granizo",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


@lru_cache(maxsize=1)
def _polideportivos() -> tuple[list[dict], str]:
    try:
        r = requests.get(POLIDEPORTIVOS_URL, timeout=HTTP_TIMEOUT, headers={"User-Agent": "InfoSport-PB2/1.0"})
        r.raise_for_status()
        return r.json()["@graph"], "api"
    except Exception:
        datos = json.loads((FALLBACK_DIR / "polideportivos.json").read_text(encoding="utf-8"))
        return datos["@graph"], "fallback"


def _ficha(p: dict) -> dict:
    adr = p.get("address", {})
    distrito = adr.get("district", {}).get("@id", "").rsplit("/", 1)[-1]
    org = p.get("organization", {})
    return {
        "nombre": p.get("title", ""),
        "direccion": f"{adr.get('street-address', '')}, {adr.get('postal-code', '')} Madrid",
        "distrito": distrito,
        "horario": " ".join((org.get("schedule") or "").split())[:400],
        "transporte": " ".join((org.get("organization-desc") or "").split())[:300],
        "accesible": org.get("accesibility") == "1",
        "lat": p.get("location", {}).get("latitude"),
        "lon": p.get("location", {}).get("longitude"),
    }


@tool
def buscar_polideportivos(texto: str = "", distrito: str = "", max_resultados: int = 5) -> str:
    """Busca centros deportivos municipales de Madrid en el open data del Ayuntamiento
    (datos.madrid.es). Filtra por texto en el nombre/dirección y/o por distrito
    (p. ej. 'Retiro', 'Moncloa-Aravaca'). Devuelve dirección, distrito, horario y transporte."""
    datos, origen = _polideportivos()
    t, d = _norm(texto), _norm(distrito).replace(" ", "")
    fichas = []
    for p in datos:
        f = _ficha(p)
        if t and t not in _norm(f["nombre"] + " " + f["direccion"]):
            continue
        if d and d not in _norm(f["distrito"]).replace(" ", ""):
            continue
        fichas.append(f)
    max_resultados = max(1, min(int(max_resultados), 10))
    return json.dumps(
        {"origen": origen, "total_encontrados": len(fichas), "resultados": fichas[:max_resultados]},
        ensure_ascii=False,
    )


@tool
def tiempo_madrid() -> str:
    """Tiempo actual y previsión de hoy en Madrid (Open-Meteo): temperatura, estado del cielo,
    viento y probabilidad de lluvia. Útil para decidir actividades al aire libre."""
    params = {
        "latitude": MADRID_LAT,
        "longitude": MADRID_LON,
        "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 1,
        "timezone": TIMEZONE,
    }
    try:
        r = requests.get(METEO_URL, params=params, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        datos, origen = r.json(), "api"
    except Exception:
        datos = json.loads((FALLBACK_DIR / "tiempo_madrid.json").read_text(encoding="utf-8"))
        origen = "fallback (datos de ejemplo guardados, NO actuales)"
    cur, day = datos["current"], datos["daily"]
    return json.dumps(
        {
            "origen": origen,
            "hora_medicion": cur["time"],
            "temperatura_c": cur["temperature_2m"],
            "sensacion_c": cur.get("apparent_temperature"),
            "cielo": _WMO.get(cur["weather_code"], f"código {cur['weather_code']}"),
            "viento_kmh": cur["wind_speed_10m"],
            "precipitacion_mm": cur["precipitation"],
            "max_hoy_c": day["temperature_2m_max"][0],
            "min_hoy_c": day["temperature_2m_min"][0],
            "prob_lluvia_hoy_pct": day["precipitation_probability_max"][0],
        },
        ensure_ascii=False,
    )
