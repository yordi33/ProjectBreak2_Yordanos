from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from config import (
    CLASIFICACION_CSV,
    CSV_EXCLUIDOS_RAG,
    DATA_DIR,
    EXTENSIONES_CSV,
    EXTENSIONES_PDF,
    EXTENSIONES_TEXTO,
)


def _num(v) -> str:
    if pd.isna(v):
        return "-"
    try:
        f = float(str(v).replace(",", "."))
        return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        return str(v).strip()


def cargar_clasificacion(ruta: Path) -> list[Document]:
    df = pd.read_csv(ruta, sep=";", encoding="latin-1")
    docs = []
    for grupo, g in df.groupby("Nombre_grupo", sort=False):
        g = g.sort_values("Posicion")
        r0 = g.iloc[0]
        cabecera = (
            f"CLASIFICACIÓN del grupo {grupo}\n"
            f"Competición: {r0['Nombre_competicion']} | Fase: {r0['Nombre_fase']} | "
            f"Deporte: {r0['Nombre_deporte']} | Categoría: {str(r0['Nombre_categoria']).strip()} | "
            f"Sexo: {r0['Nombre-Sexo']} | Distrito: {r0['Nombre_distrito']} | "
            f"Temporada: {r0['Nombre_temporada']}"
        )
        filas = [
            f"Posición {_num(r['Posicion'])}: {str(r['Nombre_equipo']).strip()} — "
            f"{_num(r['Puntos'])} puntos, PJ {_num(r['Partidos_jugados'])}, "
            f"PG {_num(r['Partidos_ganados'])}, PE {_num(r['Partidos_empatados'])}, "
            f"PP {_num(r['Partidos_perdidos'])}, GF {_num(r['Goles_favor'])}, GC {_num(r['Goles_contra'])}"
            for _, r in g.iterrows()
        ]
        docs.append(
            Document(
                page_content=cabecera + "\n" + "\n".join(filas),
                metadata={
                    "source": ruta.name,
                    "tipo": "clasificacion",
                    "grupo": str(grupo),
                    "deporte": str(r0["Nombre_deporte"]),
                    "cabecera": cabecera,
                },
            )
        )
    return docs


def cargar_csv_filas(ruta: Path) -> list[Document]:
    df = pd.read_csv(ruta, sep=";", encoding="latin-1", low_memory=False)
    docs = []
    for i, fila in df.iterrows():
        partes = [f"{c}: {str(v).strip()}" for c, v in fila.items() if not pd.isna(v) and str(v).strip()]
        docs.append(Document(page_content="\n".join(partes), metadata={"source": ruta.name, "fila": int(i)}))
    return docs


def cargar_archivo(ruta: Path) -> list[Document]:
    sufijo = ruta.suffix.lower()
    if sufijo in EXTENSIONES_PDF:
        return PyPDFLoader(str(ruta)).load()
    if sufijo in EXTENSIONES_TEXTO:
        return TextLoader(str(ruta), encoding="utf-8").load()
    if sufijo in EXTENSIONES_CSV:
        if ruta.name in CSV_EXCLUIDOS_RAG:
            return []
        if ruta.name == CLASIFICACION_CSV.name:
            return cargar_clasificacion(ruta)
        return cargar_csv_filas(ruta)
    return []


def normalizar(texto: str) -> str:
    t = texto.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return "\n".join(linea.strip() for linea in t.split("\n")).strip()


def cargar_documentos() -> list[Document]:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"No encuentro la carpeta data en: {DATA_DIR}")
    documentos: list[Document] = []
    for ruta in sorted(DATA_DIR.iterdir()):
        if not ruta.is_file() or ruta.name.lower() == "readme.md":
            continue
        docs = cargar_archivo(ruta)
        for d in docs:
            texto = normalizar(d.page_content)
            if not texto:
                continue
            d.metadata["source"] = Path(d.metadata.get("source", ruta.name)).name
            if ruta.name.startswith("eli-"):
                texto = "[REGLAMENTO DE INSTALACIONES DEPORTIVAS MUNICIPALES DE MADRID]\n" + texto
            documentos.append(Document(page_content=texto, metadata=dict(d.metadata)))
        if docs:
            print(f"Cargado: {ruta.name} ({len(docs)} documentos)")
        elif ruta.name in CSV_EXCLUIDOS_RAG:
            print(f"Omitido del índice (tool estructurada): {ruta.name}")
    return documentos
