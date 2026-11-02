# Informe de decisiones · InfoSport Agente (Project Break 2)

## 1. Grafo: por qué estos especialistas y este momento HITL

```
START → supervisor ─┬─ especialista_normativa ─────┐
                    ├─ especialista_instalaciones ─┼─► supervisor
                    ├─ especialista_imagen ────────┘
                    └─ sintetizar ─► supervisor ─(FINISH)→ aplicar [HITL] → END
```

- **Tres especialistas, uno por tipo de fuente.** Las preguntas de InfoSport caen en tres grupos:
  - lo que dice un **documento** (reglamento, clasificaciones): lo resuelve el RAG;
  - lo que dicen los **datos vivos o tabulares** (polideportivos, tiempo, partidos): lo resuelven las APIs y pandas;
  - lo que dice una **imagen**.

  Separarlos permite dar a cada uno una allowlist mínima. Por ejemplo, el especialista de imagen no
  puede llamar a APIs y el de normativa no puede leer ficheros. Así cada prompt es corto y concreto.
  Un pedido mixto («¿a qué hora abre el CDM y qué normas debo cumplir?») pasa por dos especialistas.
- **El supervisor decide con el LLM (temperatura 0), pero Python lo vigila:**
  - valida la opción elegida;
  - no deja visitar dos veces al mismo especialista;
  - corta en `MAX_ITER=6`;
  - impide sintetizar sin haber consultado a nadie;
  - si el LLM falla, aplica un **fallback determinista** por palabras clave.
- **HITL justo antes de `aplicar`** (`interrupt_before=["aplicar"]`). El plan ya está completo y
  revisable, pero todavía no se ha cerrado nada. `done` solo cambia en `aplicar`, nunca por decisión
  del LLM. Si se rechaza, el reinicio es parcial: se borran el plan, las notas y los visitados, pero
  se conservan el hilo y el historial, y se puede pedir otra cosa en el mismo `thread_id`.

## 2. Tools: qué hace cada una y cómo se conecta el RAG

| Tool | Categoría | Qué hace |
|---|---|---|
| `rag_ask` | RAG completo | Llama a `rag.responder()`: embedding de la pregunta → top-4 en Chroma → Gemini con contexto → JSON `{respuesta, hay_evidencia, fuentes}` |
| `buscar_polideportivos` | API externa | Open data de centros deportivos municipales (datos.madrid.es). Si la red falla, usa un JSON local |
| `tiempo_madrid` | API externa | Open-Meteo: tiempo actual y previsión del día. El fallback se marca como «NO actuales» |
| `consultar_partidos` | Datos estructurados | Filtro exacto con pandas sobre los 28.743 partidos |
| `hora_actual` | Auxiliar | Fecha, hora y día de la semana en Europe/Madrid |
| `describir_imagen` | Multimodal | Gemini visión. Solo lee rutas dentro de `assets/` o `output/uploads/` |

**Enchufe del RAG:** el módulo `rag/` es el PB1 refactorizado y su API se puede usar sin UI
(`responder`, `rag_ask`). `src/tools/rag_ask.py` lo envuelve con `@tool` de LangChain. El especialista
nunca lo llama directamente: propone `{"accion":"tool","tool":"rag_ask","args":{...}}` y
`ejecutar_tool` comprueba la allowlist global y la del especialista, ejecuta la tool y registra la
traza (`tool, args, status, ms, preview`).

**Decisión de corpus:** el CSV de partidos no se embebe. Son 28k filas, que con la cuota gratuita
supondrían horas de indexado, y preguntas como «¿coordenadas del campo de PECHETINGS el 31/01?» se
responden mejor con un filtro exacto. La clasificación se indexa como **un documento por grupo**: en
el PB1, con una fila por chunk y `TOP_K=2`, faltaban equipos del grupo.

## 3. HITL observado

**Aprobación** (Streamlit, thread `infosport-55293396`). Pedido: *«Lee este cartel: ¿qué días cierra
el centro y cómo llego en metro?»* con `assets/imagen_demo.png`. El supervisor eligió
`especialista_imagen` → `describir_imagen` (8,3 s) → `sintetizar`. El plan tenía 2 pasos (evitar los
días 24, 25 y 31 de diciembre, el 1 de enero y el 1 de mayo; ir en metro Línea 9 hasta Pavones). Tras
pulsar **Aprobar** el log mostró `[aplicar] HITL: APROBADO → done=True`, el chat quedó cerrado y el
historial recogió `decision: aprobar`.

**Rechazo** (thread `infosport-0ed626c9`). Pedido: *«¿A qué hora cierra la taquilla del CDM La Elipa
y hace buen tiempo hoy para correr?»*. El supervisor eligió `especialista_instalaciones`, que llamó a
`buscar_polideportivos({"texto":"La Elipa"})` (API, 570 ms) y a `tiempo_madrid()` (API, 864 ms). La
respuesta: la taquilla cierra a las 20:30, cielo despejado y 15 °C. Tras **rechazar** con el
comentario «no me convence», el log mostró `RECHAZADO → plan descartado, done=False`. El siguiente
mensaje en el **mismo thread** («qué partidos de fútbol sala están suspendidos») se procesó con
normalidad (`consultar_partidos`: 34 partidos), se aprobó, y el historial del hilo contiene los dos
turnos. Esto confirma que el checkpointer reutiliza el `thread_id`.

## 4. Multimodal

La imagen es `assets/imagen_demo.png`, una ficha del CDM Moratalaz generada por
`scripts/crear_imagen_demo.py` con datos reales del open data (dirección, horario de taquilla,
cierres, metro y accesibilidad). Ante la pregunta «¿a qué hora cierra la taquilla el sábado?», la tool
devolvió la transcripción completa (C/ Valdebernardo 2, L-V de 9 a 20:30, sábados y domingos de 9 a
14:30, metro Pavones L9) y respondió correctamente **14:30 h**. No inventó ningún dato.

## 5. RAG: indexado, pregunta del corpus y abstención

`python main.py --prepare --index` → 1.585 documentos, **1.674 chunks** indexados en Chroma (≈80 s).

| Pregunta | Resultado | Fuente / chunks |
|---|---|---|
| ¿Qué multa máxima se aplica a las faltas muy graves? | «hasta 3.000 euros» (art. 60) · `hay_evidencia=true` | Reglamento, distancia 0,31 |
| ¿Obligaciones de los usuarios? | Enumera los deberes a)–g) del reglamento | Reglamento, distancia 0,19 |
| ¿Quién quedó primero en JDM VIV MBC BEN MIX? | VALLEKAS BASKET ANGEL NIETO | clasificación CSV, distancia 0,30 |
| ¿Calorías en 45 min en las barcas de recreo? | **Abstención** · `hay_evidencia=false`, `fuentes=[]` | mejor distancia 0,59 (no relevante) |

*Hallazgo:* el JSON de evaluación del PB1 daba «1.500 €» como respuesta correcta para las muy graves,
pero el artículo 60.1 dice **3.000 €** (1.500 € es para las graves). El RAG acertó y la nota estaba mal.

**Vía el agente** (`python main.py --demo --auto`, log en `output/demo_cli.log`, mismo thread
`infosport-c076ea28`, 3 turnos):
1. *«Quiero nadar en el CDM Moratalaz esta tarde: hora de cierre de taquilla, metro y normas»*:
   supervisor → `especialista_instalaciones` (`buscar_polideportivos`, `hora_actual`) →
   `especialista_normativa` (`rag_ask`) → `sintetizar`. Respuesta: cierra a las 20:30, y como eran
   las 20:57 de un lunes la taquilla ya estaba cerrada; metro Pavones L9. Plan de 3 pasos →
   **aprobado** → `done=True`.
2. *Clasificación + tiempo*: `rag_ask` + `consultar_partidos` + `tiempo_madrid`. Plan → **rechazado**
   → `done=False`, y el hilo sigue.
3. *Cartel*: `especialista_imagen` → `describir_imagen` → horario y cierres correctos → **aprobado**.

En una primera ejecución de la demo, `gemini-3.5-flash` devolvió **429** (cuota agotada) y los
especialistas se quedaban sin datos. Se añadieron dos defensas, enfriamiento del modelo agotado y un
fallback determinista por especialista (ver fallo 2).

## 6. Tres fallos y qué haríamos en MLOps / siguiente iteración

1. **Cuota de embeddings.** Con `gemini-embedding-001` en la cuota gratuita se procesaba un lote
   por minuto, un corte de red (`WinError 10053`) tumbó el primer intento y, a los ~750 de 1.685
   chunks, la API pidió esperar **45.205 s**: la cuota *diaria* estaba agotada. Tampoco se podían
   embeber las preguntas del RAG, así que el agente se quedaba sin RAG. *Decisión:* embeddings
   **locales** con fastembed (`paraphrase-multilingual-MiniLM-L12-v2`). Ahora 1.674 chunks se indexan
   en unos 80 s, sin cuota ni red. Gemini se mantiene para el LLM y la visión, y como opción
   configurable para los embeddings. Como el modelo local trunca a unos 128 tokens, se bajó
   `CHUNK_SIZE` a 700 para los PDF y cada tabla de clasificación se dejó como **un único chunk**. Al
   principio se partía, y para «¿quién quedó primero en JDM VIV MBC BEN MIX?» solo se recuperaba el
   trozo con las posiciones 8 y 9. *MLOps:*
   construir el índice en CI como **artefacto versionado** (Chroma + hash del corpus + modelo de
   embeddings) y no reindexar si nada cambia.
2. **Disponibilidad y cuota de los modelos.** `gemini-flash-latest` devolvía 503 por saturación,
   `gemini-2.5-flash` ya da 404 a usuarios nuevos y, en mitad de la demo, `gemini-3.5-flash` agotó
   su cuota (429). Sin LLM, supervisor y especialistas acababan en «Sin datos». *Mitigación:*
   - `src/llm.py` reintenta los 503, pone en **enfriamiento** el modelo con 429 y salta al siguiente de
     `GEMINI_MODELS` (5 modelos). El log indica qué modelo respondió.
   - El supervisor tiene un fallback por palabras clave.
   - Cada especialista tiene un **fallback determinista** que llama a su tool principal
     (`rag_ask`, `describir_imagen`, `tiempo_madrid`…). Así siempre hay datos reales de las tools. *MLOps:*
   métricas de latencia y error por modelo, alertas y *circuit breaker*; fijar versiones de modelo
   por entorno.
3. **Entorno y fuentes.** En Windows, Python daba `CERTIFICATE_VERIFY_FAILED` contra la API de Google
   (no usaba el almacén de certificados del sistema). Se arregló con `truststore`. Además, ChromaDB
   1.x y onnxruntime se caían (`access violation` / `DLL load failed`) por un runtime de Visual C++
   antiguo (14.31); se resuelve instalando el redistribuible oficial de Microsoft. Además, madrid.es
   responde 403 a las descargas automáticas de PDFs nuevos (tarifas 2026, normativa JDM), así que el
   corpus se quedó en el del PB1. *Siguiente iteración:* descargar esos PDFs a mano, documentarlos y
   reindexar. *MLOps:* contenedor con certificados controlados y una ingesta programada con
   validación del corpus.

Otros detalles corregidos durante las pruebas:
- El sintetizador citaba al especialista en lugar de la fuente; se corrigió el prompt.
- `itertuples` renombraba las columnas que empiezan por `_`.
- La regex del PB1 `\n{3.}` no hacía nada.

## 7. Siguientes pasos (pieza 3 · MLOps)

- Empaquetar con Docker: la API del agente (FastAPI con `procesar_turno` y `aprobar_plan`) separada de la UI.
- Cambiar `MemorySaver` por `SqliteSaver` o Postgres (ya está preparado: `CHECKPOINTER="sqlite"`).
- Hacer observable `output/agent_trazas.jsonl` y `output/rag_metrics_log.json` (LangSmith o Prometheus).
- Evaluación automática: preguntas del corpus y fuera del corpus en CI, midiendo la tasa de abstención correcta.
