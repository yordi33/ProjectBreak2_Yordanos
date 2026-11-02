"""Streamlit: cliente del grafo (sin lógica de grafo aquí).

Chat + HITL en la barra lateral (Aprobar / Rechazar) + expander de debug
(log, traza de tools, thread_id, flags HITL/done) + «Nueva conversación» = nuevo thread_id.
Ejecutar: streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import IMAGEN_DEMO, MAX_ITER, MAX_STEPS, MAX_TURNS
from src.agent import aprobar_plan, historial, procesar_turno
from src.state import EstadoProducto
from src.tools import CATEGORIA
from src.tools.describir_imagen import UPLOADS_DIR

st.set_page_config(page_title="InfoSport Agente", page_icon="🏟️", layout="centered")


def _reset() -> None:
    st.session_state.estado = EstadoProducto()
    st.session_state.mensajes = [{
        "role": "assistant",
        "content": "Hola, soy **InfoSport Agente**. Pregúntame por normas de las instalaciones deportivas "
                   "municipales de Madrid, clasificaciones y partidos de los Juegos Deportivos Municipales, "
                   "polideportivos, el tiempo… o adjunta una imagen de un cartel. Antes de cerrar te "
                   "propondré un plan para que lo apruebes o rechaces.",
    }]


if "estado" not in st.session_state:
    _reset()
estado: EstadoProducto = st.session_state.estado

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("InfoSport Agente")
    st.caption(f"thread_id: `{estado.thread_id}`")
    if st.button("🆕 Nueva conversación", use_container_width=True):
        _reset()
        st.rerun()

    st.subheader("Imagen (multimodal)")
    subida = st.file_uploader("Adjunta una imagen al próximo mensaje", type=["png", "jpg", "jpeg"])
    usar_demo = st.checkbox("Usar assets/imagen_demo.png", value=False)

    st.subheader("Revisión humana (HITL)")
    if estado.hitl_pendiente:
        st.warning("Plan pendiente de tu decisión")
        for p in estado.ultimo_plan:
            st.markdown(f"- {p}")
        comentario = st.text_input("Comentario (opcional)")
        c1, c2 = st.columns(2)
        decision = None
        if c1.button("✅ Aprobar", use_container_width=True, type="primary"):
            decision = True
        if c2.button("❌ Rechazar", use_container_width=True):
            decision = False
        if decision is not None:
            with st.spinner("Aplicando decisión…"):
                aprobar_plan(estado, decision, comentario)
            texto = ("✅ Plan **aprobado**. Conversación cerrada (`done=True`)." if decision
                     else "❌ Plan **rechazado**. Puedes enviar otro pedido en el mismo hilo.")
            st.session_state.mensajes.append({"role": "assistant", "content": texto})
            st.rerun()
    elif estado.done:
        st.success("Último plan aprobado · done=True")
    else:
        st.info("Sin plan pendiente")
    st.caption(f"Límites: MAX_ITER={MAX_ITER} · MAX_STEPS={MAX_STEPS} · MAX_TURNS={MAX_TURNS}")

# ------------------------------------------------------------------ chat
st.title("🏟️ InfoSport Agente")
st.caption("Deporte municipal de Madrid · LangGraph multiagente + RAG + HITL")

for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("imagen"):
            st.image(m["imagen"], width=280)

bloqueado = estado.hitl_pendiente
prompt = st.chat_input("Apruebe o rechace el plan en la barra lateral" if bloqueado else "Tu pregunta…",
                       disabled=bloqueado)
if prompt:
    imagen = None
    if subida is not None:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        destino = UPLOADS_DIR / subida.name.replace("/", "_").replace("\\", "_")
        destino.write_bytes(subida.getvalue())
        imagen = str(destino)
    elif usar_demo:
        imagen = str(IMAGEN_DEMO)
    st.session_state.mensajes.append({"role": "user", "content": prompt, "imagen": imagen})
    with st.chat_message("user"):
        st.markdown(prompt)
        if imagen:
            st.image(imagen, width=280)
    with st.chat_message("assistant"):
        with st.status("Supervisor y especialistas trabajando…", expanded=False) as s:
            procesar_turno(estado, prompt, imagen=imagen)
            s.update(label="Plan listo para revisión" if estado.hitl_pendiente else "Hecho", state="complete")
        if estado.error:
            contenido = f"⚠️ {estado.error}"
        else:
            plan = "\n".join(f"- {p}" for p in estado.ultimo_plan)
            contenido = f"{estado.ultima_respuesta}\n\n**Plan propuesto** (apruébalo o recházalo en la barra lateral):\n{plan}"
        st.markdown(contenido)
    st.session_state.mensajes.append({"role": "assistant", "content": contenido})
    st.rerun()

# ------------------------------------------------------------------ debug
with st.expander("🔍 Debug: log, tools, thread_id y flags"):
    st.json(estado.flags())
    st.markdown("**Traza de tools**")
    if estado.trazas:
        st.dataframe(
            pd.DataFrame([{
                "turno": t.get("turno"), "especialista": t.get("especialista"), "tool": t["tool"],
                "categoría": CATEGORIA.get(t["tool"], "?"), "status": t["status"], "ms": t["ms"],
                "args": str(t["args"]), "preview": t["preview"],
            } for t in estado.trazas]),
            hide_index=True, width="stretch",
        )
    else:
        st.caption("Todavía no se ha llamado a ninguna tool.")
    st.markdown("**Log del grafo**")
    st.code("\n".join(estado.log) or "(vacío)", language="text")
    st.markdown("**Historial HITL del hilo**")
    st.json(historial(estado))
