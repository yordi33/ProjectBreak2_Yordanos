# Spec 01 — RAG completo como módulo (`rag/`)

## Origen
Reutilizado del Project Break 1 (InfoSport). Cambios respecto al PB1:
| Cambio | Motivo |
|---|---|
| Clasificación: 1 documento **por grupo** (tabla completa) en vez de 1 por fila | En el PB1, con TOP_K=2 faltaban equipos del grupo (ver informe PB1) |
| CSV de partidos (28.7k filas) **fuera del índice** → tool `consultar_partidos` | Embeberlo excede la cuota gratuita y la consulta exacta es más fiable |
| Cliente Gemini por API key (`gemini_auth.py`) en vez de Vertex + credenciales JSON | Reproducible sin cuenta de servicio |
| Embeddings **locales** (fastembed, multilingual MiniLM) por defecto; Gemini opcional | La cuota gratuita diaria de `gemini-embedding-001` se agotó a los ~750 chunks |
| Chunks de 700 caracteres para PDF; cada tabla de clasificación es **un único chunk** | El modelo local trunca a ~128 tokens: el texto embebido es la cabecera (grupo, competición, deporte) y el LLM recibe la tabla entera. Partirla dejaba trozos con solo las posiciones 8 y 9 |
| `task_type` RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY en embeddings | Mejor recuperación asimétrica |
| Embeddings reanudables (guardado por lote) y reintento ante 429/cortes | Cuota gratuita ≈ 1 lote/min |
| Bug `\n{3.}` → `\n{3,}` en `normalizar` | La regex del PB1 no colapsaba saltos de línea |

## Pipeline offline
`python main.py --prepare --index`
1. **load** (`rag/load.py`): PDF (PyPDFLoader), CSV de clasificación agrupado, TXT/MD.
2. **chunk** (`rag/chunk.py`): RecursiveCharacterTextSplitter `CHUNK_SIZE=700`, `CHUNK_OVERLAP=100` → `output/chunks.json`.
3. **embed** (`rag/embed.py`): `EMBEDDING_PROVIDER="local"` (fastembed) o `"gemini"`, lotes de 50 → `output/embeddings.joblib`.
4. **index** (`rag/index.py`): ChromaDB persistente `output/chroma_db`, coseno, metadatos `source`, `tipo`, `grupo`, `chunk_index`, `embedding_model`.

## API interna (sin UI)
```python
from rag import responder, rag_ask
responder(pregunta, top_k=None) -> {"respuesta", "hay_evidencia", "fuentes", "chunks", "error", "modelo", "latencia_s"}
rag_ask(pregunta) -> str
```
- Valida pregunta vacía / > `MAX_PREGUNTA`.
- Recupera top-k (`TOP_K=4`), construye prompt con `RAG_BEHAVIOUR` y pide JSON
  `{"respuesta", "hay_evidencia", "fuentes_citadas"}`.
- **Abstención**: si el contexto no basta → `hay_evidencia=false` y explicación.
- Log de métricas en `output/rag_metrics_log.json`.

## Criterios de aceptación
- [x] Indexa el corpus (≥2 formatos: PDF + CSV).
- [x] Pregunta in-corpus responde con fuentes (p. ej. multa máxima por falta muy grave).
- [x] Pregunta fuera de corpus se abstiene (p. ej. calorías en barcas de recreo).
- [x] Se puede llamar desde la tool `rag_ask` del agente y desde `python main.py --rag`.
