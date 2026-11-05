"""Configuración centralizada de InfoSport Agente (Project Break 2).

Todos los límites (MAX_ITER, MAX_STEPS, MAX_TURNS…), modelos, rutas y la
allowlist por especialista viven aquí para poder experimentar sin tocar código.
"""
from pathlib import Path

# ---------------------------------------------------------------- rutas
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
FALLBACK_DIR = DATA_DIR / "fallback"
ASSETS_DIR = PROJECT_DIR / "assets"
OUTPUT_DIR = PROJECT_DIR / "output"
CHROMA_DIR = OUTPUT_DIR / "chroma_db"
CHUNKS_JSON = OUTPUT_DIR / "chunks.json"
EMBEDDINGS_FILE = OUTPUT_DIR / "embeddings.joblib"
RAG_LOG_JSON = OUTPUT_DIR / "rag_metrics_log.json"
AGENT_LOG_JSONL = OUTPUT_DIR / "agent_trazas.jsonl"
CHECKPOINT_DB = OUTPUT_DIR / "checkpoints.sqlite"
IMAGEN_DEMO = ASSETS_DIR / "imagen_demo.png"

PARTIDOS_CSV = DATA_DIR / "211549-0-partidos-csv.csv"
CLASIFICACION_CSV = DATA_DIR / "211549-2-clasificacion-csv.csv"

# ---------------------------------------------------------------- modelos
# El primero disponible se usa; si la API devuelve 503/429/404 se prueba el siguiente.
GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]
VISION_MODELS = GEMINI_MODELS
# Embeddings: "local" (fastembed, CPU, sin cuota) por defecto; "gemini" usa gemini-embedding-001
# (la cuota gratuita diaria se agotó a los ~750 chunks: ver informe, fallo 1).
EMBEDDING_PROVIDER = "local"
LOCAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_MODEL = LOCAL_EMBEDDING_MODEL if EMBEDDING_PROVIDER == "local" else GEMINI_EMBEDDING_MODEL
MODELOS_DIR = PROJECT_DIR / "output" / "modelos"
TEMPERATURE_SUPERVISOR = 0.0
TEMPERATURE_ESPECIALISTAS = 0.2
TEMPERATURE_RAG = 0.2
LLM_REINTENTOS = 2  # reintentos por modelo ante errores transitorios

# ---------------------------------------------------------------- RAG
CHUNK_SIZE = 700   # el modelo local trunca a ~128 tokens: chunks cortos
CHUNK_OVERLAP = 100
EMBED_BATCH_SIZE = 50
TOP_K = 4
MAX_GRUPO_CHROMA = 500
COLLECTION_NAME = "infosport_pb2"
MAX_PREGUNTA = 300
EXTENSIONES_PDF = {".pdf"}
EXTENSIONES_TEXTO = {".txt", ".md"}
EXTENSIONES_CSV = {".csv"}
# El CSV de partidos (28k filas) no se embebe: se consulta con la tool estructurada
# `consultar_partidos`. La clasificación se indexa agrupada (1 documento por grupo).
CSV_EXCLUIDOS_RAG = {PARTIDOS_CSV.name}

RAG_BEHAVIOUR = """Eres el módulo RAG de InfoSport: deporte municipal de Madrid
(reglamento de instalaciones deportivas municipales, Juegos Deportivos Municipales y clasificaciones).

Reglas:
- Usa ÚNICAMENTE el contexto proporcionado. No uses conocimiento externo.
- Para normativa o qué está permitido, prioriza los fragmentos del Reglamento (PDF).
- Para clasificaciones, equipos y grupos usa los fragmentos de clasificación (CSV).
- Responde SOLO con un JSON válido (sin markdown) con este esquema exacto:
  {"respuesta": string, "hay_evidencia": boolean, "fuentes_citadas": [string]}
- Si el contexto no basta, hay_evidencia=false y explica la abstención en "respuesta".
- fuentes_citadas: nombres de archivo que aparecen en el contexto y que has usado."""

# ---------------------------------------------------------------- agente / grafo
MAX_ITER = 6          # vueltas máximas del supervisor por turno
MAX_STEPS = 3         # llamadas a tools máximas por especialista y turno
MAX_TURNS = 20        # turnos máximos por conversación (thread_id)
MAX_MENSAJE = 500     # longitud máxima del mensaje del usuario
CHECKPOINTER = "memory"  # "memory" (MemorySaver, obligatorio) | "sqlite" (extra)

# Allowlist por especialista: el LLM propone, Python solo ejecuta lo que esté aquí.
ESPECIALISTAS = {
    "especialista_normativa": {
        "descripcion": "Reglamento de instalaciones deportivas municipales, normas de uso, "
                       "sanciones, Juegos Deportivos Municipales y clasificaciones (RAG).",
        "tools": ["rag_ask", "hora_actual"],
    },
    "especialista_instalaciones": {
        "descripcion": "Polideportivos municipales (dirección, horario, transporte), tiempo "
                       "en Madrid para actividad al aire libre y partidos programados/resultados.",
        "tools": ["buscar_polideportivos", "tiempo_madrid", "consultar_partidos", "hora_actual"],
    },
    "especialista_imagen": {
        "descripcion": "Lee y describe imágenes (carteles, paneles, folletos) aportadas por el usuario.",
        "tools": ["describir_imagen"],
    },
}

# ---------------------------------------------------------------- APIs externas
POLIDEPORTIVOS_URL = "https://datos.madrid.es/egob/catalogo/200186-0-polideportivos.json"
METEO_URL = "https://api.open-meteo.com/v1/forecast"
MADRID_LAT, MADRID_LON = 40.4168, -3.7038
HTTP_TIMEOUT = 8
TIMEZONE = "Europe/Madrid"
