"""Tool estructurada sobre el CSV de partidos (28k filas) con pandas.

El CSV es demasiado grande para embeberlo fila a fila; una consulta exacta por
equipo / fecha / estado es además más fiable que la búsqueda semántica.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache

import pandas as pd
from langchain_core.tools import tool

from config import PARTIDOS_CSV

ESTADOS = {
    "A": "Reprogramado", "C": "Comité disciplinario", "F": "Finalizado", "S": "Suspendido",
    "N": "No presentado", "O": "Aplazado organización", "R": "Resultado desconocido",
}


def _norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


@lru_cache(maxsize=1)
def _partidos() -> pd.DataFrame:
    df = pd.read_csv(PARTIDOS_CSV, sep=";", encoding="latin-1", low_memory=False)
    df["n_local"] = df["Equipo_local"].map(_norm)
    df["n_visit"] = df["Equipo_visitante"].map(_norm)
    df["estado_txt"] = df["Estado"].map(ESTADOS).fillna("Desconocido")
    return df


@tool
def consultar_partidos(
    equipo: str = "", fecha: str = "", estado: str = "", deporte: str = "", max_resultados: int = 8
) -> str:
    """Consulta exacta de partidos de las competiciones municipales de Madrid (temporada 2025/2026).
    Filtros opcionales: equipo (texto en local o visitante), fecha (AAAA-MM-DD), estado
    (Finalizado, Suspendido, Aplazado, Reprogramado, No presentado…) y deporte (p. ej. FUTBOL SALA).
    Devuelve el total de coincidencias y los primeros partidos con campo, distrito y resultado."""
    df = _partidos()
    m = pd.Series(True, index=df.index)
    if equipo:
        e = _norm(equipo)
        m &= df["n_local"].str.contains(e, regex=False) | df["n_visit"].str.contains(e, regex=False)
    if fecha:
        m &= df["Fecha"].astype(str).str.startswith(fecha.strip())
    if estado:
        m &= df["estado_txt"].map(_norm).str.contains(_norm(estado), regex=False)
    if deporte:
        m &= df["Nombre_deporte"].map(_norm).str.contains(_norm(deporte), regex=False)
    sel = df[m]
    max_resultados = max(1, min(int(max_resultados), 20))
    filas = [
        {
            "fecha": r.Fecha, "hora": r.Hora, "deporte": r.Nombre_deporte, "grupo": r.Nombre_grupo,
            "local": r.Equipo_local, "visitante": r.Equipo_visitante,
            "resultado": f"{r.Resultado1}-{r.Resultado2}" if pd.notna(r.Resultado1) else "-",
            "estado": r.estado_txt, "campo": r.Campo, "distrito": r.Distrito,
            "coord_x": r.COORD_X_CAMPO, "coord_y": r.COORD_Y_CAMPO,
        }
        for r in sel.head(max_resultados).itertuples()
    ]
    return json.dumps(
        {"fuente": PARTIDOS_CSV.name, "total_coincidencias": int(len(sel)), "partidos": filas},
        ensure_ascii=False,
        default=str,
    )
