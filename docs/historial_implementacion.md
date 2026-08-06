# Historial de implementación por commit

Este archivo lleva un registro narrativo de lo que se implementa en cada commit del
proyecto **Puente LSCh**. Es un complemento del `git log`: acá se explica **qué se hizo
y por qué**, no solo qué archivos cambiaron.

## Convención

Cada entrada debe incluir:

- **Encabezado** con fecha ISO (`YYYY-MM-DD`), hash corto del commit (si ya se conoce)
  y referencia a la speccubierta (si aplica).
- **Resumen** de 1–2 frases del objetivo del commit.
- **Cambios** concretos (archivos o módulos nuevos/modificados, comportamiento
  añadido).
- **Verificación** ejecutada para darlo por bueno (comandos o comprobaciones).
- **Notas** opcionales (decisiones diferidas, seguimientos).

Regla: **antes de cada `git commit`** se debe agregar (o actualizar) la entrada
correspondiente en este archivo. Esto aplica a sesiones automatizadas (opencode y
similares) y a commits manuales.

---

## 2026-07-22 — `5aeee70` — Implementación inicial · scaffold + hello world WebSocket
**Refs:** SPEC-001 `specs/SPEC-001-fundacion-proyecto.md` (Completada)

**Resumen:** Se levantó la fundación del repositorio: estructura de carpetas del
proyecto, backend FastAPI mínimo con WebSocket de eco, frontend PWA React+Vite
gestionado con `pnpm`, y orquestación con Docker Compose.

**Cambios:**
- Raíz: `.gitignore`, `README.md`, `AGENTS.md`, `docker-compose.yml`.
- Backend (`backend/`):
  - `app/main.py` — FastAPI con `GET /health` y `WebSocket /ws/echo`
    (eco con timestamps ISO-8601).
  - `requirements.txt` (`fastapi`, `uvicorn[standard]`, `ruff`).
  - `.env.example`, `Dockerfile` (python:3.11-slim), `.dockerignore`, `data/.gitkeep`.
- Frontend (`frontend/`):
  - `package.json` con `packageManager: pnpm@9`, `vite.config.js` con
    `vite-plugin-pwa` (manifest + service worker), `index.html`.
  - `src/main.jsx`, `src/App.jsx` (input + panel de eco vía WebSocket),
    `src/App.css`, `public/icon.svg`.
  - `Dockerfile` (build Vite + nginx estático, con `ARG VITE_WS_URL`).
  - `.dockerignore`.
- `ml/.gitkeep` para reservar directorio de scripts de experimentación.
- `specs/SPEC-001-fundacion-proyecto.md` + `specs/README.md` (flujo de trabajo
  a base de specs).

**Verificación:**
- `ruff check backend` → `All checks passed!`
- `pnpm install` + `pnpm build` en `frontend/` → build OK, PWA generada
  (sw.js + manifest.webmanifest).
- Backend en local: `GET /health` → `{"status":"ok"}`.
- WebSocket `/ws/echo` → eco correcto con `received_at` / `echoed_at`.
- (Pendiente de ejecutar por el usuario) `docker compose up --build`.

**Notas:**
- Gestor de paquetes JS fijado a **pnpm** (no npm/yarn).
- No se incluyeron submódulos vacíos (`asr/`, `glossary/`, etc.) — se
  introducirán en sus specs correspondientes.
- Próxima spec prevista: SPEC-002 (backend completo del flujo profesor→alumno).

## 2026-07-22 — `7d17881` — Registro de hash en historial
**Refs:** docs/historial_implementacion.md

**Resumen:** Commit mínimo para sincronizar el hash `5aeee70` en el historial de
implementación, cumpliendo la regla de AGENTS.md.

**Cambios:**
- `docs/historial_implementacion.md` — hash añadido al encabezado de la entrada
  SPEC-001.

**Verificación:** n/a (commit documental).

---

## 2026-07-22 — `72d0c35` — Backend completo del flujo profesor→alumno
**Refs:** SPEC-002 `specs/SPEC-002-backend-flujo-profesor-alumno.md` (Completada)

**Resumen:** Se implementó el backend completo del núcleo profesor→alumno:
arquitectura modular con ASR streaming (capa abstracta con Google v2 + stub),
glosario SQLite, motor de coincidencia por lema con spaCy, WebSockets de
profesor/alumno con broadcast por sala, y logging mínimo de segmentos para
evaluación futura.

**Cambios:**
- **Nuevos submódulos** en `backend/app/`:
  - `core/config.py` — settings con pydantic-settings (`.env`).
  - `core/nlp.py` — singleton de spaCy (`es_core_news_md`).
  - `core/db.py` — conexión SQLite + init schema.
  - `asr/base.py` — interfaz `StreamingASRProvider` + `ResultadoASR` + factory.
  - `asr/stub.py` — `StubAsrProvider` (sin credenciales, frases prefijadas).
  - `asr/google_streaming.py` — `GoogleStreamingProvider` (v2 streaming, es-CL).
  - `glossary/schema.py` — gestión de esquema SQLite.
  - `glossary/repository.py` — CRUD curso/termino + seed idempotente.
  - `glossary/matching.py` — `buscar_terminos()` con lematización spaCy + n-gramas,
    filtrando stopwords (DET, ADP, CCONJ, SCONJ).
  - `evaluation/logging.py` — persistir sesiones y segmentos en SQLite.
  - `signs_recognition/__init__.py` — placeholder (módulo secundario, fuera de spec).
- **Endpoints** en `backend/app/main.py`:
  - `GET /health` (mantenido de SPEC-001).
  - `GET /api/cursos` — lista de cursos sembrados.
  - `GET /api/cursos/{id}/glosario` — términos del curso.
  - `POST /api/sesiones` — crear sesión de clase.
  - `WebSocket /ws/profesor?curso_id=...` — recibe audio/texto, ejecuta ASR +
    matching, emite eventos `{segmento, senas}` a la sala.
  - `WebSocket /ws/alumno/{curso_id}` — se une a sala, recibe eventos broadcast.
  - `WebSocket /ws/echo` (mantenido de SPEC-001).
  - `StaticFiles /data/videos_senas` — sirve clips MP4 de señas.
- **Esquema SQLite** (`data/schema.sql`): `curso`, `termino`, `sesion`, `segmento`.
- **Seed** (`scripts/seed_glosario.py` + `data/seed_glosario.json`): 1 curso piloto
  con 12 términos (lemas ajustados a spaCy real), 12 placeholders MP4.
- **Tests** (`backend/tests/`):
  - `test_schema.py` — creación, idempotencia, FK de esquema SQLite.
  - `test_matching.py` — n-grama largo, varios matches, flexiones verbales, sin match.
- **Actualizaciones:**
  - `requirements.txt` — `spacy>=3.8`, `pydantic-settings`, `pytest`, `pytest-asyncio`,
    `google-cloud-speech`.
  - `Dockerfile` — descarga `es_core_news_md`, ejecuta seed al arrancar.
  - `.env.example` — variables nuevas (`ASR_PROVIDER`, `SPACY_MODEL`, `DB_PATH`, etc.).
  - `AGENTS.md` — comando `pytest backend/tests` añadido a verificación mínima.
  - `specs/README.md` — SPEC-002 marcada como Completada.
  - `specs/SPEC-002-backend-flujo-profesor-alumno.md` — estado actualizado.

**Verificación:**
- `ruff check backend` → `All checks passed!`
- `pytest backend/tests` → 10/10 passed (matching + schema).
- Smoke end-to-end con `ASR_PROVIDER=stub`:
  - `GET /health` → `{"status":"ok"}`
  - `GET /api/cursos` → 1 curso.
  - `GET /api/cursos/1/glosario` → 12 términos.
  - `POST /api/sesiones?curso_id=1` → `sesion_id=1`.

**Notas:**
- Los lemas del glosario se ajustaron a los lemas reales que spaCy `es_core_news_md`
  devuelve (e.g., "derivada" → lema "derivado", "raíz cuadrada" → "raíz cuadrado").
  Esto es un requisito para que el matching por lema funcione correctamente.
- El matching filtra stopwords (DET, ADP, CCONJ, SCONJ) antes de buscar n-gramas,
  para que "teorema del valor medio" coincida con el lema "teorema valor medio".
- `GoogleStreamingProvider` requiere credenciales de Google Cloud; sin ellas,
  usar `ASR_PROVIDER=stub` para desarrollo.
- El frontend de SPEC-001 sigue funcionando con el backend nuevo (mismo `/ws/echo`).
- Próxima spec prevista: SPEC-003 (PWA con vistas profesor/alumno + captura de
  audio + reproducción de video de señas).

## 2026-07-23 — `75132e3` — PWA completa: vistas profesor y alumno
**Refs:** SPEC-003 `specs/SPEC-003-pwa-vistas-profesor-alumno.md` (Completada)

**Resumen:** Se implementó la PWA completa del proyecto con dos vistas reales:
profesor (captura de audio con getUserMedia + MediaRecorder, envío de chunks
binarios por WebSocket) y alumno (recepción de subtítulos en tiempo real +
reproducción de videos de señas). Se reemplazó el demo de eco de SPEC-001 con
una arquitectura de routing por hash, selección de curso, y hook reutilizable
de WebSocket.

**Cambios:**
- **Nuevos archivos** en `frontend/src/`:
  - `hooks/useWebSocket.js` — hook reutilizable: conexión, reconexión simple,
    send, estado (conectado/desconectado).
  - `api/cliente.js` — fetch helper para endpoints REST (`fetchCursos`,
    `fetchGlosario`, `crearSesion`).
  - `views/Landing.jsx` — landing con botones "Soy profesor" / "Soy alumno".
  - `views/ProfesorView.jsx` — captura de audio con getUserMedia +
    MediaRecorder (WebM/Opus, chunks 250ms), envío binario por WebSocket,
    indicador de estado (idle/conectando/grabando/detenido), contador de
    chunks, tiempo transcurrido, manejo de errores de permisos.
  - `views/AlumnoView.jsx` — conexión a `/ws/alumno/{curso_id}`, panel de
    subtítulos en vivo (final consolidado + provisional), panel de señas
    (reproducción automática de videos), control de tamaño de fuente (A+/A-).
  - `components/CursoSelector.jsx` — dropdown reutilizable cargado desde
    `GET /api/cursos`.
  - `components/Subtitulos.jsx` — render de subtítulos con scroll automático,
    distinción final/provisional.
  - `components/SenaPlayer.jsx` — reproductor de video de señas (autoPlay,
    muted, loop) con label de texto visible.
  - `components/EstadoConexion.jsx` — indicador visual de estado WebSocket.
- **Archivos modificados:**
  - `App.jsx` — routing por hash (`#/profesor`, `#/alumno`, landing por defecto).
  - `App.css` — tema completo (landing, vistas, subtítulos, señas, responsive).
  - `vite.config.js` — limpieza (ya no usa VITE_WS_URL hardcodeado al echo).
  - `frontend/Dockerfile` — soporte para ARG `VITE_API_URL` además de
    `VITE_WS_URL`.
  - `docker-compose.yml` — args de frontend actualizados, `ASR_PROVIDER=stub`
    en backend.
  - `specs/README.md` — SPEC-003 marcada como Completada.
  - `specs/SPEC-003-pwa-vistas-profesor-alumno.md` — estado actualizado.

**Verificación:**
- `pnpm build` → build OK, PWA generada (sw.js, manifest, 39 módulos).
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 10/10 passed (no se tocó backend).
- `docker compose up --build` → levanta backend + frontend correctamente.
- Stub end-to-end: alumno recibe frases automáticas del stub y ve videos de
  señas cuando hay coincidencia con el glosario.

**Notas:**
- El hook `useWebSocket` maneja `null` url (no conecta) — útil cuando no hay
  curso seleccionado.
- Los videos de señas son placeholders (archivos mínimos sin contenido real);
  se reproducen sin error pero no muestran video real — se reemplazan cuando
  el autor grabe los clips.
- La reconexión WebSocket es simple (1 intento cada 3s); no hay backoff
  exponencial todavía.
- Próxima spec prevista: SPEC-004 (piloto de evaluación: WER, latencia, SUS).

## 2026-07-23 — `d444cfc` — Perfil único centrado en el estudiante + sesiones en vivo con fan-out + historial con replay
**Refs:** SPEC-004 `specs/SPEC-004-perfil-estudiante-sesiones-fanout-historial.md` (Completada)

**Resumen:** Reestructuración mayor del sistema. Se eliminó el modelo "profesor →
alumno" y se migró a un perfil único centrado en el estudiante con autenticación
(RUT + contraseña, JWT), dashboard académico, gestión de salas pub/sub con fan-out,
y un sistema completo de historial con replay de clases.

**Cambios:**

- **Backend — Modelo de datos:**
  - `schema.sql` ampliado con tablas `usuario`, `inscripcion`, `clase`, `evento_clase`.
  - `curso` ahora incluye `cod_ramo` (ej. "INF-221").
  - Identificador de sala: `[COD_RAMO]-[SECCION]` (ej. `INF-221-SEC1`).

- **Backend — Auth (`app/auth/` + `app/core/auth.py`):**
  - `POST /api/auth/login` — login con RUT + password, devuelve JWT.
  - `GET /api/auth/usuario/me?rut=...` — datos del usuario + carga académica.
  - JWT firmado con HS256, expiración 1h. Hash de passwords con SHA-256 + salt.
  - Preparado para migrar a SSO/OAuth2 con Intranet institucional en el futuro.

- **Backend — Salas (`app/salas/manager.py`):**
  - `RoomManager` con `RoomState`: emitter_ws, listeners (set), timeline en memoria.
  - Patrón pub/sub (fan-out): el audio se procesa una sola vez, resultado broadcast.
  - `RoomManager.existe()`, `.crear()`, `.obtener()`, `.agregar_listener()`, `.broadcast()`, `.eliminar()`.
  - Soporte para pausa/reanudación implícita (cuando el emisor deja de enviar audio).
  - Finalización con persistencia automática del timeline.

- **Backend — Historial (`app/historial/`):**
  - `repository.py` — CRUD `clase`/`evento_clase`: crear, finalizar, guardar evento, listar, detalle.
  - `routes.py` — `GET /api/historial?rut=...`, `GET /api/historial/{clase_id}`, `GET /api/salas/{room_id}/estado`.

- **Backend — main.py refactor:**
  - `WebSocket /ws/sala/{room_id}?rol=emitter|listener&token=...` unificado.
  - Eliminados `/ws/profesor` y `/ws/alumno/{curso_id}` (reemplazados por `/ws/sala`).
  - `POST /api/sesiones` eliminado (creado implícito al iniciar sala).
  - `/api/cursos?rut=...` ahora devuelve asignaturas inscritas del estudiante.
  - CORS middleware añadido.

- **Backend — Seed y configuración:**
  - `seed_glosario.json` ampliado: 2 cursos con cod_ramo, 1 usuario, 3 inscripciones.
  - `seed_glosario.py` siembra usuarios e inscripciones (DELETE ALL + INSERT).
  - `requirements.txt` añade `PyJWT`, `httpx`.
  - `config.py` + `.env.example` añaden `JWT_SECRET`, `SALA_TIMEOUT_MS`, `AUTH_PROVIDER`.

- **Backend — Tests (21/21):**
  - `test_auth.py` — login válido, login inválido, usuario/me, cursos con rut, health.
  - `test_sala.py` — sala estado sin sala, listener sin sala.
  - `test_historial.py` — historial lista, detalle, no encontrado.
  - `test_schema.py` + `test_matching.py` — actualizados y mantenidos.

- **Frontend — Auth:**
  - `useAuth.js` — hook con login, logout, persistencia en localStorage.
  - `LoginView.jsx` — formulario RUT + contraseña, manejo de errores.

- **Frontend — Nueva estructura de vistas:**
  - `DashboardView.jsx` — lista de asignaturas inscritas con estado en vivo, botón Entrar.
  - `SalaView.jsx` — vista unificada emisor/listener.
    - Emisor: `getUserMedia` + `MediaRecorder` (chunks 250ms), pausar/reanudar/finalizar.
    - Listener: recibe subtítulos + señas en tiempo real.
    - Clase finalizada: notificación + link a historial.
  - `HistorialView.jsx` — lista de clases guardadas (asignatura, fecha, duración).
  - `ClaseDetailView.jsx` — dos modos:
    - Modo Apunte: transcripción completa como texto continuo con badges de señas.
    - Modo Replay: reproductor interactivo que simula la traducción en vivo con Play/Pausa/velocidad 1x-2x.
  - `ReplayPlayer.jsx` — reproductor de timeline con barra de progreso.
  - `ControlesEmisor.jsx` — iniciar/pausar/reanudar/finalizar.

- **Frontend — Eliminaciones:**
  - `Landing.jsx`, `ProfesorView.jsx`, `AlumnoView.jsx` removidos del routing.
  - `App.jsx` refactorizado con nuevas rutas (`#/login`, `#/dashboard`, `#/sala/{id}`, `#/historial`, `#/historial/{id}`).
  - `App.css` reescrito con estilos de login, dashboard, sala, historial, replay, responsive.

- **Frontend — API:**
  - `cliente.js` ampliado: `loginRequest`, `fetchCursosUsuario`, `fetchUsuario`, `fetchSalaEstado`, `fetchHistorial`, `fetchHistorialDetalle`.

**Verificación:**
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 21/21 passed.
- `pnpm --prefix frontend build` → build OK (43 módulos, PWA generada).
- `docker compose up --build` → listo para verificar end-to-end con stub.

**Notas:**
- Cambio de paradigma: el profesor no interactúa con la plataforma. Todo lo gestiona el estudiante.
- El micrófono lavalier se conecta al dispositivo del estudiante; el transmisor se entrega al profesor.
- El timeline de la clase se guarda en SQLite (no audio/video). Replay funcional con controles.
- El sistema está preparado para SSO/OAuth2 con Intranet institucional (interfaz conceptual).
- Stakeholders: comunidad sorda, estudiantes, profesores (indirectamente a través del lavalier).
- Próxima spec prevista: SPEC-005 (piloto de evaluación si se retoma el plan original).

## 2026-07-23 — `8b6f79b` — Rediseño del Dashboard (UI)
**Refs:** Mejora visual (sin spec formal)

**Resumen:** Rediseño completo del Dashboard para coincidir con la UI objetivo:
navbar superior con logo + LSCh Inclusion + tabs Home/History + iconos mic/settings,
tarjeta de usuario con nombre/RUT/badge de micrófono y botón Historial, sección
destacada de "Clase Actual" con título grande y botón "Iniciar Transmisión",
grid de 3 columnas con "Todas mis Asignaturas".

**Cambios:**
- `frontend/src/components/Header.jsx` — **nuevo**: navbar sticky con logo SVG
  (azul), título "LSCh Inclusion", tabs Home/History (con underline azul en activo),
  iconos de micrófono y settings.
- `frontend/src/views/DashboardView.jsx` — rediseñado:
  - Tarjeta de usuario: nombre + RUT formateado + badge "Micrófono Conectado"
    (con punto verde) + botón "Historial de Clases" + botón "Salir".
  - Sección "CLASE ACTUAL" destacada con badge azul, título grande del ramo
    actual, sección y botón primario "Iniciar Transmisión de Clase" con icono
    de micrófono.
  - Sección "Todas mis Asignaturas" con grid de 3 columnas (responsive a
    2 en tablet, 1 en móvil), cada card con título, sección y botón "Iniciar"
    con icono de play.
- `frontend/src/App.css` — reescrito: variables CSS refinadas, header sticky,
  user-card, clase-actual (centrado, tipografía grande), grid de asignaturas
  con `grid-template-columns: repeat(3, 1fr)`, botones con sombras, hover
  states, badges con punto verde animado, responsive breakpoints.
- `backend/data/seed_glosario.json` — ampliado:
  - 4 cursos: INF-221 Estructuras de Datos, MAT-101 Álgebra Lineal,
    FIS-110 Física General, HUM-105 Ética Profesional.
  - Usuario de prueba sigue siendo Juan Pérez (RUT 12345678-9, password test123).
  - Inscrito en los 4 cursos (sección 1 INF-221, sección 3 MAT-101,
    sección 2 FIS-110, sección 1 HUM-105).
  - Glosario con 29 términos distribuidos entre los 4 cursos (comparten
    términos como "duda", "clase", "ejercicio" para que el matching funcione).

**Verificación:**
- `pnpm build` → build OK (44 módulos, CSS 8.38 KB, JS 161 KB).
- La primera asignatura inscrita (INF-221) aparece como "Clase Actual"
  destacada; las otras 3 aparecen en el grid inferior.

**Notas:**
- La lógica de "Clase Actual" es simple: muestra la primera asignatura
  inscrita. Si quieres otra lógica (por horario, por uso reciente, etc.),
  se puede refinar.
- El icono de micrófono en la navbar y el badge "Micrófono Conectado"
  son visuales; el estado real del micrófono se gestiona al iniciar la
  transmisión en la vista de Sala.

## 2026-07-23 — `9317fbb` — Rediseño de la Sala de traducción (UI)
**Refs:** Mejora visual (sin spec formal)

**Resumen:** Rediseño completo de la vista de Sala (traducción en vivo) para
coincidir con la UI objetivo: top bar con Salir/título/badge EN VIVO/settings,
panel izquierdo de subtítulos con control de tamaño A+/A− y términos del
glosario resaltados en bold, panel derecho con reproductor de video de seña
y tarjeta flotante "TRADUCIENDO CONCEPTO CLAVE", bottom bar con estado del
sistema y controles Pausar/Finalizar.

**Cambios:**
- `frontend/src/views/SalaView.jsx` — reescrito:
  - **Top bar:** botón Salir (izq), título centrado con `roomId` formateado
    (ej. "INF-221 — Estructuras de Datos"), badge "EN VIVO" con punto rojo
    pulsante, botón de settings (der).
  - **Layout 2 columnas:** subtítulos (35%) + video (65%).
  - **Panel de subtítulos:** header con icono + "Transcripción en Tiempo Real"
    + A+/A− para tamaño de fuente (12-32px). Subtítulos finales con
    **términos del glosario resaltados** (bold, fondo azul translúcido).
    Estado al pie: "Escuchando al profesor..." con icono de micrófono.
  - **Panel de video:** reproductor con aspect-ratio 16:9, gradiente oscuro,
    botones flotantes (expandir, más opciones) en esquina inferior derecha.
  - **Tarjeta concepto clave:** aparece flotante en esquina inferior izquierda
    cuando se detecta un término, mostrando "TRADUCIENDO CONCEPTO CLAVE" +
    término + icono de mano. Se oculta automáticamente tras 4s.
  - **Bottom bar (solo emisor):** "Estado del Sistema — Audio y video
    sincronizados" (izq) + botones "Pausar/Reanudar Transcripción" (gris
    oscuro) y "Finalizar y Guardar" (rojo con sombra).
- `frontend/src/App.css` — sección de Sala completamente nueva:
  - `.sala`, `.sala-topbar`, `.sala-grid` con grid 2 columnas.
  - `.sala-subtitulos__contenido` con scroll y tamaño de fuente dinámico.
  - `.sala-video__player` con gradiente y aspect-ratio.
  - `.concepto-card` con animación slideIn y backdrop-filter.
  - `.sala-bottombar` con `btn--ghost-pause` y `btn--detener-finalizar`.
  - `.termino` para highlight de glosario.
  - Animación `pulse` para el badge "EN VIVO".

**Verificación:**
- `pnpm build` → build OK (41 módulos, CSS 12.61 KB, JS 166 KB).

**Notas:**
- La función `highlightText` usa regex sobre los `texto_visible` de los
  términos matched para envolverlos en `<strong class="termino">`.
- El título de la sala se construye reemplazando el primer `-` por ` — `
  para mostrar "INF-221 — Estructuras de Datos".
- La tarjeta de concepto se muestra solo cuando hay match, con auto-hide
  tras 4s para no saturar la UI.
- El "EN VIVO" badge está siempre visible (la transmisión está activa
  mientras el emisor no finalice).

## 2026-07-23 — `abcca0f` — Modal de Finalizar Sesión + título de clase
**Refs:** Mejora UX (sin spec formal)

**Resumen:** Se agregó el modal "¿Finalizar Sesión?" con campo de título/nota
opcional al presionar "Finalizar y Guardar". El botón "Salir" del topbar ya
no permite cerrar la pantalla mientras hay una sesión activa sin antes
finalizarla. El título se guarda en la tabla `clase` y se muestra en el
historial y en el detalle de la clase.

**Cambios:**

- **Backend:**
  - `schema.sql` — columna `titulo TEXT` agregada a tabla `clase`.
  - `app/core/db.py` — migración que agrega `titulo` a tablas `clase`
    existentes (ALTER TABLE si la columna no existe).
  - `app/historial/repository.py` — `finalizar_clase` acepta `titulo` opcional.
  - `app/historial/routes.py` — `titulo` incluido en respuestas de
    `/api/historial` y `/api/historial/{id}`.
  - `app/main.py` — WebSocket handler refactorizado con `asyncio.Queue` para
    audio y un receiver task separado. Parsea JSON del emisor para extraer
    `{action: "finalizar", titulo: "..."}` y lo pasa a `finalizar_clase`.

- **Frontend:**
  - `components/FinalizarModal.jsx` — **nuevo**: modal con overlay oscuro
    + blur, header con título "¿Finalizar Sesión?" + botón X, descripción
    explicando que es opcional, input con placeholder "ej. Algoritmos de
    ordenamiento" (max 120 chars, autofocus), botones "Cancelar" (gris) y
    "Guardar y Salir" (azul primario). Cierra con Escape o click fuera.
  - `views/SalaView.jsx`:
    - El botón "Finalizar y Guardar" del bottom bar ahora abre el modal
      en vez de finalizar directamente.
    - El botón "Salir" del topbar, cuando el emisor está grabando, abre
      el modal de finalizar (no deja salir sin finalizar). En otros
      estados (listener, sin iniciar), funciona normal.
    - Al confirmar el modal, se envía por WebSocket
      `{"action":"finalizar","titulo":"..."}` con el título.
  - `views/HistorialView.jsx` — muestra el `titulo` si existe, sino el
    nombre del curso.
  - `views/ClaseDetailView.jsx` — el `h1` principal muestra el `titulo`
    si existe, con fallback a `${cod_ramo} — ${seccion}`. Subtítulo
    muestra el nombre del curso + sección.
  - `App.css` — estilos del modal: `.modal-overlay` con backdrop-filter,
    `.modal` con border, shadow y animación `modalIn`, header/body/footer
    con padding, input con focus azul, animaciones `fadeIn` y `modalIn`.

**Verificación:**
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 21/21 passed.
- `pnpm build` → build OK (42 módulos, CSS 14.39 KB, JS 169 KB).

**Notas:**
- El título es opcional: si se deja vacío, se guarda como `null` en la BD.
- El modal se cierra con Escape, click fuera del modal, o con los botones
  "X" del header o "Cancelar".
- El `Salir` del topbar fue modificado para que durante una sesión activa
  (emitter grabando), su acción sea abrir el modal — garantizando que
  el usuario no pueda salir sin finalizar y guardar.

## 2026-07-23 — `b7e4498` — Fix: esperar a 'Iniciar Transmisión' antes del WebSocket
**Refs:** Bugfix (sin spec formal)

**Resumen:** En modo stub, al entrar a la Sala como emisor el WebSocket se
conectaba inmediatamente y el stub empezaba a emitir frases antes de que el
usuario presionara "Iniciar Transmisión" en el bottom bar. Se refactorizó
SalaView para que el WebSocket solo se conecte cuando el usuario presiona
explícitamente el botón de iniciar (emitter) o cuando ya existe una
transmisión activa (listener).

**Cambios:**
- `frontend/src/views/SalaView.jsx`:
  - Nuevo estado `sesionIniciada` (boolean, default `false`).
  - `useEffect` de WebSocket ahora depende también de `sesionIniciada`;
    solo se conecta cuando es `true`.
  - Para emitter: `sesionIniciada` se setea en `true` dentro de la
    función `iniciar()` (después de obtener permisos de micrófono y
    crear el MediaRecorder).
  - Para listener: `sesionIniciada` se setea en `true` automáticamente
    en el `useEffect` que determina el rol (porque ya hay transmisión
    activa y debe conectarse para recibir el broadcast).
  - El botón "Iniciar Transmisión" del bottom bar ahora se muestra en
    el estado inicial (sin grabar), y al presionarlo se obtiene el
    permiso de micrófono, se inicia MediaRecorder y se activa
    `sesionIniciada` para conectar el WebSocket.
  - El status "Escuchando al profesor..." solo aparece cuando
    `grabando && !pausado`, evitando confusión cuando el stub aún no
    está activo.

**Verificación:**
- `pnpm build` → build OK (42 módulos, CSS 14.39 KB, JS 169 KB).

**Notas:**
- El orden de operaciones en `iniciar()` es: `recorder.start(250)` →
  `setGrabando(true)` → `setSesionIniciada(true)`. Esto garantiza que
  cuando el WS se conecte (tras el re-render), el recorder ya está
  activo. El primer chunk puede llegar 250ms después, tiempo suficiente
  para la conexión.
- El listener no se ve afectado: sigue conectándose automáticamente
  al cargar la Sala si ya hay transmisión activa.

## 2026-07-23 — `50a1df0` — Fix: la clase solo se finaliza explícitamente
**Refs:** Bugfix (sin spec formal)

**Resumen:** En modo stub, al acabarse la lista de frases el WebSocket se cerraba
y el `finally` del handler llamaba automáticamente a `finalizar_clase`,
provocando que la Sala saltara a una pantalla de "Clase finalizada" sin que
el usuario hubiera presionado "Finalizar y Guardar". Se refactorizó para que
la clase solo se marque como finalizada cuando el emisor envía la acción
explícita. Al confirmar el modal, se redirige al dashboard.

**Cambios:**

- **Backend:**
  - `app/asr/stub.py` — el stub ahora itera infinitamente sobre la lista
    de frases (`while True: idx % len(FRASES)`), en vez de emitir una sola
    vez y terminar.
  - `app/main.py` — el `finally` del WebSocket handler del emisor ahora
    solo llama a `finalizar_clase` si `session_state["finalizar"]` es
    `True` (es decir, si el receptor detectó la acción `finalizar`
    explícita del frontend). Si el emisor se desconecta sin finalizar,
    la sala se cierra pero la clase queda en estado "en progreso" en la
    BD y se loggea con un warning.

- **Frontend:**
  - `views/SalaView.jsx`:
    - Eliminado el estado `claseFinalizada` y `claseId`.
    - Eliminado el handler de `data.type === 'clase_finalizada'`.
    - Eliminado el render condicional que mostraba la pantalla
      "Clase finalizada" con botón "Ver en historial".
    - En `confirmarFinalizar`, después de enviar el WebSocket se
      hace `setSesionIniciada(false)` y se redirige a `#/dashboard`
      tras 200ms (para que el WS se cierre limpiamente antes de
      desmontar el componente).

**Verificación:**
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 21/21 passed.
- `pnpm build` → build OK.

**Notas:**
- Si el emisor cierra la pestaña sin finalizar, la clase queda como
  huérfana en la BD. Esto es aceptable para el MVP; se puede limpiar
  con un job periódico o al iniciar la siguiente clase del mismo
  room_id (descartar la anterior sin finalizar).
- El stub ahora nunca termina solo. Solo termina cuando el emisor
  envía la acción `finalizar` o cuando se desconecta el WebSocket.

## 2026-07-23 — `87d24d5` — Altura fija en Sala + ClaseDetailView con mismo layout
**Refs:** Mejora UX (sin spec formal)

**Resumen:** Se corrigió el problema de que la pantalla de Sala se alargaba
hacia abajo a medida que se generaban más transcripciones, empujando los
controles del bottom bar fuera de la vista. Además, se refactorizó
ClaseDetailView para que use el mismo layout visual que SalaView (top
bar + grid 2 columnas + bottom bar condicional) con elementos extras
para visualizar clases guardadas.

**Cambios:**

- **CSS (frontend/src/App.css):**
  - `.sala` ahora usa `height: 100vh` + `overflow: hidden` en vez de
    `min-height: 100vh`, para que la pantalla no crezca con el contenido.
  - `.sala-grid` y `.sala-subtitulos` tienen `min-height: 0` para
    permitir que sus hijos con `overflow-y: auto` hagan scroll interno.
  - `.sala-topbar` y `.sala-bottombar` tienen `flex-shrink: 0` para
    mantenerse fijos.
  - `.sala-subtitulos__contenido` mantiene `overflow-y: auto` con
    `min-height: 0` para scroll interno.
  - Nuevo `.sala-badge-historial` (badge azul "HISTORIAL" en lugar de
    "EN VIVO" rojo).
  - Nuevos `.sala-subtitulos__modos` y `.sala-subtitulos__modo-btn`
    para el toggle Apunte/Replay.
  - Nuevo `.sala-video__placeholder` con icono SVG grande y texto
    descriptivo cuando no hay video de seña.
  - Nuevo `.sala-bottombar__progreso` para la barra de progreso del
    Replay.

- **Frontend (views/SalaView.jsx):**
  - El video player ahora muestra un placeholder "Esperando video de
    la seña..." cuando no hay `conceptoClave`, en vez de quedar vacío.

- **Frontend (views/ClaseDetailView.jsx) — REFACTORIZADO COMPLETO:**
  - Ahora usa la misma estructura que SalaView:
    - Top bar con botón "Volver" (izq), título de la clase (centro),
      badge "HISTORIAL" (der), icono de settings.
    - Grid 2 columnas: panel de subtítulos (izq) + video player (der).
    - Bottom bar condicional (solo en modo Replay) con barra de
      progreso, Play/Pausa, controles de velocidad 1x/1.5x/2x.
  - Header del panel de subtítulos tiene:
    - Título "Transcripción" con icono.
    - Toggle Apunte/Replay con estilo de botones pill.
    - Controles A+/A− para tamaño de fuente.
  - Modo Apunte: muestra todas las frases con términos resaltados.
  - Modo Replay: muestra frases progresivamente, video player muestra
    la seña del concepto actual, bottom bar con controles de
    reproducción.
  - Función `highlightText` copiada para resaltar términos del
    glosario en el texto.
  - Componente interno `ReplayEffect` maneja el timer de avance
    automático basado en `timestamp_ms` y `velocidad`.

**Verificación:**
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 21/21 passed.
- `pnpm build` → build OK (43 módulos, CSS 15.72 KB, JS 174 KB).

**Notas:**
- En el modo Replay, las frases pasadas se muestran con opacidad 0.6
  y la actual con peso 600 para destacar el progreso.
- El `ReplayEffect` usa `setInterval` con un delay calculado como
  `(timestamp_ms[pos+1] - timestamp_ms[pos]) / velocidad`, con un
  mínimo de 200ms para evitar timers demasiado rápidos.
- En móvil (< 600px) el grid cambia a 1 columna con 2 filas
  (subtítulos arriba, video abajo), ambos con scroll interno.

## 2026-07-23 — `886d751` — Rediseño del Historial de Clases
**Refs:** Mejora UX (sin spec formal)

**Resumen:** Se rediseñó completamente la página de Historial de Clases
siguiendo la UI objetivo: header con "Inclusión LSCh" + tabs Inicio/Historial
+ avatar del usuario, título grande "Historial de Clases", subtítulo
descriptivo, search bar con icono, filtros de asignatura y fecha, y cards
de clase en filas horizontales scrollables agrupadas por mes.

**Cambios:**

- **Backend (app/historial/repository.py + routes.py):**
  - `listar_clases` ahora calcula `palabras` (conteo total de palabras
    en `evento_clase.texto` de la clase) y `preview` (primer evento
    estable) usando subqueries en SQL.
  - `GET /api/historial` ahora incluye `palabras` y `preview` en
    cada item de la respuesta.

- **Frontend (components/Header.jsx):**
  - Título cambiado de "LSCh Inclusion" a "Inclusión LSCh" (color
    normal, no azul como antes).
  - Tabs actualizadas a "Inicio" y "Historial" (en español).
  - Tab activa se muestra con color azul (var(--accent)) y underline
    azul, en vez de blanco.
  - Nuevo avatar del usuario (círculo con iniciales) en la derecha
    del header, con gradiente azul.
  - Header acepta prop `user` para generar las iniciales.

- **Frontend (views/DashboardView.jsx):**
  - Pasa `user` al Header para mostrar el avatar.

- **Frontend (views/HistorialView.jsx) — REFACTORIZADO COMPLETO:**
  - Usa el mismo `Header` que el Dashboard.
  - Título grande "Historial de Clases" (2.5rem, 700 weight).
  - Subtítulo descriptivo: "Revisa transcripciones pasadas, notas
    guardadas y momentos destacados de tus sesiones anteriores. Usa
    los filtros para encontrar clases específicas rápidamente."
  - **Search bar** con icono de lupa y placeholder
    "Buscar por título, asignatura o palabras clave...".
  - **Filtro de asignatura** (select dropdown) generado
    dinámicamente desde los cod_ramo de las clases.
  - **Filtro de fecha** (botón "Todas las fechas" con icono de
    calendario) — placeholder para date picker futuro.
  - **Filtrado en tiempo real** (client-side) por texto y asignatura.
  - **Agrupación por mes**: clases agrupadas bajo headers
    "Octubre 2024", "Septiembre 2024", etc. (en español).
  - **Cards horizontales scrollables**: cada fila de mes es un
    scroll horizontal con `scroll-snap-type: x mandatory` y
    `flex: 0 0 320px` por card.
  - **Card estructura:**
    - Header: badge con nombre de asignatura + dot de color (rojo
      para FIS-110, gris para los demás) + fecha/hora.
    - Título (1 línea, truncado con ellipsis).
    - Descripción (3 líneas, truncado con ellipsis, viene del
      `preview` de la primera frase de la transcripción).
    - Footer: metadata (palabras / marcador / pizarras según
      duración) + "Ver clase →" en azul.

- **Frontend (App.css):**
  - `.header__title` color normal, tabs "Inicio"/"Historial"
    con underline azul cuando activas.
  - `.header__avatar` con gradiente azul y hover effect.
  - `.historial-page` con padding generoso y `max-width: 1280px`.
  - `.historial-page__titulo` título grande (2.5rem, 700 weight).
  - `.historial-search` con border azul en focus.
  - `.historial-filtro` select con chevron SVG inline.
  - `.historial-grupo__cards` con scroll horizontal + scroll-snap.
  - `.historial-card` con `flex: 0 0 320px`, hover effect
    (translateY + border azul).
  - `.historial-card__asignatura` badge con dot de color.
  - `.historial-card__titulo` y `__desc` con line-clamp.

**Verificación:**
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 21/21 passed.
- `pnpm build` → build OK (CSS 20.33 KB, JS 178 KB).

**Notas:**
- El dot rojo en la asignatura es solo para FIS-110 (Física
  Mecánica), basado en la convención de "asignatura crítica".
  Se puede extender a más ramos modificando la lógica de
  `historial-card__dot--{cod_ramo}`.
- El tipo de metadata (palabras / marcador / pizarras) se decide
  según la duración de la clase: <10min → palabras, 10-30min →
  marcador, ≥30min → pizarras.
- El filtro de fecha es un placeholder visual; la lógica de
  filtrado por rango de fechas se puede añadir después.
- En móvil, las cards siguen siendo de 320px y se hace scroll
  horizontal dentro del grupo, lo cual es consistente con la UI
  de apps móviles (estilo Netflix/YouTube).

## 2026-08-05 — *(hash pendiente)* — Mejoras de UX: feedback de conexión, reproducción de señas y errores visibles
**Refs:** SPEC-005 `specs/SPEC-005-mejoras-ux-feedback-conexion-senas.md` (Completada)

**Resumen:** Se implementó la auditoría de UX del flujo completo (login → dashboard → sala → historial → replay): feedback real de conexión y errores, reproducción de los videos de señas en vivo y en replay, cierre correcto de salas (fix de un bug donde la clase nunca se finalizaba), auth con token en REST, y limpieza de controles muertos y código huérfano.

**Cambios:**

- **Backend — Auth REST:**
  - `app/core/auth.py` — nuevo helper `obtener_rut(request)` (Bearer token, 401 claro).
  - `app/auth/routes.py` — `GET /api/auth/usuario/me` migrado a token (se elimina `?rut=`).
  - `app/main.py` — `GET /api/cursos` y `GET /api/cursos/{id}/glosario` requieren token.
  - `app/historial/routes.py` — `/api/historial`, `/api/historial/{id}` y `/api/salas/{room_id}/estado` requieren token; detalle valida participación (emisor o inscrito en la sección) → 403 si no (R19/R20).
  - `app/historial/repository.py` — `usuario_participa()`.

- **Backend — Cierre de salas (fix bug crítico + R21/R22):**
  - `app/main.py` — se reestructuró el handler del emisor con `stop_event` + tareas (`_receiver`, `_transcribir`): antes el `async for` de transcripción nunca terminaba (stub infinito + cola bloqueante) y `finalizar_clase` nunca se ejecutaba; la clase quedaba "en progreso" para siempre.
  - Distinción entre finalización explícita (`{action: finalizar}`) y desconexión del emisor: en desconexión se difunde `{type: "emisor_desconectado"}`, se espera `SALA_TIMEOUT_MS` (config) y se guarda el timeline parcial.
  - `_cerrar_listeners()` — al finalizar, se difunde `clase_finalizada` y se cierran los WebSockets de los listeners (antes quedaban 30s colgados en silencio).
  - Loop de listener simplificado (`ws.receive()` con manejo de disconnect).

- **Backend — Tests (29/29):**
  - `test_auth.py` — endpoints con/ sin token (401), login, usuario/me.
  - `test_sala.py` — fan-out + finalizar explícito (título guardado), desconexión de emisor → `emisor_desconectado` + `clase_finalizada` + timeline parcial, segundo emisor rechazado, estado sin token.
  - `test_historial.py` — lista/detalle con token, 401 sin token, 404, 403 sin inscripción.
  - Fixtures con `STUB_INTERVAL_MS=200` y `SALA_TIMEOUT_MS=100` para tests rápidos.

- **Frontend — API y hooks:**
  - `api/cliente.js` — header `Authorization: Bearer` central, manejo de 401 (limpia sesión + evento `puente-auth-expired` + mensaje "Sesión expirada"), `normalizarRut()` (módulo-11 chileno), `getToken()`/`expulsarSesion()`.
  - `hooks/useAuth.js` — escucha el evento `puente-auth-expired` → logout + redirect a `#/login`.
  - `hooks/useWebSocket.js` — reconexión con backoff (3s/6s/12s/24s, máx. 5 intentos), estados `conectado/reconectando/fallo`, `reintentar()` manual, handlers vía ref.

- **Frontend — Componentes:**
  - `components/Feedback.jsx` — **nuevo**: banner de aviso (error/info/warning) con cierre.
  - `components/EstadoConexion.jsx` — **recreado**: indicador conectado/reconectando/desconectado/fallo con dot animado.
  - `components/SenaPlayer.jsx` — **mejorado**: fallback "Video no disponible" ante `onError`, `playsInline`, label del término; en el player 16:9 el video llena con `object-fit: contain` y el label se superpone abajo.
  - `components/Header.jsx` — tabs como `<button>` con `aria-current`.

- **Frontend — Vistas:**
  - `views/SalaView.jsx` — migrado a `useWebSocket`; indicador de conexión en la topbar (EN VIVO solo si conectado); banners de error de WS (`{type: "error"}` con `mensaje`, sin redirección silenciosa); handlers de `clase_finalizada` (aviso + retorno a dashboard en 3s) y `emisor_desconectado`; video real de la seña con `SenaPlayer`; error visible al denegar micrófono; tiempo transcurrido mm:ss del emisor; persistencia de A+/A− en localStorage; eliminados botones muertos (gear, expandir, más opciones) y el estado falso "Audio y video sincronizados"; estado de error si falla la verificación de sala.
  - `views/LoginView.jsx` — normalización y validación de RUT (DV mod-11) antes de enviar; aviso de sesión expirada desde `sessionStorage`.
  - `views/DashboardView.jsx` — estado real "En vivo"/"Sin clase activa" por asignatura (el fetch ya existía pero no se renderizaba); botón dinámico ("Entrar a la clase" / "Iniciar Transmisión de Clase"); eliminado el badge falso "Micrófono Conectado"; estados de carga/error/lista vacía diferenciados con "Reintentar".
  - `views/HistorialView.jsx` — filtro de fecha funcional (select con meses disponibles de las clases, aplicado al filtrado); eliminado el botón placeholder muerto.
  - `views/ClaseDetailView.jsx` — estado de error ("Clase no encontrada" + volver al historial, sin "Cargando..." infinito); replay reproduce el video de la seña actual con `SenaPlayer`; persistencia de A+/A−; eliminados botones muertos.

- **Frontend — Limpieza (R23):** eliminados `views/Landing.jsx`, `views/ProfesorView.jsx`, `views/AlumnoView.jsx`, `components/CursoSelector.jsx`, `components/Subtitulos.jsx`, `components/ControlesEmisor.jsx`, `components/ReplayPlayer.jsx` (huérfanos desde SPEC-004; el replay vive en `ClaseDetailView`).

- **Frontend — `App.css`:** variables `--accent-soft` (faltante) y `--warning`; estilos de `.feedback`, `.estado-conexion`, `.sena-grid/.sena-item/.sena-video/.sena-label/.sena-error`, estado en vivo del dashboard (`.clase-actual__estado`, `.estado-dot`, `.asignatura-card__estado`).

**Verificación:**
- `ruff check backend` → All checks passed.
- `pytest backend/tests` → 29/29 passed (antes 21).
- `pnpm --prefix frontend build` → build OK sin warnings (44 módulos, PWA generada).

**Notas:**
- Fix implícito importante: antes de esta spec, el flujo "Finalizar y Guardar" nunca persistía la clase (el `async for` de transcripción bloqueaba la finalización del handler); ahora se detecta con `stop_event` y tareas.
- La desconexión del emisor sin "Finalizar" ahora guarda el timeline parcial tras `SALA_TIMEOUT_MS` (comportamiento de SPEC-004 R5 que no se había implementado).
- Diferido (SPEC-005 §9): catch-up de listeners tardíos, "reclamar emisor", notificaciones push.

## 2026-07-23 — `0142dc0` — Fix: position: fixed en .sala para evitar scroll de página
**Refs:** Bugfix (sin spec formal)



**Resumen:** Aunque `.sala` ya tenía `height: 100vh` y `overflow: hidden`,
el `body`/`html` permitían scroll de página, lo que hacía que cuando el
contenido crecía, la página completa scrolleara en vez de hacer scroll
interno en el panel de subtítulos. Se agregó `position: fixed; inset: 0`
a `.sala` para que la vista esté anclada al viewport independientemente
del scroll de la página.

**Cambios:**
- `frontend/src/App.css` — `.sala` ahora incluye `position: fixed;
  inset: 0; z-index: 1;` además de `height: 100vh; overflow: hidden`.
  Esto garantiza que la Sala siempre cubra el viewport completo y
  que el scroll interno del panel de subtítulos funcione correctamente
  sin que la página completa scrollee.

**Verificación:**
- `pnpm build` → build OK.

**Notas:**
- El `FinalizarModal` usa `position: fixed; inset: 0` por su cuenta,
  así que sigue funcionando correctamente sobre la Sala fija.
- Las demás vistas (Dashboard, Historial, Login) no se ven afectadas
  porque no usan la clase `.sala`.