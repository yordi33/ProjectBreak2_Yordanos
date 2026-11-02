# Spec 04 — Clientes: CLI y Streamlit

Ambos son **clientes** del contrato de `src/agent.py`; ninguno contiene lógica del grafo.

## CLI (`main.py`)
| Comando | Qué hace |
|---|---|
| `--prepare --index` | Pipeline offline del RAG |
| `--rag "pregunta"` | RAG directo (respuesta, evidencia, fuentes, chunks) |
| `--tool NOMBRE --args '{...}'` | Ejecuta una tool aislada vía allowlist |
| `--demo --auto` | 3 pedidos guiados en el mismo `thread_id`, decisiones HITL automáticas (aprobar, rechazar, aprobar) |
| `--demo` | Igual, pero el humano decide cada HITL |
| `--chat` | Interactivo: `/imagen [ruta]`, `/nueva`, `/historial`, `/salir`; HITL manual |

## Streamlit (`app.py`)
- Chat con historial visual (solo UI; el estado real está en el checkpointer).
- Sidebar: `thread_id`, «Nueva conversación» (nuevo `thread_id`), subida de imagen o imagen demo,
  bloque HITL con el plan, comentario y botones **Aprobar / Rechazar**, límites activos.
- El chat se deshabilita mientras hay un plan pendiente.
- Expander debug: flags (`thread_id`, `turnos`, `hitl_pendiente`, `done`), tabla de trazas de tools
  (especialista, tool, categoría, status, ms, args, preview), log del grafo e historial HITL.
