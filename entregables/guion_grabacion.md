# Guion de grabación · InfoSport Agente (~10 min)

Soporte visual: `entregables/presentacion_infosport_agente.pdf` (15 diapositivas).
Bloques: **A · Producto ≈ 4 min** (diapositivas 1-6) y **B · Técnico ≈ 6 min** (diapositivas 7-15), con demos en vivo intercaladas.

---

## Antes de grabar (10 min de preparación)

1. Abre una terminal en la carpeta del proyecto y activa el entorno:
   ```bash
   cd C:\TheBridge\ProjectBreak2_Yordanos
   .venv\Scripts\activate
   ```
2. Comprueba que la API key responde, porque la cuota gratuita de Gemini se agota:
   ```bash
   python main.py --rag "¿Qué sanción tienen las infracciones leves?"
   ```
   Si da error o tarda mucho, espera un rato o cambia la clave en `.env`.
3. Arranca Streamlit en otra terminal y déjalo abierto en el navegador:
   ```bash
   streamlit run app.py
   ```
4. Ten preparadas tres ventanas: el **PDF** a pantalla completa, la **terminal** con letra grande (Ctrl + rueda) y el **navegador** con Streamlit.
5. Abre GitHub (`github.com/yordi33/ProjectBreak2_Yordanos`) en una pestaña para la diapositiva 13.
6. Graba con la Xbox Game Bar (Win + G) u OBS. Cierra las notificaciones.

> Consejo: haz las demos en vivo, pero si Gemini falla, enseña las capturas del README (`docs/img/`). Muestran exactamente lo mismo.

---

## A · Producto (≈ 4 min)

### 1 · Portada (15 s)
> «Hola, soy Yordanos. Os presento **InfoSport Agente**, un asistente multiagente sobre el deporte municipal de Madrid, construido con LangGraph para el Project Break 2.»

### 2 · El problema (40 s)
> «Si usas los polideportivos de Madrid, la información está repartida: el reglamento es un PDF de 25 páginas, las clasificaciones y los partidos son CSV de miles de filas, los horarios de los centros están en el open data y, además, influyen cosas como el tiempo o lo que pone en un cartel.
> Un chatbot genérico se inventa la respuesta, y un buscador te obliga a abrir cuatro webs.»

### 3 · La solución (45 s)
> «InfoSport Agente funciona como un equipo. Un supervisor entiende lo que pides y reparte el trabajo entre tres especialistas. Cada uno consulta fuentes reales con herramientas. Si un dato no está en las fuentes, el agente lo dice en lugar de inventarlo. Y antes de cerrar te propone un plan que **tú apruebas o rechazas**.»

Señala el ejemplo de la derecha.

### 4 · Dominio y datos (30 s)
> «Todos los datos son públicos y de Madrid: el reglamento oficial, las clasificaciones y los partidos de los Juegos Deportivos Municipales, la API de centros deportivos y Open-Meteo para el tiempo. Elegí este dominio porque continúa el PB1 y mezcla texto, tablas y datos en vivo.»

### 5 · Pieza del puzzle (25 s)
> «Es la segunda pieza del proyecto. El RAG del PB1 no se sustituye: el agente lo llama como una tool más, a través de su función `responder`. En la tercera pieza lo empaquetaremos y desplegaremos con MLOps.»

### 6 · Demo de uso (1 min 30 s) · **EN VIVO en Streamlit**
1. Cambia al navegador. Escribe:
   *«¿A qué hora cierra la taquilla del CDM La Elipa y hace buen tiempo hoy para correr?»*
2. > «Fijaos en que el supervisor manda el pedido al especialista de instalaciones, que llama a la API de polideportivos y a la del tiempo. La respuesta cita de dónde sale cada dato.»
3. Señala la barra lateral: > «El plan queda **en pausa**. El chat está bloqueado hasta que yo decida.»
4. Pulsa **Rechazar**. > «Lo rechazo: el plan se descarta, pero la conversación sigue.»
5. Escribe: *«¿Qué multa máxima hay para una infracción muy grave?»* → espera → **Aprobar**.
   > «Ahora consulta el RAG del reglamento: hasta 3.000 euros, artículo 60. Lo apruebo y la conversación se marca como terminada, `done=True`.»

---

## B · Técnico (≈ 6 min)

### 7 · Grafo (50 s)
> «Por dentro es un StateGraph de LangGraph. El supervisor elige un especialista; cada especialista vuelve al supervisor con sus notas; cuando hay datos suficientes pasa a sintetizar, que escribe la respuesta y el plan. Con el plan listo va a `aplicar`, y ahí está el **interrupt_before**: el grafo se para hasta que decide un humano.
> Lo importante es que las reglas están en Python: el supervisor no puede elegir un nodo que no existe ni repetir especialista, hay un máximo de 6 vueltas y `done` solo lo cambia `aplicar`.»

### 8 · Tools (40 s)
> «Hay seis tools: el RAG, dos APIs externas, una consulta estructurada de partidos, la hora y la de imágenes. El LLM solo **propone** qué tool usar; `ejecutar_tool` comprueba la allowlist general y la del especialista. Si no está permitida, queda bloqueada. Cada llamada deja una traza con argumentos, estado y milisegundos.»

**EN VIVO** (terminal, 15 s):
```bash
python main.py --tool borrar_todo
```
> «Una tool inventada queda `bloqueada`.»

### 9 · RAG (50 s) · **EN VIVO**
```bash
python main.py --rag "¿Cuántas calorías se queman en las barcas de recreo?"
```
> «El RAG es el del PB1 con mejoras: 1.674 chunks en Chroma, top-4 y respuesta en JSON con un campo de evidencia. Esta pregunta no está en el corpus y **se abstiene**: `hay_evidencia` es false. Antes vimos una pregunta del corpus respondida con su fuente.»

### 10 · HITL y persistencia (45 s)
> «El HITL funciona así: `procesar_turno` invoca el grafo con un `thread_id` y se para antes de `aplicar`. `aprobar_plan` escribe la decisión con `update_state` y reanuda con `invoke(None)`. Si apruebo, `done=True`; si rechazo, se descarta el plan y el hilo sigue. El checkpointer es `MemorySaver`. Como extra, con `SqliteSaver` un plan pendiente sobrevive a cerrar el programa.»

**EN VIVO** (opcional, 40 s): abre el expander **Debug** en Streamlit.
> «Aquí se ven el `thread_id`, los flags HITL y `done`, la traza de tools y el log de cada nodo.»

### 11 · Multimodal (45 s) · **EN VIVO en Streamlit**
1. Pulsa **Nueva conversación** (> «nuevo `thread_id`»), marca **Usar assets/imagen_demo.png** y pregunta:
   *«Lee este cartel: ¿qué horario tiene la taquilla el sábado?»*
2. > «El supervisor manda el pedido al especialista de imagen, que usa Gemini visión. La ficha está generada con datos reales del open data, y responde 14:30 sin inventar nada.»
3. Aprueba el plan.

### 12 · Límites y robustez (30 s)
> «Todos los límites están en `config.py`: MAX_ITER, MAX_STEPS, MAX_TURNS. Si el LLM falla, el supervisor decide por palabras clave y cada especialista llama a su tool principal. Si un modelo se queda sin cuota, se salta al siguiente de una cadena de cinco. Y si no hay red, las APIs usan un JSON local, marcado en la traza.»

### 13 · Git y SDD (30 s) · enseña GitHub
> «Trabajé con `main`, `develop` y una rama por bloque, integradas con merge. Antes de programar escribí specs para cada parte, en la carpeta `specs/`, y las usé para dirigir al asistente de código. Al final verifiqué todo desde un clon limpio. No hay secretos en el repo: la clave está en `.env`, que está ignorado.»

### 14 · Tres fallos (50 s)
> «Tres fallos reales:
> Uno, la cuota diaria de embeddings de Gemini se agotó a mitad del indexado; pasé a embeddings locales y ahora indexa en 80 segundos. En MLOps el índice sería un artefacto versionado.
> Dos, modelos saturados o sin cuota a mitad de la demo; lo resolví con la cadena de modelos y los fallbacks. En MLOps añadiría métricas y alertas por modelo.
> Tres, el entorno Windows: certificados SSL y un runtime de Visual C++ antiguo que tumbaba Chroma. La solución definitiva es un contenedor Docker, que es justo la pieza 3.»

### 15 · Cierre (15 s)
> «Todo está en el repositorio, con el README, las capturas, el informe y las specs. Gracias.»

---

## Si algo falla durante la grabación

| Problema | Qué hacer |
|---|---|
| La respuesta tarda más de 40 s | Corta el silencio al editar, o di «el modelo está saturado, por eso hay una cadena de fallback» y sigue |
| Error 429 / respuestas pobres | Cambia la clave en `.env`, reinicia Streamlit y repite la toma |
| Streamlit no arranca (puerto ocupado) | `streamlit run app.py --server.port 8502` |
| Falla el RAG («No existe el índice») | `python main.py --prepare --index` (2 min) |
