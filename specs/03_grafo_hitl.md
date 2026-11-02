# Spec 03 — Grafo multiagente, HITL y persistencia (`src/graph.py`, `src/agent.py`)

## Grafo
```
START → supervisor ─┬─ especialista_normativa ─────┐
                    ├─ especialista_instalaciones ─┼─► supervisor
                    ├─ especialista_imagen ────────┘
                    └─ sintetizar ─► supervisor
         supervisor (FINISH) → aplicar  [interrupt_before] → END
```

## Nodos
| Nodo | Responsabilidad | Tools |
|---|---|---|
| `supervisor` | Elige siguiente especialista no visitado, `sintetizar` o `FINISH` | — |
| `especialista_normativa` | Reglamento, JDM, clasificaciones | `rag_ask`, `hora_actual` |
| `especialista_instalaciones` | Polideportivos, tiempo, partidos | `buscar_polideportivos`, `tiempo_madrid`, `consultar_partidos`, `hora_actual` |
| `especialista_imagen` | Leer imágenes adjuntas | `describir_imagen` |
| `sintetizar` | Notas → respuesta + plan (2-5 viñetas) | — |
| `aplicar` | Solo tras decisión humana: aprobar → `done=True`; rechazar → reset parcial | — |

## Reglas decididas en Python (no por el LLM)
- `MAX_ITER=6` vueltas del supervisor por turno → se fuerza `sintetizar`.
- `MAX_STEPS=3` tools por especialista y turno.
- `MAX_TURNS=20` turnos por `thread_id`; `MAX_MENSAJE=500` caracteres.
- La elección del supervisor se valida contra la lista de opciones; si el LLM falla o devuelve
  algo inválido → **fallback determinista** por palabras clave (`ruta_fallback`).
- No se puede sintetizar sin haber consultado al menos a un especialista.
- Si ya hay plan → `FINISH` → `aplicar` (pausado por `interrupt_before`).
- `done` solo cambia en `aplicar`.

## Estado del grafo (`EstadoGrafo`)
Por turno (se resetea en cada pedido): `pedido, imagen, turno, notas, visitados, siguiente,
iteracion, respuesta, plan, decision, comentario_humano, done`.
Acumulados en el hilo (reducer `operator.add`): `log, trazas, historial`.

## HITL
1. `procesar_turno` → `graph.invoke(entrada, {"thread_id"})` → se detiene antes de `aplicar`.
2. `_marcar_hitl` lee `graph.get_state(cfg).next == ("aplicar",)` → `hitl_pendiente=True`.
3. `aprobar_plan` → `graph.update_state(cfg, {"decision": "aprobar"|"rechazar", "comentario_humano"})`
   → `graph.invoke(None, cfg)` → `aplicar` → END.

## Persistencia
`compile(checkpointer=MemorySaver(), interrupt_before=["aplicar"])`. El grafo se compila una vez
por proceso (`agent.get_graph()`), así el mismo `thread_id` recupera el hilo entre turnos.
Extra: `CHECKPOINTER="sqlite"` usa `SqliteSaver` (`output/checkpoints.sqlite`) y sobrevive a reinicios.

## Criterios de aceptación
- [x] Un pedido produce log multiagente + plan + pausa HITL.
- [x] Aprobar → `done=True`; rechazar → `done=False` y se puede enviar otro mensaje.
- [x] Mismo `thread_id` reutiliza el checkpointer (historial con ambos turnos).
