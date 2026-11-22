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
  - Usuarios de prueba: Juan Pérez (RUT 12345678-5) y María González (RUT 9876543-3); password `test123`.
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

## 2026-08-05 — `62c0cb9` — Mejoras de UX: feedback de conexión, reproducción de señas y errores visibles
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

## 2026-11-16 — `7e0e796` — Acceso HTTPS por IP local, túnel de Cloudflare y RUT de prueba válidos
**Refs:** Mejora de despliegue (sin spec formal)

**Resumen:** Se confirman cambios de despliegue que estaban sin commitear: acceso a la
PWA desde otros dispositivos por la IP local con HTTPS, publicación opcional mediante
un túnel de Cloudflare y RUT de prueba con dígito verificador válido.

**Cambios:**
- `docker-compose.yml` — `CERT_HOST` configurable desde el entorno; servicio
  `lsch_tunnel` (perfil `cloudflare`) que toma `CLOUDFLARE_TUNNEL_TOKEN` del `.env`.
- `run-cloudflare.ps1` — **nuevo**: valida el token en `.env`, construye y levanta
  backend, frontend y túnel.
- `run.ps1` — construye backend y frontend; instrucciones para confiar en la CA local.
- `frontend/src/views/SalaView.jsx` — con `VITE_WS_URL` vacío, el WebSocket usa el
  mismo origen (`ws://` o `wss://` según la página), necesario detrás de nginx o del túnel.
- `backend/data/seed_glosario.json`, `frontend/src/views/LoginView.jsx` — RUT de
  prueba con DV correcto (`12345678-5`, `9876543-3`); antes el login los rechazaba
  por la validación mod-11 de SPEC-005.
- `README.md` — sección de Cloudflare Tunnel.

**Verificación:**
- `ruff check backend` → All checks passed.
- `pytest backend/tests` → 29/29 passed.
- `pnpm --prefix frontend build` → build OK.
- No se verificó el túnel de Cloudflare.

## 2026-11-16 — `905d5ad` — Specs de cierre del anteproyecto (SPEC-006 a SPEC-009)
**Refs:** `specs/SPEC-006` a `specs/SPEC-009` (Borrador)

**Resumen:** Se redactan cuatro specs a partir de la revisión del prototipo contra la
propuesta aprobada y el informe de avance: transcripción real, glosario piloto y
matching, mediciones de la PoC, y acceso/sesión/saneamiento.

**Cambios:**
- `specs/SPEC-006-asr-real-captura-pcm.md` — **nueva**.
- `specs/SPEC-007-glosario-piloto-clips-ensayo-matching.md` — **nueva**.
- `specs/SPEC-008-mediciones-poc.md` — **nueva**.
- `specs/SPEC-009-acceso-sesion-saneamiento.md` — **nueva**.
- `specs/README.md` — índice, orden recomendado y dependencias.
- Este archivo — hash `7e0e796` registrado en la entrada anterior.

**Verificación:** n/a (commit documental).

---

## 2026-11-17 — `c5106cb` — Transcripción real: captura PCM con AudioWorklet + faster-whisper local
**Refs:** SPEC-006 `specs/SPEC-006-asr-real-captura-pcm.md` (Completada)

**Resumen:** Se reemplazó la captura WebM/Opus (`MediaRecorder`) por captura PCM s16le mono a 16 kHz mediante `AudioWorklet`, se incorporó el segmentador por energía y el proveedor local `FasterWhisperProvider` con carga única por proceso, se corrigió el handler de sala para procesar matching y persistencia solo sobre segmentos finales y vaciar el búfer al finalizar, y se retiró el proveedor roto de Google Cloud Speech.

**Cambios:**
- **Backend — ASR y configuración:**
  - `app/asr/base.py` — `ResultadoASR` ahora incluye `segmento_id`; `StreamingASRProvider` acepta `contexto` opcional (`lang="es"`); eliminada rama `google` (errores listan `whisper | stub`).
  - `app/asr/google_streaming.py` — **eliminado** junto a `google-cloud-speech` en `requirements.txt` y `GOOGLE_APPLICATION_CREDENTIALS` en `config.py`/`.env.example`.
  - `app/asr/segmentador.py` — **nuevo**: `Segmentador` determinista por RMS sobre subtramas de 30 ms (con pre-roll de 240 ms) y `Ventana`.
  - `app/asr/whisper_local.py` — **nuevo**: `FasterWhisperProvider` con `WhisperModel` cacheado por proceso, lock de concurrencia entre salas, fallback `auto` GPU→CPU con `logger.warning`, salto de provisionales ante atraso (> `ASR_PARCIAL_MS`), cierre por falta de tramas (`ASR_SILENCIO_MS`), `vad_filter=True`, `condition_on_previous_text=False`, y `initial_prompt` configurable con `ASR_PROMPT_GLOSARIO`.
  - `app/asr/stub.py` — adopta `segmento_id`, `inicio_ms`, `fin_ms`, parámetro `contexto` y termina limpiamente al cerrarse `audio_iter`.
  - `app/core/config.py`, `backend/.env.example` — añadidas variables `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `ASR_SILENCIO_MS`, `ASR_MAX_SEGMENTO_MS`, `ASR_PARCIAL_MS`, `ASR_FLUSH_TIMEOUT_MS`, `ASR_MAX_TRAMA_BYTES`, `ASR_PROMPT_GLOSARIO`.
  - `app/salas/manager.py`, `app/main.py` — carga inicial del modelo en `lifespan` si `ASR_PROVIDER=whisper`, validación de tramas (longitud par y `<= ASR_MAX_TRAMA_BYTES`, 1 warning/sesión), centinela `None` al recibir `finalizar` con espera de vaciado hasta `ASR_FLUSH_TIMEOUT_MS`, matching y persistencia solo en `estable=True`, y limpieza garantizada de sala y lock por event loop.
- **Backend — Tests (`backend/tests/`):**
  - `conftest.py` — registra `@pytest.mark.modelo` (omitido por defecto).
  - `test_segmentador.py` — **nuevo**: pruebas de `Segmentador` (silencio 30 s, provisional/final, duración máxima, `cerrar`, trama impar), `FasterWhisperProvider` con modelo falso (prompt, descarte de vacíos, timeout sin tramas, omisión de provisionales por atraso, exclusión mutua entre salas, fallback CPU, errores de configuración en español) y prueba de humo `@pytest.mark.modelo`.
  - `test_sala.py` — pruebas de provisional/final sin duplicación ni matching provisional, vaciado al finalizar, rechazo de tramas fuera de contrato y `ASR_PROMPT_GLOSARIO=false`.
- **Frontend — Captura PCM e interfaz:**
  - `frontend/src/audio/pcm-worklet.js` — **nuevo**: `AudioWorkletProcessor` que remuestrea por interpolación lineal a 16 kHz cuando `sampleRate !== 16000`, empaqueta tramas de 1600 muestras (3200 bytes s16le) y calcula RMS.
  - `frontend/src/audio/capturaPcm.js` — **nuevo**: ciclo `iniciar`/`pausar`/`reanudar`/`detener` con limpieza de pistas y `AudioContext`.
  - `frontend/src/views/SalaView.jsx`, `frontend/src/App.css` — reemplazo de `MediaRecorder` por `capturaPcm`, medidor visual de nivel de audio, aviso `"No se detecta audio en el micrófono"` tras 10 s bajo umbral (sin detener sesión y desapareciendo al volver señal), reemplazo de subtítulos por `segment_id`, y espera de `clase_finalizada` antes de cerrar el WebSocket al finalizar.
- **Docker / Nginx / Documentación:**
  - `backend/requirements.txt`, `backend/Dockerfile`, `docker-compose.yml` — `faster-whisper==1.2.*`, `numpy>=1.26,<3`, `libgomp1`, variables `ASR_PROVIDER`/`WHISPER_MODEL`/`WHISPER_DEVICE` y volumen `whisper_cache`.
  - `frontend/nginx.conf`, `frontend/Dockerfile`, `frontend/docker-entrypoint.sh` — `BACKEND_UPSTREAM` configurable (por defecto `backend:8000`).
  - `README.md`, `specs/README.md`, `specs/SPEC-006-asr-real-captura-pcm.md` — compatibilidad verificada en Python 3.14 y estado actualizado.

**Verificación:**
- `ruff check backend` → `All checks passed!`
- `pytest backend/tests` → 45 passed, 1 skipped (`@pytest.mark.modelo`).
- `pytest backend/tests -m modelo` → 1 passed (carga real de `WhisperModel('tiny')` en CUDA).
- `pnpm --prefix frontend build` → OK (45 módulos, PWA generada).
- Prueba adicional: síntesis de voz en español (`Microsoft Helena Desktop`) pasada por `FasterWhisperProvider` (`small`, CUDA) generó provisional + final correctos; prueba en Node de `pcm-worklet.js` a 48 kHz y 44.1 kHz emitió tramas s16le de 3200 bytes con RMS esperado.
- Pendiente por entorno: `docker compose up --build` (daemon Docker apagado) y prueba manual en navegador con micrófono físico.

---

## 2026-11-19 — `7c72e00` — Documentación formal del anteproyecto y guía de defensa del prototipo
**Refs:** `docs/` (commit documental)

**Resumen:** Se incorporaron al repositorio los documentos formales del Anteproyecto (propuesta aprobada e informe de avance hasta el capítulo 4, reemplazando el borrador `.docx`) junto con una guía técnica completa de referencia y defensa para el estado actual del prototipo.

**Cambios:**
- `docs/2026_2_PROP_CINF_AP_ESPI___A_Gutierrez.pdf` — **agregado**: propuesta formal aprobada del proyecto de título (cronograma AP y PT).
- `docs/ICINF-AP-Avance-Espinoza-Gutierrez.pdf` — **agregado**: informe de avance hasta el capítulo 4 (requerimientos RF/RNF/RN/CA y factibilidad).
- `docs/Propuesta_Proyecto_Titulo.docx` — **eliminado** (reemplazado por la versión PDF aprobada).
- `docs/documentacion_prototipo_defensa.md` — **nuevo**: documentación técnica detallada de arquitectura, decisiones, módulos, contratos API/WebSocket, despliegue, verificación, limitaciones y banco de preguntas frecuentes de defensa.
- Este archivo — hash `c5106cb` registrado en la entrada de SPEC-006.

**Verificación:** n/a (commit documental; contenido contrastado directamente contra el código vigente tras `c5106cb`).

---

## 2026-11-19 — `04c6c7f` — Congelamiento de partición de prueba protegida (`ml/datos/`)
**Refs:** SPEC-008 `specs/SPEC-008-mediciones-poc.md` (R11–R12, previo a SPEC-007)

**Resumen:** Se redactó y congeló la partición de prueba protegida (`66` frases) junto a la partición de ajuste (`36` frases) en `ml/datos/frases_anotadas.jsonl` antes de definir formas y bloqueos del glosario piloto en SPEC-007, evitando sesgo de evaluación (`RNF04`).

**Cambios:**
- `ml/datos/frases_anotadas.jsonl` — **nuevo**: 102 frases anotadas (66 `prueba`, 36 `ajuste`) para los 15 conceptos propuestos de `INF-221`.
- `ml/datos/README.md` — **nuevo**: origen, criterio y separación temporal de las particiones.
- Este archivo — hash `7c72e00` registrado en la entrada anterior.

**Verificación:** validación JSONL por script (`{'prueba': 66, 'ajuste': 36}`, todos los conceptos pertenecen al inventario de 15 términos).

---

## 2026-11-19 — `4783e1b` — Glosario piloto provisional, clips de ensayo y motor de coincidencia
**Refs:** SPEC-007 `specs/SPEC-007-glosario-piloto-clips-ensayo-matching.md` (Completada)

**Resumen:** Se redefinió el glosario de la PoC en torno a un único curso piloto provisional (`INF-221`, 15 conceptos) más un curso de control sin términos (`MAT-101`), se generaron y versionaron 15 clips MP4 de ensayo sin personas, se reemplazaron los lemas manuales por un índice automático con doble clave (lemas + formas) y bloqueos con registro de abstenciones, y se incorporó una cola acotada en el cliente sin bucle ni truncamiento a 4 segundos.

**Cambios:**
- **Seed, esquema y clips (`backend/data/`, `backend/scripts/`, `.gitignore`):**
  - `schema.sql`, `app/core/db.py` — `termino` reemplaza `lema`/`n_palabras` por `formas_json`, `bloqueos_json` y `estado` (`ensayo | publicado | retirado`); `evento_clase` añade `abstenciones_json` con migración automática.
  - `seed_glosario.json`, `scripts/seed_glosario.py` — curso piloto provisional `INF-221` (*Estructuras de Datos*, 15 conceptos en `estado="ensayo"`) y curso de control `MAT-101` sin términos; nota de provisionalidad sin acuerdo con PIESDI; validación de índice sin claves ambiguas.
  - `scripts/generar_clips_ensayo.py` — **nuevo**: genera MP4 H.264 640×360 de 3 s con `ffmpeg` (`"CLIP DE ENSAYO"` + concepto, sin personas, sin sobrescribir salvo `--forzar`).
  - `.gitignore` — retirada `backend/data/videos_senas/` y versionados los 15 clips de ensayo (eliminados los 12 placeholders de 28 bytes).
- **Motor NLP y sala (`backend/app/`):**
  - `glossary/indice.py` — **nuevo**: `construir_indice()` (doble clave lema/forma, omite retirados, detecta claves ambiguas y colisiones de bloqueos) y `obtener_indice_curso()` con caché por `(DB_PATH, curso_id)`.
  - `glossary/matching.py`, `glossary/repository.py` — `buscar_terminos()` con doble clave y n-gramas dinámicos, recuperación de `texto_detectado` original y `Coincidencias(senas, abstenciones)` (bloqueos conservan preposiciones/artículos como `"de memoria"`).
  - `salas/manager.py`, `historial/repository.py`, `main.py`, `asr/stub.py` — `RoomState.indice`, persistencia de `abstenciones_json` sin difundirlas por WebSocket, filtro de retirados en prompt Whisper y frases de stub adaptadas a `INF-221`.
- **Frontend (`frontend/src/`):**
  - `hooks/useColaSenas.js` — **nuevo**: cola secuencial de hasta 3 pendientes (descarta la más antigua sumando `omitidas`) y supresión de menciones repetidas dentro de 20 s tras finalizar.
  - `components/SenaPlayer.jsx` — reproducción única sin `loop`, avance por `onEnded` (con fallback si `onError`), y rótulo `"Clip de ensayo · sin validación lingüística"` para `estado="ensayo"`.
  - `views/SalaView.jsx`, `views/ClaseDetailView.jsx`, `App.css` — integración de `useColaSenas`, contador visible `"disponibles en el historial"`, resaltado por `texto_detectado`, y replay secuencial único.
- **Tests y documentación (`backend/tests/`, `README.md`, `docs/`):**
  - `test_indice.py`, `test_seed.py` — **nuevos**; `test_matching.py` reescrito; `test_schema.py`, `test_sala.py` y `test_historial.py` actualizados.
  - `README.md`, `specs/README.md`, `specs/SPEC-007-...md` — declaración explícita de provisionalidad y estado de la spec.
  - `docs/documentacion_prototipo_defensa.md` — actualizada hasta `SPEC-007` y el congelamiento previo de la partición `"prueba"` (`04c6c7f`).

**Verificación:**
- `ruff check backend` → `All checks passed!`
- `pytest backend/tests` → 54 passed, 1 skipped (`@pytest.mark.modelo`).
- `pnpm --prefix frontend build` → OK (46 módulos, PWA generada).
- Pruebas extra: `generar_clips_ensayo.py` (15 MP4 H.264 640×360 3 s validados con `ffprobe`), `seed_glosario.py`, y simulación en Node de `useColaSenas` (cola máx 3, descartes, ventana 20 s).
- Pendiente por entorno: verificación en clon limpio con `docker compose build` (daemon Docker apagado) y prueba manual interactiva en navegador.

---

## 2026-11-20 — `0a8209c` — SPEC-008 (1/2): instrumentación de métricas, scripts de medición y corpus propio
**Refs:** SPEC-008 `specs/SPEC-008-mediciones-poc.md` (R1–R16, R18–R19; parcial)

**Resumen:** Se implementó la instrumentación de latencias por segmento en el servidor, se retiraron `evaluation/logging.py` y las tablas heredadas `sesion`/`segmento`, se crearon los scripts reproducibles de evaluación (`normalizacion.py`, `evaluar_asr.py`, `evaluar_matching.py`, `prueba_carga.py`) con sus pruebas y dependencias separadas en `ml/`, y se ensamblaron y revisaron los dos audios propios del autor (`clase_01_cerca.wav` y `clase_02_cerca.wav`) junto a sus guiones y referencias.

**Cambios:**
- **Backend — Instrumentación y esquema (`backend/`):**
  - `data/schema.sql`, `app/core/db.py`, `scripts/seed_glosario.py` — reemplazo de tablas `sesion` y `segmento` por `metrica_segmento` (limpieza también al inicializar esquema).
  - `app/evaluation/metricas.py` — **nuevo** (reemplaza a la eliminada `evaluation/logging.py`): `registrar_segmento()` controlada por `METRICAS` (`True` por defecto en `app/core/config.py` y `.env.example`).
  - `app/asr/base.py`, `app/asr/segmentador.py`, `app/asr/stub.py`, `app/asr/whisper_local.py` — `Ventana` suma `llegada_fin_ms` y `ResultadoASR` suma `llegada_fin_ms` y `asr_ms` (`0` en stub; en `FasterWhisperProvider` se marca la llegada de tramas con reloj monotónico en `_pump()` y se mide duración de inferencia).
  - `app/salas/manager.py`, `app/main.py` — `RoomManager.broadcast()` retorna receptores conectados; el evento `"segmento"` agrega `"servidor_ms"` (epoch ms al difundir); `ws_sala` mide `nlp_ms` y `emitido_ms` con reloj monotónico y persiste métricas de segmentos finales en `metrica_segmento`.
  - `tests/test_schema.py`, `tests/test_segmentador.py`, `tests/test_sala.py` — pruebas de `metrica_segmento`, eliminación de tablas obsoletas, `llegada_fin_ms`, `asr_ms`, `servidor_ms` y `METRICAS=false`.
- **ML, corpus y configuración (`ml/`, `.gitignore`, `AGENTS.md`):**
  - `ml/requirements.txt` — `jiwer`, `psutil`, `websockets` separadas de `backend/requirements.txt`.
  - `.gitignore` — ignora `ml/datos/audio/` y `audios-pruebas/`.
  - `AGENTS.md` — incorpora `ruff check backend ml` y `pytest ml/tests` a la verificación mínima.
  - `ml/comun.py`, `ml/normalizacion.py`, `ml/evaluar_matching.py`, `ml/evaluar_asr.py`, `ml/prueba_carga.py` — implementación completa + suite en `ml/tests/`.
  - `ml/datos/guiones/clase_01.txt`, `ml/datos/guiones/clase_02.txt`, `ml/datos/referencias/`, `ml/datos/README.md` — guiones del curso `INF-221`, referencias revisadas contra los 26 tramos `.m4a` ensamblados (`6 min 44.65 s` y `6 min 54.21 s`) y fichas con brecha declarada respecto a la condición de ruido/distancia.
- **Mediciones preliminares acumuladas en `ml/resultados/`:**
  - `carga_escenario_A_stub_20261119_212452.json` y `carga_escenario_B_stub_20261119_212954.json` (pruebas completas de 5 minutos: `0` perdidos/duplicados/fuera de orden).

**Verificación:**
- `ruff check backend ml` → `All checks passed!`
- `pytest backend/tests` → `59 passed, 1 skipped` (`@pytest.mark.modelo`).
- `pytest ml/tests` → `11 passed`.
- `pnpm --prefix frontend build` → OK (46 módulos).
- `git status --short ml/datos/audio` → vacío (sin audios versionados).

**Notas:**
- Próximo paso (2/2): ejecutar la matriz de `ml/evaluar_asr.py` a ritmo real sobre ambos audios ensamblados, actualizar `matching` sobre commit limpio y consolidar `docs/resultados_poc.md`.

---

## 2026-11-21 — `ed14036` — SPEC-008 (2/2): resultados medidos de PoC, informe técnico y documentación sincronizada
**Refs:** SPEC-008 `specs/SPEC-008-mediciones-poc.md` (Completada con brecha acústica R9 declarada)

**Resumen:** Se ejecutó la batería completa de evaluación de matching y transcripción ASR a ritmo real sobre las dos grabaciones del autor bajo el commit `0a8209c`, se consolidaron las cifras trazables y sus limitaciones en `docs/resultados_poc.md`, y se actualizó la documentación del prototipo y las especificaciones.

**Cambios:**
- **`ml/resultados/` — Evidencia JSON trazable al commit `0a8209c`:**
  - `matching_ajuste_20261121_005927.json` (`36` frases: `TP=40, FP=0, FN=0`) y `matching_prueba_20261121_005931.json` (`66` frases protegidas: `TP=79, FP=3, FN=2`, Precisión `96.34 %`, Recuperación `97.53 %`, compuestos `100 %`).
  - `asr_clase_01_cerca_small_cuda_prompt_20261121_010621.json` y `asr_clase_02_cerca_small_cuda_prompt_20261121_011321.json` (`1x` ritmo real en GPU RTX 3050: WER `3.16 %` y `3.56 %`, glosario `100 %` y `95.71 %`, `RTF total 0.2841–0.3069`, latencia servidor p95 `804.55 ms` y `821.05 ms`).
  - `asr_clase_01_cerca_small_cuda_sinprompt_20261121_011350.json` y `asr_clase_02_cerca_small_cuda_sinprompt_20261121_011418.json` (`--rapido`: ablación sin prompt — WER `3.97 %` y `5.01 %`, glosario `94.74 %` y `80.00 %`).
  - `asr_clase_01_cerca_base_cpu_prompt_20261121_012108.json` y `asr_clase_02_cerca_base_cpu_prompt_20261121_012807.json` (`1x` ritmo real en CPU: WER `8.25 %` y `9.45 %`, glosario `96.49 %` y `87.14 %`, `RTF total 0.7040–0.7091`, p95 `1908.35 ms` y `2250.70 ms`).
- **Documentación y specs:**
  - `docs/resultados_poc.md` — **nuevo**: condiciones de medición, tablas frente a `RNF01`, `RNF03`, `RNF04` y `RNF06`, trazabilidad JSON/commit, desglose de errores, limitaciones (voz única leída, sin evaluación con usuarios y brecha pendiente de audio con ruido/distancia) y configuración recomendada.
  - `docs/documentacion_prototipo_defensa.md`, `README.md`, `specs/SPEC-008-mediciones-poc.md`, `specs/README.md` — actualización de módulos, esquema (`metrica_segmento`), contrato WS (`servidor_ms`), resultados y estado de `SPEC-008`.

**Verificación:**
- `ruff check backend ml` → `All checks passed!`
- `pytest backend/tests` → `59 passed, 1 skipped` (`@pytest.mark.modelo`).
- `pytest ml/tests` → `11 passed`.
- `pnpm --prefix frontend build` → OK (46 módulos).
- `git status --short ml/datos/audio` → vacío (sin audios versionados).

**Notas:**
- Próxima spec recomendada para cerrar el Anteproyecto: `SPEC-009` (`specs/SPEC-009-acceso-sesion-saneamiento.md`).

---

## 2026-11-21 — `b809773` — Guía explicativa en lenguaje simple sobre las pruebas de la PoC
**Refs:** `docs/explicacion_pruebas_poc.md`, `docs/resultados_poc.md` (commit documental)

**Resumen:** Se añadió una guía sin tecnicismos en `docs/explicacion_pruebas_poc.md` explicando en qué consistió cada prueba de la PoC (ASR, mapeo NLP y carga WebSocket), qué significan sus métricas y qué limitaciones deben declararse con transparencia en defensa.

**Cambios:**
- `docs/explicacion_pruebas_poc.md` — **nuevo**: explicación paso a paso en lenguaje cotidiano de WER, recuperación de términos del glosario, `RTF`, latencia `p95`, partición protegida `"prueba"`, escenarios de carga a `20` receptores y tabla resumen con límites de alcance.
- Este archivo — hash `ed14036` registrado en la entrada anterior.

**Verificación:** n/a (commit documental; todas las cifras contrastadas contra `docs/resultados_poc.md`).

---

## 2026-11-22 — `3df46e1` — Mejoras tras prueba real en vivo: captura PCM nativa y Replay continuo sin tiempos muertos
**Refs:** hallazgos de prueba manual en vivo (`SPEC-006`, `SPEC-007`)

**Resumen:** Tras la primera prueba interactiva con micrófono real en Zen Browser (Windows 11), se corrigió la compatibilidad de captura PCM usando frecuencia nativa del hardware sin cancelación de eco conflictiva, y se rediseñó el modo Replay para respetar Play/Pausa real, aplicar velocidad a los videos y avanzar continuamente al ritmo de lectura y señas sin silencios muertos.

**Cambios:**
- `frontend/src/audio/capturaPcm.js` — usa `new AudioContext()` a frecuencia nativa (delegando el remuestreo a `pcm-worklet.js`) y `echoCancellation: false` / `noiseSuppression: false` con `autoGainControl: true`, evitando bloqueos WASAPI/Bluetooth y Firefox/Zen.
- `frontend/src/components/SenaPlayer.jsx` — agrega props opcionales `reproduciendo = true` y `velocidad = 1` para controlar `play()`/`pause()`, `playbackRate` y el fallback de error únicamente en reproducción activa (compatible sin cambios con `SalaView.jsx`).
- `frontend/src/views/ClaseDetailView.jsx` — corrige el bug que reproducía clips automáticamente estando pausado, memoriza `estables` con `useMemo` para evitar reinicios de temporizador, reemplaza la espera por diferencia de `timestamp_ms` por avance continuo coordinado entre tiempo mínimo de lectura proporcional al texto (`2–5,5 s` base) y término completo de todas las señas del segmento (escalado por `1x / 1.5x / 2x`), muestra estado real (`En pausa` / `Reproduciendo` / `Finalizado`) más marca de tiempo original de referencia y permite saltar a cualquier diálogo ya visible haciendo clic.
- `docs/documentacion_prototipo_defensa.md` — sincroniza las secciones §6.2 y §6.3 con los cambios de captura y Replay.

**Verificación:**
- `ruff check backend ml` → `All checks passed!`
- `pytest backend/tests` → `59 passed, 1 skipped` (`@pytest.mark.modelo`).
- `pytest ml/tests` → `11 passed`.
- `pnpm --prefix frontend build` → OK (46 módulos).

---

## 2026-11-22 — SPEC-009: acceso por inscripción, permiso de captura, estado de sesión, seguridad y saneamiento
**Refs:** SPEC-009 `specs/SPEC-009-acceso-sesion-saneamiento.md` (R1–R25, Completada)

**Resumen:** Se cerraron las brechas de control de acceso, estado de sesión, seguridad y mantenimiento entre el prototipo y la especificación del informe: autorización por inscripción en salas/glosario/estado/clips, permiso explícito `puede_capturar`, pausa compartida en servidor con discontinuidades y cierre `explicito|timeout`, aviso previo de condiciones, contraseñas con `scrypt`, JWT de 480 min sin secreto fijo, CORS acotado, limpieza de código sin uso y documentación vigente.

**Cambios:**
- **Esquema, permisos y seguridad (`backend/`):**
  - `data/schema.sql`, `app/core/db.py` — agrega `inscripcion.puede_capturar`, `clase.cierre`, `clase.condiciones_confirmadas` y `evento_clase.tipo` con migraciones idempotentes.
  - `app/core/permisos.py` — **nuevo**: `resolver_sala`, `inscripcion`, `inscripcion_en_curso`, `exigir_inscripcion` y `exigir_inscripcion_curso`.
  - `app/core/auth.py`, `app/auth/routes.py` — derivación de contraseñas con `hashlib.scrypt` y sal aleatoria de 16 bytes (`scrypt$16384$8$1$...`), verificación con `hmac.compare_digest` y vigencia de JWT según `JWT_EXP_MIN` (`480`).
  - `app/core/config.py`, `.env.example`, `docker-compose.yml` — elimina `AUTH_PROVIDER`, deja `JWT_SECRET` vacío (genera secreto aleatorio al arrancar con `logger.warning`), agrega `JWT_EXP_MIN=480` y `CORS_ORIGINS=http://localhost:5173`.
  - `data/seed_glosario.json`, `scripts/seed_glosario.py` — tres usuarios de prueba (`12345678-5` con captura, `9876543-3` oyente sin captura, `11111111-1` solo en `MAT-101` para pruebas negativas), reutilizando `app.core.auth.hash_password`.
- **Clips protegidos, estado de sesión y limpieza (`backend/`, `frontend/nginx.conf`, `ml/`):**
  - `app/glossary/repository.py`, `app/main.py`, `frontend/nginx.conf` — agrega `GET /api/cursos/{curso_id}/senas/{termino_id}/video` (401/403/404/200 `video/mp4`, ruta desde BD), retira el montaje público `/data/videos_senas` y `location /data/`, elimina `/ws/echo`, `list_cursos`, `insert_curso` e `insert_termino`, y acota `CORSMiddleware` con `allow_credentials=False`.
  - `app/salas/manager.py`, `app/asr/whisper_local.py`, `app/main.py` — elimina `RoomState.timeline` e `inicio_ms`; mantiene `RoomState.estado` (`activa|pausada`), maneja `pausar`/`reanudar`, descarta tramas en pausa, vacía el segmento abierto al pausar (`b""` en `FasterWhisperProvider`), envía `estado_sesion` al conectarse un oyente, exige `condiciones=1` al emisor y registra discontinuidades (`pausa`, `reanudacion`, `desconexion`) más `cierre` (`explicito|timeout`).
  - `app/historial/repository.py`, `app/historial/routes.py` — reemplaza `usuario_participa` por `app.core.permisos.inscripcion`, expone `cierre`, `tipo` y `puede_capturar` (sin `rut_emisor`), y calcula `palabras`/`preview` solo sobre `tipo='segmento'`.
  - `ml/prueba_carga.py`, `ml/comun.py` — compatibilidad con `&condiciones=1` y rutas protegidas de clips.
- **Frontend (`frontend/src/`):**
  - `api/clips.js` — **nuevo**: descarga clips con `Authorization: Bearer`, caché en `Map` de object URLs, `precargar(glosario)` sin bloquear y `liberarClips()` al salir.
  - `api/cliente.js` — elimina `fetchCursos`, adjunta `error.status` y propaga `403` en `fetchSalaEstado`.
  - `components/CondicionesModal.jsx` — **nuevo**: aviso informativo y confirmación obligatoria previa a solicitar el micrófono (`R14`).
  - `components/SenaPlayer.jsx` — reproduce clips desde URL de objeto autenticada (`obtenerClip`).
  - `views/DashboardView.jsx`, `views/SalaView.jsx` — UI condicional según `puede_capturar`, precarga de clips al entrar a sala, modal de condiciones + `&condiciones=1`, acciones WS `pausar`/`reanudar` y banner `"Transmisión en pausa"`.
  - `views/HistorialView.jsx`, `views/ClaseDetailView.jsx`, `App.css` — insignia `"Registro incompleto"` en cierres `timeout`, separadores de pausa/reanudación/desconexión con marca de tiempo en Apunte (omitidos por Replay) y liberación de blob URLs al desmontar.
- **Pruebas y documentación:**
  - `backend/tests/` (`test_auth.py`, `test_historial.py`, `test_sala.py`, `test_schema.py`, `test_seed.py`, `test_segmentador.py`) — cobertura completa de R1–R24 con secretos de ≥ 32 bytes.
  - `docs/decisiones_tecnicas.md` — **nuevo**: tabla de divergencias entre informe/plan y prototipo.
  - `README.md`, `AGENTS.md`, `specs/SPEC-009-acceso-sesion-saneamiento.md`, `specs/README.md`, `docs/documentacion_prototipo_defensa.md` — actualizados al estado real post `SPEC-009`.

**Verificación:**
- `ruff check backend ml` → `All checks passed!`
- `pytest backend/tests` → `70 passed, 1 skipped` (`@pytest.mark.modelo`).
- `pytest ml/tests` → `11 passed`.
- `pnpm --prefix frontend build` → OK (48 módulos).
- `python backend/scripts/seed_glosario.py` → OK (2 cursos, 15 términos, 3 usuarios, 5 inscripciones).
