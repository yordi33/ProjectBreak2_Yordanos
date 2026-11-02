# Spec 02 — Tools controladas (`src/tools/`)

## Principio
El LLM **propone** `{"accion": "tool", "tool": nombre, "args": {...}}`; Python **decide**.
`ejecutar_tool(nombre, args, permitidas)`:
1. `nombre ∉ ALLOWLIST` → `status="bloqueada"` (no se ejecuta nada).
2. `nombre ∉ permitidas` (allowlist del especialista, `config.ESPECIALISTAS`) → `bloqueada`.
3. Se ejecuta con `BaseTool.invoke(args)` (valida tipos). Excepción → `status="error"`, nunca rompe el grafo.
4. Devuelve traza `{tool, args, status, resultado, preview, ms}`; el grafo añade `especialista, paso, turno`.

## Catálogo
| Tool | Categoría | Fuente | Fallback |
|---|---|---|---|
| `rag_ask(pregunta)` | RAG completo | `rag.responder` (Chroma + Gemini) | error en traza |
| `buscar_polideportivos(texto, distrito, max_resultados)` | API externa | datos.madrid.es (JSON) | `data/fallback/polideportivos.json` |
| `tiempo_madrid()` | API externa | Open-Meteo | `data/fallback/tiempo_madrid.json` (marcado «NO actuales») |
| `consultar_partidos(equipo, fecha, estado, deporte, max_resultados)` | datos estructurados (extra) | CSV partidos con pandas | — |
| `hora_actual()` | auxiliar determinista | `datetime` Europe/Madrid | — |
| `describir_imagen(ruta, pregunta)` | multimodal | Gemini visión | — |

`describir_imagen` solo acepta rutas dentro de `assets/` u `output/uploads/` (evita leer ficheros
arbitrarios del disco por inyección en el pedido).

## Criterios de aceptación
- [x] Cada tool se prueba aislada: `python main.py --tool <nombre> --args '{...}'`.
- [x] Una tool inexistente (`borrar_todo`) queda `bloqueada`.
- [x] Una tool válida pero no permitida al especialista queda `bloqueada`.
- [x] Las APIs indican `origen: api|fallback` en el resultado.
