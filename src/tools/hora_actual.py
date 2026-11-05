"""Herramienta auxiliar determinista: fecha y hora actuales en Madrid."""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

from config import TIMEZONE

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


@tool
def hora_actual() -> str:
    """Devuelve la fecha, la hora y el día de la semana actuales en Madrid (Europe/Madrid).
    Útil para plazos (p. ej. anular una reserva con antelación) o saber si algo está abierto."""
    ahora = datetime.now(ZoneInfo(TIMEZONE))
    return json.dumps(
        {
            "fecha": ahora.strftime("%Y-%m-%d"),
            "hora": ahora.strftime("%H:%M"),
            "dia_semana": _DIAS[ahora.weekday()],
            "fin_de_semana": ahora.weekday() >= 5,
            "zona": TIMEZONE,
        },
        ensure_ascii=False,
    )
