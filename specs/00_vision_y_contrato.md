# Spec 00 — Visión, alcance y contrato

> Spec-Driven Development: cada feature se especificó aquí **antes** de implementarla y la spec
> se usó como guía de la implementación. Si el código y la spec discrepan, manda la spec
> (y se actualiza la spec en el mismo commit si se cambia de idea).

## Tema
**InfoSport Agente**: asistente de deporte municipal de Madrid. Reutiliza el RAG del Project
Break 1 (reglamento de instalaciones deportivas municipales + Juegos Deportivos Municipales) y
lo amplía con datos abiertos en vivo (polideportivos, tiempo) y lectura de carteles.

## Qué SÍ resuelve
- Normas del Reglamento de instalaciones deportivas municipales (derechos, obligaciones, sanciones…).
- Clasificaciones por grupo de las competiciones municipales 2025/2026 (RAG sobre el CSV).
- Partidos concretos: por equipo, fecha, estado o deporte (tool estructurada sobre el CSV).
- Polideportivos municipales: dirección, distrito, horario de taquilla, cómo llegar (API datos.madrid.es).
- Tiempo actual en Madrid para actividad al aire libre (API Open-Meteo).
- Fecha/hora actual (plazos, «¿está abierto ahora?»).
- Leer un cartel / panel / folleto en imagen (multimodal).

## Qué NO resuelve (debe abstenerse o decir que no puede confirmarlo)
- Información fuera del corpus y de las tools (p. ej. calorías, precios no presentes en el corpus).
- Hacer reservas o pagos reales: el agente **propone un plan**, no ejecuta acciones externas.
- Inventar datos cuando una tool falla o no encuentra evidencia.

## Contrato (igual para CLI y Streamlit)
```
procesar_turno(estado: EstadoProducto, mensaje: str, imagen: str|None) -> EstadoProducto
aprobar_plan(estado: EstadoProducto, aprobar: bool, comentario: str = "") -> EstadoProducto
```
- `EstadoProducto` (src/state.py): `thread_id, turnos, hitl_pendiente, done, ultima_respuesta,
  ultimo_plan, log, trazas, error`.
- Un `thread_id` = una conversación en el checkpointer. «Nueva conversación» = nuevo `thread_id`.
- Mientras `hitl_pendiente=True` no se aceptan nuevos pedidos (error explícito).
- `done=True` solo lo fija el nodo `aplicar` tras una aprobación humana.

## Datos y privacidad
Solo datos públicos (datos.madrid.es, sede.madrid.es, Open-Meteo), uso educativo. Sin secretos en
el repo: la API key va en `.env` (ignorado por git).
